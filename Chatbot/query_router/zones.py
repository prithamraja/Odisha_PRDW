"""
Three-zone confidence handling (spec Section 6).

Retrieval scores are partitioned by two tunable thresholds:
  proceed   — best candidate is clearly the interpretation; execute (happy path)
  ambiguous — several templates score alike; pause and let the user pick
  no_match  — nothing plausible; say so and offer the nearest catalog questions

Every chip built here carries send_text that routes back through the normal
matcher, so a tap can only ever lead to an executable catalog question.
"""
import re

from .config import (
    CLARIFY_SCORE_MARGIN,
    CLARIFY_UPPER_THRESHOLD,
    NO_MATCH_LOWER_THRESHOLD,
)
from .entity_validator import mask_aadhaar
from .models import Chip, EntityCandidate

ScoredCandidate = tuple[str, str, float]  # (query_id, display_question, cosine)


def zone(scores: list[float]) -> str:
    """'proceed' | 'ambiguous' | 'no_match' for a descending score list."""
    if not scores or scores[0] < NO_MATCH_LOWER_THRESHOLD:
        return "no_match"
    if (
        len(scores) > 1
        and scores[0] < CLARIFY_UPPER_THRESHOLD
        and scores[0] - scores[1] < CLARIFY_SCORE_MARGIN
    ):
        return "ambiguous"
    return "proceed"


# How an UNFILLED slot reads in a chip. The naive "a " + slot_name produces
# "a farmer name", "a aadhaar", "a top n" — text a user is being invited to tap
# but which reads as a placeholder leaking through, so each slot gets a phrase
# an English speaker would actually say.
_SLOT_PHRASES: dict[str, str] = {
    "farmer_name":       "a farmer",
    "aadhaar":           "an Aadhaar number",
    "district":          "a district",
    "mandal":            "a mandal",
    "village":           "a village",
    "crop":              "a crop",
    "scheme":            "a scheme",
    "scheme_2":          "another scheme",
    "season":            "a season",
    "top_n":             "N",
    "scheme_count":      "N",
    "social_category":   "a social category",
    "social_category_2": "another social category",
    "crop_year":         "a year",
}

_VOWELS = "aeiou"


def _slot_phrase(name: str) -> str:
    """Readable stand-in for an unfilled slot."""
    phrase = _SLOT_PHRASES.get(name)
    if phrase is not None:
        return phrase
    words = name.replace("_", " ")
    return ("an " if words[:1].lower() in _VOWELS else "a ") + words


def _readable(question: str, fill: dict[str, str] | None = None) -> str:
    """'input subsidy in {district}?' -> 'input subsidy in Krishna?' when the
    value is known from the user's own utterance, else 'input subsidy in a
    district?' (either way the text stays routable).

    Many AP questions already name the unit after the slot ('in {mandal}
    mandal'), so the placeholder swallows a following repeat of its own name
    rather than emitting 'a mandal mandal'."""
    def _sub(match: re.Match) -> str:
        name = match.group(1)
        unit = match.group(2) or ""      # ' mandal' in 'in {mandal} mandal'
        if fill and name in fill:
            return str(fill[name]) + unit
        return _slot_phrase(name)              # unit dropped: 'in a mandal'

    # The backreference means group 2 only ever matches a word that repeats the
    # slot name, so ordinary following words are never eaten.
    return re.sub(r"\{(\w+?)\}(\s+\1\b)?", _sub, question)


def readable_question(question: str, fill: dict[str, str] | None = None) -> str:
    """Public form of _readable: a catalog question rendered for a chip, with
    the slots the caller knows filled in and the rest turned into readable
    stand-ins. Always routable."""
    return _readable(question, fill)


def question_chips(
    candidates: list[ScoredCandidate],
    limit: int,
    fill: dict[str, str] | None = None,
) -> list[Chip]:
    """Nearest catalog questions as tappable chips (deduplicated), with slots
    pre-filled from entities already present in the user's query."""
    chips: list[Chip] = []
    seen: set[str] = set()
    for _, question, _ in candidates:
        text = _readable(question, fill)
        if text in seen:
            continue
        seen.add(text)
        chips.append(Chip(label=text, send_text=text))
        if len(chips) == limit:
            break
    return chips


def candidate_label(candidate: EntityCandidate, *, masked: bool = False) -> str:
    """What tells this candidate apart, for a chip or a prompt.

    District alone does not do it for people: two of the four farmers called
    Lakshmi Devi are both in Nellore, so a district-only label offers two
    identical chips and the user cannot choose. Village leads.
    """
    where = [candidate.village] if candidate.village else []
    where += [d for d in candidate.districts if d != candidate.village]
    label = f"{candidate.name} ({', '.join(where)})" if where else candidate.name
    if masked and candidate.aadhaar:
        label += f" · {mask_aadhaar(candidate.aadhaar)}"
    return label


def candidate_replies(candidates: list[EntityCandidate]) -> list[str]:
    """One send_text per candidate, each of which resolves to that ONE person.

    Sending the bare name back is the loop this path exists to break: the name
    is precisely what was ambiguous, so it would clarify again, forever. A
    person is referenced as 'Lakshmi Devi of Rambilli', which the roster
    validator resolves outright.

    Name + village is unique across the whole roster on this drop. Where a
    future drop makes it collide, the masked Aadhaar is appended — masked, never
    the full number, and short enough that the reply still reads as a slot
    answer rather than a new question.

    A candidate that is a NAME rather than a person has no village, but it may
    have been narrowed to one district already. Carrying that district into the
    reply is what stops the next round offering people the user just ruled out.
    """
    replies = [
        f"{c.name} of {c.village}" if c.village
        else (f"{c.name} of {c.districts[0]}" if len(c.districts) == 1 else c.name)
        for c in candidates
    ]
    duplicated = {r for r in replies if replies.count(r) > 1}
    return [
        f"{r} {mask_aadhaar(c.aadhaar)}" if r in duplicated and c.aadhaar else r
        for c, r in zip(candidates, replies)
    ]


def candidate_chips(
    candidates: list[EntityCandidate], limit: int | None = None
) -> list[Chip]:
    """Disambiguation chips: one per candidate the prompt listed, labelled with
    what tells them apart ('Lakshmi Devi (Rambilli, Visakhapatnam)') and sending
    a reference to that one person, which resolves the paused question outright."""
    chosen = list(candidates[:limit] if limit else candidates)
    replies = candidate_replies(chosen)
    chips: list[Chip] = []
    for candidate, reply in zip(chosen, replies):
        # The reply only carries a masked Aadhaar when name + village was not
        # enough; when it did, the label says so too, so what the user reads
        # matches what distinguishes them.
        masked = bool(candidate.aadhaar) and mask_aadhaar(candidate.aadhaar) in reply
        chips.append(
            Chip(label=candidate_label(candidate, masked=masked), send_text=reply)
        )
    return chips


def corrected_query_chips(
    raw_query: str,
    raw_value: str,
    suggestions: list[str],
    limit: int,
) -> list[Chip]:
    """'Did you mean…' chips: the user's own query with the entity corrected.

    When the suggestion is LONGER than what was matched, the extra words are
    almost always the rest of a name the extractor only caught the head of
    ("Rajesh" out of "Rajesh Sri"). Substituting the head alone leaves the tail
    stranded — "…about Rajesh Babu Sri" — so the replacement also swallows that
    many following capitalised words. Same-length corrections ('Krishnaa' →
    'Krishna') consume nothing, so ordinary text is never eaten.
    """
    chips: list[Chip] = []
    raw_words = len(raw_value.split())
    for suggestion in suggestions[:limit]:
        extra = max(0, len(suggestion.split()) - raw_words)
        # The scoped (?i:…) keeps the value match case-insensitive while the
        # trailing-word check stays case-SENSITIVE — a global IGNORECASE would
        # make [A-Z] match lowercase and swallow ordinary following words.
        pattern = re.compile(
            r"(?i:" + re.escape(raw_value) + r")"
            + r"(?:\s+[A-Z][\w'’-]*){0,%d}" % extra
        )
        if pattern.search(raw_query):
            send = pattern.sub(suggestion, raw_query, count=1)
        else:
            send = f"{raw_query} ({suggestion})"
        chips.append(Chip(label=suggestion, send_text=send))
    return chips
