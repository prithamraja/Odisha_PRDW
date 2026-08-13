from dotenv import load_dotenv
load_dotenv()

import os
import json
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
)
from query_router.vector_retriever  import VectorRetriever
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.template_catalog  import TEMPLATE_CATALOG
from query_router.config            import MAX_SUGGESTION_CHIPS, USE_VECTOR_RETRIEVAL
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
    echo_answer_without_caveat,
)
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
from query_router.date_phrase       import extract_date_window
from query_router.preprocessor      import normalize
from query_router.zones             import readable_question

# A bare place name is read as the widest scope it validates as — "Bhubaneswar"
# is a district before it is the block of the same name. A frame that already
# binds that scope is skipped, so a district-scoped question reads "in Barpali?"
# as the block it must be.
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

    _openai_client = OpenAI(api_key=oai_key)
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

def _fragment_top_match(message: str, fill: dict[str, str]) -> Optional[str]:
    """What the fragment WOULD have matched on its own, as tappable text.

    Retrieval only — no rerank, and nothing is executed. This is offered as one
    reading of an ambiguous fragment, never served as the answer to it.
    """
    if _retriever is None:
        return None
    try:
        scored = _retriever.retrieve_scored(normalize(message), 1)
    except Exception:
        return None
    if not scored:
        return None
    return readable_question(scored[0][1], fill)


def _fragment_edit(frame: ContextFrame, message: str):
    """Read a slot-only fragment ("in kurnool?") as an edit, without an LLM.

    The follow-up classifier is not reliable on these: measured on the same
    Q027 frame and the same "in kurnool?", it answered `frame_edit` on one run
    and `new_question` on the next, and only the first reached the drill hop.
    The fragment is unambiguous to read deterministically, though — every word
    in it is either a function word, a period, or a place — so it is read here
    and the classifier's coin flip stops mattering.

    Returns a FrameEdit for the geography named, or None when the message is not
    a bare fragment, names no place we hold, or names a slot the frame already
    has bound (an executable edit, which is the classifier's job).
    """
    if not is_slot_only_fragment(message, _geo_tokens):
        return None
    phrase = fragment_place_phrase(message, _geo_tokens)
    if not phrase:
        return None
    for slot, entity_type in GEO_TIERS_WIDEST_FIRST:
        if slot in frame.bound_params:
            continue
        try:
            resolved = _validator.validate(phrase, entity_type).resolved_value
        except Exception:
            continue
        return FrameEdit(slot=slot, value=resolved)
    return None


def _reroute_unexecutable_edit(
    frame: ContextFrame,
    edit,
    message: str,
    *,
    start_date: str,
    end_date: str,
    session_id: str,
) -> RouteResult:
    """Items 1–3 for a slot edit the current template has no parameter for."""
    fill = {edit.slot: edit.value} if edit.slot and edit.value else {}

    # Item 2 — deterministic drill hop to the mapped sibling.
    hop = serve_drill_hop(
        frame, edit.slot, edit.value,
        template_map=_template_map, cache_conn=get_adapter(), validator=_validator,
        dashboard_results=_dashboard_results, dashboard_questions=_dashboard_questions,
        user_query=message, start_date=start_date, end_date=end_date,
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
    return ambiguous_fragment_clarify(
        frame_question=frame.template_question,
        value=edit.value,
        contextual_question=contextual,
        fragment_question=_fragment_top_match(message, fill),
        user_query=message,
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
                return QueryResponse(
                    session_id=session_id,
                    context_frame=frame,
                    tier="operation",
                    answer=op_result.answer,
                    result=op_result.result,
                    query_id=frame.template_id,
                    date_range={
                        "start_date": op_start,
                        "end_date":   op_end,
                        "is_default": is_default and not carried,
                        "derived_from_question": derived_from_question,
                    },
                    latency_ms=(time.monotonic() - followup_started) * 1000,
                    operation=op_result.operation,
                    operation_mode=op_result.mode.value,
                )

        if decision.kind == "frame_edit" and decision.edit is not None:
            edit = decision.edit
            edit_start, edit_end = start_date, end_date
            if edit.start_date and edit.end_date:
                edit_start, edit_end = edit.start_date, edit.end_date
            elif current_frame.time_range.grain == "day" and current_frame.time_range.start:
                edit_start = current_frame.time_range.start
                edit_end   = current_frame.time_range.end
            try:
                result = serve_frame_edit(
                    current_frame,
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
            # _fragment_edit for why that second reading is needed at all.
            unexecutable = (
                decision.edit if decision.kind == "unexecutable_edit" else None
            )
            if unexecutable is None and decision.kind in ("new_question", "frame_edit"):
                # A "frame_edit" still standing here is one that threw on
                # execution — a mandal read as a district, say. That loses the
                # context exactly as a demotion does, so it takes the same path.
                unexecutable = _fragment_edit(current_frame, req.message)
            if unexecutable is not None:
                result = _reroute_unexecutable_edit(
                    current_frame, unexecutable, req.message,
                    start_date=start_date, end_date=end_date, session_id=session_id,
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
        # Composed so the CAVEAT IS LAST — it is the thing an officer must not
        # stop reading before. echo_answer already appends it, so the scope note
        # is inserted ahead of it rather than after.
        answer = echo_answer(result)
        if inherited_scope:
            # Inheriting scope silently would be the same class of defect as
            # answering state-wide silently. Name what was carried and from
            # where, and lead the chips with the way out.
            carried = ", ".join(inherited_scope.values())
            note = (
                f"Answered for {carried}, carried over from your previous "
                "question."
            )
            answer = append_caveat(
                f"{echo_answer_without_caveat(result)}\n\n{note}", result.caveat
            )
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
        query_description=result.query_description,
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
    """Breadcrumb back: restore the previous frame and its exact table."""
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
    """Typed operation invoked from UI affordances on the current result table."""
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
        # exactly as misleading as the count it came from.
        answer=append_caveat(op_result.answer, caveat),
        result=op_result.result,
        query_id=frame.template_id,
        caveat=caveat,
        latency_ms=(time.monotonic() - started) * 1000,
        operation=op_result.operation,
        operation_mode=op_result.mode.value,
    )
