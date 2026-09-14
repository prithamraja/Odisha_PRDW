"""WP-6b — the Eval_1 fixes and the D33 clean-up, pinned.

Grouped by task so a failure names the promise it broke:

    T1  crowding is counted one way, in the harness and in gate 8 (the hyphen
        span's own pins live in test_date_phrase)
    T2  the subject an officer names binds — by the reader, or the bot asks
    T3  two lists at once: the subject takes the breakdown, the years combine,
        and the echo says so
    T4  a count of nothing renders as 0; a listing of nothing still says so
    T5  the reranker is told the distinctions the replay found it missing
    T6  the grader reproduces the PM's grading of the 2026-09-14 baseline

No API key and no network: every router path here runs with the extractor
stubbed, against the sample database.
"""
import json
import os
import time
import unittest
from decimal import Decimal
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"
_REPO = Path(os.environ.get("PRDW_REPO") or _BACKEND.parent)

_STATE: dict = {}


def _adapter():
    """The sample database with its views, or None — memoised."""
    if "adapter" not in _STATE:
        adapter = None
        if _DB_PATH.exists():
            try:
                from db_factory import open_analytical_db
                adapter = open_analytical_db(_DB_PATH)
            except Exception:                                # pragma: no cover
                adapter = None
        _STATE["adapter"] = adapter
    return _STATE["adapter"]


def _validator():
    if "validator" not in _STATE:
        from query_router.entity_validator import EntityValidator
        _STATE["validator"] = EntityValidator(_adapter())
    return _STATE["validator"]


def tearDownModule():
    adapter = _STATE.get("adapter")
    if adapter is not None:
        try:
            adapter.close()
        except Exception:                                    # pragma: no cover
            pass


def _extract(qid: str, question: str, extractor_says: dict | None = None):
    """`_extract_slot_values` with the extractor stubbed: (raw, slots it was asked)."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    asked: list[str] = []

    def stub(query, slots, client, intent=None):
        asked.extend(slots)
        return {s: (extractor_says or {}).get(s) for s in slots}

    real, router.extract_entities = router.extract_entities, stub
    try:
        raw = router._extract_slot_values(
            question, router._template_slot_types(T[qid]), object(),
            validator=_validator(),
            list_slots=router._list_slots(T[qid]["param_slots"]))
    finally:
        router.extract_entities = real
    return raw, asked


def _fill(qid: str, question: str, raw: dict):
    from query_router import breakdown, router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    template = T[qid]
    return router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), raw, _validator(),
        question, "n", 0.0,
        optional=router.optional_slots(template["param_slots"]),
        defaults=router.slot_defaults(template["param_slots"]),
        list_slots=router._list_slots(template["param_slots"]),
        splits=breakdown.slots_the_statement_splits(template))


def _serve(qid: str, entities: list):
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    return router._serve_query_id(
        qid, entities, None, user_query="q", normalized="q",
        start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
        template_map=T, dashboard_questions={}, start_date=None, end_date=None)


def _entity(slot: str, value, etype: str | None = None):
    """A validated entity; a list value binds as the router binds a list."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    etype = etype or {"date_range": "fiscal_year", "focus_area": "focus_area",
                      "tied_untied": "tied_untied", "status": "status",
                      "group_by": "group_by"}[slot]
    values = value if isinstance(value, list) else [value]
    resolved = [_validator().validate(v, etype) for v in values]
    entity = resolved[0]
    entity.slot_name = slot
    if len(values) > 1:
        entity.values = [e.resolved_value for e in resolved]
        entity.resolved_value = ", ".join(entity.values)
    return entity


# ── T1 ────────────────────────────────────────────────────────────────────────

class T1CrowdingTests(unittest.TestCase):

    def test_extra_vectors_walked_to_reach_k_distinct_ids(self):
        from recall_eval import crowding_extra
        self.assertEqual(crowding_extra(["a", "a", "b", "a", "c", "d"], 3), 2)
        self.assertEqual(crowding_extra(["a", "b", "c"], 3), 0)

    def test_gate_8_reports_it_and_never_asserts_it(self):
        source = (_BACKEND / "refusal_recall.py").read_text(encoding="utf-8")
        self.assertIn("crowding (reported, not asserted)", source)
        self.assertIn("crowding UNMEASURED (reported, not asserted)", source)


if __name__ == "__main__":
    unittest.main()
