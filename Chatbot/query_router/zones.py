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
# "a gp name", "a date range", "a top n" — text a user is being invited to tap
# but which reads as a placeholder leaking through, so each slot gets a phrase
# an English speaker would actually say.
#
# KEYED ON THE WORKBOOK'S BIND NAMES, which is what appears in a catalogue
# question's {placeholders}, not on the entity types behind them. `$date_range`
# is a fiscal year and reads as one; `$gp_name` binds an LGD code but the user
# still says a panchayat.
_SLOT_PHRASES: dict[str, str] = {
    "date_range":         "a year",
    "date_range_2":       "another year",
    "district_name":      "a district",
    "block_name":         "a block",
    "block_name_2":       "another block",
    "gp_name":            "a gram panchayat",
    "gp_name_2":          "another gram panchayat",
    "focus_area":         "a focus area",
    "theme":              "an LSDG theme",
    "scheme":             "a scheme",
    "scheme_2":           "another scheme",
    "status":             "a work status",
    "asset_category":     "an asset category",
    "asset_sub_category": "an asset sub-category",
    "activity_code":      "an activity",
    "top_n":              "N",
    "threshold":          "a threshold",
    "amount_threshold":   "an amount",
    "deadline":           "a deadline",
}

_VOWELS = "aeiou"


def _slot_phrase(name: str) -> str:
    """Readable stand-in for an unfilled slot."""
    phrase = _SLOT_PHRASES.get(name)
    if phrase is not None:
        return phrase
    words = name.replace("_", " ")
    return ("an " if words[:1].lower() in _VOWELS else "a ") + words


# The nouns a question may repeat after a placeholder, per slot. Without this,
# "in {block_name} block" renders "in a block block" — the AP version compared
# the following word to the SLOT NAME itself with a backreference, which worked
# while slots were called `mandal` and stopped working the moment they were
# called `block_name`.
_SLOT_UNIT_NOUNS: dict[str, tuple[str, ...]] = {
    "district_name":  ("district", "districts", "zilla", "zp"),
    "block_name":     ("block", "blocks", "samiti", "ps"),
    "block_name_2":   ("block", "blocks", "samiti"),
    "gp_name":        ("gp", "gps", "panchayat", "panchayats"),
    "gp_name_2":      ("gp", "gps", "panchayat", "panchayats"),
    "date_range":     ("year", "fy"),
    "date_range_2":   ("year", "fy"),
    "theme":          ("theme",),
    "scheme":         ("scheme",),
    "focus_area":     ("area",),
    "activity_code":  ("activity",),
}


def _unit_nouns(slot: str) -> tuple[str, ...]:
    """The words this slot's placeholder may swallow after itself.

    Always includes the slot name and its stem, so a question written "in
    {block_name} block_name" or "in {block} block" behaves too.
    """
    stem = re.sub(r"_(name|code|range)(_\d)?$", "", slot)
    return tuple({slot, stem, *_SLOT_UNIT_NOUNS.get(slot, ())})


def _readable(question: str, fill: dict[str, str] | None = None) -> str:
    """'GPDP status for {gp_name}?' -> 'GPDP status for Andhrua?' when the value
    is known from the user's own utterance, else 'GPDP status for a gram
    panchayat?' (either way the text stays routable).

    Many questions already name the unit after the slot ('in {block_name}
    block'), so the placeholder swallows a following repeat of its own unit
    rather than emitting 'a block block'. Only a UNIT noun is eaten — ordinary
    following words are left alone, or 'in {district_name} have uploaded' would
    lose its verb.
    """
    def _sub(match: re.Match) -> str:
        name = match.group(1)
        following = match.group(2) or ""          # ' block' in '{block_name} block'
        word = (match.group(3) or "").lower()
        swallowed = word in _unit_nouns(name)
        if fill and name in fill:
            # A known value keeps the unit — "in Khordha district" reads better
            # than "in Khordha" and is what the user said.
            return str(fill[name]) + following
        return _slot_phrase(name) + ("" if swallowed else following)

    return re.sub(r"\{(\w+?)\}(\s+(\w+)\b)?", _sub, question)


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


def candidate_tiebreak(candidate: EntityCandidate) -> str | None:
    """The identifier that separates two candidates their places cannot.

    A gram panchayat's LGD code is a public identifier and is shown in full; a
    farmer's Aadhaar is the same mechanism but must never leave this function
    unmasked. One place to get that distinction right.
    """
    if candidate.code:
        return str(candidate.code)
    return mask_aadhaar(candidate.aadhaar) if candidate.aadhaar else None


def candidate_label(candidate: EntityCandidate, *, masked: bool = False) -> str:
    """What tells this candidate apart, for a chip or a prompt.

    The district alone does not do it: a district holds ~10 blocks and a gram
    panchayat name can repeat inside one, so the narrower place (the block)
    leads.
    """
    where = [candidate.parent_place] if candidate.parent_place else []
    where += [d for d in candidate.districts if d != candidate.parent_place]
    label = f"{candidate.name} ({', '.join(where)})" if where else candidate.name
    tiebreak = candidate_tiebreak(candidate)
    if masked and tiebreak:
        label += f" · {tiebreak}"
    return label


def candidate_replies(candidates: list[EntityCandidate]) -> list[str]:
    """One send_text per candidate, each of which resolves to that ONE panchayat.

    Sending the bare name back is the loop this path exists to break: the name
    is precisely what was ambiguous, so it would clarify again, forever. A gram
    panchayat is referenced as 'Naugaon of Barpali', which the roster validator
    resolves outright.

    Name + block is the reference form, and it is unique for every panchayat in
    this drop. Statewide two panchayats CAN share a name inside one block, and
    the LGD code is appended for those — a public identifier, shown in full, and
    short enough that the reply still reads as a slot answer rather than a new
    question. (The same slot appends a MASKED Aadhaar where the domain has
    people rather than places; `candidate_tiebreak` owns that distinction.)

    A candidate that is a NAME rather than one panchayat has no parent place,
    but it may have been narrowed to one district already. Carrying that
    district into the reply is what stops the next round offering the ones the
    user just ruled out.
    """
    replies = [
        f"{c.name} of {c.parent_place}" if c.parent_place
        else (f"{c.name} of {c.districts[0]}" if len(c.districts) == 1 else c.name)
        for c in candidates
    ]
    duplicated = {r for r in replies if replies.count(r) > 1}
    return [
        f"{r} {candidate_tiebreak(c)}"
        if r in duplicated and candidate_tiebreak(c) else r
        for c, r in zip(candidates, replies)
    ]


def candidate_chips(
    candidates: list[EntityCandidate], limit: int | None = None
) -> list[Chip]:
    """Disambiguation chips: one per candidate the prompt listed, labelled with
    what tells them apart ('Naugaon (Barpali, Bargarh)') and sending a reference
    to that one panchayat, which resolves the paused question outright."""
    chosen = list(candidates[:limit] if limit else candidates)
    replies = candidate_replies(chosen)
    chips: list[Chip] = []
    for candidate, reply in zip(chosen, replies):
        # The reply only carries the code/masked Aadhaar when name + place was
        # not enough; when it did, the label says so too, so what the user reads
        # matches what distinguishes them.
        tiebreak = candidate_tiebreak(candidate)
        masked = bool(tiebreak) and tiebreak in reply
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
