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
    question_chips,
    readable_question,
    zone,
)
from .fragment_reroute   import drill_target
from .suggestions       import elicitation_chips
from .config            import (
    MAX_CLARIFY_OPTIONS,
    MAX_MISS_SUGGESTIONS,
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


def _date_predicate(
    alias: str, column: str, date_kind: str | None, start_date: str, end_date: str
) -> tuple[str, list]:
    """(predicate SQL with ? placeholders, the values to bind after the template's own).

    Column references are quoted because AP columns are mixed-case
    ("SurveyDate", "PROCUREMENT_DATE"), and the alias is omitted entirely when
    the template's date_filter carries alias '' — most AP SQL is single-table,
    where `alias.column` would emit a broken leading dot.
    """
    col = f'{alias}."{column}"' if alias else f'"{column}"'

    if date_kind in (None, "", "iso"):
        return f"{col}::DATE BETWEEN ? AND ?", [start_date, end_date]

    if date_kind == "year":
        # agriculture has no date column, only cropyear — a plain number.
        return f"{col} >= ? AND {col} <= ?", [_year_of(start_date), _year_of(end_date)]

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
) -> tuple[str, int, list]:
    """
    Appends the date condition to the SQL, inserting just before the first
    GROUP BY / ORDER BY / LIMIT after the last WHERE clause.

    Returns (sql, placeholder_offset, date_params). Placeholders bind by their
    order in the SQL TEXT, and the predicate can land ahead of one the template
    already has — 'LIMIT ?' on the top-N templates is the case that bites. So the
    caller must splice, not append: `params[:offset] + date_params + params[offset:]`.
    Use merge_date_params() rather than doing it by hand.
    """
    predicate, date_params = _date_predicate(alias, column, date_kind, start_date, end_date)

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
                return head + condition + '\n' + sql[m.start():], head.count("?"), date_params

    return sql.rstrip() + condition, sql.count("?"), date_params


def merge_date_params(param_values: list, offset: int, date_params: list) -> list:
    """Put the date values where their placeholders actually sit in the SQL."""
    return param_values[:offset] + date_params + param_values[offset:]


def _exec_template(cache_conn, query_id: str, sql_template: str, param_values: list, ttl: int) -> list[dict]:
    h = hashlib.sha256(
        json.dumps([str(p) for p in param_values]).encode()
    ).hexdigest()[:8]
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
# not something a user ever says ("how long is an Aadhaar?"). Asking the LLM for
# them wastes a slot and asking the user produces a nonsense clarify prompt, so
# they are filled in here before extraction.
_CONSTANT_ENTITY_TYPES: dict[str, str] = {"aadhaar_length": "12"}

# Numeric slots whose value the QUESTION IMPLIES, so asking for it is a stall
# rather than a clarification: "Rank farmers by number of schemes enrolled."
# does not need "for which top n?" — a ranking implies a list length, and a
# tolerance question implies the standard tolerance.
#
# Strictly numeric-and-presentational. A categorical slot (crop, scheme,
# district) or a threshold that changes the population (threshold_hectares,
# scheme_count) must NEVER get a default: guessing there silently answers a
# different question than the one asked. Routing handles those instead — the
# rerank descriptions say which template applies when no value is named.
_DEFAULT_ENTITY_VALUES: dict[str, str] = {
    "top_n": "10",          # a ranking with no length asked for
    "tolerance_pct": "10",  # matches the P11 answer-key figure
}

# A land threshold stated outright — "under 2 acres", "less than 50 cents",
# "below 1.5 ha". These are the common shapes, and reading them here means the
# frequent case never depends on the LLM at all: not just deterministic
# arithmetic (the validator handles that), but deterministic end to end.
# Anything this cannot see still goes to the extractor.
_LAND_THRESHOLD_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*(acres?|ac|cents?|hectares?|ha)(?![a-z])",
    re.IGNORECASE,
)
# A RANGE is not a threshold: "between 1 and 2 acres" has two figures and only
# the second carries a unit, so the plain scan would see one match and silently
# answer "under 2 acres". One threshold slot cannot express a range, so hand the
# sentence to the extractor instead of guessing.
_LAND_RANGE_RE = re.compile(
    r"\bbetween\b|"
    r"\d+(?:\.\d+)?\s*(?:acres?|ac|cents?|hectares?|ha)?\s*(?:and|to|–|—|-)\s*\d",
    re.IGNORECASE,
)
# The policy bands, which name a threshold without stating a figure.
_LAND_BAND_VALUES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bsmall\s+(?:and|or|/)\s+marginal\b|\bmarginal\s+(?:and|or|/)\s+small\b",
                re.IGNORECASE), "2"),
    (re.compile(r"\bmarginal\b", re.IGNORECASE), "1"),
    (re.compile(r"\bsmall\b", re.IGNORECASE), "2"),
]


def land_threshold_from_text(text: str) -> str | None:
    """'farmers under 2 acres' -> '2 acres'. None when it is not stated plainly.

    Returns the figure WITH its unit word, exactly the shape the extractor is
    now asked for, so the validator does the one conversion either way. Only a
    SINGLE unambiguous match counts — two figures in one question ("between 1
    and 2 acres") is not something one threshold slot can represent, so that
    falls through to the LLM rather than silently picking one.
    """
    if _LAND_RANGE_RE.search(text or ""):
        return None
    matches = _LAND_THRESHOLD_RE.findall(text or "")
    if len(matches) == 1:
        number, unit = matches[0]
        return f"{number} {unit.lower()}"
    if matches:
        return None          # ambiguous — let the extractor read the sentence
    for pattern, hectares in _LAND_BAND_VALUES:
        if pattern.search(text or ""):
            return hectares  # bands are defined in hectares, so no unit word
    return None


def _extract_slot_values(
    user_query: str,
    slot_type: dict[str, str],
    openai_client,
    *,
    intent: str | None = None,
) -> dict[str, str | None]:
    """extract_entities() over the genuinely user-supplied slots, with the
    catalog's constant slots filled in afterwards, and land thresholds read
    straight out of the text when they are stated plainly."""
    prefilled: dict[str, str] = {}
    for slot, etype in slot_type.items():
        if etype == "threshold_hectares":
            found = land_threshold_from_text(user_query)
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
    filter several subqueries by the same district/mandal/farmer).

    A slot may declare {"bind": "aadhaar"}, and every per-farmer template does.
    It binds the resolved PERSON's Aadhaar rather than their name, because a
    name is not a person: 71% of roster names are shared, so a name-keyed filter
    silently returned — and F12 summed — everyone who happened to be called
    that. `person_ids` carries slot -> Aadhaar for the entities that resolved to
    one individual; a person-bound slot with nothing there is a bug upstream and
    fails loudly rather than falling back to the name.
    """
    ordered = sorted(param_slots, key=lambda s: s["position"])
    person_ids = person_ids or {}
    missing = [
        n for n in dict.fromkeys(s["name"] for s in ordered)
        if n not in params_by_name
    ]
    if missing:
        raise ValueError(
            f"missing parameter(s){context}: {', '.join(missing)}"
        )

    values = []
    for slot in ordered:
        if slot.get("bind") == "aadhaar":
            aadhaar = person_ids.get(slot["name"])
            if not aadhaar:
                raise ValueError(
                    f"'{slot['name']}'{context} did not resolve to one person"
                )
            values.append(aadhaar)
        else:
            values.append(params_by_name[slot["name"]])
    return values


def _person_bound_slots(param_slots: list[dict]) -> set[str]:
    """The slot names this template binds by person rather than by name."""
    return {s["name"] for s in param_slots if s.get("bind") == "aadhaar"}


def _person_ids_for(
    param_slots: list[dict],
    slot_types: dict[str, str],
    params_by_name: dict,
    validator: EntityValidator,
) -> dict[str, str]:
    """Recover each person-bound slot's Aadhaar by re-resolving its value.

    A context frame stores bound parameters as plain strings, so an identity
    resolved on the original turn is not in it. Re-validating gets it back: the
    roster resolves a person REFERENCE ('Lakshmi Devi of Rambilli') to the same
    individual every time, which is exactly why resolved_value carries the
    village whenever a name is shared.
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
        if entity.person_aadhaar:
            person_ids[name] = entity.person_aadhaar
    return person_ids


def _fill_slots_or_clarify(
    query_id: str,
    slot_type: dict[str, str],
    raw_entities: dict,
    validator: EntityValidator,
    user_query: str,
    normalized: str,
    start: float,
) -> tuple[list[ExtractedEntity], RouteResult | None]:
    """Validate every slot value, or return a clarify carrying pending state so
    the user's next message can resume this exact question.

    Slots the user DID supply are validated first, even when an earlier slot is
    missing, so the pending state carries them. The AP catalog makes this
    load-bearing: every mandal-scoped question reads "…in {mandal} mandal" but
    its SQL also needs {district}, so the router must ask for the district
    without throwing away the mandal the user just named.
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
        if raw_val is None:
            # A slot the question implies is filled from the default table rather
            # than clarified for. Applied here, in the one place every path
            # validates through, so the vector path and the resumed-pending path
            # behave identically.
            raw_val = _DEFAULT_ENTITY_VALUES.get(slot_type[slot])
        if raw_val is None:
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


def _broad_question_clarify(
    user_query: str,
    normalized: str,
    start: float,
    *,
    validator: EntityValidator,
    openai_client,
) -> RouteResult | None:
    """"How is Krishna doing?" / "Tell me what we know about Rajesh Sri" — an
    entity with no measure. Offer the measures we hold for that entity rather
    than a failure message. Best-effort: None means "fall through to the miss".

    District wins ties on purpose. Many AP district names ("Krishna", "Guntur")
    also occur as farmer names, and a bare place name almost always means the
    place. The cost is that "Tell me about Rajesh Sri in Guntur" elicits on
    Guntur — acceptable, because the miss chips still carry the farmer name.

    Note this is the ONE-farmer path and deliberately keeps roster
    disambiguation. F14 ("which farmers share the name X?") is the opposite
    question — it uses entity_type name_search precisely to bypass this — and
    reaches its own template through normal routing, never through here.
    """
    try:
        raw = extract_entities(user_query, ["district", "farmer_name"], openai_client)
    except Exception:
        return None

    raw_district = raw.get("district")
    if raw_district:
        try:
            district = validator.validate(raw_district, "district")
        except Exception:
            pass
        else:
            chips = elicitation_chips("district", district.resolved_value)
            if chips:
                return _clarify(
                    "broad_question",
                    f"What would you like to know about {district.resolved_value}?",
                    chips, user_query, normalized, start,
                )

    raw_name = raw.get("farmer_name")
    if not raw_name:
        return None
    try:
        farmer = validator.validate(raw_name, "farmer_name")
    except ClarificationNeeded as e:
        # Several people answer to the name. Offer the user's own question with
        # each candidate's REFERENCE substituted — every chip routes cleanly and
        # no pending state has to survive the round trip. The reference, not the
        # name: where the candidates are four people all called Lakshmi Devi,
        # substituting the name gives four identical chips and no way to choose.
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

    chips = elicitation_chips("farmer_name", farmer.resolved_value)
    if not chips:
        return None
    return _clarify(
        "broad_question",
        f"What would you like to know about {farmer.resolved_value}?",
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
    # "How is Krishna doing?" gets measure chips, not a failure message.
    # One extraction call covers both probes; district is tried FIRST because
    # district names are also farmer names ("Krishna"), and a district reading
    # of a bare place name is the safer default.
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
        options=question_chips(scored, MAX_MISS_SUGGESTIONS, fill),
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

    param_values = bind_param_values(
        slots, params, context=f" for {query_id}",
        person_ids=_person_ids_for(slots, slot_types, params, validator),
    )

    sql = template["sql_template"]
    date_filter = template.get("date_filter")
    if date_filter and start_date and end_date:
        sql, offset, date_params = _inject_date_filter(
            sql, date_filter["alias"], date_filter["column"],
            template.get("date_kind"), start_date=start_date, end_date=end_date,
        )
        param_values = merge_date_params(param_values, offset, date_params)

    return _exec_template(
        cache_conn, query_id, sql, param_values,
        template.get("result_ttl_seconds", RESULT_CACHE_DEFAULT_TTL),
    )


# ── Frame scope inheritance ───────────────────────────────────────────────────
# A new question asked inside a conversation about one district usually means
# that district. "How much was procured in each mandal of East Godavari?" then
# "how many small or marginal farmers" routes to G06-S and answers STATE-WIDE —
# a different question from the one the user believes they asked, and nothing in
# the answer says so.
#
# The catalog's Gnn-S / -D / -M convention encodes scope in the id (46 families,
# every one with all three), so narrowing is a deterministic sibling lookup, not
# a guess. Two rules keep it honest:
#   - it only ever fires when the question named NO geography of its own;
#   - the answer says the scope was carried over, and ships an undo chip.

_GEO_SLOT_ORDER = ("mandal", "district")   # deepest first

# Wordings that mean "deliberately not narrowed". Bare "ap" and bare "all" are
# excluded: too loose to distinguish from ordinary phrasing.
_EXPLICIT_STATEWIDE = re.compile(
    r"\b(state[\s-]?wide|entire state|whole state|across the state|"
    r"in the state|andhra pradesh)\b",
    re.IGNORECASE,
)


def _scope_sibling(query_id: str, frame, template_map: dict[str, dict]) -> str | None:
    """The narrower sibling of a state-level template that the frame can fill."""
    match = re.match(r"^(.+)-S$", query_id or "")
    if not match:
        return None
    for suffix in ("-M", "-D"):
        sibling = match.group(1) + suffix
        template = template_map.get(sibling)
        if template is None:
            continue
        needed = {s["name"] for s in template["param_slots"]}
        if needed and needed <= set(frame.bound_params):
            return sibling
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
    if any(e.entity_type in _GEO_SLOT_ORDER for e in (result.entities or [])):
        return None   # the question named its own geography — that one wins

    sibling = _scope_sibling(result.query_id, frame, template_map)
    if sibling is None:
        return None

    template = template_map[sibling]
    entities: list[ExtractedEntity] = []
    inherited: dict[str, str] = {}
    try:
        for name, etype in _template_slot_types(template).items():
            value = frame.bound_params[name]
            entity = validator.validate(value, etype)
            entity.slot_name = name
            entities.append(entity)
            if name in _GEO_SLOT_ORDER:
                inherited[name] = entity.resolved_value

        narrowed = _serve_query_id(
            sibling, entities, _QID_TO_INTENT.get(sibling),
            user_query=user_query, normalized=normalize(user_query),
            start=time.monotonic(),
            cache_conn=cache_conn, dashboard_results=dashboard_results,
            template_map=template_map, dashboard_questions=dashboard_questions,
            start_date=start_date, end_date=end_date,
        )
    except Exception as ex:
        _log.debug("frame scope inheritance to %s failed: %s", sibling, ex)
        return None

    if narrowed.tier != RouteTier.TIER2_TEMPLATE:
        return None
    return narrowed, inherited


def statewide_undo_chip(query_id: str, template_map: dict[str, dict]) -> Chip | None:
    """'Show this state-wide instead' — the escape from an inherited scope.

    The -S question is slotless, so its own text routes cleanly through the
    normal matcher and lands back on the un-narrowed answer.
    """
    match = re.match(r"^(.+)-[DM]$", query_id or "")
    if not match:
        return None
    template = template_map.get(match.group(1) + "-S")
    if template is None or template["param_slots"]:
        return None
    question = template["abstract_question"]
    return Chip(label="Show this state-wide instead", send_text=question)


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

    person_bound = _person_bound_slots(template["param_slots"])
    entities: list[ExtractedEntity] = []
    for name, etype in slot_types.items():
        if name == edit_slot and edit_value is not None:
            entity = validator.validate(edit_value, etype)
            entity.slot_name = name
        else:
            current = frame.bound_params.get(name)
            if current is None:
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
) -> RouteResult | None:
    """Answer the current question at the geography the fragment named, by
    hopping to the mapped sibling. No LLM call is involved at all.

    None means "no hop applies" — no sibling for this slot, a value that isn't a
    real place of that kind, or a sibling whose other slots the frame can't fill
    (a state-wide frame cannot reach a -M template, which also needs the
    district). Every one of those falls through to the contextual re-route.
    """
    target = drill_target(frame.template_id, edit_slot)
    template = template_map.get(target) if target else None
    if template is None:
        return None

    entities: list[ExtractedEntity] = []
    try:
        for name, etype in _template_slot_types(template).items():
            raw = edit_value if name == edit_slot else frame.bound_params.get(name)
            if raw is None:
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
    return result


def ambiguous_fragment_clarify(
    *,
    frame_question: str | None,
    value: str | None,
    contextual_question: str | None,
    fragment_question: str | None,
    user_query: str,
    start: float | None = None,
) -> RouteResult:
    """Ask which reading was meant, instead of serving a confident wrong one.

    Both readings go in the prompt in words, and both go in the chips as
    executable catalog questions. The third chip is the escape for a user who
    meant neither — it routes through the miss path, which offers the nearest
    catalog questions.
    """
    options: list[Chip] = []
    seen: set[str] = set()
    for text in (contextual_question, fragment_question):
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
    # Dashboard (Tier-1) — serve pre-computed result
    if query_id.startswith("D"):
        return RouteResult(
            tier=RouteTier.TIER1_DASHBOARD,
            result=dashboard_results.get(query_id, []),
            raw_query=user_query,
            normalized_query=normalized,
            total_latency_ms=(time.monotonic() - start) * 1000,
            query_id=query_id,
            intent=intent,
            query_description=dashboard_questions.get(query_id),
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
            # A land threshold the user gave in acres or cents. Echo their own
            # words and show the conversion, so "less than 1 acre" does not come
            # back as the unrecognisable "less than 0.4047 hectares".
            entity_values[e.slot_name] = f"{e.raw_value} ({e.resolved_value} ha)"
        else:
            entity_values[e.slot_name] = e.resolved_value
    try:
        query_description = template["abstract_question"].format(**entity_values)
    except KeyError:
        query_description = template["abstract_question"]
    # Every threshold_hectares question reads "{slot} hectares", which turns into
    # "1 acre (0.4047 ha) hectares" once the echo above carries its own unit.
    query_description = re.sub(
        r"(\(\d+(?:\.\d+)?\s*ha\))\s+hectares\b", r"\1", query_description
    )
    # Q125 reads "{farmer_name} of {village}", and a farmer whose name is shared
    # resolves to "Lakshmi Devi of Rambilli" so the person survives a round trip
    # — which renders "…of Rambilli of Rambilli". Same place named twice, said
    # once. Only an immediate repeat collapses, so two real places never merge.
    query_description = re.sub(
        r"\bof\s+(\S+)\s+of\s+\1\b", r"of \1", query_description, flags=re.IGNORECASE
    )

    params_by_name = {e.slot_name: e.resolved_value for e in validated_entities}
    person_ids = {
        e.slot_name: e.person_aadhaar for e in validated_entities if e.person_aadhaar
    }
    try:
        param_values = bind_param_values(
            param_slots, params_by_name, context=f" for {query_id}",
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
            )
        except DateFilterUnsupported as ex:
            return _fallback(str(ex), user_query, normalized, start)
        param_values        = merge_date_params(param_values, offset, date_params)
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
        start_date=start_date,
        end_date=end_date,
        date_filter_applied=date_filter_applied,
    )


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
        fill = _extract_fill_values(
            user_query, [qid for qid, _, _ in scored],
            template_map, validator, openai_client,
        )
        return _clarify(
            "ambiguous_templates",
            "I can read that a few ways — which of these did you mean?",
            question_chips(scored, MAX_CLARIFY_OPTIONS, fill),
            user_query, normalized, start,
        )

    candidates = [(qid, q) for qid, q, _ in scored]
    query_id, near_misses = rerank(user_query, candidates, openai_client)

    if query_id == "no_match" or (
        not query_id.startswith("D") and query_id not in template_map
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
                question_chips(picked, MAX_CLARIFY_OPTIONS, fill),
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

    # Extract entities for exactly the slots this template needs
    validated_entities = []
    if not query_id.startswith("D"):
        slot_type = _template_slot_types(template_map[query_id])
        if slot_type:
            raw_entities = _extract_slot_values(
                user_query, slot_type, openai_client, intent=intent
            )
            validated_entities, clarify_result = _fill_slots_or_clarify(
                query_id, slot_type, raw_entities, validator,
                user_query, normalized, start,
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
