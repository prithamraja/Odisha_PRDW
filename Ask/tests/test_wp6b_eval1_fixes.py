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


# ── T2 ────────────────────────────────────────────────────────────────────────

# Eval_1 rows 303-313, verbatim: ten of these eleven answered with ALL ongoing
# activities on 2026-09-14.
ROAD_ROWS = {
    303: "How many road construction activities are in progress for 2024 to 2026?",
    304: "Give the count of ongoing road construction activities for 2024 to 2026.",
    305: "What is the number of road works currently in progress for 2024 to 2026?",
    306: "How many GPDP road construction activities have an in-progress status "
         "for 2024 to 2026?",
    307: "Provide the total number of road construction activities currently "
         "underway for 2024 to 2026.",
    308: "How many road construction activities are currently in progress for "
         "2020-2021?",
    309: "How many road construction activities are in progress for 2021-2022?",
    310: "Give the count of ongoing road construction activities for 2022-2023.",
    311: "What is the number of road works currently in progress for 2020-2021?",
    312: "How many GPDP road construction activities have an in-progress status "
         "for 2021-2022?",
    313: "Provide the total number of road construction activities currently "
         "underway for 2022-2023.",
}


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T2SubjectPrefillTests(unittest.TestCase):
    """The alias tables as a deterministic reader, ahead of the extractor."""

    def test_every_alias_key_prefills_its_own_value(self):
        from query_router.entity_validator import REGISTRY_CONFIG, _collapse_ws
        from query_router.subject_reader import (
            SUBJECT_TYPES, _NOT_READ, named_subjects, prefill_phrase)
        for etype in SUBJECT_TYPES:
            for key, target in REGISTRY_CONFIG[etype]["aliases"].items():
                if key in _NOT_READ.get(etype, ()):
                    continue
                with self.subTest(type=etype, key=key):
                    question = f"How many activities under {key} in 2024-2025?"
                    named = named_subjects(question, {"x": etype}, _validator())
                    phrase = prefill_phrase(named.get("x", []))
                    self.assertIsNotNone(phrase)
                    resolved = _validator().validate(phrase, etype).resolved_value
                    self.assertEqual(_collapse_ws(resolved), _collapse_ws(target))

    def test_the_common_words_are_left_to_the_extractor(self):
        from query_router.subject_reader import named_subjects
        slots = {"status": "status", "plan_type": "plan_type"}
        for question in ("What is the total approved cost in 2024-2025?",
                         "How much work was done in 2024-2025?",
                         "What are the main focus areas in 2024-2025?"):
            with self.subTest(question=question):
                self.assertEqual(named_subjects(question, slots, _validator()), {})

    def test_the_road_group_binds_roads_without_the_extractor(self):
        """Rows 303-313: the extractor returns nothing, as it did on ten of them."""
        for n, question in ROAD_ROWS.items():
            with self.subTest(row=n):
                raw, asked = _extract("STS-003", question)
                self.assertNotIn("focus_area", asked)
                self.assertNotIn("status", asked)
                validated, clarify = _fill("STS-003", question, raw)
                self.assertIsNone(clarify)
                bound = {e.slot_name: e.resolved_value for e in validated}
                self.assertEqual(bound["focus_area"], "Roads")
                self.assertEqual(bound["status"].strip(), "WORK ONGOING")

    def test_the_road_count_is_the_road_count(self):
        """Not the 400 ongoing activities of every kind in 2024-25."""
        question = "How many road construction activities are in progress for 2024-2025?"
        raw, _ = _extract("STS-003", question)
        validated, _ = _fill("STS-003", question, raw)
        roads = sum(r["activities"] for r in _serve("STS-003", validated).result)
        everything = sum(r["activities"] for r in _serve(
            "STS-003", [e for e in validated if e.slot_name != "focus_area"]).result)
        want = _adapter().execute(
            "SELECT COUNT(*) FROM v_activity WHERE fiscal_year = '2024-2025' "
            "AND focus_area_name = 'Roads' AND is_ongoing = 1").fetchone()[0]
        self.assertEqual(roads, want)
        self.assertEqual(everything, 400)
        self.assertLess(roads, everything)

    def test_the_groups_that_already_bound_still_bind_the_same(self):
        """Rows 17-22 (Swachh Bharat, with its caveat), 215-227, 230-242."""
        cases = [
            ("STS-003", "Count of completed sanitation activities tied to Swachh "
                        "Bharat for 2024 to 2025.", "Sanitation", True),
            ("STS-003", "How many sanitation activities have been completed under "
                        "Swachh Bharat for 2025 to 2026?", "Sanitation", True),
            ("PLN-049", "How many activities are planned under the sanitation "
                        "sector for 2024 to 2025?", "Sanitation", False),
            ("PLN-049", "Number of activities proposed within the sanitation "
                        "category for 2021 to 2022.", "Sanitation", False),
            ("PLN-031", "Which GP has planned the most activities under piped water "
                        "supply for 2024 to 2025?", "Drinking water", False),
            ("PLN-031", "Which Gram Panchayat proposed the most activities for piped "
                        "water for 2025 to 2026?", "Drinking water", False),
        ]
        from query_router.entity_validator import lossy_caveat
        for qid, question, focus, lossy in cases:
            with self.subTest(question=question):
                raw, _ = _extract(qid, question)
                validated, clarify = _fill(qid, question, raw)
                self.assertIsNone(clarify)
                entity = next(e for e in validated if e.slot_name == "focus_area")
                self.assertEqual(entity.resolved_value, focus)
                self.assertEqual(lossy_caveat(entity) is not None, lossy)

    def test_a_comparison_is_left_to_the_extractor(self):
        """Two focus areas are a list for the extractor to read, never a pick."""
        question = "Compare tied fund spending between water and sanitation for 2022 to 2023."
        raw, asked = _extract("EXP-009", question,
                              {"focus_area": ["Drinking water", "Sanitation"]})
        self.assertIn("focus_area", asked)
        self.assertEqual(raw["focus_area"], ["Drinking water", "Sanitation"])

    def test_the_longest_reading_wins_across_slots(self):
        from query_router.subject_reader import named_subjects
        slots = {"focus_area": "focus_area", "theme": "theme"}
        named = named_subjects("planned under water sufficient village", slots, _validator())
        self.assertEqual(list(named), ["theme"])
        named = named_subjects("spend on GP office infrastructure", slots, _validator())
        self.assertEqual(list(named), ["focus_area"])


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class T2UnboundSubjectGuardTests(unittest.TestCase):
    """A question that names a subject is never answered as if it had not."""

    def test_a_named_subject_left_unbound_asks(self):
        question = "How many road construction activities are in progress for 2024-2025?"
        validated, clarify = _fill("STS-003", question,
                                   {"date_range": "2024-2025", "status": "ongoing"})
        self.assertEqual(validated, [])
        self.assertEqual(clarify.clarification.reason, "unbound_subject")
        self.assertEqual(clarify.clarification.prompt, "Did you mean the Roads focus area?")
        self.assertEqual([c.label for c in clarify.clarification.options], ["Roads"])
        self.assertEqual(clarify.pending.missing_slot, "focus_area")

    def test_a_comparison_the_extractor_missed_asks_with_both(self):
        """The reader stands aside for two values; the stubbed extractor then
        returns nothing — the case the guard exists for."""
        question = "How many road and water works are in progress for 2024-2025?"
        raw, asked = _extract("STS-003", question)
        self.assertIn("focus_area", asked)
        _, clarify = _fill("STS-003", question, raw)
        self.assertEqual(clarify.clarification.reason, "unbound_subject")
        self.assertEqual([c.label for c in clarify.clarification.options],
                         ["Roads", "Drinking water"])

    def test_tapping_the_chip_resumes_the_same_question(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        question = "How many road and water works are in progress for 2024-2025?"
        raw, _ = _extract("STS-003", question)
        _, clarify = _fill("STS-003", question, raw)
        result = router.serve_pending_answer(
            clarify.pending, "Roads", template_map=T, cache_conn=_adapter(),
            validator=_validator(), dashboard_results={}, dashboard_questions={},
            start_date=None, end_date=None)
        self.assertEqual(result.query_id, "STS-003")
        self.assertEqual({e.slot_name: e.resolved_value for e in result.entities}
                         ["focus_area"], "Roads")

    def test_a_subject_the_template_does_not_offer_is_not_asked_about(self):
        """PLN-001 counts plans; it has no focus area to bind."""
        question = "How many GPs uploaded a GPDP with road works for 2024-2025?"
        validated, clarify = _fill("PLN-001", question, {"date_range": "2024-2025"})
        self.assertIsNone(clarify)

    def test_both_halves_of_a_split_are_still_not_a_question(self):
        """WP-6 §8.1 holds: tied/untied is not read, so BUD-005 still answers."""
        question = "What percentage of the sanctioned budget is tied and untied in 2024-25?"
        raw, asked = _extract("BUD-005", question, {"tied_untied": ["Tied", "Untied"]})
        self.assertIn("tied_untied", asked)
        _, clarify = _fill("BUD-005", question, raw)
        self.assertIsNone(clarify)


if __name__ == "__main__":
    unittest.main()
