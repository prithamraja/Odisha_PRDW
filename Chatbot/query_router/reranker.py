"""
LLM re-ranker for template-direct retrieval.

Given the user query and the top-K catalog candidates from the vector retriever,
pick the single query_id whose question best matches — including the right
parameter variant (e.g. prefer the {district} template only if the query names a
district). When no candidate truly answers the query, it returns "no_match"
plus the 2-3 most plausible near-misses, so the clarify zone can offer
semantically chosen interpretations instead of raw embedding neighbours.

Each candidate is shown with a curated family description (rerank_context.py) and
the filters it accepts, so the model can tell apart templates whose wording looks
alike but which measure different things.
"""
import json
from openai import OpenAI

from .config import RERANK_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT_SECONDS, REASONING_MODELS
from .rerank_context import DESC_BY_QID
from .template_catalog import TEMPLATE_CATALOG
from .unanswerable_catalog import UNANSWERABLE_CATALOG

_TEMPLATES = dict(TEMPLATE_CATALOG)

_RERANK_SYS = """\
You match a user's question to the single best canonical question from a numbered list, for the Odisha Panchayati Raj & Drinking Water Department's panchayat analytics database. Its users are programme officers. It covers the Gram Panchayat Development Plan (GPDP) cycle: the plans GPs upload each year, the activities inside those plans, what each activity was budgeted and what was actually spent, administrative and technical approvals, physical progress evidence, the assets created, and Swachh Bharat Mission (SBM) sanitation work. Geography is three tiers — Gram Panchayat inside Block (Panchayat Samiti) inside District (Zilla Parishad).

Some candidates carry two extra lines:
- "↳" — what the question actually measures: the measure and its accounting basis, the row grain, any status filter, and for SBM questions the keyword pattern that defines the subject.
- "accepts filters:" — every filter that candidate can actually apply. This is authoritative for that candidate.

Judge a candidate with a "↳" line by that description rather than by surface word overlap with its wording. A "↳" describes a question FAMILY: where two candidates are variants of one family they repeat the same description word-for-word, and you choose between them with "accepts filters:".

Rules:
- Return the id of the candidate whose question best matches the user's intent.
- MOST CANDIDATES ANSWER AT EVERY GEOGRAPHIC SCOPE. Their district, block and GP filters are OPTIONAL: the same candidate answers state-wide when the query names no place, and narrowed when it names one. So do NOT reject a candidate because the query names a district and the candidate's wording does not, or the reverse. Choose on the MEASURE, and let the filters follow.
- {placeholders} mark filters a candidate expects. Where a filter is genuinely required — a second GP or block for a head-to-head comparison, an activity code for a single-activity lookup, a deadline — prefer the candidate whose required filters the query actually supplies.
- Pick the MOST SPECIFIC candidate that matches the query.

Disambiguation — the distinctions this database punishes most:
- TWO EXPENDITURE CONVENTIONS, and they do not agree. "Expenditure"/"spent"/"utilisation" normally means the PLAN basis (expenditure booked against a planned activity). The CASHBOOK basis is the voucher ledger — receipts and payments. A candidate whose "↳" says CASHBOOK answers a different question from one that says PLAN basis; never substitute one for the other.
- PLANNED versus APPROVED versus STARTED versus COMPLETED are four different measures, not synonyms. "Planned" is every activity in the plan; "approved" means an administrative approval exists (only ~17% of activities have one); "ongoing"/"completed" are work statuses. Match the one asked for.
- UPLOADED versus APPROVED plans: "how many GPs uploaded a GPDP" counts every plan row, "how many had it approved" counts the approved subset. Different candidates.
- ABSENCE questions are their own family — "which GPs have NOT uploaded", "which planned nothing under this theme", "which recorded no activity". Their "↳" says they read the GP ROSTER. Never answer one with a counting question over activities: an activity-side query cannot return a GP that has no activities.
- SBM questions identify their subject by SEARCHING ACTIVITY TEXT for keywords, and every SBM candidate's "↳" quotes its own pattern. Two SBM candidates can accept identical filters and differ only in that pattern (community compost pits versus household compost pits; segregation sheds versus segregation bins). Read the pattern; it is the only thing separating them.
- COST words are not interchangeable: planned cost (what the GP entered), approved cost (the action plan's), administratively sanctioned amount (the approval order's), technically approved cost, and actual expenditure are five different columns.
- DATA-QUALITY questions ("missing", "no record", "duplicate", "mismatch", "not decoded") are integrity checks and are their own family — do not answer them with a coverage or spend question.
- TIED versus UNTIED funds is a grant-component split, not a scheme.
- Some listed questions are ones this database CANNOT answer (beneficiary counts, pensions, ward-level detail, delay reasons). If one of those matches the user's intent, return it: naming what is missing is better than a near-miss that answers something else.
- If NONE of the candidates can answer the query exactly, return "no_match" for query_id — and in "candidates", list up to 3 ids of the questions that come CLOSEST to what the user wants (the ones a helpful analyst would offer instead), best first. Judge closeness by meaning, not wording.
- If the query is entirely off-topic for this database, return "no_match" and an empty "candidates" list.

Return ONLY a JSON object: {"query_id": "<id or no_match>", "candidates": ["<id>", ...]}."""


def _accepted_filters(qid: str) -> str:
    """The filters a query_id can actually apply — ground truth from its param_slots.

    Dashboards (D*) are precomputed and take no parameters, so they are state-wide.
    """
    template = _TEMPLATES.get(qid)
    if template is None:
        return "none (state-wide totals only)"
    slots = [slot["name"] for slot in template.get("param_slots") or []]
    return ", ".join(slots) if slots else "none (state-wide totals only)"


def _unanswerable_context(qid: str) -> tuple[str, str]:
    """The ↳ line for a question the database cannot answer.

    These are in the candidate list on purpose, so the model has to be told what
    they are — otherwise a beneficiary question, whose whole point is that it
    CANNOT be answered, reads to the model like any other candidate and either
    gets picked silently or loses to a near-miss that answers something else.
    The reason is the workbook's own.
    """
    entry = UNANSWERABLE_CATALOG[qid]
    return (
        f"CANNOT BE ANSWERED from this database. {entry['reason']} "
        f"Pick this when the user genuinely asked for it: saying what is missing "
        f"is a better answer than a near-miss that measures something else.",
        "none — this question cannot be answered",
    )


def _build_qid_to_context() -> dict[str, tuple[str, str]]:
    """query_id -> (family description, accepted filters) for the reranker listing.

    The accepted-filter line is per-query_id ground truth read straight off
    param_slots, so EVERY template gets one. It is what lets the model choose
    between parameter variants of one family — the AP catalog is full of them
    (S03 "{scheme} Aadhaar not in PM-KISAN" against its per-dataset siblings
    Q112/Q135, G01-S/-D/-M at three geographic scopes). Without it the model
    falls back to surface wording and reliably picks the wrong variant.

    The family description is the second layer, and the one that carries set
    logic ("in X but NOT in Y" against "in BOTH X and Y"), which no amount of
    filter metadata can express. It comes from rerank_context.DESC_BY_QID, where
    every template has an entry and siblings of a family share one string
    verbatim — the contract _RERANK_SYS states.
    """
    context = {
        qid: (DESC_BY_QID.get(qid, ""), _accepted_filters(qid))
        for qid in _TEMPLATES
    }
    context.update({qid: _unanswerable_context(qid) for qid in UNANSWERABLE_CATALOG})
    return context


_QID_TO_CONTEXT: dict[str, tuple[str, str]] = _build_qid_to_context()


def parse_rerank_response(data: dict, valid_ids: set[str]) -> tuple[str, list[str]]:
    """Pure projection of the LLM's JSON onto (query_id | 'no_match', near_miss_ids)."""
    by_lower = {qid.lower(): qid for qid in valid_ids}

    def _canonical(value) -> str | None:
        text = str(value).strip()
        if text in valid_ids:
            return text
        return by_lower.get(text.lower())

    chosen = _canonical(data.get("query_id", "no_match")) or "no_match"

    raw_candidates = data.get("candidates")
    candidates: list[str] = []
    if isinstance(raw_candidates, list):
        for item in raw_candidates:
            qid = _canonical(item)
            if qid and qid != chosen and qid not in candidates:
                candidates.append(qid)
            if len(candidates) == 3:
                break
    return chosen, candidates


# How many times the reranker has been asked to choose. The deterministic paths
# (drill hop, frame edit, resumed pending) exist precisely to avoid this call, so
# tests assert on the counter rather than on wall-clock or a log scrape.
_CALL_COUNT = 0


def rerank_call_count() -> int:
    return _CALL_COUNT


def rerank(query: str, candidates: list[tuple[str, str]], client: OpenAI) -> tuple[str, list[str]]:
    """candidates: list of (query_id, question).
    Returns (query_id | 'no_match', llm_picked_near_miss_ids)."""
    global _CALL_COUNT
    if not candidates:
        return "no_match", []
    _CALL_COUNT += 1

    valid_ids = {qid for qid, _ in candidates}
    lines = []
    for qid, question in candidates:
        ctx = _QID_TO_CONTEXT.get(qid)
        if ctx:
            desc, filters = ctx
            line = f"{qid}: {question}"
            if desc:
                line += f"\n    ↳ {desc}"
            lines.append(f"{line}\n    accepts filters: {filters}")
        else:
            lines.append(f"{qid}: {question}")
    listing = "\n".join(lines)
    user_msg = f'Candidates:\n{listing}\n\nUser question: "{query}"\nJSON:'

    try:
        kwargs = dict(
            model=RERANK_MODEL,
            timeout=LLM_TIMEOUT_SECONDS,
            messages=[
                {"role": "system", "content": _RERANK_SYS},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
        )
        if RERANK_MODEL in REASONING_MODELS:
            kwargs["max_completion_tokens"] = 500
            kwargs["extra_body"] = {"reasoning_effort": "low"}
        else:
            kwargs["temperature"] = LLM_TEMPERATURE
            kwargs["max_tokens"] = 80

        resp = client.chat.completions.create(**kwargs)
        data = json.loads(resp.choices[0].message.content.strip())
        return parse_rerank_response(data, valid_ids)

    except Exception:
        return "no_match", []
