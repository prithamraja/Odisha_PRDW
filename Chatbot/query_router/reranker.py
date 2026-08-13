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

_TEMPLATES = dict(TEMPLATE_CATALOG)

_RERANK_SYS = """\
You match a user's question to the single best canonical question from a numbered list, for the Andhra Pradesh Department of Agriculture "RTGS Decision Aid" database. It covers eight departmental datasets: the PM-KISAN farmer roster, Agriculture (input/seed subsidy and eCrop booking), Horticulture/APMIP (micro-irrigation subsidy), Fisheries, Sericulture, MARKFED (MSP procurement and payments), RySS (natural farming / Rythu Sadhikara), and Survey & Land Records.

Some candidates carry two extra lines:
- "↳" — what the question measures, with example queries.
- "accepts filters:" — every filter that candidate can actually apply. This is authoritative for that candidate.

Judge a candidate with a "↳" line by that description rather than by surface word overlap with its wording. But a "↳" description describes a question FAMILY, not one candidate: sibling candidates that are parameter variants of the same family repeat the same description and the same examples word-for-word. So an example may name a district or scheme that THIS candidate cannot accept — sometimes matching the user's query almost word-for-word. Use "↳" to choose the family, then "accepts filters:" and the {placeholder} rule to choose the variant within it. Never pick a candidate merely because one of its examples resembles the query: if the query names a filter the candidate does not accept and a sibling does accept it, the sibling wins.

Rules:
- Return the id of the candidate whose question best matches the user's intent.
- {placeholders} in a candidate mark filters it expects. Prefer the variant that matches the filters ACTUALLY present in the query:
    - Query names a district -> prefer the {district} variant over the state-wide one.
    - Query names a mandal   -> prefer the {mandal} variant (mandals are inside districts; a mandal-scoped question usually reports by village).
    - Query names no place   -> prefer the state-wide (no-placeholder) variant.
    - Same for {crop}, {season}, {scheme}, {social_category}, {gender}, {crop_year} and the numeric filters ({top_n}, {threshold_hectares}, {tolerance_pct}).
- Pick the MOST SPECIFIC candidate that matches the query.

Disambiguation — these words mean different datasets depending on context:
- "subsidy": input subsidy / seed subsidy -> AGRICULTURE. Micro-irrigation, drip, sprinkler, APMIP -> HORTICULTURE. Do not treat them as one measure.
- "payment": MSP / procurement / paddy purchase payment -> MARKFED. Incentive for cocoon or silk -> SERICULTURE. Natural-farming payment -> RySS.
- "registered": eCrop / crop booking registration -> AGRICULTURE. Fisheries society or vessel registration -> FISHERIES. Natural-farming membership -> RySS.
- Farmer lookup: if the query gives a NAME, prefer the {farmer_name} candidate; if it gives a 12-digit number, prefer the {aadhaar} candidate. Never substitute one for the other.
- Scheme membership ("which schemes is this farmer in", "how many farmers are in both X and Y") is a different family from benefit amount ("how much has this farmer received"). Match the one the user actually asked for.
- Scheme set logic: "in X but NOT in Y" is a DIFFERENCE — answer it with the {scheme}/{scheme_2} difference template, never with an overlap or intersection candidate, however closely that candidate's wording matches the two datasets named. "in BOTH X and Y" is an overlap. When the difference is measured from the PM-KISAN roster and only one other scheme is named, prefer the single-{scheme} roster-minus-scheme template over the two-scheme one.
- Land questions: "declared"/"PM-KISAN extent" is the roster's own area_hectares; "surveyed"/"revenue record" is Survey & Land Records. A question comparing the two is the mismatch family.
- Data-quality questions ("missing", "duplicate", "malformed", "mismatch") are integrity checks and are their own family — do not answer them with a coverage or payment question.
- If NONE of the candidates can answer the query exactly, return "no_match" for query_id — and in "candidates", list up to 3 ids of the questions that come CLOSEST to what the user wants (the ones a helpful analyst would offer instead), best first. Judge closeness by meaning, not wording — e.g. a question about women farmers is closest to a gender-breakdown question even if the words differ.
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
    return {
        qid: (DESC_BY_QID.get(qid, ""), _accepted_filters(qid))
        for qid in _TEMPLATES
    }


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
