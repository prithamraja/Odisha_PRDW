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


# How an unfilled OPTIONAL slot reads in an ANSWER, which is a different job
# from how it reads in a chip. A chip is an invitation — "GPDP status for a
# gram panchayat?" asks the user to name one. An answer is a report of what was
# actually run: an absent optional slot bound SQL NULL, the filter was off, and
# every GP is in the result. Echoing the chip's "a gram panchayat" over an
# answer covering all of them is a wrong description of the query that ran.
#
# TWO READINGS, decided by the template's `grouped_geo` (emitted by
# tools/derive_catalog.py from the outermost GROUP BY):
#   collective   the filter is simply off — one figure spanning them all
#                ("How many GPs across all districts uploaded the GPDP?")
#   distributive the statement returns ONE ROW PER unit
#                ("total expenditure incurred by each GP")
_SLOT_COLLECTIVES: dict[str, str] = {
    "date_range":         "all years",
    "date_range_2":       "all years",
    "district_name":      "all districts",
    "block_name":         "all blocks",
    "block_name_2":       "all blocks",
    "gp_name":            "all GPs",
    "gp_name_2":          "all GPs",
    "focus_area":         "all focus areas",
    "theme":              "all themes",
    "scheme":             "all schemes",
    "scheme_2":           "all schemes",
    "status":             "all statuses",
    "plan_type":          "both plan types",
    "tied_untied":        "tied and untied funds",
    "asset_category":     "all categories",
    "asset_sub_category": "all categories",
    "activity_code":      "all activities",
}

# How a bound value reads when it has to be APPENDED because the question text
# has no placeholder for it. Written the way an officer says the tier, not the
# way the bind name spells it: "Laxmipur block", never "Laxmipur block_name".
# A slot with no entry here appends its bare value, which is right for the ones
# whose value already says what it is (a fiscal year, a theme, a status).
_APPEND_NOUNS: dict[str, str] = {
    "district_name": "district",
    "block_name":    "block",
    "block_name_2":  "block",
    "gp_name":       "GP",
    "gp_name_2":     "GP",
}

_SLOT_DISTRIBUTIVES: dict[str, str] = {
    "district_name": "each district",
    "block_name":    "each block",
    "block_name_2":  "each block",
    "gp_name":       "each GP",
    "gp_name_2":     "each GP",
}


def unfilled_phrases(
    slots: list[dict],
    bound: set[str] | frozenset[str],
    grouped_geo: list[str] | None = None,
) -> dict[str, str]:
    """Slot -> how it reads in an answer, for every optional slot left unbound.

    Only OPTIONAL slots get a phrase. A required slot cannot legitimately be
    unbound on a serving path (validation stops first), and describing one as
    "all thresholds" would state something the query never did — so anything
    else falls through to the chip stand-in, which reads as the placeholder it
    is rather than as a claim about the result.

    A slot carrying a DEFAULT renders that default: `$top_n` left unsaid was
    still bound, to 10.
    """
    grouped = set(grouped_geo or ())
    phrases: dict[str, str] = {}
    for slot in slots:
        name = slot["name"]
        if name in bound or name in phrases or not slot.get("optional"):
            continue
        if "default" in slot:
            phrases[name] = str(slot["default"])
        elif name in grouped and name in _SLOT_DISTRIBUTIVES:
            phrases[name] = _SLOT_DISTRIBUTIVES[name]
        elif name in _SLOT_COLLECTIVES:
            phrases[name] = _SLOT_COLLECTIVES[name]
    return phrases


# ── How a bound value READS (WP-6d T7) — display only ─────────────────────────
#
# ONE renderer serves the answer echo (`resolved_question`) and the chips
# (`readable_question`). Nothing here reaches SQL: the bound values stay the
# database's own labels, and only the sentence printed above the answer, or on a
# chip, says them in English. Measured on WP-6c's replays: ~100 raw breakdown
# values ("(fiscal_year)"), 25 bare list lengths ("(10)"), ~60 plan-type and
# tied/untied values with no noun ("(Main)"), ~40 focus areas the reader could not
# tell were filters, and the database's scheme labels in capitals.

# Database label -> what an officer calls it. Any label not here shows as stored.
DISPLAY_NAMES: dict[str, str] = {
    "5TH STATE FINANCE COMMISSION": "5th State Finance Commission (SFC)",
    "XV Finance Commission":        "15th Finance Commission (CFC)",
    "4TH STATE FINANCE SCHEME":     "4th State Finance Commission",
    "WORK COMPLETED":               "completed",
    "WORK ONGOING":                 "ongoing",
    "WORK ABANDONED":               "abandoned",
    "UNDER APPROVAL":               "awaiting approval",
}

# An appended filter carries its noun, so the reader can tell it is a filter.
_PLAN_TYPE_WORDS = {"Main": "main GPDP", "Supplementary": "supplementary plan"}
_STATUS_WORK = {"completed": "completed work", "ongoing": "ongoing work",
                "abandoned": "abandoned work", "awaiting approval": "work awaiting approval"}

# What a ranking ranks, for "(bottom 10, focus areas with at least 50 activities)".
_RANKED_NOUNS = {
    "focus_area_name": "focus areas", "theme": "themes", "district_name": "districts",
    "block_name": "blocks", "gp_name": "GPs", "status_label": "work statuses",
    "scheme_name": "schemes", "plan_type": "plan types", "fiscal_year": "years",
}

_GEO_FINEST_FIRST = ("gp_name", "block_name", "district_name")
_THRESHOLD_TYPES = ("threshold", "amount_threshold")
# "1 lakh (₹100000)": an amount the officer gave in lakhs, echoed with its figure.
_CONVERTED_RE = re.compile(r"^(?P<written>.+?)\s+\(₹[\d.]+\)$")


def display_label(value) -> str:
    """A database label as an officer reads it; anything else unchanged."""
    text = str(value).strip()
    return DISPLAY_NAMES.get(text, text)


def _values(value) -> list[str]:
    """A bound value as its list of values (a list slot may name several)."""
    items = value if isinstance(value, (list, tuple)) else [value]
    return [str(v).strip() for v in items if v is not None and str(v).strip()]


def join_values(values) -> str:
    """'A', 'A and B', 'A, B and C' — several values NAMED, never summed away."""
    values = list(values)
    if len(values) <= 1:
        return "".join(values)
    return ", ".join(values[:-1]) + f" and {values[-1]}"


def _geo_phrase(slot: str, values: list[str]) -> str:
    """'Kalimela block', 'Khordha and Ganjam districts' — a place with its tier."""
    noun = _APPEND_NOUNS.get(slot, "")
    joined = join_values(values)
    if not noun:
        return joined
    if len(values) > 1:
        return f"{joined} {noun}s"
    # main.py's tier chips already pass "Laxmipur block".
    return joined if joined.lower().endswith(" " + noun.lower()) else f"{joined} {noun}"


def _filter_phrase(slot: str, values: list[str]) -> str:
    """How one appended filter reads, with its noun."""
    base = re.sub(r"_2$", "", slot)
    if slot in _APPEND_NOUNS:
        return _geo_phrase(slot, values)
    if base == "plan_type":
        return join_values(_PLAN_TYPE_WORDS.get(v, f"{v} plan") for v in values)
    if base == "tied_untied":
        return f"{join_values(v.lower() for v in values)} funds"
    if base == "focus_area":
        return f"{join_values(values)} focus area{'s' if len(values) > 1 else ''}"
    if base == "status":
        shown = [display_label(v) for v in values]
        return join_values(_STATUS_WORK.get(s, f"{s} status") for s in shown)
    return join_values(display_label(v) for v in values)


def list_direction(sql: str | None) -> str | None:
    """'top' or 'bottom' for a `LIMIT $top_n` list — the first key of the ORDER BY
    it limits (ASC, or no keyword, is bottom). None when there is no such list."""
    sql = sql or ""
    limit = re.search(r"\bLIMIT\s+\$top_n\b", sql)
    if not limit:
        return None
    orders = list(re.finditer(r"\bORDER\s+BY\b", sql[:limit.start()], re.IGNORECASE))
    if not orders:
        return None
    depth, key = 0, []
    for ch in sql[orders[-1].end():limit.start()]:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            break
        key.append(ch)
    return "top" if re.search(r"\bDESC\b", "".join(key), re.IGNORECASE) else "bottom"


def _ranked_noun(template: dict, group_by: str | None) -> str:
    from .breakdown import DIMENSIONS, _parse
    column = DIMENSIONS[group_by][0] if group_by in DIMENSIONS else \
        _parse(template.get("sql_template") or "")[1]
    return _RANKED_NOUNS.get(column or "", "groups")


def _length_phrase(length, floor, template: dict, group_by) -> str:
    """'top 10' / 'bottom 10' / 'the lowest', and a floor the officer set."""
    direction = list_direction(template.get("sql_template"))
    if length is None:
        length = next((s.get("default") for s in template.get("param_slots", [])
                       if s["name"] == "top_n"), None)
    if length is None:
        text = ""
    elif str(length) == "1":
        text = "the lowest" if direction == "bottom" else "the highest"
    else:
        text = f"{direction or 'first'} {length}"
    if floor is not None:
        noun = _ranked_noun(template, group_by)
        text = f"{text}, {noun} with at least {floor} activities" if text else \
            f"{noun} with at least {floor} activities"
    return text


def _threshold_phrase(value: str, slot: dict) -> str:
    """'above ₹20,000', 'below 50%', 'fewer than 5 activities' — never a bare number."""
    from .threshold_reply import _comparison_word, figure_label
    converted = _CONVERTED_RE.match(value)
    written = converted.group("written") if converted else value
    unit, direction = slot.get("unit"), slot.get("direction")
    if not direction:
        return f"threshold {written}"
    label = figure_label(written, unit)
    if unit == "activities":
        label = f"{label} activities"
    return f"{_comparison_word(direction, unit)} {label}"


_TEMPLATE_BY_QUESTION: dict[str, dict] | None = None


def _template_for(question: str) -> dict | None:
    """The catalogue entry a question text belongs to, when the caller had none."""
    global _TEMPLATE_BY_QUESTION
    if _TEMPLATE_BY_QUESTION is None:
        from .template_catalog import TEMPLATE_CATALOG
        _TEMPLATE_BY_QUESTION = {}
        for entry in TEMPLATE_CATALOG.values():
            _TEMPLATE_BY_QUESTION.setdefault(entry["abstract_question"], entry)
    return _TEMPLATE_BY_QUESTION.get(question)


def _appended(question: str, rendered: str, fill: dict, template: dict | None,
              used: set, *, chip: bool) -> list[str]:
    """The phrases for every filled slot the question has no gap for, in order.

    The list length and a floor the officer set share one phrase, first. A
    breakdown is said by `breakdown.describe` on an answer; on a chip, where
    nothing else would say it, it reads "broken down by district" so a tap
    re-reads it. The default floor (1) is never shown.
    """
    slots = {s["name"]: s for s in (template or {}).get("param_slots", [])}
    parts: list[str] = []
    length = floor = None
    group_by = None
    for slot, value in fill.items():
        values = _values(value)
        if slot == "group_by":
            group_by = values[0] if values else None
            continue
        if not values or slot in used or f"{{{slot}}}" in question:
            continue
        if slots and slot not in slots:
            continue            # a chip's template cannot apply it
        decl = slots.get(slot, {})
        etype = decl.get("entity_type", slot)
        if etype == "top_n":
            length = values[0]
            continue
        if etype in _THRESHOLD_TYPES:
            if "default" in decl:                  # a declared ranking floor (WP-6d)
                if values[0] != str(decl["default"]):
                    floor = values[0]
                continue
            parts.append(_threshold_phrase(values[0], decl))
            continue
        if join_values(values) in rendered:
            continue
        parts.append(_filter_phrase(slot, values))
    if template and (length is not None or floor is not None):
        phrase = _length_phrase(length, floor, template, group_by)
        if phrase:
            parts.insert(0, phrase)
    elif length is not None:
        parts.insert(0, f"first {length}" if str(length) != "1" else "the first")
    if chip and group_by:
        from .breakdown import DIMENSIONS, _parse
        absent = _parse((template or {}).get("sql_template") or "")[1]
        if group_by == "total":
            parts.append("as one total")
        elif group_by in DIMENSIONS and DIMENSIONS[group_by][0] != absent:
            parts.append(f"broken down by {DIMENSIONS[group_by][1]}")
    return parts


def _with_appended(rendered: str, parts: list[str]) -> str:
    if not parts:
        return rendered
    return f"{rendered.rstrip('?. ')} ({'; '.join(parts)})?"


def _borrowed_geography(question: str, fill: dict) -> tuple[dict[str, str], set]:
    """({gap: 'Kalimela block'}, the slots used) — a chip's unfilled geography gap
    takes the place the officer named at another tier (WP-6d T6b).

    PLN-024 reads "…each GPDP theme in {gp_name} in {date_range}?". With
    `block_name = Kalimela` it rendered "in a gram panchayat" and lost Kalimela;
    appending "(Kalimela block)" after "in a gram panchayat" would name two
    scopes, so the place takes the gap, with its noun.
    """
    gaps = [s for s in _GEO_FINEST_FIRST if f"{{{s}}}" in question and s not in fill]
    spare = [s for s in _GEO_FINEST_FIRST
             if s in fill and f"{{{s}}}" not in question and _values(fill[s])]
    borrowed, used = {}, set()
    for gap in gaps:
        if not spare:
            break
        slot = spare.pop(0)
        borrowed[gap] = _geo_phrase(slot, _values(fill[slot]))
        used.add(slot)
    return borrowed, used


_GEO_PAIR_RE = re.compile(r"\{(district_name|block_name|gp_name)\}/\{(district_name|block_name|gp_name)\}")


def _one_tier(question: str, fill: dict) -> str:
    """'in {gp_name}/{block_name}' with only the block known -> 'in {block_name}'.

    Six questions offer two tiers side by side (PLN-001 "in {district_name}/
    {block_name}", PLN-044 "in {gp_name}/{block_name}"). On a chip, the tier the
    officer did not name read "in a gram panchayat/Bheden" — a stand-in beside the
    place. The named tier alone is what the chip means (WP-6d pilot row 1041).
    """
    def _sub(match: re.Match) -> str:
        first, second = match.group(1), match.group(2)
        if first in fill and second not in fill:
            return "{" + first + "}"
        if second in fill and first not in fill:
            return "{" + second + "}"
        return match.group(0)
    return _GEO_PAIR_RE.sub(_sub, question)


def _readable(
    question: str,
    fill: dict[str, str] | None = None,
    phrases: dict[str, str] | None = None,
    *,
    tier_nouns: bool = False,
) -> str:
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
            # than "in Khordha" and is what the user said. A database label reads
            # by its display name (WP-6d T7); several values are named.
            values = _values(fill[name])
            if tier_nouns and name in _APPEND_NOUNS and not swallowed:
                # On a CHIP a place carries its tier: Kalimela and Laxmipur are
                # both a block and a GP, and a tap sends only the text, so "in
                # Laxmipur" would lose the "GP" the officer wrote (WP-6d T6).
                return _geo_phrase(name, values) + following
            return join_values(display_label(v) for v in values) + following
        stand_in = (phrases or {}).get(name) or _slot_phrase(name)
        return stand_in + ("" if swallowed else following)

    return re.sub(r"\{(\w+?)\}(\s+(\w+)\b)?", _sub, question)


def readable_question(question: str, fill: dict[str, str] | None = None,
                      template: dict | None = None) -> str:
    """A catalog question rendered for a CHIP, with the slots the caller knows
    filled in and the rest turned into readable stand-ins. Always routable.

    NOTHING THE FILL KNOWS IS DROPPED (WP-6d T6b), the rule `resolved_question`
    and `suggestions._chip_for` already follow. A chip tap sends only its text,
    so a value the text leaves out is gone for good: "…in a gram panchayat in
    2024-2025?" lost Kalimela, and the BUD-003 chip lost the schemes. A place
    named at another tier takes an unfilled geography gap ("in Kalimela
    block"); every other filled slot with no gap is appended in the echo's words.
    """
    fill = fill or {}
    template = template or _template_for(question)
    shown = _one_tier(question, fill)
    borrowed, used = _borrowed_geography(shown, fill)
    rendered = _readable(shown, fill, borrowed, tier_nouns=True)
    return _with_appended(rendered, _appended(shown, rendered, fill, template, used,
                                              chip=True))


def resolved_question(
    question: str,
    fill: dict[str, str] | None = None,
    phrases: dict[str, str] | None = None,
    template: dict | None = None,
) -> str:
    """The question as ANSWERED — every placeholder substituted, none left.

    Per-placeholder, deliberately. The router used to call
    `abstract_question.format(**entity_values)`, which is all-or-nothing: one
    unbound slot raises KeyError and the fallback echoed the RAW abstract
    question, discarding even the substitutions that HAD resolved. Under D2 that
    is the normal case rather than an edge one — every geography slot is
    optional — so an officer asking for "each GP in 2024-25" saw both
    `{gp_name}` AND `{date_range}` come back unfilled while the query underneath
    executed perfectly (operator report, 2026-08-13).

    `phrases` comes from unfilled_phrases(); anything it does not name falls back
    to the chip stand-in. A `{` must never survive into an answer.

    A BOUND SLOT WITH NO PLACEHOLDER IS APPENDED, not dropped. Under D2 a
    template filters on slots its question text never names — EXP-001 reads
    "…incurred by {gp_name} in {date_range}?" but its SQL also filters on
    `$block_name`. Measured in WP-4's eval run: "what about Laxmipur?" bound
    `block_name = Laxmipur`, returned the one right row, and echoed "…incurred
    by each GP in 2024-2025?" — no Laxmipur anywhere. Correct answer, wrong
    question printed above it, which is the SAME defect the operator reported
    wearing different clothes. `suggestions._chip_for` already appends for this
    reason; the answer echo has to as well.

    IN ENGLISH SINCE WP-6d T7: every appended filter carries its noun and they
    share one bracket ("(Sanitation focus area; main GPDP)"); a list length reads
    "(bottom 10)"; the breakdown is left to `breakdown.describe`'s suffix and
    never appended as a raw value.
    """
    fill = fill or {}
    template = template or _template_for(question)
    rendered = _readable(question, fill, phrases)
    return _with_appended(rendered, _appended(question, rendered, fill, template, set(),
                                              chip=False))


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
        text = readable_question(question, fill)
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
