from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
import time
from uuid import uuid4
from datetime import date

def _last_year_range() -> tuple[str, str]:
    y = date.today().year - 1
    return f"{y}-01-01", f"{y}-12-31"
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI

from db_factory import get_adapter
from query_router.entity_validator  import EntityValidator
from query_router.entity_extractor  import refresh_prompt_enums
from query_router.router            import (
    route,
    ambiguous_fragment_clarify,
    drill_question,
    inherit_frame_scope,
    requery_template,
    serve_drill_hop,
    serve_frame_edit,
    serve_pending_answer,
    serve_scope_alternative,
    statewide_undo_chip,
    tier_collision_clarify,
    TIER_NOUNS,
)
from query_router.vector_retriever  import VectorRetriever
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.template_catalog  import TEMPLATE_CATALOG
from query_router.config            import (MAX_SUGGESTION_CHIPS, USE_VECTOR_RETRIEVAL,
                                            LLM_TIMEOUT_SECONDS)
from query_router.models            import (
    Chip,
    Clarification,
    ContextFrame,
    OperationRequest,
    OperationResult,
    RouteResult,
    RouteTier,
)
from query_router.pending_resolver  import (
    REASK,
    RESUME,
    SERVE_ALTERNATIVE,
    resolve_pending_reply,
)
from query_router.interpretation   import (
    Interpretation,
    against_frame,
    against_pending,
    operation_detail,
    period_detail,
    readable_slot,
    slot_detail,
)
from query_router.context_store     import ContextStore, build_context_frame
from query_router.column_metadata   import build_catalog_column_metadata
from query_router.operations        import run_operation
from query_router.followup_classifier import (
    catalog_question_patterns,
    classify_followup,
    matches_catalog_question,
)
from query_router.fragment_reroute  import (
    GEO_SLOTS,
    combined_question,
    drill_target,
    executable_geo_slots,
    fragment_place_phrase,
    geo_vocabulary_tokens,
    is_slot_only_fragment,
    templates_share_subject,
)
from query_router.followup_classifier import FrameEdit
from query_router.suggestions       import suggest_followups
from query_router.echo              import (
    append_caveat,
    echo_answer,
    operation_answer,
    operation_description,
)
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
from query_router.date_phrase       import extract_date_window
from query_router.preprocessor      import normalize
from query_router.zones             import readable_question

# A bare place name is read as the widest scope it validates as — "Bhubaneswar"
# is a district before it is the block of the same name.
#
# TIER PRECEDENCE IS NO LONGER A SILENT PICK (D28.4, WP-4c T2b). This list used
# to be walked widest-first with any tier the frame ALREADY BOUND skipped, so a
# GP-scoped question read "what about Laxmipur?" as the block it was not: only
# block and district competed, block won, and the drill hop then bound the OLD GP
# together with the NEW block, returned zero rows and abandoned the follow-up
# (operator report, 2026-08-13). The bound tier now COMPETES, as a replacement
# reading — "the same question for Laxmipur GP" is at least as likely as "…for
# Laxmipur block" — and the rule is:
#
#   one viable reading   -> serve it, and name the tier in the echo when the
#                           NAME was ambiguous;
#   two or more          -> the tier-qualified clarification (D18.P3: ask which
#                           place, never infer which tier);
#   the user said which  -> "in Laxmipur block?" is not ambiguous. An explicit
#                           tier noun in the message settles it and nothing is
#                           asked.
#
# A reading at one tier DROPS any bound geography NARROWER than it, because
# "what about Laxmipur block?" over an Andhrua-GP answer means the block, not
# Andhrua-inside-Laxmipur. Wider bound scopes are kept: a district on screen
# still contains the block just named.
#
# PAIRED, because the two halves are no longer the same word and mixing them is
# silent: a context frame keys `bound_params` by the workbook's BIND NAME
# (`district_name`), while the entity registry is keyed by ENTITY TYPE
# (`district`). `registry_values("district_name")` returns [] rather than
# raising, so a mix-up would empty the place vocabulary and simply stop every
# follow-up fragment working, with nothing in the logs.
GEO_TIERS_WIDEST_FIRST: tuple[tuple[str, str], ...] = (
    ("district_name", "district"),
    ("block_name",    "block"),
    ("gp_name",       "gp"),
)
GEO_SLOTS_WIDEST_FIRST = tuple(slot for slot, _ in GEO_TIERS_WIDEST_FIRST)
GEO_ENTITY_TYPES_WIDEST_FIRST = tuple(etype for _, etype in GEO_TIERS_WIDEST_FIRST)

_context_store = ContextStore()
_catalog_column_metadata = build_catalog_column_metadata(DASHBOARD_CATALOG, TEMPLATE_CATALOG)

app = FastAPI(title="Odisha PR&DW Panchayat Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons ────────────────────────────────────────────────────────────────
_validator:           EntityValidator | None       = None
_openai_client:       OpenAI | None                = None
_retriever:           VectorRetriever | None       = None
_dashboard_results:   dict[str, list[dict]]        = {}
_dashboard_questions: dict[str, str]               = {}
_template_map:        dict[str, dict]              = {}
_catalog_patterns:    list                         = []  # compiled catalog-question shapes
_geo_tokens:          set[str]                     = set()  # words that occur in place names
_default_start_date:  str
_default_end_date:    str
_default_start_date, _default_end_date = _last_year_range()


@app.on_event("startup")
def startup():
    global _validator, _openai_client, _retriever
    global _dashboard_results, _dashboard_questions, _template_map
    global _default_start_date, _default_end_date

    adapter = get_adapter()
    print("[startup] DB ready")

    # Auto-seed cache (in-memory adapter needs seeding on each start)
    from startup import seed as seed_cache
    seed_cache(adapter, force=False)

    print(f"[startup] Default date range: {_default_start_date} to {_default_end_date}")

    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if not oai_key:
        print("[startup] WARNING: OPENAI_API_KEY not set — /query endpoint disabled")
        return

    # A client-level timeout, because two call paths do not set one per request:
    # the startup index build and the query-time embedding in VectorRetriever.
    # The four chat sites pass timeout=LLM_TIMEOUT_SECONDS themselves and are
    # unaffected by this default.
    #
    # Without it a stalled embedding blocks startup FOREVER. The index build
    # below is wrapped in try/except so a failure degrades to intent
    # classification and the app still serves -- but a hang is not an exception,
    # so that fallback never runs, uvicorn never binds, and the health check
    # never passes. Observed in ECS: tasks sat idle at 0.7 CPU units past the
    # grace period and were killed, repeatedly, while a task started earlier
    # kept serving. The service could not be replaced.
    _openai_client = OpenAI(api_key=oai_key, timeout=LLM_TIMEOUT_SECONDS)
    _validator     = EntityValidator(adapter)

    # The extraction prompt's enum lists are GENERATED from the registry, never
    # hand-written — an incomplete enumeration is a value the extractor cannot
    # emit, and that failure is silent (see entity_extractor's docstring). The
    # registry only exists once the validator above has read the database, so
    # this is the one place the prompt can be finalised.
    refresh_prompt_enums(_validator.registry_values)

    # The place vocabulary, as words. Used to tell a follow-up FRAGMENT ("in
    # Ganjam?") from a question that merely mentions a place. Indexed by ENTITY
    # TYPE — `fragment_reroute.GEO_SLOTS` holds bind names, which the registry
    # does not answer to.
    _geo_tokens.update(geo_vocabulary_tokens(
        *(_validator.registry_values(etype)
          for etype in GEO_ENTITY_TYPES_WIDEST_FIRST)
    ))

    # Load pre-computed dashboard results from cache
    rows = adapter.execute(
        "SELECT query_id, result FROM dashboard_cache WHERE status = 'FRESH'"
    ).fetchall()
    for qid, result_json in rows:
        if result_json:
            try:
                _dashboard_results[qid] = json.loads(result_json)
            except Exception:
                pass

    _dashboard_questions = {k: v["question"] for k, v in DASHBOARD_CATALOG.items()}
    _template_map        = {k: v for k, v in TEMPLATE_CATALOG.items()}
    _catalog_patterns.extend(catalog_question_patterns(
        [t["abstract_question"] for t in _template_map.values()]
        + list(_dashboard_questions.values())
    ))

    # Build the vector-retrieval index (embeds the catalog once; cached to .tmp)
    if USE_VECTOR_RETRIEVAL:
        try:
            # The known-unanswerables are indexed alongside the templates on
            # purpose: an officer's beneficiary question has to RETRIEVE before
            # it can be refused with a reason instead of a generic miss.
            _retriever = VectorRetriever(
                _openai_client, DASHBOARD_CATALOG, TEMPLATE_CATALOG,
                UNANSWERABLE_CATALOG,
            )
            print(f"[startup] Vector retriever ready — {len(_retriever.ids)} catalog entries")
        except Exception as e:
            print(f"[startup] WARNING: vector retriever failed to build ({e}) — "
                  "falling back to intent classification")
            _retriever = None

    print(f"[startup] Router ready — "
          f"{len(_dashboard_results)} cached results, "
          f"{len(_template_map)} templates, "
          f"mode={'vector' if _retriever else 'intent'}")


# ── Models ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    message:    str
    session_id: Optional[str] = None
    reset_context: bool = False
    start_date: Optional[str] = None   # YYYY-MM-DD; defaults to last full month of data
    end_date:   Optional[str] = None   # YYYY-MM-DD
    from_chip:  bool = False           # tapped chip: text we generated — skip the
                                       # follow-up classifier, go straight to matching

class QueryResponse(BaseModel):
    session_id:          str
    context_frame:       Optional[ContextFrame] = None
    tier:               str
    answer:             str
    result:             Optional[list[dict]] = None
    query_id:           Optional[str]        = None
    query_description:  Optional[str]        = None
    intent:             Optional[str]        = None
    entities:           Optional[list[dict]] = None
    # The matched catalogue entry's answerability note, when it has one. The
    # answer layer and the frontend are responsible for surfacing it; it is a
    # separate field rather than glued onto `answer` so a caveat can be rendered
    # distinctly (and cannot be lost when the answer text is regenerated).
    caveat:             Optional[str]        = None
    # {"start_date", "end_date", "is_default", "derived_from_question"} —
    # derived_from_question marks a window read out of the question text rather
    # than sent by the date picker, so the UI can show what it actually answered.
    date_range:          dict                 = {}
    date_filter_applied: bool                = False
    latency_ms:         float
    operation:          Optional[str]        = None  # set when the answer is an operation result
    operation_mode:     Optional[str]        = None  # client | requery | rejected
    clarification:      Optional[Clarification] = None
    suggestions:        Optional[list[Chip]]    = None
    # WHICH QUESTION THIS ANSWERS, and how the message got there. Every path
    # that binds a message to the question already on screen stamps it; anything
    # routed standalone leaves the default, and the UI then draws nothing. See
    # query_router/interpretation.py — the reading is invisible without this
    # field, because a frame edit returns an ordinary successful answer that no
    # client can tell apart from a fresh question.
    interpretation:     Interpretation = Interpretation()


def _looks_like_slot_answer(message: str) -> bool:
    """A bare answer to a pending clarification ('Krishna', 'Ramesh Naidu'),
    not a fresh question. Long messages route normally."""
    return len(message.strip().strip("?.!").split()) <= 6


def _catalog_question(query_id: Optional[str]) -> Optional[str]:
    if not query_id:
        return None
    if query_id in _template_map:
        return _template_map[query_id]["abstract_question"]
    return _dashboard_questions.get(query_id)


def _catalog_caveat(query_id: Optional[str]) -> Optional[str]:
    """The answerability note for a query_id, from whichever catalogue holds it.

    Used by the endpoints that serve rows WITHOUT re-routing (/context/pop
    restores a stored table, /operation recomputes on one). The caveat is a
    property of the question the rows answer, so it has to be re-attached there
    too — dropping it on the way back through a breadcrumb would quietly turn a
    caveated answer into an uncaveated one.
    """
    if not query_id:
        return None
    if query_id in _template_map:
        return _template_map[query_id].get("caveat")
    return (DASHBOARD_CATALOG.get(query_id) or {}).get("caveat")


class OperationCallRequest(OperationRequest):
    session_id:    str
    result_set_id: str  # guard: must match the current frame's table


# Tiers that put an ANSWER on the officer's screen, as opposed to a question or
# a refusal. `RouteTier`'s values are "tier1"/"tier2"; the operation path sets
# the literal "operation".
_SERVED_TIERS = frozenset({"tier1", "tier2", "operation"})


def _echoed(tier, query_description: str | None, query_id: str | None) -> str | None:
    """Every served answer restates the question it answered. Enforced (D31.2).

    WHY THIS IS AN ASSERTION AND NOT A DEFAULT. `query_description` is the
    disclosure D3 rests on, and the one path that quietly left it None — the
    operations path — is where the truncated-table defect lived undetected for a
    whole work package. WP-4c measured 1 / 4 / 3 served answers per replay with
    no echo at all. Substituting a placeholder here would restore the silence in
    a form that reads like an answer; raising makes a missing echo a failure of
    the run, visible to the eval harness and to the suite, on the first replay
    rather than the fiftieth.

    Non-answer tiers pass through untouched: a clarification's prompt IS its
    text, and a refusal states the workbook's reason.
    """
    value = getattr(tier, "value", tier)
    if value in _SERVED_TIERS and not (query_description or "").strip():
        raise AssertionError(
            f"served answer for query_id={query_id!r} (tier={value}) carries no "
            f"query_description — D3 requires every served answer to restate the "
            f"question it answered"
        )
    return query_description


def _requery_for_frame(frame: ContextFrame, start_date: str, end_date: str):
    """Compare hook: re-run the frame's template with one parameter swapped."""
    if frame.time_range.grain == "day" and frame.time_range.start and frame.time_range.end:
        start_date, end_date = frame.time_range.start, frame.time_range.end

    def requery(slot: str, value: str) -> list[dict]:
        return requery_template(
            frame.template_id,
            template_map=_template_map,
            cache_conn=get_adapter(),
            validator=_validator,
            bound_params=frame.bound_params,
            swap_slot=slot,
            swap_value=value,
            start_date=start_date,
            end_date=end_date,
        )

    return requery


# ── Follow-up fragments (AP_FOLLOWUP_FRAGMENT_HANDOFF items 1–3) ─────────────
# A fragment whose slot the current template cannot execute must never route on
# its own: "in kurnool?" carries a district and no subject, so matching it alone
# lands wherever the district name points. Order of attempts: deterministic
# drill hop, then re-route WITH the frame's question, then — if what comes back
# still isn't plausibly the same subject — ask instead of serving.

def _fragment_top_match(
    message: str, fill: dict[str, str]
) -> tuple[Optional[str], Optional[str]]:
    """What the fragment WOULD have matched on its own: (query_id, tappable text).

    Retrieval only — no rerank, and nothing is executed. This is offered as one
    reading of an ambiguous fragment, never served as the answer to it. The id
    comes back too so the caller can test whether the match shares a subject
    with the frame at all — retrieval on a bare place name matches on the NAME,
    which is not a reading of anything.
    """
    if _retriever is None:
        return None, None
    try:
        scored = _retriever.retrieve_scored(normalize(message), 1)
    except Exception:
        return None, None
    if not scored:
        return None, None
    return scored[0][0], readable_question(scored[0][1], fill)


# The tier the user named OUT LOUD, if they named one. "in Laxmipur block?" is
# not an ambiguous message, and asking "did you mean the block or the GP?" about
# it makes the officer repeat a word they already typed.
#
# Phrase-level rather than token-level because "panchayat" belongs to two tiers:
# bare it means the gram panchayat, but "panchayat samiti" IS the block, so the
# GP pattern refuses it in front of `samiti`.
_TIER_PHRASES: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("district_name", re.compile(r"\b(districts?|zillas?|zp)\b")),
    ("block_name",    re.compile(r"\b(blocks?|samitis?)\b")),
    ("gp_name",       re.compile(r"\b(gps?|gram\s+panchayats?|"
                                 r"panchayats?(?!\s+samiti)|villages?)\b")),
)


def _tier_named_in(message: str) -> set[str]:
    """The geography slots whose tier noun the message actually says."""
    text = (message or "").lower()
    return {slot for slot, pattern in _TIER_PHRASES if pattern.search(text)}


def _place_readings(frame: ContextFrame, phrase: str) -> list[tuple[str, str]]:
    """Every (slot, resolved value) a place phrase could mean, widest first.

    NOT filtered by what the frame can execute — the caller needs the whole set
    to tell "this name is ambiguous" from "this name is a block".

    A tier the frame ALREADY BINDS is included, as a replacement reading (D28.4).
    It used to be skipped, on the reasoning that a bound slot is an executable
    edit and therefore the classifier's job; but this function is only reached
    when the classifier did not produce one, and dropping the reading is what
    made a GP-scoped frame read a GP-and-block name as the block. Whether a
    reading replaces a bound value or adds a new filter is `slot in
    frame.bound_params`, which the caller can ask directly.
    """
    readings: list[tuple[str, str]] = []
    for slot, entity_type in GEO_TIERS_WIDEST_FIRST:
        try:
            readings.append(
                (slot, _validator.validate(phrase, entity_type).resolved_value))
        except Exception:
            continue
    return readings


def _fragment_tiers(frame: ContextFrame, message: str) -> list[tuple[str, str]]:
    """`_place_readings` for a message that is nothing but a place and/or date."""
    if not is_slot_only_fragment(message, _geo_tokens):
        return []
    phrase = fragment_place_phrase(message, _geo_tokens)
    if not phrase:
        return []
    return _place_readings(frame, phrase)


def _scope_for_reading(frame: ContextFrame, slot: str) -> dict[str, str]:
    """The frame's bound parameters with any geography NARROWER than `slot`
    dropped.

    "what about Laxmipur?" read as a block, over an answer already scoped to
    Andhrua GP, means the block — not Andhrua-inside-Laxmipur, which is the
    zero-row bind the drill hop used to produce and then abandon. Wider scopes
    stay: a district on screen still contains the block just named.
    """
    order = list(GEO_SLOTS_WIDEST_FIRST)
    narrower = set(order[order.index(slot) + 1:]) if slot in order else set()
    return {name: value for name, value in frame.bound_params.items()
            if name not in narrower and name != slot}


def _narrowed_frame(frame: ContextFrame, slot: str | None) -> ContextFrame:
    """The frame as the serving paths should see it for a reading at `slot`.

    `serve_drill_hop` and `serve_frame_edit` both read `bound_params` directly,
    so dropping the narrower geography in the CHIP alone would leave the served
    answer computing the very combination the chip promised not to.
    """
    if not slot or slot not in GEO_SLOTS_WIDEST_FIRST:
        return frame
    scoped = _scope_for_reading(frame, slot)
    if scoped == frame.bound_params:
        return frame
    return frame.model_copy(update={"bound_params": scoped})


def _tier_reading_chip(frame: ContextFrame, slot: str, value: str) -> tuple[str, str]:
    """(label, send_text) for one tier of an ambiguous place name.

    The label is tier-qualified because the bare name is precisely what was
    ambiguous — "Laxmipur (GP)" against "Laxmipur (block)". The send_text is the
    frame's own question narrowed to that reading, with the tier noun written
    into the sentence so the re-route cannot land on the other tier; where the
    question has no placeholder for that slot the scope is APPENDED rather than
    silently dropped, the same rule `suggestions._chip_for` follows.

    The narrower bound geography is dropped from the fill, so the chip states the
    scope the answer will actually be computed over.
    """
    noun = TIER_NOUNS.get(slot, "")
    label = f"{value} ({noun})" if noun else str(value)
    template = _template_map.get(frame.template_id) or {}
    fill = {**_scope_for_reading(frame, slot), slot: f"{value} {noun}".strip()}
    question = drill_question(frame.template_id, fill, _template_map) or (
        template.get("abstract_question") or frame.template_question or str(value)
    )
    if str(value) not in question:
        question = f"{question.rstrip('?. ')} in {value} {noun}".strip() + "?"
    return label, question


def _tier_collision(
    frame: ContextFrame, readings: list[tuple[str, str]], message: str
) -> Optional[RouteResult]:
    """The tier-qualified clarification, when more than one reading is viable.

    ONE FUNCTION, BOTH PATHS (D28.3). The D18.P3 ruling is about behaviour, not
    about which code read the fragment: whether the LLM follow-up classifier
    produced the edit or `_fragment_reading` read it deterministically, a name
    belonging to two tiers the frame can both execute is a question to ask, not a
    coin flip to serve. In WP-4's replays G1524 bypassed the check every time
    because the classifier answered first.
    """
    viable = _viable_readings(frame, readings, message)
    if len(viable) < 2:
        return None
    return tier_collision_clarify(
        frame_question=frame.template_question,
        readings=[_tier_reading_chip(frame, slot, value) for slot, value in viable],
        user_query=message,
    )


def _tier_collision_for_edit(
    frame: ContextFrame, edit, message: str
) -> Optional[RouteResult]:
    """The same check, for an edit the LLM classifier produced.

    The classifier hands over ONE (slot, value) — it has already picked a tier,
    silently, from a name that may belong to two. So the value is re-read against
    every tier here: if more than one is viable, what the classifier produced was
    a guess, and D28.3 says ask.

    Nothing fires unless the edit is geographic, the value resolves at two or
    more tiers the frame can execute, and the user did not name a tier out loud.
    """
    slot, value = getattr(edit, "slot", None), getattr(edit, "value", None)
    if slot not in GEO_SLOTS_WIDEST_FIRST or not value:
        return None
    return _tier_collision(frame, _place_readings(frame, str(value)), message)


def _viable_readings(
    frame: ContextFrame, readings: list[tuple[str, str]], message: str
) -> list[tuple[str, str]]:
    """The readings that compete: executable by the frame's template, and not
    ruled out by a tier the user named explicitly."""
    executable = executable_geo_slots(frame.template_id)
    viable = [(slot, value) for slot, value in readings if slot in executable]
    named = _tier_named_in(message)
    if len(named) == 1:
        explicit = [reading for reading in viable if reading[0] in named]
        if explicit:
            return explicit
    return viable


def _fragment_reading(
    frame: ContextFrame, message: str
) -> tuple[Optional[FrameEdit], Optional[RouteResult], bool]:
    """Read a slot-only fragment ("in kurnool?") as an edit, without an LLM.

    The follow-up classifier is not reliable on these: measured on the same
    Q027 frame and the same "in kurnool?", it answered `frame_edit` on one run
    and `new_question` on the next, and only the first reached the drill hop.
    The fragment is unambiguous to read deterministically, though — every word
    in it is either a function word, a period, or a place — so it is read here
    and the classifier's coin flip stops mattering.

    TIERS ARE FILTERED BY WHAT THE FRAME CAN EXECUTE, BEFORE ONE IS PICKED.
    Walking widest-first and stopping at the first tier that merely VALIDATES
    reads "what about Laxmipur?" as a block, and Laxmipur is both a block and a
    GP in the 20-GP sample; the frame's EXP-001 has no `$block_name` to hop on,
    so `drill_target` returned None and the whole follow-up collapsed into a
    generic "narrowed, or new?" prompt (operator report, 2026-08-13). Only tiers
    the template can actually bind get to compete.

    Returns `(edit, clarify, name_tier)`:
      exactly one tier fits   -> the edit, and `name_tier` when the NAME was
                                 ambiguous across tiers, so the echo says which
                                 one was served;
      two or more fit         -> a TIER clarification (D18.P3: ask, don't infer),
                                 never the generic ambiguous-fragment prompt;
      none fits               -> the widest reading, so the value still reaches
                                 the contextual re-route, which is where a
                                 fragment the frame cannot answer has always
                                 been handled;
      not a place fragment    -> nothing.
    """
    tiers = _fragment_tiers(frame, message)
    if not tiers:
        return None, None, False
    fitting = _viable_readings(frame, tiers, message)

    if len(fitting) > 1:
        return None, _tier_collision(frame, tiers, message), False

    if fitting:
        slot, value = fitting[0]
        return FrameEdit(slot=slot, value=value), None, len(tiers) > 1

    slot, value = tiers[0]
    return FrameEdit(slot=slot, value=value), None, False


def _reroute_unexecutable_edit(
    frame: ContextFrame,
    edit,
    message: str,
    *,
    start_date: str,
    end_date: str,
    session_id: str,
    name_tier: bool = False,
) -> RouteResult:
    """Items 1–3 for a slot edit the current template has no parameter for."""
    fill = {edit.slot: edit.value} if edit.slot and edit.value else {}

    # Item 2 — deterministic drill hop to the mapped sibling, over the scope this
    # reading implies: geography narrower than the named tier is dropped, or the
    # hop binds the old GP together with the new block, returns nothing, and
    # abandons a follow-up it could have answered (D28.4).
    frame = _narrowed_frame(frame, edit.slot)
    hop = serve_drill_hop(
        frame, edit.slot, edit.value,
        template_map=_template_map, cache_conn=get_adapter(), validator=_validator,
        dashboard_results=_dashboard_results, dashboard_questions=_dashboard_questions,
        user_query=message, start_date=start_date, end_date=end_date,
        name_tier=name_tier,
    )
    if hop is not None:
        return hop

    # Item 1 — standard matching on the frame's question PLUS the fragment, so
    # the subject the fragment omits is in the text being matched.
    candidate: RouteResult | None = None
    try:
        candidate = route(
            combined_question(frame.template_question, message),
            validator=_validator, openai_client=_openai_client,
            cache_conn=get_adapter(), dashboard_results=_dashboard_results,
            template_map=_template_map, dashboard_questions=_dashboard_questions,
            retriever=_retriever, start_date=start_date, end_date=end_date,
            session_id=session_id,
        )
    except Exception:
        candidate = None

    # Serve it only if it is both the same subject AND actually narrowed by what
    # the fragment named. A match that shares the subject but dropped the place
    # is the frame's own question re-served — the narrowing vanishes, and
    # nothing in the answer says so.
    if (
        candidate is not None
        and candidate.tier == RouteTier.TIER2_TEMPLATE
        and candidate.query_id
        and templates_share_subject(frame.template_id, candidate.query_id)
        and any(
            e.slot_name == edit.slot
            or str(e.resolved_value).lower() == str(edit.value or "").lower()
            for e in (candidate.entities or [])
        )
    ):
        return candidate

    # Item 3 — nothing came back that is plausibly the same subject. Offer both
    # readings rather than serving one of them.
    contextual = None
    if candidate is not None:
        if candidate.tier == RouteTier.TIER2_TEMPLATE and candidate.query_description:
            contextual = candidate.query_description
        elif candidate.clarification and candidate.clarification.options:
            contextual = candidate.clarification.options[0].send_text
    fragment_id, fragment_text = _fragment_top_match(message, fill)
    return ambiguous_fragment_clarify(
        frame_question=frame.template_question,
        value=edit.value,
        contextual_question=contextual,
        fragment_question=fragment_text,
        user_query=message,
        frame_query_id=frame.template_id,
        fragment_query_id=fragment_id,
    )


def _fragment_guard(
    frame: ContextFrame, result: RouteResult, message: str
) -> Optional[RouteResult]:
    """The same subject test on the PLAIN path (item 3, second half).

    A fragment that the classifier called a new question outright still routes
    alone — "in kurnool?" reaches here whenever the LLM declines to read it as an
    edit. So the guard is applied to any served answer whose message named only
    places and periods: no measure word means no subject of its own, which means
    the only subject available was the one on screen.
    """
    entities = result.entities or []
    if any(e.entity_type not in GEO_SLOTS for e in entities):
        return None
    if not is_slot_only_fragment(message, _geo_tokens):
        return None
    if templates_share_subject(frame.template_id, result.query_id):
        return None

    geo = next((e for e in entities if e.entity_type in GEO_SLOTS), None)
    target = drill_target(frame.template_id, geo.slot_name) if geo else None
    contextual = None
    if target is not None:
        contextual = drill_question(
            target,
            {**frame.bound_params, **({geo.slot_name: geo.resolved_value} if geo else {})},
            _template_map,
        )
    return ambiguous_fragment_clarify(
        frame_question=frame.template_question,
        value=geo.resolved_value if geo else None,
        contextual_question=contextual,
        fragment_question=result.query_description,
        user_query=message,
        frame_query_id=frame.template_id,
        fragment_query_id=result.query_id,
    )


def _execute_operation(
    op_request: OperationRequest,
    session_id: str,
    start_date: str,
    end_date: str,
) -> tuple[ContextFrame, OperationResult] | None:
    stored = _context_store.get_with_rows(session_id)
    if stored is None:
        return None
    frame, rows = stored
    result = run_operation(
        op_request, frame, rows,
        requery=_requery_for_frame(frame, start_date, end_date),
    )
    return frame, result


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "router": {
            "cached_results": len(_dashboard_results),
            "templates":      len(_template_map),
        }
    }

@app.get("/debug/cache")
def debug_cache():
    adapter = get_adapter()
    total = adapter.execute("SELECT COUNT(*) FROM dashboard_cache").fetchone()[0]
    fresh = adapter.execute("SELECT COUNT(*) FROM dashboard_cache WHERE status='FRESH'").fetchone()[0]
    sample = adapter.execute(
        "SELECT query_id, status, row_count FROM dashboard_cache ORDER BY query_id"
    ).fetchall()
    return {
        "cache_table_total": total,
        "cache_table_fresh": fresh,
        "in_memory_dict_size": len(_dashboard_results),
        "sample": [{"qid": r[0], "status": r[1], "rows": r[2]} for r in sample[:20]],
    }

@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    if _openai_client is None:
        raise HTTPException(
            status_code=503,
            detail="Router not initialised. Add OPENAI_API_KEY to .env."
        )
    # Resolve date range, in precedence order:
    #   1. whatever the request carried — the UI's date picker always wins;
    #   2. an explicit period named in the question text ("…in 2024?"), which
    #      would otherwise be answered over the default window in silence;
    #   3. the default window.
    derived_from_question = False
    if req.start_date is None and req.end_date is None:
        derived = extract_date_window(req.message)
        if derived is None:
            start_date, end_date = _default_start_date, _default_end_date
            is_default = True
        else:
            start_date, end_date = derived
            is_default = False
            derived_from_question = True
    else:
        is_default = False
        start_date = req.start_date or _default_start_date
        end_date   = req.end_date   or _default_end_date
    session_id = req.session_id or str(uuid4())
    if req.reset_context:
        _context_store.reset(session_id)

    result: RouteResult | None = None
    inherited_scope: dict[str, str] = {}   # geo carried over from the frame
    # Standalone until a path says otherwise (interpretation.py): a reading that
    # never binds is correct by omission, and one that forgets to stamp itself
    # reports no marker rather than a wrong one.
    interpretation = Interpretation()

    # Resume a pending clarification first: the system just asked a question
    # ("For which district?"), so a short reply that answers it resumes the
    # paused template. Anything else clears the pending state (one-shot) and
    # routes normally.
    # A chip tap sends text we generated from the catalog — it is a complete
    # question by construction, never a slot answer or a follow-up fragment.
    # The exception is a disambiguation chip, whose send_text IS the slot value:
    # skipping the resume there would route a bare name to nowhere.
    pending = _context_store.take_pending(session_id)
    if pending is not None and _looks_like_slot_answer(req.message) and (
        not req.from_chip or bool(pending.candidates)
    ):
        resolution = resolve_pending_reply(
            req.message, pending, _validator, template_map=_template_map,
        )

        if resolution.kind == RESUME:
            try:
                result = serve_pending_answer(
                    pending, resolution.value,
                    template_map=_template_map,
                    cache_conn=get_adapter(),
                    validator=_validator,
                    dashboard_results=_dashboard_results,
                    dashboard_questions=_dashboard_questions,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception:
                result = None  # resumption failed — fall through to matching

        elif resolution.kind == SERVE_ALTERNATIVE:
            try:
                result = serve_scope_alternative(
                    resolution.query_id, pending,
                    template_map=_template_map,
                    cache_conn=get_adapter(),
                    validator=_validator,
                    dashboard_results=_dashboard_results,
                    dashboard_questions=_dashboard_questions,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception:
                result = None

        elif resolution.kind == REASK:
            # Ask again rather than let the fragment route on its own — and
            # carry the paused question forward, so nothing is lost.
            result = RouteResult(
                tier=RouteTier.CLARIFY,
                clarification=Clarification(
                    reason=resolution.reason,
                    prompt=resolution.prompt,
                    options=resolution.options,
                ),
                pending=resolution.pending,
                raw_query=req.message,
                normalized_query=req.message,
                total_latency_ms=0.0,
            )

        if result is not None:
            # The reply was read against the question we paused on — which is
            # NOT the one the answer will name, so nothing in the response says
            # so unless we do. Anchored to the pending, because the frame at
            # this point is some earlier answered question or nothing at all.
            interpretation = against_pending(pending, {
                RESUME:            f"answered: {readable_slot(pending.missing_slot)}",
                SERVE_ALTERNATIVE: "served the wider question offered",
                REASK:             f"still needs: {readable_slot(pending.missing_slot)}",
            }.get(resolution.kind))
        # FALLTHROUGH: not an answer to what we asked — treat as a new message.

    # Follow-up classification against the current frame (spec Section 4):
    # frame edit → re-query same template; operation → compute on the table;
    # new question → standard catalog matching.
    followup_started = time.monotonic()
    current_frame = _context_store.get(session_id) if result is None else None
    if current_frame is not None and (
        req.from_chip
        # A message that is word-for-word a catalog question (typed or tapped)
        # can never be a frame edit or an operation — don't let the classifier
        # capture it ("How many PM-KISAN beneficiaries…?" is not a count).
        or matches_catalog_question(req.message, _catalog_patterns)
    ):
        current_frame = None
    if current_frame is not None:
        decision = classify_followup(req.message, current_frame, _openai_client)

        if decision.kind == "operation" and decision.operation is not None:
            # A day-grain frame carries the window its rows were computed over —
            # including one this pack derived from the earlier question — and
            # _requery_for_frame honours it. Resolve it here so the response
            # reports the window the answer actually used; reporting the
            # handler's default alongside frame-window rows is the same silent
            # mismatch this module exists to remove.
            op_start, op_end = start_date, end_date
            if (current_frame.time_range.grain == "day"
                    and current_frame.time_range.start
                    and current_frame.time_range.end):
                op_start = current_frame.time_range.start
                op_end   = current_frame.time_range.end
            carried = (op_start, op_end) != (start_date, end_date)

            executed = _execute_operation(decision.operation, session_id, op_start, op_end)
            if executed is not None:
                frame, op_result = executed
                # THE ECHO AND THE CAVEAT, both of which this path used to skip
                # (D31.2). The caveat qualifies the rows, so it qualifies any
                # number taken from them; the echo says which operation ran and
                # over what, which is how a reader catches a minimum computed
                # over a table the question truncated.
                op_caveat = _catalog_caveat(frame.template_id)
                return QueryResponse(
                    session_id=session_id,
                    context_frame=frame,
                    tier="operation",
                    answer=operation_answer(frame, op_result, op_caveat),
                    result=op_result.result,
                    query_id=frame.template_id,
                    query_description=_echoed(
                        "operation", operation_description(frame, op_result),
                        frame.template_id),
                    caveat=op_caveat,
                    date_range={
                        "start_date": op_start,
                        "end_date":   op_end,
                        "is_default": is_default and not carried,
                        "derived_from_question": derived_from_question,
                    },
                    latency_ms=(time.monotonic() - followup_started) * 1000,
                    operation=op_result.operation,
                    operation_mode=op_result.mode.value,
                    # Anchored to the frame the message was CLASSIFIED against,
                    # not to `frame` above — they are the same question here,
                    # and reading it off the classification is the habit that
                    # keeps the marker honest on the paths where they differ.
                    interpretation=against_frame(
                        "operation", current_frame, operation_detail(op_result)
                    ),
                )

        # D28.3 — the tier check belongs on the CLASSIFIER path too. Applied
        # before either serving branch, because both bypassed it: an executable
        # `frame_edit` was served outright, and an `unexecutable_edit` went
        # straight to the re-route without `_fragment_reading` ever running. That
        # second route is the one G1524 took in all three WP-4 replays.
        if decision.kind in ("frame_edit", "unexecutable_edit") and decision.edit:
            result = _tier_collision_for_edit(
                current_frame, decision.edit, req.message
            )
            if result is not None:
                # Asking which place is still a reading of the message against
                # the frame — the whole clarification only makes sense as one —
                # so it is marked like every other fragment reading.
                interpretation = against_frame(
                    "fragment_reroute", current_frame,
                    slot_detail(decision.edit.slot, decision.edit.value),
                )

        if result is None and decision.kind == "frame_edit" and decision.edit is not None:
            edit = decision.edit
            edit_start, edit_end = start_date, end_date
            if edit.start_date and edit.end_date:
                edit_start, edit_end = edit.start_date, edit.end_date
            elif current_frame.time_range.grain == "day" and current_frame.time_range.start:
                edit_start = current_frame.time_range.start
                edit_end   = current_frame.time_range.end
            try:
                result = serve_frame_edit(
                    _narrowed_frame(current_frame, edit.slot),
                    edit_slot=edit.slot,
                    edit_value=edit.value,
                    template_map=_template_map,
                    cache_conn=get_adapter(),
                    validator=_validator,
                    dashboard_results=_dashboard_results,
                    dashboard_questions=_dashboard_questions,
                    user_query=req.message,
                    start_date=edit_start,
                    end_date=edit_end,
                )
                if (edit_start, edit_end) != (start_date, end_date):
                    # The edit (or the carried frame) chose the window, not us
                    # and not the default — say so, or the response reports a
                    # window it did not answer over.
                    derived_from_question = False
                    is_default = False
                start_date, end_date = edit_start, edit_end
                # The one path the frontend could never infer: this re-queries
                # the SAME template and returns an ordinary answer.
                interpretation = against_frame(
                    "frame_edit", current_frame,
                    slot_detail(edit.slot, edit.value)
                    or period_detail(edit_start, edit_end),
                )
            except Exception:
                result = None  # edit didn't apply — fall through to matching

        if result is None:
            # A slot edit the current question has no parameter for. Keep the
            # context: hop to the mapped sibling, else re-route the fragment
            # together with the frame's question, else ask which was meant. This
            # path never lets the bare fragment route on its own.
            #
            # The classifier's own verdict is taken when it says so, and a bare
            # place fragment is read deterministically when it doesn't — see
            # _fragment_reading for why that second reading is needed at all.
            unexecutable = (
                decision.edit if decision.kind == "unexecutable_edit" else None
            )
            name_tier = False
            if unexecutable is None and decision.kind in ("new_question", "frame_edit"):
                # A "frame_edit" still standing here is one that threw on
                # execution — a mandal read as a district, say. That loses the
                # context exactly as a demotion does, so it takes the same path.
                unexecutable, tier_clarify, name_tier = _fragment_reading(
                    current_frame, req.message
                )
                if tier_clarify is not None:
                    # The name is ambiguous across tiers the frame can BOTH
                    # execute. D18.P3: ask which place, not whether they meant
                    # to follow on — that part was never in doubt.
                    result = tier_clarify
                    interpretation = against_frame(
                        "fragment_reroute", current_frame,
                        slot_detail(
                            "place", fragment_place_phrase(req.message, _geo_tokens)
                        ),
                    )
            if result is None and unexecutable is not None:
                result = _reroute_unexecutable_edit(
                    current_frame, unexecutable, req.message,
                    start_date=start_date, end_date=end_date, session_id=session_id,
                    name_tier=name_tier,
                )
                # Whichever of the three readings came back — the deterministic
                # drill hop, the re-route of the fragment WITH the frame's
                # question, or the clarification offering both — the fragment
                # was read against the question on screen. A bare "in ganjam?"
                # has no subject of its own; the only one available was that one.
                interpretation = against_frame(
                    "fragment_reroute", current_frame,
                    slot_detail(unexecutable.slot, unexecutable.value),
                )

    if result is None:
        try:
            result = route(
                req.message,
                validator=_validator,
                openai_client=_openai_client,
                cache_conn=get_adapter(),
                dashboard_results=_dashboard_results,
                template_map=_template_map,
                dashboard_questions=_dashboard_questions,
                retriever=_retriever,
                start_date=start_date,
                end_date=end_date,
                session_id=session_id,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # A new question asked inside a conversation about one district usually
        # means that district — answering it state-wide is a different question
        # from the one the user thinks they asked. Narrow to the scope already
        # on screen, then SAY SO and offer the way back (see below); silent
        # narrowing would just trade one invisible mismatch for another.
        if current_frame is not None:
            narrowed = inherit_frame_scope(
                result, current_frame,
                user_query=req.message,
                template_map=_template_map,
                cache_conn=get_adapter(),
                validator=_validator,
                dashboard_results=_dashboard_results,
                dashboard_questions=_dashboard_questions,
                start_date=start_date,
                end_date=end_date,
            )
            if narrowed is not None:
                result, inherited_scope = narrowed
                interpretation = against_frame(
                    "scope_inherited", current_frame,
                    "; ".join(slot_detail(slot, value) or ""
                              for slot, value in inherited_scope.items()) or None,
                )

            # The fragment guard, on the path where the classifier called the
            # fragment a new question and it routed alone.
            if (
                not inherited_scope
                and result.tier == RouteTier.TIER2_TEMPLATE
                and result.query_id
            ):
                guarded = _fragment_guard(current_frame, result, req.message)
                if guarded is not None:
                    result = guarded
                    interpretation = against_frame(
                        "fragment_reroute", current_frame,
                        slot_detail(
                            "place", fragment_place_phrase(req.message, _geo_tokens)
                        ),
                    )

    # Remember any clarification we just asked, so the next reply can resume it
    if result.pending is not None:
        _context_store.set_pending(session_id, result.pending)

    if result.query_id and result.result is not None:
        frame = build_context_frame(
            result,
            _catalog_column_metadata.get(result.query_id),
            _catalog_question(result.query_id),
        )
        if frame is not None:
            result.context_frame = _context_store.set_frame(
                session_id, frame, rows=result.result
            )
    else:
        result.context_frame = _context_store.get(session_id)

    # Build human-readable answer + next-question chips
    suggestions: list[Chip] | None = None
    if result.tier.value in ("tier1", "tier2"):
        # THE SCOPE NOTE IS GONE FROM THE ANSWER TEXT. It used to read "Answered
        # for X, carried over from your previous question." — the right
        # information in the wrong place. The answer body is what an officer
        # copies, exports and pastes into a report, and a system log embedded in
        # it reads there as noise. `interpretation` now carries the same fact as
        # a field, for every binding path rather than this one alone, and the
        # frontend draws it beside the answer instead of inside it. The chips
        # below are untouched: "show this state-wide instead" is a sharper
        # escape than the generic re-ask, and the two coexist.
        answer = echo_answer(result)
        if result.context_frame is not None:
            suggestions = suggest_followups(result.context_frame) or None
        if inherited_scope:
            undo = statewide_undo_chip(result.query_id, _template_map)
            if undo is not None:
                suggestions = [undo] + [
                    c for c in (suggestions or []) if c.send_text != undo.send_text
                ][:MAX_SUGGESTION_CHIPS - 1]
    elif result.tier.value == "clarify":
        answer = result.clarification.prompt if result.clarification else "Could you clarify what you mean?"
    else:
        answer = result.fallback_message or "I couldn't find an answer to that."

    return QueryResponse(
        session_id=session_id,
        context_frame=result.context_frame,
        tier=result.tier,
        answer=answer,
        result=result.result,
        query_id=result.query_id,
        query_description=_echoed(
            result.tier, result.query_description, result.query_id),
        intent=result.intent,
        caveat=result.caveat,
        entities=[
            {"slot": e.slot_name, "value": e.resolved_value, "confidence": e.confidence}
            for e in (result.entities or [])
        ],
        date_range={
            "start_date": start_date,
            "end_date":   end_date,
            "is_default": is_default,
            "derived_from_question": derived_from_question,
        },
        date_filter_applied=result.date_filter_applied,
        latency_ms=result.total_latency_ms,
        clarification=result.clarification,
        suggestions=suggestions,
        interpretation=interpretation,
    )


class ContextRequest(BaseModel):
    session_id: str


@app.post("/context/reset")
def context_reset(req: ContextRequest):
    """Explicit new-question affordance: drop the frame and history."""
    _context_store.reset(req.session_id)
    return {"session_id": req.session_id, "reset": True}


@app.post("/context/pop", response_model=QueryResponse)
def context_pop(req: ContextRequest):
    """Breadcrumb back: restore the previous frame and its exact table.

    RESTORATION IS NOT A FOLLOW-UP. There is no new message here to have been
    read one way or the other, so `interpretation` stays at its `new_question`
    default and the UI draws no marker on the restored answer.
    """
    popped = _context_store.pop(req.session_id)
    if popped is None:
        raise HTTPException(status_code=409, detail="No earlier question to go back to.")
    frame, rows = popped

    base = frame.template_question or frame.template_id
    caveat = _catalog_caveat(frame.template_id)
    # Verbatim, on the way back too: a breadcrumb hop restores the rows, so it
    # has to restore what qualifies them. See echo.append_caveat.
    answer = append_caveat("Back to: " + base, caveat)

    return QueryResponse(
        session_id=req.session_id,
        context_frame=frame,
        # MEMBERSHIP, not a prefix. This read `startswith("T")`, which was a
        # workable stand-in only while AP dashboards were "D…" and templates
        # were not. Twelve PR&DW template ids begin with T (TRD-001…012) and 340
        # do not, so the prefix test would label almost every restored answer
        # tier1.
        tier="tier1" if frame.template_id in DASHBOARD_CATALOG else "tier2",
        answer=answer,
        result=rows,
        query_id=frame.template_id,
        caveat=caveat,
        latency_ms=0.0,
        suggestions=suggest_followups(frame) or None,
    )


@app.post("/operation", response_model=QueryResponse)
def operation_endpoint(req: OperationCallRequest):
    """Typed operation invoked from UI affordances on the current result table.

    NO MARKER HERE EITHER, unlike the "total?" path through /query. A control
    tapped ON a table names the table it computes over; nothing was classified,
    so there is no reading to report and nothing the user could have meant
    differently. `interpretation` keeps its `new_question` default.
    """
    if _openai_client is None:
        raise HTTPException(
            status_code=503,
            detail="Router not initialised. Add OPENAI_API_KEY to .env."
        )
    started = time.monotonic()
    start_date, end_date = _default_start_date, _default_end_date

    stored = _context_store.get_with_rows(req.session_id)
    if stored is None:
        raise HTTPException(
            status_code=409,
            detail="No active result to operate on — ask a question first.",
        )
    frame, rows = stored
    # Stale-table guard must run before any computation or requery
    if req.result_set_id != frame.result_set.id:
        raise HTTPException(
            status_code=409,
            detail="That table is no longer the active result — re-run the question first.",
        )

    op_result = run_operation(
        OperationRequest(**req.model_dump(exclude={"session_id", "result_set_id"})),
        frame, rows,
        requery=_requery_for_frame(frame, start_date, end_date),
    )

    caveat = _catalog_caveat(frame.template_id)
    return QueryResponse(
        session_id=req.session_id,
        context_frame=frame,
        tier="operation",
        # An operation RECOMPUTES on the same question's rows — a top-N, a share,
        # a re-sort. The caveat qualifies the rows, so it qualifies the
        # recomputation too: a percentage taken over a 17%-covered population is
        # exactly as misleading as the count it came from. The echo above it
        # names the operation and its SCOPE, which is the disclosure a tapped
        # control needs just as much as a typed follow-up does.
        answer=operation_answer(frame, op_result, caveat),
        result=op_result.result,
        query_id=frame.template_id,
        query_description=_echoed(
            "operation", operation_description(frame, op_result),
            frame.template_id),
        caveat=caveat,
        latency_ms=(time.monotonic() - started) * 1000,
        operation=op_result.operation,
        operation_mode=op_result.mode.value,
    )
