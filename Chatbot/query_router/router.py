"""
Router with two selectable front-ends (see config.USE_VECTOR_RETRIEVAL):

  Template-direct (default):
    Step 1 — vector_retrieve(query, k)          → top-K candidate query_ids
    Step 2 — rerank(query, candidates)          → (query_id | no_match, near-miss ids)
    Step 3 — extract_entities(query, slots)     → {slot: raw_value}   (slots come
             from the chosen template's param_slots)

  Legacy intent path (USE_VECTOR_RETRIEVAL=False, or no retriever available):
    Step 1 — classify_intent(query)             → intent
    Step 2 — extract_entities(query, slots)     → {slot: raw_value}
    Step 3 — INTENT_LOOKUP[(intent, entities)]  → query_id

Both front-ends converge on _serve_query_id(), which validates params, injects
the optional date filter, executes/serves, and builds the RouteResult.
"""
import re
import time
import json
import hashlib
import logging

_log = logging.getLogger(__name__)

from .models            import (
    Chip,
    Clarification,
    ClarificationNeeded,
    EntityCandidate,
    EntityNotFound,
    ExtractedEntity,
    PendingClarification,
    RouteResult,
    RouteTier,
)
from .preprocessor      import normalize
from .intent_catalog    import INTENT_LOOKUP, INTENT_SLOTS
from .intent_classifier import classify_intent
from .entity_extractor  import extract_entities
from .entity_validator  import EntityValidator, mask_aadhaar
from .reranker          import rerank
from .fallback          import generate_fallback_message
from .zones             import (
    candidate_chips,
    candidate_replies,
    corrected_query_chips,
    readable_question,
    resolved_question,
    unfilled_phrases,
    zone,
)
from .dashboard_catalog import DASHBOARD_CATALOG
from .unanswerable_catalog import UNANSWERABLE_CATALOG, refusal_for
from .fragment_reroute   import drill_target, templates_share_subject
from .date_phrase        import resolve_fiscal_years
from .sql_params         import NAMED, param_style
from .suggestions       import elicitation_chips
from .config            import (
    CLARIFY_SCORE_MARGIN,
    MAX_CLARIFY_OPTIONS,
    MAX_MISS_SUGGESTIONS,
    NO_MATCH_LOWER_THRESHOLD,
    RESULT_CACHE_DEFAULT_TTL,
    USE_VECTOR_RETRIEVAL,
    VECTOR_TOP_K,
)

# Simple in-process TTL result cache
_result_cache: dict[str, tuple[list[dict], float]] = {}

# query_id → a representative intent (for display/logging on the vector path)
_QID_TO_INTENT: dict[str, str] = {}
for (_intent, _entities), _qid in INTENT_LOOKUP.items():
    _QID_TO_INTENT.setdefault(_qid, _intent)


def _cache_get(key: str) -> list[dict] | None:
    if key in _result_cache:
        val, exp = _result_cache[key]
        if time.time() < exp:
            return val
        del _result_cache[key]
    return None


def _cache_set(key: str, value: list[dict], ttl: int) -> None:
    _result_cache[key] = (value, time.time() + ttl)


class DateFilterUnsupported(Exception):
    """The template's date_kind has no injection strategy — refuse rather than
    emit a predicate that would compare incompatible units and quietly return
    the wrong rows."""


def _year_of(value: str) -> int:
    """'2024-03-01' -> 2024. Accepts a bare year too."""
    return int(str(value).strip()[:4])


# Names for the injected date placeholders on the NAMED path. Double underscore
# so they cannot collide with a catalogue bind name (the Parameter Registry's
# names are all plain, e.g. district_name, fin_year).
DATE_START_PARAM = "__date_start"
DATE_END_PARAM   = "__date_end"


def _date_predicate(
    alias: str,
    column: str,
    date_kind: str | None,
    start_date: str,
    end_date: str,
    *,
    named: bool = False,
) -> tuple[str, list | dict]:
    """(predicate SQL, the date values to bind).

    Placeholder style follows the template's own: `?` with a list of values for
    positional SQL, `$__date_start`/`$__date_end` with a dict for named SQL. A
    template's injected predicate MUST match the style of the statement it is
    spliced into — DuckDB will not mix `?` and `$name` in one prepared statement.

    Column references are quoted because AP columns are mixed-case
    ("SurveyDate", "PROCUREMENT_DATE"), and the alias is omitted entirely when
    the template's date_filter carries alias '' — most AP SQL is single-table,
    where `alias.column` would emit a broken leading dot.
    """
    col = f'{alias}."{column}"' if alias else f'"{column}"'
    lo  = f"${DATE_START_PARAM}" if named else "?"
    hi  = f"${DATE_END_PARAM}"   if named else "?"

    def _binds(start, end) -> list | dict:
        if named:
            return {DATE_START_PARAM: start, DATE_END_PARAM: end}
        return [start, end]

    if date_kind in (None, "", "iso"):
        return f"{col}::DATE BETWEEN {lo} AND {hi}", _binds(start_date, end_date)

    if date_kind == "year":
        # agriculture has no date column, only cropyear — a plain number.
        return (
            f"{col} >= {lo} AND {col} <= {hi}",
            _binds(_year_of(start_date), _year_of(end_date)),
        )

    if date_kind == "serial":
        # Excel day serials. No template ships with this kind any more (the data
        # contract is real dates) — if one reappears, fail loudly.
        raise DateFilterUnsupported(
            f"date filtering on '{column}' is not supported yet: the column holds "
            "Excel day serials, not dates. Ask the question without a date range."
        )

    raise DateFilterUnsupported(f"unknown date_kind '{date_kind}' for column '{column}'")


def _inject_date_filter(
    sql: str,
    alias: str,
    column: str,
    date_kind: str | None = "iso",
    *,
    start_date: str,
    end_date: str,
    named: bool = False,
) -> tuple[str, int, list | dict]:
    """
    Appends the date condition to the SQL, inserting just before the first
    GROUP BY / ORDER BY / LIMIT after the last WHERE clause.

    Returns (sql, placeholder_offset, date_params).

    POSITIONAL (`named=False`): placeholders bind by their order in the SQL TEXT,
    and the predicate can land ahead of one the template already has — 'LIMIT ?'
    on the top-N templates is the case that bites. So the caller must splice, not
    append: `params[:offset] + date_params + params[offset:]`. Use
    merge_date_params() rather than doing it by hand.

    NAMED (`named=True`): placeholders bind by name, so text order carries no
    meaning and `date_params` is a dict the caller merges with `{**params,
    **date_params}`. The returned offset is 0 and must be ignored.
    """
    predicate, date_params = _date_predicate(
        alias, column, date_kind, start_date, end_date, named=named,
    )

    # AP templates are terminated with ';' — drop it so a trailing append lands
    # inside the statement rather than after it.
    sql = sql.rstrip().rstrip(";")

    has_where = bool(re.search(r'\bWHERE\b', sql, re.IGNORECASE))
    keyword   = "AND" if has_where else "WHERE"
    condition = f"\n  {keyword} {predicate}"

    last_where_end = 0
    for m in re.finditer(r'\bWHERE\b', sql, re.IGNORECASE):
        last_where_end = m.end()

    for kw in (r'\bGROUP\s+BY\b', r'\bORDER\s+BY\b', r'\bLIMIT\b'):
        for m in re.finditer(kw, sql, re.IGNORECASE):
            if m.start() >= last_where_end:
                head = sql[:m.start()].rstrip()
                offset = 0 if named else head.count("?")
                return head + condition + '\n' + sql[m.start():], offset, date_params

    return sql.rstrip() + condition, (0 if named else sql.count("?")), date_params


def merge_date_params(param_values: list, offset: int, date_params: list) -> list:
    """Put the date values where their placeholders actually sit in the SQL."""
    return param_values[:offset] + date_params + param_values[offset:]


def _merge_date_binds(
    params: list | dict, offset: int, date_params: list | dict
) -> list | dict:
    """Style-agnostic merge of the injected date binds into the template's own."""
    if isinstance(params, dict):
        return {**params, **date_params}
    return merge_date_params(params, offset, date_params)


def _param_cache_fingerprint(param_values: list | dict) -> str:
    """A stable string identifying one set of bound values.

    Named binds are a DICT, and iterating a dict yields its KEYS — the original
    positional-only fingerprint would have hashed `["district_name", "fin_year"]`
    for every question of that shape, so two different districts would have
    shared one cache entry and the second would have been served the first's
    rows. Sort by key so ordering cannot change the fingerprint either.
    """
    if isinstance(param_values, dict):
        payload = [[k, str(v)] for k, v in sorted(param_values.items())]
    else:
        payload = [str(p) for p in param_values]
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:8]


def _exec_template(
    cache_conn, query_id: str, sql_template: str,
    param_values: list | dict, ttl: int,
) -> list[dict]:
    h = _param_cache_fingerprint(param_values)
    cache_key = f"tmpl:{query_id}:{h}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    result = cache_conn.execute(sql_template, param_values)
    cols = result.description
    rows = [dict(zip(cols, r)) for r in result.fetchmany(200)]
    _cache_set(cache_key, rows, ttl)
    return rows


def _fallback(msg: str, user_query: str, normalized: str, start: float) -> RouteResult:
    return RouteResult(
        tier=RouteTier.FALLBACK,
        fallback_message=msg,
        raw_query=user_query,
        normalized_query=normalized,
        total_latency_ms=(time.monotonic() - start) * 1000,
    )


def _template_slot_types(template: dict) -> dict[str, str]:
    """Unique slot names in first-seen order, each with its registry type."""
    slot_type: dict[str, str] = {}
    for s in template["param_slots"]:
        slot_type.setdefault(s["name"], s.get("entity_type", s["name"]))
    return slot_type


# Entity types the catalog exposes as SQL parameters but which are constants,
# not something a user ever says. Asking the LLM for them wastes a slot and
# asking the user produces a nonsense clarify prompt, so they are filled in here
# before extraction.
#
# EMPTY FOR PR&DW. The AP catalogue's one member was `aadhaar_length` (fixed at
# 12, exposed only so the rule was visible in the SQL); none of the workbook's
# 19 bind names is a constant of that kind. The mechanism is kept because it is
# the right shape for one if the statewide catalogue ever adds it — a constant
# must never reach the user as "for which Aadhaar length?".
_CONSTANT_ENTITY_TYPES: dict[str, str] = {}

# Numeric slots whose value the QUESTION IMPLIES, so asking for it is a stall
# rather than a clarification: "Which theme has the most planned activities?"
# does not need "for which top n?" — a ranking implies a list length.
#
# Strictly numeric-and-presentational. A categorical slot (theme, scheme,
# district) or a threshold that changes the population ($threshold,
# $amount_threshold) must NEVER get a default: guessing there silently answers a
# different question than the one asked. $threshold is especially not defaultable
# — the Parameter Registry is explicit that its unit varies by question between
# percent, rupees, days and a minimum activity count.
#
# KEYED BY ENTITY TYPE, and now the FALLBACK rather than the authority: since
# D18.P1 the PR&DW catalogue declares the default on the slot itself
# (`{"optional": True, "default": "10"}`, emitted by tools/build_catalog.py), and
# slot_defaults() below wins over this table. The table stays for templates whose
# slots carry no declaration — the AP fixtures still in the test suite — and
# tests/test_param_binding.py asserts the two agree, so they cannot drift.
_DEFAULT_ENTITY_VALUES: dict[str, str] = {
    "top_n": "10",          # a ranking with no length asked for
}

# The slots a plainly-stated rupee figure may prefill. `threshold` is included
# because some of its questions are rupee questions, and `amount_from_text`
# claims a figure only when the text carries a money marker — so the percent /
# days / activity-count readings of `threshold` still reach the extractor.
_AMOUNT_ENTITY_TYPES = frozenset({"amount_threshold", "threshold"})

# The slots a DETERMINISTIC reader can recover when the extractor comes back
# empty. See _fiscal_year_from_text() for why this exists at all.
_FISCAL_YEAR_ENTITY_TYPES = frozenset({"fiscal_year", "fiscal_year_2"})

# A rupee amount stated outright — "above ₹1 lakh", "more than 50,000",
# "over 2.5 crore". Reading it here means the frequent case never depends on the
# LLM at all: not just deterministic arithmetic (the validator handles that),
# but deterministic end to end. Anything this cannot see still goes to the
# extractor.
#
# A MONEY MARKER is required — the ₹/Rs prefix, or a lakh/crore/thousand
# multiplier, or a trailing "rupees". A bare "more than 50" is deliberately NOT
# claimed: $threshold's unit varies by question (percent, rupees, days, or a
# minimum activity count, per the Parameter Registry sheet), so prefilling a
# bare figure would bypass the extractor's reading of which one was meant.
_AMOUNT_TEXT_RE = re.compile(
    r"(?:(?P<sym>₹|₨|\bRs\.?|\bINR)\s*(?P<n1>\d[\d,]*(?:\.\d+)?)"
    r"\s*(?P<u1>lakhs?|lacs?|crores?|cr|thousand|k)?"
    r"|(?P<n2>\d[\d,]*(?:\.\d+)?)\s*(?P<u2>lakhs?|lacs?|crores?|cr|thousand)\b"
    r"|(?P<n3>\d[\d,]*(?:\.\d+)?)\s*(?=rupees\b))",
    re.IGNORECASE,
)
# A RANGE is not a threshold: "between ₹1 lakh and ₹5 lakh" has two figures, so
# the plain scan would claim one and silently answer about the wrong bound. One
# threshold slot cannot express a range — hand the sentence to the extractor.
_AMOUNT_RANGE_RE = re.compile(r"\bbetween\b", re.IGNORECASE)


def amount_from_text(text: str) -> str | None:
    """'activities above ₹1 lakh' -> '1 lakh'. None when not stated plainly.

    Returns the figure WITH its multiplier word, exactly the shape the extractor
    is asked for, so `entity_validator.parse_amount` does the one conversion
    either way. Only a SINGLE unambiguous match counts.
    """
    text = text or ""
    if _AMOUNT_RANGE_RE.search(text):
        return None
    matches = [m for m in _AMOUNT_TEXT_RE.finditer(text)]
    if len(matches) != 1:
        return None          # none, or ambiguous — let the extractor read it
    m = matches[0]
    number = m.group("n1") or m.group("n2") or m.group("n3")
    unit = m.group("u1") or m.group("u2")
    return f"{number} {unit.lower()}" if unit else number


def _extract_slot_values(
    user_query: str,
    slot_type: dict[str, str],
    openai_client,
    *,
    intent: str | None = None,
) -> dict[str, str | None]:
    """extract_entities() over the genuinely user-supplied slots, with the
    catalog's constant slots filled in afterwards, and rupee amounts read
    straight out of the text when they are stated plainly."""
    prefilled: dict[str, str] = {}
    for slot, etype in slot_type.items():
        if etype in _AMOUNT_ENTITY_TYPES:
            found = amount_from_text(user_query)
            if found is not None:
                prefilled[slot] = found

    askable = [
        s for s, etype in slot_type.items()
        if etype not in _CONSTANT_ENTITY_TYPES and s not in prefilled
    ]
    raw: dict[str, str | None] = (
        extract_entities(user_query, askable, openai_client, intent=intent)
        if askable else {}
    )
    raw.update(prefilled)
    for slot, etype in slot_type.items():
        if etype in _CONSTANT_ENTITY_TYPES:
            raw[slot] = _CONSTANT_ENTITY_TYPES[etype]
    return raw


def _fiscal_year_from_text(
    user_query: str, slot: str, entity_type: str, validator: EntityValidator
) -> ExtractedEntity | None:
    """The fiscal year read straight off the user's own question, or None.

    WHY THIS EXISTS (WP-4 finding F1). The extractor returns a well-formed
    `{"date_range": null}` on roughly a quarter of calls — measured over 12
    IDENTICAL calls: nine read the year, three did not, every one of them
    `finish_reason=stop` with valid JSON and no exception. The model is not
    failing; it is answering "this question names no fiscal year" about a
    sentence containing '2024-2025'. Under D9 `$date_range` is required on 344
    of the 346 templates, so each of those became "For which date range?" asked
    of an officer who had already said it — 30% of the eval set.

    THE READER WAS ALREADY HERE. `date_phrase` is a word-bounded regex pass
    built in WP-2 for exactly this mapping, and `_validate_fiscal_year` already
    calls it, consults the loaded years for relative phrases, and splits a
    two-year phrase across `$date_range` / `$date_range_2` by entity type. It
    was simply never reachable: it received the string the EXTRACTOR produced,
    so a null meant it was never consulted. All this does is hand it the
    question instead. Measured against WP-4's failures: 55 of 62 recovered with
    the gold value, zero wrong.

    A FALLBACK, NOT A PREFILL. It runs only where the extractor produced
    nothing, so no call that works today can change; `amount_from_text` takes
    the prefill approach for rupee figures and this could follow it later, on
    the evidence of the disagreement log below.
    """
    try:
        entity = validator.validate(user_query, entity_type)
    except (EntityNotFound, ClarificationNeeded):
        # Genuinely no year in the text — which is a legitimate outcome ("GPDP
        # status?"), so the caller falls through to the ordinary missing-slot
        # clarification. Swallowed deliberately: letting EntityNotFound out here
        # would render "I couldn't find a date range called '<the entire
        # question>'", quoting the officer's sentence back as a bad value.
        return None
    entity.slot_name = slot
    # The raw value is the whole question at this point, which is true but
    # unhelpful in an echo or a pending state. Say where the value came from.
    entity.raw_value = f"{entity.resolved_value} (read from the question)"
    _log.info("date_range recovered deterministically for %s: %r",
              slot, entity.resolved_value)
    return entity


def _order_paired_fiscal_years(
    validated: list[ExtractedEntity], slot_type: dict[str, str]
) -> None:
    """`$date_range` is the LATER year of a pair. Enforced, not hoped for.

    WHY THIS EXISTS, AND WHY `e3e70ff` DID NOT CLOSE IT. All five paired
    templates bind `$date_range_2` as **year1** and `$date_range` as **year2**,
    three of them compute `$date_range - $date_range_2`, and their question text
    reads "between {date_range_2} and {date_range}" — so `$date_range` is the
    later year (pinned against the SQL in `test_fiscal_year_fallback`). WP-4 §5.1a
    fixed `_validate_fiscal_year`'s split of ONE string carrying two years, on the
    stated understanding that "the extractor normally assigns the two slots
    itself and got it right".

    IT DID NOT. Read off WP-4's own recorded replays, on every paired-template
    row in all three runs:

        run1/2/3  PLN-039, TRD-002, TRD-004
                  date_range = 2023-2024, date_range_2 = 2024-2025

    which is backwards, and the served table proves the cost — PLN-039 answered
    "which themes showed the greatest INCREASE" with
    `change_in_activities = +663` for Theme 6, which actually **declined by 663**.
    All three rows graded `hit`, because route-graded evals do not look at values.

    The cause is a rule collision, not a wobble: the extraction prompt defines the
    pair by MENTION ORDER ("'2024-25 vs 2023-24' → fiscal_year='2024-25',
    fiscal_year_2='2023-24'") while the catalogue defines it CHRONOLOGICALLY, and
    the question text happens to name the earlier year first. Stable in all three
    replays, which is exactly what a prompt/schema conflict looks like.

    So the ordering is imposed here rather than asked for: it is a property of the
    SQL, and no phrasing of a prompt can be trusted to reproduce a property of
    the SQL. Both slots must be bound for anything to happen — a single year is
    not a pair, and nothing else about extraction changes.
    """
    if not ({"date_range", "date_range_2"} <= set(slot_type)):
        return
    if slot_type.get("date_range") not in _FISCAL_YEAR_ENTITY_TYPES:
        return
    by_slot = {e.slot_name: e for e in validated}
    later, earlier = by_slot.get("date_range"), by_slot.get("date_range_2")
    if later is None or earlier is None:
        return
    # The stored form is 'YYYY-YYYY', so lexicographic order IS chronological.
    if str(later.resolved_value) >= str(earlier.resolved_value):
        return
    _log.info(
        "paired fiscal years arrived inverted and were re-ordered: "
        "date_range=%r date_range_2=%r → date_range=%r date_range_2=%r "
        "($date_range is the later year; three paired templates compute "
        "$date_range - $date_range_2, so the old order inverts the sign)",
        later.resolved_value, earlier.resolved_value,
        earlier.resolved_value, later.resolved_value,
    )
    later.resolved_value, earlier.resolved_value = (
        earlier.resolved_value, later.resolved_value)
    later.raw_value, earlier.raw_value = earlier.raw_value, later.raw_value


def _log_fiscal_year_disagreement(
    user_query: str, slot: str, entity_type: str, extracted: str
) -> None:
    """Record where the extractor and the deterministic reader differ.

    This is the evidence that decides whether the reader can be promoted from a
    FALLBACK to a PREFILL — read the year first and drop the slot from the
    extractor's job entirely, the way `amount_from_text` already does for rupee
    figures. That change would alter calls that currently succeed, so it wants a
    log behind it rather than an argument. Pure regex, no network: costs nothing
    to leave on.
    """
    try:
        years = resolve_fiscal_years(user_query, ())
    except Exception:                                        # pragma: no cover
        return
    if not years:
        return
    # The pair split `_validate_fiscal_year` applies, mirrored so a comparison
    # question is not logged as a disagreement with itself.
    expected = years[-1] if (len(years) > 1 and entity_type.endswith("_2")) else years[0]
    if str(extracted).strip() != expected:
        _log.info(
            "fiscal-year disagreement on %s: extractor=%r date_phrase=%r query=%r",
            slot, extracted, expected, user_query[:120],
        )


def optional_slots(param_slots: list[dict]) -> set[str]:
    """Slot names this template may execute WITHOUT a value.

    An optional slot marked {"optional": True} binds NULL when nothing was
    extracted, which the Odisha catalogue's filter idiom

        ($district_name IS NULL OR gp.district_name = $district_name)

    reads as "don't filter on district". That is how one consolidated template
    per question answers at every geographic scope, instead of the AP catalogue's
    -S/-D/-M sibling variants. Absent optional slots must NOT stall on a
    clarification: "how many activities are planned?" is a complete question
    state-wide, and asking "for which district?" would be inventing a
    requirement the question never had.

    Required slots (no "optional" key — every AP slot) are unchanged: absent
    means pause and ask, never execute broken SQL.

    A slot may be optional AND carry a default (D18.P1's `$top_n`). Optional
    there means "the router supplies it instead of asking", not "bind NULL" —
    see slot_defaults().
    """
    return {s["name"] for s in param_slots if s.get("optional")}


def slot_defaults(param_slots: list[dict]) -> dict[str, str]:
    """Slot name -> the value to use when the question did not state one.

    Declared by the catalogue (`tools/build_catalog.py::DEFAULTED_SLOTS`), so
    the generated file is the single source of truth and a future defaulted slot
    needs no runtime edit. Decision D18.P1 puts exactly one slot here: `$top_n`,
    the presentational LIMIT on 91 templates that no officer ever states.

    Distinct from optional-and-absent, which binds SQL NULL: `LIMIT NULL` is
    UNBOUNDED, the opposite of a page size, so a defaulted slot that reached the
    binder empty would silently dump the whole result set.
    """
    return {s["name"]: s["default"] for s in param_slots if "default" in s}


# A slot may bind the RESOLVED CODE of the one roster row its value named
# rather than the name itself. "code" is the neutral spelling PR&DW templates
# use ($gp_name -> gp_lgd_code, decision D10); "aadhaar" is the AP spelling of
# the same mechanism and stays accepted so the AP catalogue keeps binding while
# it is still in the tree.
_CODE_BIND_KINDS = frozenset({"code", "aadhaar"})


def _resolve_slot_value(
    slot: dict,
    params_by_name: dict,
    person_ids: dict[str, str],
    context: str,
):
    """The value one slot binds — its resolved code, its extracted value, or None.

    Shared by the positional and named binders so the two cannot drift on which
    slot binds what.
    """
    name = slot["name"]
    if name not in params_by_name and "default" in slot:
        # A defaulted slot must never fall through to NULL: `LIMIT NULL` is
        # unbounded. _fill_slots_or_clarify normally fills it, so this is the
        # backstop for the paths that bind without going through validation.
        return slot["default"]
    if slot.get("bind") in _CODE_BIND_KINDS:
        # An optional code-bound slot that was never supplied is absent, not
        # unresolved — bind NULL rather than failing.
        if name not in params_by_name and slot.get("optional"):
            return None
        code = person_ids.get(name)
        if not code:
            raise ValueError(
                f"'{name}'{context} did not resolve to one record"
            )
        return code
    return params_by_name.get(name)


def _check_required(
    param_slots: list[dict], params_by_name: dict, context: str
) -> None:
    """Raise unless every REQUIRED slot has a value."""
    optional = optional_slots(param_slots)
    missing = [
        n for n in dict.fromkeys(s["name"] for s in param_slots)
        if n not in params_by_name and n not in optional
    ]
    if missing:
        raise ValueError(
            f"missing parameter(s){context}: {', '.join(missing)}"
        )


def bind_param_values(
    param_slots: list[dict],
    params_by_name: dict,
    *,
    context: str = "",
    person_ids: dict[str, str] | None = None,
) -> list:
    """
    One value per SQL placeholder: walk param_slots in positional order,
    repeating a logical value wherever its slot name recurs (many templates
    filter several subqueries by the same district/block/GP).

    A slot may declare {"bind": "code"} (or the AP spelling {"bind": "aadhaar"}
    — same mechanism). It binds the resolved ROW's unique code rather than its
    name, because a name is not a row: statewide, GP names repeat across the 314
    blocks, so a name-keyed filter silently aggregates every panchayat that
    happens to be called that — the AP defect (F12 summed four Lakshmi Devis
    into one farmer's total) transplanted into geography. `person_ids` carries
    slot -> code for the entities that resolved to one record; a code-bound slot
    with nothing there is a bug upstream and fails loudly rather than falling
    back to the name.

    A slot marked {"optional": True} with no value binds None (SQL NULL) instead
    of raising — see optional_slots().
    """
    ordered = sorted(param_slots, key=lambda s: s["position"])
    person_ids = person_ids or {}
    _check_required(ordered, params_by_name, context)
    return [
        _resolve_slot_value(slot, params_by_name, person_ids, context)
        for slot in ordered
    ]


def bind_named_params(
    param_slots: list[dict],
    params_by_name: dict,
    *,
    context: str = "",
    person_ids: dict[str, str] | None = None,
) -> dict:
    """
    {name: value} for SQL that uses `$name` placeholders — ONE entry per slot
    NAME, however many times the name occurs in the statement.

    This is the whole reason named binding is worth having: the Odisha catalogue
    repeats every optional filter's parameter twice
    (`($p IS NULL OR col = $p)`), and some questions repeat one across several
    subqueries. Positional binding would need the value duplicated at exactly
    the right offsets, which is where the conversion bugs live.

    `position` is irrelevant here and is not required on the slot dicts.
    """
    person_ids = person_ids or {}
    _check_required(param_slots, params_by_name, context)
    return {
        slot["name"]: _resolve_slot_value(slot, params_by_name, person_ids, context)
        for slot in param_slots
    }


def bind_for_template(
    template: dict,
    params_by_name: dict,
    *,
    context: str = "",
    person_ids: dict[str, str] | None = None,
) -> list | dict:
    """Bind in whichever style the template's SQL is written in.

    Returns a LIST for positional (`?`) SQL and a DICT for named (`$name`) SQL;
    both are what the DuckDB-backed adapters take directly.
    """
    binder = (
        bind_named_params if param_style(template) == NAMED else bind_param_values
    )
    return binder(
        template["param_slots"], params_by_name,
        context=context, person_ids=person_ids,
    )


def _person_bound_slots(param_slots: list[dict]) -> set[str]:
    """The slot names this template binds by resolved code rather than by name."""
    return {s["name"] for s in param_slots if s.get("bind") in _CODE_BIND_KINDS}


def _person_ids_for(
    param_slots: list[dict],
    slot_types: dict[str, str],
    params_by_name: dict,
    validator: EntityValidator,
) -> dict[str, str]:
    """Recover each code-bound slot's identifier by re-resolving its value.

    A context frame stores bound parameters as plain strings, so an identity
    resolved on the original turn is not in it. Re-validating gets it back: the
    roster resolves a REFERENCE ('Naugaon of Barpali') to the same panchayat
    every time, which is exactly why resolved_value carries the block whenever a
    name is shared.
    """
    person_ids: dict[str, str] = {}
    for name in _person_bound_slots(param_slots):
        value = params_by_name.get(name)
        if value is None:
            continue
        try:
            entity = validator.validate(value, slot_types.get(name, name))
        except Exception:
            continue   # bind_param_values reports it as the unresolved person
        if entity.resolved_code:
            person_ids[name] = entity.resolved_code
    return person_ids


def _fill_slots_or_clarify(
    query_id: str,
    slot_type: dict[str, str],
    raw_entities: dict,
    validator: EntityValidator,
    user_query: str,
    normalized: str,
    start: float,
    *,
    optional: set[str] | frozenset[str] = frozenset(),
    defaults: dict[str, str] | None = None,
) -> tuple[list[ExtractedEntity], RouteResult | None]:
    """Validate every slot value, or return a clarify carrying pending state so
    the user's next message can resume this exact question.

    Slots the user DID supply are validated first, even when an earlier slot is
    missing, so the pending state carries them. The AP catalog makes this
    load-bearing: every mandal-scoped question reads "…in {mandal} mandal" but
    its SQL also needs {district}, so the router must ask for the district
    without throwing away the mandal the user just named.

    `optional` names the slots that may be left unfilled (see optional_slots()).
    An absent optional slot is simply not validated and not reported missing —
    the binder turns it into NULL, which the SQL reads as "don't filter". A
    SUPPLIED optional value is validated exactly as a required one: "in Kendrapara
    district" naming a district the registry doesn't know is a mistake to
    surface, not a filter to silently drop.

    `defaults` (slot -> value, from slot_defaults()) fills a slot the question
    left unstated but which must not bind NULL — `$top_n`, whose NULL means
    "no limit". A defaulted value is validated like any other, so the 1,000
    ceiling still applies to it.
    """
    validated: list[ExtractedEntity] = []
    missing: list[str] = []

    def _pending(
        missing_slot: str, candidates: list[EntityCandidate] | None = None
    ) -> PendingClarification:
        return PendingClarification(
            query_id=query_id,
            missing_slot=missing_slot,
            slot_type=slot_type[missing_slot],
            filled={e.slot_name: e.resolved_value for e in validated},
            original_query=user_query,
            candidates=candidates or [],
        )

    for slot in slot_type:
        raw_val = raw_entities.get(slot)
        etype = slot_type[slot]

        if etype in _FISCAL_YEAR_ENTITY_TYPES:
            if raw_val is None:
                # WP-4 F1: the extractor said nothing. Read the question
                # ourselves before asking the user for something they said.
                # Ahead of the defaults deliberately — evidence from the user's
                # own text beats any value the system supplies — and ahead of
                # the `optional` check too, because ALR-001/ALR-008 carry an
                # optional $date_range (D13.3) where binding NULL would answer
                # across every year about a question that named one.
                recovered = _fiscal_year_from_text(user_query, slot, etype, validator)
                if recovered is not None:
                    validated.append(recovered)
                    continue
            else:
                _log_fiscal_year_disagreement(user_query, slot, etype, raw_val)

        if raw_val is None:
            # A slot the question implies is filled from its declared default
            # rather than clarified for. Applied here, in the one place every
            # path validates through, so the vector path and the resumed-pending
            # path behave identically. The catalogue's own declaration wins; the
            # entity-type table is the fallback for slots that carry none.
            raw_val = (defaults or {}).get(slot)
        if raw_val is None:
            raw_val = _DEFAULT_ENTITY_VALUES.get(slot_type[slot])
        if raw_val is None:
            if slot not in optional:
                missing.append(slot)
            continue
        try:
            entity = validator.validate(raw_val, slot_type[slot])
            entity.slot_name = slot
            validated.append(entity)
        except EntityNotFound as e:
            if e.suggestions:
                clarify = _clarify(
                    "unknown_entity",
                    f"I couldn't find a {slot.replace('_', ' ')} called "
                    f"'{e.raw_value}'. Did you mean one of these?",
                    corrected_query_chips(
                        user_query, e.raw_value, e.suggestions, MAX_CLARIFY_OPTIONS
                    ),
                    user_query, normalized, start,
                )
            else:
                clarify = _clarify(
                    "unknown_entity",
                    f"I couldn't find a {slot.replace('_', ' ')} called '{e.raw_value}'. "
                    f"Which {slot.replace('_', ' ')} did you mean?",
                    [],
                    user_query, normalized, start,
                )
            clarify.pending = _pending(slot)
            return [], clarify
        except ClarificationNeeded as e:
            # One chip per candidate, sending the full unambiguous name — a tap
            # resolves the pause outright. The prompt already lists them in
            # prose; without chips the user has to retype a name they only just
            # learned exists.
            clarify = _clarify(
                "unknown_entity", str(e), candidate_chips(e.candidates),
                user_query, normalized, start,
            )
            clarify.pending = _pending(slot, e.candidates)
            return [], clarify

    _order_paired_fiscal_years(validated, slot_type)

    if missing:
        # Required slot empty → pause and ask, never execute broken SQL. The
        # pending state carries everything already resolved, so answering this
        # one question resumes the original query rather than restarting it.
        slot = missing[0]
        clarify = _clarify(
            "missing_parameter",
            f"For which {slot.replace('_', ' ')}?",
            [],
            user_query, normalized, start,
        )
        clarify.pending = _pending(slot)
        return [], clarify

    return validated, None


def _extract_fill_values(
    user_query: str,
    picked_ids: list[str],
    template_map: dict[str, dict],
    validator: EntityValidator,
    openai_client,
) -> dict[str, str]:
    """Entities already present in the user's utterance, resolved, keyed by
    slot — used to pre-fill clarify-chip placeholders (best-effort)."""
    slot_type: dict[str, str] = {}
    for qid in picked_ids:
        template = template_map.get(qid)
        if template:
            for name, etype in _template_slot_types(template).items():
                slot_type.setdefault(name, etype)
    if not slot_type:
        return {}
    try:
        raw = _extract_slot_values(user_query, slot_type, openai_client)
    except Exception:
        return {}
    fill: dict[str, str] = {}
    for slot, value in raw.items():
        if value is None:
            continue
        try:
            fill[slot] = validator.validate(value, slot_type[slot]).resolved_value
        except ClarificationNeeded:
            # Ambiguous, not unknown. Dropping it puts a bare placeholder where
            # the user's own words should be ("a farmer" instead of "Rajesh
            # Sri"). Keep the raw value: chip send_text routes back through the
            # normal matcher, so a tap lands in the disambiguation flow.
            fill[slot] = str(value)
        except Exception as ex:
            # A silent `continue` here is what made this class of defect
            # invisible — say which slot was dropped and why.
            _log.debug(
                "chip pre-fill dropped slot %s=%r: %s", slot, value, type(ex).__name__
            )
    return fill


def _clarify(
    reason: str,
    prompt: str,
    options: list[Chip],
    user_query: str,
    normalized: str,
    start: float,
) -> RouteResult:
    return RouteResult(
        tier=RouteTier.CLARIFY,
        clarification=Clarification(reason=reason, prompt=prompt, options=options),
        raw_query=user_query,
        normalized_query=normalized,
        total_latency_ms=(time.monotonic() - start) * 1000,
    )


def _elicitation_defaults(validator: EntityValidator) -> dict[str, str]:
    """Slots an elicitation chip must fill that the user did not say.

    Only the fiscal year, and only the most recent loaded one — which is what an
    officer naming no year means, and is read from the data rather than the wall
    clock so it stays right as the extract moves. Best-effort: a validator with
    no years loaded returns nothing and the chips degrade to a readable
    stand-in rather than disappearing.
    """
    try:
        years = validator.fiscal_years()
    except Exception:
        return {}
    return {"date_range": years[-1]} if years else {}


def _broad_question_clarify(
    user_query: str,
    normalized: str,
    start: float,
    *,
    validator: EntityValidator,
    openai_client,
) -> RouteResult | None:
    """"How is Khordha doing?" / "Tell me about Andhrua" — an entity with no
    measure. Offer the measures we hold for that entity rather than a failure
    message. Best-effort: None means "fall through to the miss".

    THE TIERS ARE TRIED WIDEST FIRST, which is the opposite of how they narrow.
    A bare place name is far more often a district than a gram panchayat — there
    are 30 districts an officer names constantly and ~6,800 panchayats — and the
    cost of guessing wrong is only that the miss chips carry the other reading
    anyway.

    The GP probe replaces the AP build's `farmer_name` one. That path existed
    because AP's roster was people; PR&DW's is places, and the same machinery —
    one extraction call, roster disambiguation, reference chips — answers "what
    about Naugaon?" including when several panchayats hold that name.
    """
    try:
        raw = extract_entities(
            user_query, ["district_name", "block_name", "gp_name"], openai_client
        )
    except Exception:
        return None

    for slot, entity_type in (("district_name", "district"),
                              ("block_name", "block")):
        raw_value = raw.get(slot)
        if not raw_value:
            continue
        try:
            place = validator.validate(raw_value, entity_type)
        except Exception:
            continue
        chips = elicitation_chips(entity_type, place.resolved_value,
                                  defaults=_elicitation_defaults(validator))
        if chips:
            return _clarify(
                "broad_question",
                f"What would you like to know about {place.resolved_value}?",
                chips, user_query, normalized, start,
            )

    raw_name = raw.get("gp_name")
    if not raw_name:
        return None
    try:
        gp = validator.validate(raw_name, "gp")
    except ClarificationNeeded as e:
        # Several panchayats answer to the name. Offer the user's own question
        # with each candidate's REFERENCE substituted — every chip routes
        # cleanly and no pending state has to survive the round trip. The
        # reference, not the name: where the candidates are three panchayats all
        # called Naugaon, substituting the name gives three identical chips and
        # no way to choose.
        chips = corrected_query_chips(
            user_query, str(raw_name),
            candidate_replies(e.candidates)[:MAX_CLARIFY_OPTIONS],
            MAX_CLARIFY_OPTIONS,
        )
        if not chips:
            return None
        return _clarify("unknown_entity", str(e), chips, user_query, normalized, start)
    except Exception:
        return None   # not in the roster — the generic miss message is honest

    chips = elicitation_chips("gp", gp.resolved_value,
                              defaults=_elicitation_defaults(validator))
    if not chips:
        return None
    return _clarify(
        "broad_question",
        f"What would you like to know about {gp.resolved_value}?",
        chips, user_query, normalized, start,
    )


def _no_match(
    scored: list[tuple[str, str, float]],
    user_query: str,
    normalized: str,
    start: float,
    *,
    validator: EntityValidator,
    openai_client,
    template_map: dict[str, dict],
) -> RouteResult:
    # Broad-question elicitation (8e): entity resolved, measure missing —
    # "How is Khordha doing?" gets measure chips, not a failure message.
    elicited = _broad_question_clarify(
        user_query, normalized, start,
        validator=validator, openai_client=openai_client,
    )
    if elicited is not None:
        return elicited

    # Nearest-question chips must keep entities the user already gave
    # ("...in Guntur" must not degrade to "...in a district?").
    fill = _extract_fill_values(
        user_query, [qid for qid, _, _ in scored],
        template_map, validator, openai_client,
    )
    result = _fallback(
        "I can't answer that exactly, but I can answer questions like these:",
        user_query, normalized, start,
    )
    result.clarification = Clarification(
        reason="no_match",
        prompt="I can't answer that exactly, but I can answer these:",
        options=_reading_chips(scored, MAX_MISS_SUGGESTIONS, fill),
    )
    return result


def requery_template(
    query_id: str,
    *,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    bound_params: dict[str, str],
    swap_slot: str,
    swap_value: str,
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    """
    Re-execute a catalog template with one bound parameter swapped (used by the
    operations layer for compare). The swapped value is validated against the
    entity registry; everything else is identical to the original execution.
    Raises ValueError / EntityNotFound on bad input.
    """
    template = template_map.get(query_id)
    if template is None:
        raise ValueError(f"'{query_id}' is not a re-queryable template")

    slots = template["param_slots"]
    slot_types = {s["name"]: s.get("entity_type", s["name"]) for s in slots}
    if swap_slot not in slot_types:
        raise ValueError(f"template {query_id} has no '{swap_slot}' parameter")

    resolved = validator.validate(swap_value, slot_types[swap_slot]).resolved_value
    params = dict(bound_params, **{swap_slot: resolved})

    param_values = bind_for_template(
        template, params, context=f" for {query_id}",
        person_ids=_person_ids_for(slots, slot_types, params, validator),
    )

    sql = template["sql_template"]
    date_filter = template.get("date_filter")
    if date_filter and start_date and end_date:
        sql, offset, date_params = _inject_date_filter(
            sql, date_filter["alias"], date_filter["column"],
            template.get("date_kind"), start_date=start_date, end_date=end_date,
            named=param_style(template) == NAMED,
        )
        param_values = _merge_date_binds(param_values, offset, date_params)

    return _exec_template(
        cache_conn, query_id, sql, param_values,
        template.get("result_ttl_seconds", RESULT_CACHE_DEFAULT_TTL),
    )


# ── Frame scope inheritance ───────────────────────────────────────────────────
# A new question asked inside a conversation about one district usually means
# that district. "What is the block-wise sanctioned amount in Khordha?" then
# "how many activities are abandoned" answers STATE-WIDE — a different question
# from the one the user believes they asked, and nothing in the answer says so.
#
# HOW THIS CHANGED IN WP-3. The AP catalogue encoded scope in the id (Gnn-S /
# -D / -M), so narrowing was a lookup for a narrower SIBLING template;
# `_scope_sibling` did that and is retired here, because decision D2 leaves no
# siblings to find. Under D2 the scope is not a different template but an
# UNBOUND OPTIONAL SLOT on the same one — which is exactly what makes the defect
# easier to hit, not harder: every geography-optional template silently answers
# state-wide the moment nothing fills its district slot.
#
# So the mechanism is re-pointed rather than removed: re-serve the SAME query_id
# with the frame's geography bound into the slot the question left empty. The
# two honesty rules are unchanged:
#   - it only ever fires when the question named NO geography of its own;
#   - the answer says the scope was carried over, and ships an undo chip.

# Deepest first — the narrowest scope the frame can supply is the one the
# conversation is actually about.
_GEO_SLOT_ORDER = ("gp_name", "block_name", "district_name")
_GEO_ENTITY_TYPES = frozenset({"gp", "gp_2", "block", "block_2", "district"})

# Wordings that mean "deliberately not narrowed", so inheritance must not fire.
# Bare "all" is excluded as too loose to tell from ordinary phrasing. "across the
# whole state" is here because `statewide_undo_chip` puts it in the chip it
# sends — the undo has to survive its own round trip or tapping it re-inherits
# the scope it was meant to escape.
_EXPLICIT_STATEWIDE = re.compile(
    r"\b(state[\s-]?wide|entire state|whole state|across the state|"
    r"across the whole state|in the state|odisha|orissa|"
    r"all districts|all blocks|all gps|all gram panchayats)\b",
    re.IGNORECASE,
)


def _inheritable_geo_slot(template: dict, frame) -> str | None:
    """The narrowest OPTIONAL geography slot this template left empty and the
    frame can fill. None when there is nothing to inherit."""
    optional = optional_slots(template["param_slots"])
    for slot in _GEO_SLOT_ORDER:
        if slot in optional and frame.bound_params.get(slot):
            return slot
    return None


def inherit_frame_scope(
    result: RouteResult,
    frame,
    *,
    user_query: str,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    dashboard_results: dict[str, list[dict]],
    dashboard_questions: dict[str, str],
    start_date: str | None,
    end_date: str | None,
) -> tuple[RouteResult, dict[str, str]] | None:
    """Re-serve a state-wide answer at the scope the conversation is already in.

    Returns (narrowed result, {slot: value} inherited) or None to leave the
    result alone. Never raises: an inheritance that fails to execute is not
    worth failing a working answer over.
    """
    if result.tier != RouteTier.TIER2_TEMPLATE or not result.query_id:
        return None
    if _EXPLICIT_STATEWIDE.search(user_query):
        return None   # the user said state-wide; narrowing would contradict them
    if any(e.entity_type in _GEO_ENTITY_TYPES for e in (result.entities or [])):
        return None   # the question named its own geography — that one wins

    template = template_map.get(result.query_id)
    if template is None:
        return None
    slot = _inheritable_geo_slot(template, frame)
    if slot is None:
        return None

    # The already-validated entities are kept as they are and the inherited
    # geography is ADDED, so re-serving cannot disturb a slot the user did fill.
    entities: list[ExtractedEntity] = list(result.entities or [])
    inherited: dict[str, str] = {}
    try:
        etype = _template_slot_types(template)[slot]
        entity = validator.validate(frame.bound_params[slot], etype)
        entity.slot_name = slot
        entities.append(entity)
        inherited[slot] = entity.resolved_value

        narrowed = _serve_query_id(
            result.query_id, entities, _QID_TO_INTENT.get(result.query_id),
            user_query=user_query, normalized=normalize(user_query),
            start=time.monotonic(),
            cache_conn=cache_conn, dashboard_results=dashboard_results,
            template_map=template_map, dashboard_questions=dashboard_questions,
            start_date=start_date, end_date=end_date,
        )
    except Exception as ex:
        _log.debug("frame scope inheritance of %s failed: %s", slot, ex)
        return None

    if narrowed.tier != RouteTier.TIER2_TEMPLATE:
        return None
    return narrowed, inherited


def statewide_undo_chip(query_id: str, template_map: dict[str, dict]) -> Chip | None:
    """'Show this state-wide instead' — the escape from an inherited scope.

    Under D2 there is no slotless state-wide sibling to send the user back to:
    the same template answers both ways, and what changes is whether its
    optional geography slot is bound. So the chip sends this template's own
    question with the geography placeholders dropped and an explicit state-wide
    phrase appended.

    That phrase is load-bearing rather than decorative. It is matched by
    `_EXPLICIT_STATEWIDE`, which is what stops the re-asked question inheriting
    the very scope the chip exists to escape — without it, tapping "show this
    state-wide" would silently return the same narrowed answer.
    """
    template = template_map.get(query_id or "")
    if template is None:
        return None
    if not (optional_slots(template["param_slots"]) & set(_GEO_SLOT_ORDER)):
        return None    # nothing to widen — the question has no geography slot

    question = re.sub(r"\s*(?:in|for|of)?\s*\{(?:gp_name|block_name|district_name)\}",
                      "", template["abstract_question"])
    question = re.sub(r"\s{2,}", " ", question).strip().rstrip("?.")
    return Chip(
        label="Show this across the whole state instead",
        send_text=f"{question} across the whole state?",
    )


def serve_frame_edit(
    frame,
    *,
    edit_slot: str | None,
    edit_value: str | None,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    dashboard_results: dict[str, list[dict]],
    dashboard_questions: dict[str, str],
    user_query: str,
    start_date: str | None,
    end_date: str | None,
) -> RouteResult:
    """
    Execute a follow-up as an edit to the current frame (spec Section 4, v1):
    swap one bound parameter and/or change the date range, within the same
    template. Raises ValueError / EntityNotFound on edits that can't apply.

    AN OPTIONAL SLOT THE FRAME DOES NOT BIND STAYS UNBOUND (WP-4c T2b). This
    used to raise `missing '<slot>' in the current context` for any slot absent
    from `bound_params` — a rule inherited from AP, where every slot was
    required and a frame therefore bound all of them. Under D2 it is the normal
    case: `bound_params` only ever holds slots that VALIDATED, so a state-wide
    EXP-001 frame binds `date_range` alone and its three optional geography
    slots are absent by design. The old rule therefore made every state-wide
    frame uneditable, and "what about Laxmipur?" fell through to an LLM re-route
    of the frame's question plus the fragment — measured in WP-4's replays as the
    path G1524 actually took, which is also why the tier check never saw it.
    Leaving the slot unbound is what D2 means by optional: the filter is simply
    off, which is exactly the state the frame was already in.
    """
    template = template_map.get(frame.template_id)
    if template is None:
        raise ValueError("the current result can't be edited — ask the question directly")

    slot_types = {
        s["name"]: s.get("entity_type", s["name"]) for s in template["param_slots"]
    }
    if edit_slot is not None and edit_slot not in slot_types:
        raise ValueError(
            f"the current question has no '{edit_slot}' to change "
            f"(it has: {', '.join(slot_types) or 'none'})"
        )

    optional = optional_slots(template["param_slots"])
    person_bound = _person_bound_slots(template["param_slots"])
    entities: list[ExtractedEntity] = []
    for name, etype in slot_types.items():
        if name == edit_slot and edit_value is not None:
            entity = validator.validate(edit_value, etype)
            entity.slot_name = name
        else:
            current = frame.bound_params.get(name)
            if current is None:
                if name in optional:
                    continue          # the filter was off and stays off (D2)
                raise ValueError(f"missing '{name}' in the current context")
            if name in person_bound:
                # The frame stores a string; a person-bound slot needs the
                # identity behind it, and only the registry has that.
                entity = validator.validate(current, etype)
                entity.slot_name = name
            else:
                entity = ExtractedEntity(
                    slot_name=name, raw_value=current, resolved_value=current,
                    entity_type=etype, confidence="context",
                )
        entities.append(entity)

    return _serve_query_id(
        frame.template_id, entities, None,
        user_query=user_query, normalized=normalize(user_query),
        start=time.monotonic(),
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )


# ── Follow-up fragments that the current template can't execute ──────────────
# "in kurnool?" over a state-wide question is a district edit with nowhere to
# go. serve_drill_hop is the deterministic answer where the catalog holds a
# narrower sibling; ambiguous_fragment_clarify is the honest answer where
# nothing on offer is plausibly the same subject. See fragment_reroute.py.

def serve_drill_hop(
    frame,
    edit_slot: str | None,
    edit_value: str | None,
    *,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    dashboard_results: dict[str, list[dict]],
    dashboard_questions: dict[str, str],
    user_query: str,
    start_date: str | None,
    end_date: str | None,
    name_tier: bool = False,
) -> RouteResult | None:
    """Answer the current question at the geography the fragment named, by
    hopping to the mapped sibling. No LLM call is involved at all.

    `name_tier` marks the case where the place resolved at several tiers and
    only one of them was executable here — the echo then says which tier was
    served, because "Laxmipur" alone does not.

    None means "no hop applies" — no sibling for this slot, a value that isn't a
    real place of that kind, or a REQUIRED slot the frame cannot fill. Every one
    of those falls through to the contextual re-route.

    An OPTIONAL slot the frame does not bind is left unbound, for the same reason
    `serve_frame_edit` now leaves it unbound: under D2 `bound_params` holds only
    the slots that validated, so a state-wide frame legitimately has none of its
    three geography slots, and refusing to hop on that basis retired the
    deterministic path for exactly the frames it was written for. (The AP rule it
    replaces — "a state-wide frame cannot reach a -M template, which also needs
    the district" — was about per-scope SIBLING templates, which D2 removed: the
    hop target is now the frame's own template with one more filter on.)
    """
    target = drill_target(frame.template_id, edit_slot)
    template = template_map.get(target) if target else None
    if template is None:
        return None

    optional = optional_slots(template["param_slots"])
    entities: list[ExtractedEntity] = []
    try:
        for name, etype in _template_slot_types(template).items():
            raw = edit_value if name == edit_slot else frame.bound_params.get(name)
            if raw is None:
                if name in optional:
                    continue
                return None
            entity = validator.validate(raw, etype)
            entity.slot_name = name
            entities.append(entity)
    except Exception as ex:
        # Includes the "is it really a mandal?" check: a value that doesn't
        # validate as the slot's entity type is not a drill, it's a new question.
        _log.debug("drill hop %s -> %s not bindable: %s", frame.template_id, target, ex)
        return None

    result = _serve_query_id(
        target, entities, _QID_TO_INTENT.get(target),
        user_query=user_query, normalized=normalize(user_query),
        start=time.monotonic(),
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )
    if result.tier != RouteTier.TIER2_TEMPLATE:
        return None
    if not result.result and not template.get("expected_empty_on_demo"):
        # The hop bound cleanly but the combination doesn't exist — a mandal of
        # some OTHER district reached through this frame's district. An empty
        # table presented as the answer is the silent wrong answer this whole
        # path exists to remove, so fall through to the contextual re-route.
        _log.debug("drill hop %s -> %s returned no rows", frame.template_id, target)
        return None
    if name_tier and edit_slot:
        result.query_description = name_the_tier(
            result.query_description, edit_value, edit_slot
        )
    return result


def ambiguous_fragment_clarify(
    *,
    frame_question: str | None,
    value: str | None,
    contextual_question: str | None,
    fragment_question: str | None,
    user_query: str,
    start: float | None = None,
    frame_query_id: str | None = None,
    fragment_query_id: str | None = None,
) -> RouteResult:
    """Ask which reading was meant, instead of serving a confident wrong one.

    Both readings go in the prompt in words, and both go in the chips as
    executable catalog questions. The third chip is the escape for a user who
    meant neither — it routes through the miss path, which offers the nearest
    catalog questions.

    THE STANDALONE-FRAGMENT CHIP IS DROPPED WHEN IT SHARES NO SUBJECT with the
    frame. The fragment retrieved here is a bare place ("what about
    Laxmipur?"), so the only signal retrieval had was a NAME — and a chip whose
    only tie to what the user said is a place name is noise dressed as a
    reading. Offering it invites a tap that silently changes the subject. It is
    kept when nothing else survives, because an empty clarification is worse
    than a noisy one; pass both ids to enable the test at all.
    """
    keep_fragment = True
    if fragment_query_id and frame_query_id and contextual_question:
        keep_fragment = templates_share_subject(frame_query_id, fragment_query_id)

    options: list[Chip] = []
    seen: set[str] = set()
    for text in (contextual_question,
                 fragment_question if keep_fragment else None):
        if not text or text in seen:
            continue
        seen.add(text)
        options.append(Chip(label=text, send_text=text))
    options.append(Chip(label="Something else", send_text="Something else"))

    subject = frame_question or "the question you were looking at"
    if value:
        prompt = (
            f"I'm not sure which you meant: “{subject}” narrowed to {value}, "
            f"or a new question about {value}. Which of these?"
        )
    else:
        prompt = (
            f"I'm not sure whether that follows on from “{subject}” or starts a "
            "new question. Which of these?"
        )
    return _clarify(
        "ambiguous_fragment", prompt, options,
        user_query, normalize(user_query),
        start if start is not None else time.monotonic(),
    )


def drill_question(
    query_id: str, fill: dict[str, str], template_map: dict[str, dict]
) -> str | None:
    """A mapped sibling rendered as tappable text, or None if it isn't one."""
    template = template_map.get(query_id)
    if template is None:
        return None
    return readable_question(template["abstract_question"], fill)


# The noun each geography tier is called in a chip and in an echo. Decision
# D18.P3 makes GP/block collisions CLARIFY in v1 rather than infer the tier from
# the sentence, so both readings have to be sayable — "Laxmipur" alone is
# exactly the string that was ambiguous.
TIER_NOUNS: dict[str, str] = {
    "district_name": "district",
    "block_name":    "block",
    "gp_name":       "GP",
}


def name_the_tier(question: str | None, value: str | None, slot: str) -> str | None:
    """'…incurred by Laxmipur in 2024-2025?' -> '…by Laxmipur (GP) in 2024-2025?'

    Used when a place name resolved at MORE THAN ONE tier and the frame's
    template could only execute one of them. The router picked; the echo has to
    say which, or the answer silently asserts a reading the user never made.
    """
    noun = TIER_NOUNS.get(slot)
    if not question or not value or not noun or f"({noun})" in question:
        return question
    return question.replace(str(value), f"{value} ({noun})", 1)


def tier_collision_clarify(
    *,
    frame_question: str | None,
    readings: list[tuple[str, str]],
    user_query: str,
    start: float | None = None,
) -> RouteResult:
    """"Laxmipur block, or Laxmipur GP?" — asked as a TIER question.

    `readings` is [(chip label, send text)], one per tier the place resolves at
    AND the frame's template can execute. This exists because the generic
    "narrowed, or a new question?" prompt is the wrong question to ask here: the
    user's intent to narrow is not in doubt, only which of two same-named places
    they meant, and D18.P3 says ask rather than infer. Answering the wrong
    question makes the officer re-type the name that was ambiguous in the first
    place.
    """
    options = [Chip(label=label, send_text=text) for label, text in readings]
    options.append(Chip(label="Something else", send_text="Something else"))
    names = " or ".join(label for label, _ in readings) or "either"
    subject = frame_question or "the question you were looking at"
    prompt = (
        f"That name belongs to more than one place — did you mean {names}? "
        f"Either way I'll narrow “{subject}”."
    )
    return _clarify(
        "tier_collision", prompt, options,
        user_query, normalize(user_query),
        start if start is not None else time.monotonic(),
    )


def serve_pending_answer(
    pending: PendingClarification,
    answer_value: str,
    *,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    dashboard_results: dict[str, list[dict]],
    dashboard_questions: dict[str, str],
    start_date: str | None,
    end_date: str | None,
) -> RouteResult:
    """
    Resume the question the router paused on: the user's short reply fills the
    missing slot and the pending template executes with all earlier context
    intact. If the template still has another unfilled slot, this returns a
    further clarify carrying updated pending state (chained elicitation).
    """
    template = template_map.get(pending.query_id)
    if template is None:
        raise ValueError(f"'{pending.query_id}' is not a resumable template")

    slot_type = _template_slot_types(template)
    raw_entities = {
        slot: (answer_value if slot == pending.missing_slot else pending.filled.get(slot))
        for slot in slot_type
    }

    start = time.monotonic()
    normalized = normalize(pending.original_query)
    validated, clarify_result = _fill_slots_or_clarify(
        pending.query_id, slot_type, raw_entities, validator,
        pending.original_query, normalized, start,
        optional=optional_slots(template["param_slots"]),
        defaults=slot_defaults(template["param_slots"]),
    )
    if clarify_result is not None:
        return clarify_result

    return _serve_query_id(
        pending.query_id, validated, _QID_TO_INTENT.get(pending.query_id),
        user_query=pending.original_query, normalized=normalized, start=start,
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )


def serve_scope_alternative(
    query_id: str,
    pending: PendingClarification,
    *,
    template_map: dict[str, dict],
    cache_conn,
    validator: EntityValidator,
    dashboard_results: dict[str, list[dict]],
    dashboard_questions: dict[str, str],
    start_date: str | None,
    end_date: str | None,
) -> RouteResult:
    """Answer the BROADER question a template's slot was narrowing, because the
    user said they don't want the narrowing ("all crops").

    Only the alternative's own slots are bound, from what the paused question
    had already resolved — the widened slot is deliberately dropped. The result
    carries the alternative's own query_description, so the answer says which
    question it actually answered.
    """
    template = template_map.get(query_id)
    if template is None:
        raise ValueError(f"'{query_id}' is not a servable scope alternative")

    entities: list[ExtractedEntity] = []
    for name, etype in _template_slot_types(template).items():
        value = pending.filled.get(name)
        if value is None:
            raise ValueError(f"missing '{name}' for scope alternative {query_id}")
        entity = validator.validate(value, etype)
        entity.slot_name = name
        entities.append(entity)

    start = time.monotonic()
    return _serve_query_id(
        query_id, entities, _QID_TO_INTENT.get(query_id),
        user_query=pending.original_query,
        normalized=normalize(pending.original_query), start=start,
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )


# ── Shared back-end: serve a resolved query_id ────────────────────────────────

def _serve_unanswerable(
    query_id: str, user_query: str, normalized: str, start: float,
    template_map: dict[str, dict],
) -> RouteResult:
    """An honest refusal for a question the database genuinely cannot answer.

    These 30 questions are in the retrieval index on purpose (see
    unanswerable_catalog's docstring): officers WILL ask them — the 13 dropped
    ones are all beneficiary questions, and "how many people got a pension here"
    is an obvious thing to want from a panchayat system. Retrieving them and
    saying exactly what is missing is a better answer than the generic miss
    message, which reads as the bot merely failing and leaves the officer
    rephrasing a question that can never work.

    The reason is the WORKBOOK'S OWN, verbatim, for the same reason a caveat is
    verbatim: it is the answer to "why not", and a paraphrase of it is a worse
    answer. Where the workbook names an answerable near-miss, it is offered as a
    chip rather than substituted silently — the user asked for something else and
    gets to choose.
    """
    entry = UNANSWERABLE_CATALOG[query_id]
    result = _fallback(refusal_for(query_id), user_query, normalized, start)
    result.query_id = query_id
    result.query_description = entry["question"]

    alternative = entry.get("alternative")
    template = template_map.get(alternative or "")
    if template is not None:
        question = readable_question(template["abstract_question"])
        result.clarification = Clarification(
            reason="known_unanswerable",
            prompt="The closest question I can answer is:",
            options=[Chip(label=question, send_text=question)],
        )
    return result


def _serve_query_id(
    query_id: str,
    validated_entities: list,
    intent: str | None,
    *,
    user_query: str,
    normalized: str,
    start: float,
    cache_conn,
    dashboard_results: dict[str, list[dict]],
    template_map: dict[str, dict],
    dashboard_questions: dict[str, str],
    start_date: str | None,
    end_date: str | None,
) -> RouteResult:
    # Known-unanswerable — retrieved on purpose, executed never.
    if query_id in UNANSWERABLE_CATALOG:
        return _serve_unanswerable(query_id, user_query, normalized, start,
                                   template_map)

    # Dashboard (Tier-1) — serve pre-computed result.
    #
    # MEMBERSHIP, NOT A PREFIX. This read `query_id.startswith("D")`, which was
    # safe only while no AP template id began with D. Fifteen PR&DW ids do —
    # DQY-001…011 (data quality) and DSS-001…006 (decision support) — and every
    # one of them would have been served here as a dashboard, returning the
    # empty `dashboard_results.get(query_id, [])` with no error and an answer
    # reading "no records matched". Fifteen templates permanently, silently
    # empty. The catalogue an id belongs to is the ground truth; a letter is not.
    if query_id in DASHBOARD_CATALOG:
        return RouteResult(
            tier=RouteTier.TIER1_DASHBOARD,
            result=dashboard_results.get(query_id, []),
            raw_query=user_query,
            normalized_query=normalized,
            total_latency_ms=(time.monotonic() - start) * 1000,
            query_id=query_id,
            intent=intent,
            query_description=dashboard_questions.get(query_id),
            caveat=(DASHBOARD_CATALOG.get(query_id) or {}).get("caveat"),
            start_date=start_date,
            end_date=end_date,
        )

    # Template (Tier-2) — execute with validated params
    template    = template_map[query_id]
    param_slots = template["param_slots"]

    # Build query description with resolved entity values. An Aadhaar is masked
    # to its last four digits — query_description is echoed back to the user and
    # a full Aadhaar must never appear in an answer.
    _display_raw = {"month", "year"}
    entity_values = {}
    for e in validated_entities:
        if e.entity_type == "aadhaar":
            entity_values[e.slot_name] = mask_aadhaar(e.resolved_value)
        elif e.entity_type in _display_raw:
            entity_values[e.slot_name] = e.raw_value
        elif e.confidence == "converted":
            # An amount the user gave in lakhs or crores. Echo their own words
            # AND the figure that was filtered on, so "above 1 lakh" does not
            # come back as the unrecognisable "above 100000" — and so the reader
            # can check the conversion rather than take it on trust.
            entity_values[e.slot_name] = f"{e.raw_value} (₹{e.resolved_value})"
        else:
            entity_values[e.slot_name] = e.resolved_value
    # PER-PLACEHOLDER, never all-or-nothing. `.format(**entity_values)` raises
    # KeyError on the first unbound slot and the old fallback echoed the RAW
    # abstract question, throwing away the substitutions that HAD resolved: the
    # operator's "each GP in 2024-25" came back with `{gp_name}` AND
    # `{date_range}` showing, while the SQL underneath had run correctly. Latent
    # in AP, where every slot was required and the except never fired; under D2
    # a partly-bound template is the normal case.
    query_description = resolved_question(
        template["abstract_question"],
        entity_values,
        unfilled_phrases(param_slots, set(entity_values),
                         template.get("grouped_geo")),
    )
    # A GP whose name is shared resolves to "Naugaon of Barpali" so the
    # panchayat survives a round trip — which renders "…of Barpali of Barpali"
    # in a question that already names the block. Same place named twice, said
    # once. Only an immediate repeat collapses, so two real places never merge.
    query_description = re.sub(
        r"\bof\s+(\S+)\s+of\s+\1\b", r"of \1", query_description, flags=re.IGNORECASE
    )

    params_by_name = {e.slot_name: e.resolved_value for e in validated_entities}
    person_ids = {
        e.slot_name: e.resolved_code for e in validated_entities if e.resolved_code
    }
    is_named = param_style(template) == NAMED
    try:
        param_values = bind_for_template(
            template, params_by_name, context=f" for {query_id}",
            person_ids=person_ids,
        )
    except ValueError as ex:
        return _fallback(f"Query failed to execute: {ex}", user_query, normalized, start)

    # Inject date filter if this template supports it
    sql = template["sql_template"]
    date_filter         = template.get("date_filter")
    date_filter_applied = False
    if date_filter and start_date and end_date:
        try:
            sql, offset, date_params = _inject_date_filter(
                sql, date_filter["alias"], date_filter["column"],
                template.get("date_kind"), start_date=start_date, end_date=end_date,
                named=is_named,
            )
        except DateFilterUnsupported as ex:
            return _fallback(str(ex), user_query, normalized, start)
        param_values        = _merge_date_binds(param_values, offset, date_params)
        date_filter_applied = True

    try:
        result_rows = _exec_template(
            cache_conn, query_id, sql, param_values,
            template.get("result_ttl_seconds", RESULT_CACHE_DEFAULT_TTL),
        )
    except Exception as ex:
        return _fallback(f"Query failed to execute: {ex}", user_query, normalized, start)

    return RouteResult(
        tier=RouteTier.TIER2_TEMPLATE,
        entities=validated_entities,
        result=result_rows,
        raw_query=user_query,
        normalized_query=normalized,
        total_latency_ms=(time.monotonic() - start) * 1000,
        query_id=query_id,
        intent=intent,
        query_description=query_description,
        caveat=template.get("caveat"),
        start_date=start_date,
        end_date=end_date,
        date_filter_applied=date_filter_applied,
    )


# ── A documented refusal must be reachable (D28.5, WP-4c T2c) ─────────────────
#
# THE DEFECT, from WP-4's three replays. Four of the 19 known-unanswerable gold
# rows never reached their `UNANSWERABLE_CATALOG` entry: BEN-001 (3/3) and
# BEN-003 (2/3) got "I couldn't match that exactly. Did you mean one of these?"
# offering IHHL templates; BEN-003's third replay and BEN-010 got the
# broad-question elicitation; and PLN-022 was ANSWERED with PLN-020 (2/3) —
# a template whose own caveat reads "pending_approvals is 0 everywhere because
# approval_date is always populated", i.e. a table of zeros served as the answer
# to "which blocks are consistently delayed". The other 15 rows work, so the
# machinery is right and the mechanism is narrow.
#
# THE MECHANISM. A refusal's fate rests entirely on one LLM judgement, and the
# reranker's own rule set resolves against it: rule 9 says "if one of those
# matches the user's intent, return it", rule 10 says "if NONE of the candidates
# can answer the query exactly, return no_match". A candidate captioned CANNOT BE
# ANSWERED satisfies rule 10 by construction, and rule 10 is the one that wins —
# which is why the failure is 3/3 stable rather than a wobble. Both zone branches
# then render that same entry as an ordinary question chip: a tappable suggestion
# of a question the database cannot answer, whose tap reproduces the identical
# clarification. The refusal was in the candidate list the whole time.
#
# THE FIX IS DETERMINISTIC, because the evidence is. Retrieval rank is not a
# judgement call: if the single closest thing in the whole index to what the
# officer typed is the catalogue's own statement that this question has no
# answer, that statement is the answer. So a rank-0 refusal takes precedence over
# a no-match verdict outright, and over a rerank pick only when retrieval can
# actually tell them apart (see the margin below). Everything else stays a
# clarification — with the refusal labelled as one.


def _refusal_precedence(
    scored: list[tuple[str, str, float]], picked: str | None
) -> str | None:
    """The known-unanswerable that should be served instead of `picked`, or None.

    RANK 0 AND NOTHING WEAKER. "Somewhere in the top 30" is not evidence — the
    unanswerables are 30 of 376 index entries and one is near almost anything.
    Rank 0 means no catalogue entry, answerable or not, matched the question more
    closely.

    AGAINST A RERANK PICK, THE MARGIN APPLIES. `CLARIFY_SCORE_MARGIN` is already
    this codebase's definition of "retrieval cannot separate these two"; inside
    it, overruling the semantic layer with the surface layer would be exactly the
    embedding-order bias the reranker exists to correct. Outside it, the two
    layers genuinely disagree about whether the question is answerable at all,
    and the catalogue's documented "no" is the safer of the two — a near-miss
    that measures something else is the confidently-wrong class this project
    exists to prevent, and PLN-020's all-zero table is what it looks like.

    Against a NO-MATCH verdict no margin is needed: the alternative is a generic
    decline, so this can only ever replace "I failed" with "here is why this
    cannot be answered". It can never displace an answer.
    """
    if not scored:
        return None
    top_qid, _question, top_score = scored[0]
    if top_qid not in UNANSWERABLE_CATALOG or top_qid == picked:
        return None
    if top_score < NO_MATCH_LOWER_THRESHOLD:
        # Below the floor nothing is a match, including this. The generic miss
        # path — which offers the nearest questions — is the honest answer.
        return None
    if picked and picked != "no_match":
        picked_score = next((s for qid, _q, s in scored if qid == picked), None)
        if (picked_score is not None
                and top_score - picked_score < CLARIFY_SCORE_MARGIN):
            return None
    _log.info("refusal precedence: serving %s (retrieval rank 0, score %.4f) "
              "instead of %r", top_qid, top_score, picked)
    return top_qid


def _reading_chips(
    candidates: list[tuple[str, str, float]],
    limit: int,
    fill: dict[str, str] | None = None,
) -> list[Chip]:
    """`question_chips`, with a documented refusal labelled as one.

    An unanswerable entry offered as a plain suggestion reads as a question the
    system is inviting the user to ask, and tapping it produces the same
    clarification it came from. Labelled, the chip is an offer to explain — and
    its send_text is still the entry's own question, which retrieves at rank 0 on
    the way back in and is therefore SERVED as the refusal by
    `_refusal_precedence`. The loop closes without an LLM in it.
    """
    chips: list[Chip] = []
    seen: set[str] = set()
    for qid, question, _score in candidates:
        text = readable_question(question, fill)
        if text in seen:
            continue
        seen.add(text)
        label = (f"Why I can't answer: {text}"
                 if qid in UNANSWERABLE_CATALOG else text)
        chips.append(Chip(label=label, send_text=text))
        if len(chips) == limit:
            break
    return chips


# ── Front-end A: template-direct (vector retrieve → rerank) ───────────────────

def _route_vector(
    user_query, normalized, start, *,
    validator, openai_client, retriever, cache_conn,
    dashboard_results, template_map, dashboard_questions,
    start_date, end_date,
) -> RouteResult:
    scored = retriever.retrieve_scored(normalized, VECTOR_TOP_K)

    # Three-zone confidence handling on retrieval scores
    score_zone = zone([s for _, _, s in scored])
    if score_zone == "no_match":
        return _no_match(
            scored, user_query, normalized, start,
            validator=validator, openai_client=openai_client,
            template_map=template_map,
        )
    if score_zone == "ambiguous":
        # No refusal override here, deliberately: this zone IS "the top two are
        # within the margin", so a rank-0 refusal has not out-matched anything.
        # It is offered as a labelled reading instead, which is what makes it
        # reachable at all (D28.5).
        fill = _extract_fill_values(
            user_query, [qid for qid, _, _ in scored],
            template_map, validator, openai_client,
        )
        return _clarify(
            "ambiguous_templates",
            "I can read that a few ways — which of these did you mean?",
            _reading_chips(scored, MAX_CLARIFY_OPTIONS, fill),
            user_query, normalized, start,
        )

    candidates = [(qid, q) for qid, q, _ in scored]
    query_id, near_misses = rerank(user_query, candidates, openai_client)

    # The catalogue's own "this cannot be answered", when it is the closest thing
    # in the index to the question asked. Before the branch below, because that
    # branch is where BEN-001 and BEN-003 spent all three WP-4 replays; and
    # before the serving call, because PLN-022 was answered with a zero-filled
    # near-miss instead.
    refusal = _refusal_precedence(scored, query_id)
    if refusal is not None:
        return _serve_unanswerable(refusal, user_query, normalized, start,
                                   template_map)

    if query_id == "no_match" or (
        query_id not in DASHBOARD_CATALOG
        and query_id not in UNANSWERABLE_CATALOG
        and query_id not in template_map
    ):
        # No exact match. The clarify chips are the reranker's semantically
        # chosen near-misses — not raw embedding order, whose surface-wording
        # bias can rank the wrong template family on top.
        by_id = {qid: (qid, question, score) for qid, question, score in scored}
        picked = [by_id[qid] for qid in near_misses if qid in by_id]
        if picked:
            # Pre-fill chip placeholders with entities the user already gave
            # ("...in Guntur" must survive into the offered interpretations).
            fill = _extract_fill_values(
                user_query, [qid for qid, _, _ in picked],
                template_map, validator, openai_client,
            )
            return _clarify(
                "ambiguous_templates",
                "I couldn't match that exactly. Did you mean one of these?",
                _reading_chips(picked, MAX_CLARIFY_OPTIONS, fill),
                user_query, normalized, start,
            )
        # The LLM offered no near-misses (off-topic or broad) — go through the
        # miss path, which also tries broad-question elicitation (8e).
        return _no_match(
            scored, user_query, normalized, start,
            validator=validator, openai_client=openai_client,
            template_map=template_map,
        )

    intent = _QID_TO_INTENT.get(query_id)

    # Extract entities for exactly the slots this template needs. Dashboards are
    # precomputed and take none; a known-unanswerable has none to take.
    validated_entities = []
    if query_id in template_map:
        slot_type = _template_slot_types(template_map[query_id])
        if slot_type:
            raw_entities = _extract_slot_values(
                user_query, slot_type, openai_client, intent=intent
            )
            validated_entities, clarify_result = _fill_slots_or_clarify(
                query_id, slot_type, raw_entities, validator,
                user_query, normalized, start,
                optional=optional_slots(template_map[query_id]["param_slots"]),
                defaults=slot_defaults(template_map[query_id]["param_slots"]),
            )
            if clarify_result is not None:
                return clarify_result

    return _serve_query_id(
        query_id, validated_entities, intent,
        user_query=user_query, normalized=normalized, start=start,
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )


# ── Front-end B: legacy intent classification ─────────────────────────────────

def _route_intent(
    user_query, normalized, start, *,
    validator, openai_client, cache_conn,
    dashboard_results, template_map, dashboard_questions,
    start_date, end_date,
) -> RouteResult:
    domain, intent = classify_intent(normalized, openai_client)

    if intent == "no_match":
        return _fallback(
            "I couldn't find a question that matches what you're asking.\n\n"
            + generate_fallback_message(dashboard_questions),
            user_query, normalized, start,
        )

    slots = INTENT_SLOTS.get(intent, [])
    raw_entities: dict[str, str | None] = {}
    if slots:
        raw_entities = extract_entities(user_query, slots, openai_client, intent=intent)

    validated_entities = []
    found_entity_types: set[str] = set()
    for slot in slots:
        raw_val = raw_entities.get(slot)
        if raw_val is None:
            continue
        try:
            entity = validator.validate(raw_val, slot)
            entity.slot_name = slot
            validated_entities.append(entity)
            found_entity_types.add(slot)
        except EntityNotFound:
            pass
        except ClarificationNeeded as e:
            return _fallback(str(e), user_query, normalized, start)

    lookup_key = (intent, frozenset(found_entity_types))
    query_id   = INTENT_LOOKUP.get(lookup_key)

    if query_id is None:
        for drop in found_entity_types:
            reduced = frozenset(found_entity_types - {drop})
            query_id = INTENT_LOOKUP.get((intent, reduced))
            if query_id:
                validated_entities = [e for e in validated_entities if e.slot_name != drop]
                found_entity_types = reduced
                break

    if query_id is None:
        query_id = INTENT_LOOKUP.get((intent, frozenset()))

    if query_id is None:
        return _fallback(
            f"I understood you were asking about **{intent.replace('_', ' ')}** "
            "but couldn't find the right query for the specific filters you mentioned.\n\n"
            + generate_fallback_message(dashboard_questions),
            user_query, normalized, start,
        )

    return _serve_query_id(
        query_id, validated_entities, intent,
        user_query=user_query, normalized=normalized, start=start,
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )


# ── Public entry point ────────────────────────────────────────────────────────

def route(
    user_query: str,
    *,
    validator: EntityValidator,
    openai_client,
    cache_conn,
    dashboard_results: dict[str, list[dict]],
    template_map: dict[str, dict],
    dashboard_questions: dict[str, str],
    retriever=None,
    start_date: str | None = None,
    end_date:   str | None = None,
    session_id: str | None = None,
) -> RouteResult:
    start      = time.monotonic()
    normalized = normalize(user_query)

    if USE_VECTOR_RETRIEVAL and retriever is not None:
        return _route_vector(
            user_query, normalized, start,
            validator=validator, openai_client=openai_client, retriever=retriever,
            cache_conn=cache_conn, dashboard_results=dashboard_results,
            template_map=template_map, dashboard_questions=dashboard_questions,
            start_date=start_date, end_date=end_date,
        )

    return _route_intent(
        user_query, normalized, start,
        validator=validator, openai_client=openai_client,
        cache_conn=cache_conn, dashboard_results=dashboard_results,
        template_map=template_map, dashboard_questions=dashboard_questions,
        start_date=start_date, end_date=end_date,
    )
