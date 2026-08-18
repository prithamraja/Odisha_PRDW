"""
What the user's next message MEANS when the system is holding a paused question.

`ContextStore.take_pending` is one-shot: the paused question is consumed before
anyone knows whether the reply answered it. The original code then validated the
reply strictly against the missing slot's entity type and, on failure, silently
dropped the pause and routed the bare fragment on its own. Two reasonable
answers are destroyed by that:

  "Which one do you mean?" (candidates listed BY DISTRICT) → "Anantapur"
      — a district is not a farmer_name, so the farmer question vanished.
  "For which crop?" → "all crops"
      — a scope-widening answer the resume path had no way to represent; the
        fragment routed standalone and confidently served an unrelated template.

Everything here is deterministic — closed vocabulary and registry lookups, no
LLM. The caller (main.py's /query) turns a Resolution into a response; nothing
in this module executes SQL or talks to a model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from .config import MAX_CLARIFY_OPTIONS
from .entity_validator import _STATE_LEVEL_TERMS, _GEO_TYPES
from .models import Chip, EntityCandidate, PendingClarification
from .zones import candidate_chips, candidate_label, candidate_replies

# "Venkateswarlu Devi of Chittoor" — a reply that names a person by where they
# are. The roster, not this module, decides which one it is.
_PLACE_REF_RE = re.compile(r"^(?P<name>.+?)\s+of\s+(?P<place>.+)$", re.IGNORECASE)

# A reply naming a candidate has to be recognised from a name the user just read
# off the screen, so typos are in scope — but the pool is four names, not a
# 300k-row roster, and picking the wrong person is unrecoverable. High bar.
_CANDIDATE_FUZZY_THRESHOLD = 88

RESUME            = "resume"             # answer the paused slot with `value`
REASK             = "reask"              # ask again; `pending` must be re-stored
SERVE_ALTERNATIVE = "serve_alternative"  # answer `query_id` instead
FALLTHROUGH       = "fallthrough"        # not an answer — route as a new message


@dataclass
class Resolution:
    kind:     str
    value:    str | None = None                     # RESUME: the slot value
    query_id: str | None = None                     # SERVE_ALTERNATIVE: target
    prompt:   str | None = None                     # REASK: what to ask
    reason:   str = "unknown_entity"                # REASK: Clarification.reason
    options:  list[Chip] = field(default_factory=list)
    pending:  PendingClarification | None = None    # REASK: re-store this


# ── Scope-widening replies ────────────────────────────────────────────────────

# "Don't filter by that at all" — the answer a slot cannot hold. Closed set:
# anything outside it is a value, not a scope instruction.
_SCOPE_TERMS = {
    "all", "any", "every", "everything", "overall",
    "doesn't matter", "doesnt matter", "does not matter", "no filter",
    "all of them", "across all", "any of them", "no preference",
}

_TRAILING_JUNK = " \t?.!,;:"


def _normalize(reply: str) -> str:
    return " ".join(str(reply).strip().strip(_TRAILING_JUNK).lower().split())


def _slot_nouns(slot_name: str) -> set[str]:
    """Naive singular/plural forms of the slot's noun, for stripping off a
    scope phrase: 'all crops' → 'all', 'any crop' → 'any'."""
    words = slot_name.replace("_", " ").strip().lower()
    nouns = {words}
    if words:
        nouns.add(words.split()[-1])
    for noun in list(nouns):
        nouns.add(noun + "s")
        if noun.endswith("s"):
            nouns.add(noun[:-1])
    return {n for n in nouns if n}


def is_scope_widening_reply(reply: str, slot_name: str) -> bool:
    """True when the reply says 'don't narrow by this' rather than naming a value.

    Geography adds the validator's own state-level scope markers, shared rather
    than duplicated so 'statewide' can never mean one thing to the validator and
    another here.
    """
    text = _normalize(reply)
    if not text:
        return False
    if text in _SCOPE_TERMS:
        return True
    if slot_name in _GEO_TYPES and text in _STATE_LEVEL_TERMS:
        return True

    # "all crops" / "across all crops" / "any crop" — the scope word plus the
    # slot's own noun, which carries no information beyond what we asked for.
    for noun in _slot_nouns(slot_name):
        if text.endswith(" " + noun):
            head = text[: -(len(noun) + 1)].strip()
            if head in _SCOPE_TERMS:
                return True
    return False


# ── Candidate matching ────────────────────────────────────────────────────────

def _match_candidate(reply: str, candidates: list[EntityCandidate]) -> str | None:
    """The reference of the candidate this reply picks, or None.

    Matching on the bare NAME is not enough once candidates can share one: four
    people called Lakshmi Devi would all match it and the first would win — a
    silent wrong-person pick, which is the defect in a new place. A name that
    several candidates answer to is therefore treated as NO match, so the caller
    narrows (by district) or asks again instead of guessing.
    """
    text = _normalize(reply)
    references = candidate_replies(candidates)

    for reference in references:
        if _normalize(reference) == text:
            return reference

    # A reply that already names a place — what a chip sends once we have
    # narrowed by district — resumes verbatim. Its head names one of these
    # candidates and the roster resolves the place, narrowing again or asking
    # once more, but never guessing which namesake was meant.
    place_ref = _PLACE_REF_RE.match(str(reply).strip())
    if place_ref and any(
        _normalize(c.name) == _normalize(place_ref.group("name")) for c in candidates
    ):
        return str(reply).strip()

    # Matching happens on the NAME, which is what a user types, and the
    # reference is what comes back — the place we added is ours, not theirs, and
    # scoring against it would only blur the comparison.
    names = [_normalize(c.name) for c in candidates]
    named = [r for n, r in zip(names, references) if n == text]
    if len(named) == 1:
        return named[0]
    if named:
        return None   # the shared name IS the ambiguity — never pick one for them

    match = process.extractOne(
        text, names, scorer=fuzz.WRatio, score_cutoff=_CANDIDATE_FUZZY_THRESHOLD
    )
    if match and names.count(match[0]) == 1:
        return references[match[2]]
    return None


def _candidates_in_district(
    district: str, candidates: list[EntityCandidate]
) -> list[EntityCandidate]:
    """The candidates in that district, each scoped down to it.

    Scoped, not merely filtered: the district the user just named is now the
    only one in play, and it is the sole thing distinguishing a name candidate
    from its namesakes elsewhere. Keeping the full list would drop that choice
    on the next round and re-offer people already ruled out.
    """
    wanted = district.strip().lower()
    return [
        c.model_copy(update={"districts": [district]})
        for c in candidates
        if any(d.strip().lower() == wanted for d in c.districts)
    ]


def _resolve_candidates(
    reply: str, pending: PendingClarification, validator
) -> Resolution | None:
    """The disambiguation prompt named people by district, so a district reply is
    exactly what it invited. Returns None when the reply is neither."""
    candidates = pending.candidates
    reference = _match_candidate(reply, candidates)
    if reference is not None:
        # The REFERENCE, not the name: resuming with the name the user was just
        # asked to disambiguate re-raises the same clarify on the next turn.
        return Resolution(kind=RESUME, value=reference)

    try:
        district = validator.validate(reply, "district").resolved_value
    except Exception:
        return None

    narrowed = _candidates_in_district(district, candidates)
    if len(narrowed) == 1:
        return Resolution(kind=RESUME, value=candidate_replies(narrowed)[0])
    if len(narrowed) > 1:
        # Still ambiguous — narrow and ask again, keeping the paused question
        # alive. Losing it here is the whole defect this module exists to fix.
        # Two of the four Lakshmi Devis are both in Nellore, so this branch has
        # to name them by something a district reply did not already say.
        return Resolution(
            kind=REASK,
            prompt=(
                f"Several of them are in {district}: "
                + "; ".join(candidate_label(c) for c in narrowed)
                + ". Which one do you mean?"
            ),
            options=candidate_chips(narrowed),
            pending=pending.model_copy(update={"candidates": narrowed}, deep=True),
        )
    return None


# ── Scope handling ────────────────────────────────────────────────────────────

def _example_chips(
    pending: PendingClarification, template: dict | None, validator
) -> list[Chip]:
    """Example values for the slot, as complete catalog questions so a tap routes
    normally instead of re-entering the pause."""
    try:
        values = validator.registry_values(pending.slot_type, by_frequency=True)
    except TypeError:
        values = validator.registry_values(pending.slot_type)
    except Exception:
        return []
    if not values or template is None:
        return []

    chips: list[Chip] = []
    for value in values[:MAX_CLARIFY_OPTIONS]:
        try:
            question = template["abstract_question"].format(
                **{**pending.filled, pending.missing_slot: value}
            )
        except (KeyError, IndexError):
            return []   # other slots still unfilled — a half-filled chip is worse
        chips.append(Chip(label=value, send_text=question))
    return chips


def _resolve_scope_widening(
    pending: PendingClarification, template_map: dict[str, dict], validator
) -> Resolution:
    template = template_map.get(pending.query_id)
    slot_words = pending.missing_slot.replace("_", " ")

    # A template may declare the broader question its slot narrows. Serve that
    # when every parameter it needs is already resolved — its own
    # query_description then keeps the answer honest about what was answered.
    alternative_id = (template or {}).get("scope_alternative")
    alternative = template_map.get(alternative_id) if alternative_id else None
    if alternative is not None:
        needed = {s["name"] for s in alternative["param_slots"]}
        if needed <= set(pending.filled):
            return Resolution(kind=SERVE_ALTERNATIVE, query_id=alternative_id)

    return Resolution(
        kind=REASK,
        reason="missing_parameter",
        prompt=(
            f"This question is answered one {slot_words} at a time — "
            f"which {slot_words}?"
        ),
        options=_example_chips(pending, template, validator),
        pending=pending,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def resolve_pending_reply(
    reply: str,
    pending: PendingClarification,
    validator,
    *,
    template_map: dict[str, dict] | None = None,
) -> Resolution:
    """Decide what a reply to a paused question means, in this order:

      1. it picks one of the candidates we listed (by name, or by the district
         we used to tell them apart);
      2. it widens the scope ("all crops") — serve the broader question if the
         catalog declares one, else re-ask and keep the pause;
      3. it validates as the slot we asked for;
      4. none of the above — ask once more if it is short enough to be a bad
         answer rather than a new question, otherwise route it as a new message.
    """
    if pending.candidates:
        resolved = _resolve_candidates(reply, pending, validator)
        if resolved is not None:
            return resolved

    if is_scope_widening_reply(reply, pending.missing_slot):
        return _resolve_scope_widening(pending, template_map or {}, validator)

    answer = str(reply).strip().strip(_TRAILING_JUNK)
    try:
        validator.validate(answer, pending.slot_type)
    except Exception:
        return _unusable_reply(answer, pending)
    return Resolution(kind=RESUME, value=answer)


# A reply this short, straight after we asked a question, is far more likely to
# be a bad answer than a new question — and routing it standalone is how an
# unrelated template captures it and answers confidently. Above this length we
# take the user at their word and route normally.
_RETRY_MAX_WORDS = 3


def _unusable_reply(reply: str, pending: PendingClarification) -> Resolution:
    """The reply answers neither the slot nor anything else we recognise.

    Serving whatever a confident matcher makes of a two-word fragment is the
    general form of the bug this module exists to fix, so ask once more instead.
    Exactly once: `retried` makes the second attempt fall through, so changing
    the subject costs one extra turn and never more. The escape chip makes even
    that turn skippable — it re-sends the same words as a chip tap, which
    bypasses the pending resume and routes normally.
    """
    words = len(reply.split())
    if pending.retried or not 0 < words <= _RETRY_MAX_WORDS:
        return Resolution(kind=FALLTHROUGH)

    slot_words = pending.missing_slot.replace("_", " ")
    escape = Chip(label=f'Ask "{reply}" instead', send_text=reply)
    return Resolution(
        kind=REASK,
        reason="missing_parameter",
        prompt=(
            f'I still need a {slot_words} to answer "{pending.original_query}". '
            f"Which {slot_words}?"
        ),
        # A disambiguation pause still knows who the choices are — re-offering
        # them beats asking an open question the user already failed to answer.
        options=candidate_chips(pending.candidates) + [escape],
        pending=pending.model_copy(update={"retried": True}, deep=True),
    )
