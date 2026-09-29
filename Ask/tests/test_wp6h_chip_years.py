"""WP-6h — a chip carries every year the officer named, or is not offered.

    T1  the chip pre-fill reads a year span as a list, as the answer path does
    T2  each chip is rendered for what its template can hold:
          a list-capable year slot   -> every year ("2022-2023, 2023-2024 and 2024-2025")
          a two-year comparison      -> exactly two years fill the pair, earlier in $date_range_2
          anything that holds fewer  -> dropped; offered marked "(2024-25 only)" only
                                        when no other chip remains
        one year named, or none      -> as before

No API key and no network: the extractor and the reranker are stubbed, and every
router path runs against the sample database.
"""
import time
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

_STATE: dict = {}

THREE = ["2022-2023", "2023-2024", "2024-2025"]
PAIRS = ("PLN-039", "PLN-040", "TRD-001", "TRD-002", "TRD-004")
LIST_NEAR_MISSES = ["PLN-024", "PLN-049", "PLN-025"]


def _adapter():
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


def _needs_db(cls):
    return unittest.skipUnless(_DB_PATH.exists(), "no sample database")(cls)


def _silent_extractor(query, slots, client, intent=None):
    return {s: None for s in slots}


class _Retriever:
    """A retriever that returns a fixed list — the chips come from the reranker."""

    def __init__(self, qids):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        self.scored = [(q, T[q]["abstract_question"], 0.9 - 0.01 * i)
                       for i, q in enumerate(qids)]

    def retrieve_scored(self, text, k):
        return self.scored[:k]

    def retrieve_with_examples(self, text, k, per_candidate):
        return self.scored[:k], {}


def _chips_for(question, near_misses):
    """The reranker no-match chips for `question`, extractor and reranker stubbed."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    real_extract, real_rerank = router.extract_entities, router.rerank
    router.extract_entities = _silent_extractor
    router.rerank = lambda query, candidates, client, examples=None: (
        "no_match", list(near_misses))
    try:
        result = router._route_vector(
            question, question, time.monotonic(), validator=_validator(),
            openai_client=object(), retriever=_Retriever(near_misses), cache_conn=_adapter(),
            dashboard_results={}, template_map=T, dashboard_questions={},
            start_date=None, end_date=None)
    finally:
        router.extract_entities, router.rerank = real_extract, real_rerank
    options = result.clarification.options
    for chip in options:
        assert chip.label == chip.send_text, chip       # the tap sends what it shows
    return [c.send_text for c in options]


def _extract(qid: str, question: str):
    """`_extract_slot_values` exactly as the answer path calls it, extractor silent."""
    from query_router import router
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    slots = T[qid]["param_slots"]
    real, router.extract_entities = router.extract_entities, _silent_extractor
    try:
        return router._extract_slot_values(
            question, router._template_slot_types(T[qid]), object(),
            validator=_validator(), list_slots=router._list_slots(slots),
            superlative_lists=router.superlative_list_slots(slots))
    finally:
        router.extract_entities = real


def _bound(qid: str, question: str) -> dict:
    """What the answer path binds for `question` on `qid` (fails if it asks)."""
    from query_router import breakdown, router, threshold_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    template = T[qid]
    entities, clarify = router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), _extract(qid, question), _validator(),
        question, "n", time.monotonic(),
        optional=router.optional_slots(template["param_slots"]),
        defaults=router.slot_defaults(template["param_slots"]),
        list_slots=router._list_slots(template["param_slots"]),
        splits=breakdown.slots_the_statement_splits(template),
        numeric=threshold_reply.numeric_meta(template["param_slots"]),
        check_direction=True)
    assert clarify is None, (qid, question, clarify)
    out = {}
    for e in entities:
        values = getattr(e, "values", None)
        out[e.slot_name] = list(values) if values else e.resolved_value
    return out


def _years(value) -> list:
    return sorted(value) if isinstance(value, (list, tuple)) else [value]


def _old_chips(candidates, limit, fill):
    """`_reading_chips` as it was before WP-6h, for the unchanged cases."""
    from query_router.router import UNANSWERABLE_CATALOG
    from query_router.zones import readable_question
    chips, seen = [], set()
    for qid, question, _ in candidates:
        text = readable_question(question, fill)
        if text in seen:
            continue
        seen.add(text)
        chips.append((f"Why I can't answer: {text}" if qid in UNANSWERABLE_CATALOG
                      else text, text))
        if len(chips) == limit:
            break
    return chips


# ── T1 + T2: a list-capable chip carries every year, and a tap binds them ──────

@_needs_db
class ListChipTests(unittest.TestCase):

    FORMS = (
        ("How many activities were planned from 2022 to 2025?", THREE),
        ("How many activities were planned in 2023-2025?", ["2023-2024", "2024-2025"]),
        ("How many activities were planned from 2022-23 to 2024-25?", THREE),
    )

    def test_every_multi_year_form_is_carried_and_a_tap_binds_every_year(self):
        from query_router.zones import join_values
        for question, years in self.FORMS:
            with self.subTest(question=question):
                chips = _chips_for(question, LIST_NEAR_MISSES)
                self.assertEqual(len(chips), 3, chips)
                for chip in chips:
                    self.assertIn(join_values(years), chip)
                per_theme = next(c for c in chips if "each GPDP theme" in c)
                self.assertEqual(
                    per_theme,
                    f"How many activities are planned under each GPDP theme in a gram "
                    f"panchayat in {join_values(years)}?")
                # The tap, re-read as a new question, binds every year.
                self.assertEqual(_years(_bound("PLN-024", per_theme)["date_range"]), years)

    def test_the_operators_row_1060_chips(self):
        chips = _chips_for("How many activities were planned from 2022-23 to 2024-25?",
                           ["PLN-024", "STS-008", "PLN-044"])
        for chip in chips:
            self.assertIn("2022-2023, 2023-2024 and 2024-2025", chip)
            self.assertNotIn("only)", chip)


# ── T2: the five two-year comparison templates ───────────────────────────────

@_needs_db
class ComparisonChipTests(unittest.TestCase):

    def test_every_comparison_template_reads_earlier_year_first(self):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        for qid in PAIRS:
            self.assertIn("between {date_range_2} and {date_range}",
                          T[qid]["abstract_question"], qid)

    def test_two_years_fill_the_pair_in_order_and_the_tap_binds_it(self):
        question = "Compare the planned figures between 2022-23 and 2024-25"
        for qid in PAIRS:
            with self.subTest(qid=qid):
                chips = _chips_for(question, [qid])
                self.assertEqual(len(chips), 1, chips)
                self.assertIn("between 2022-2023 and 2024-2025", chips[0])
                self.assertNotIn("only)", chips[0])
                raw = _extract(qid, chips[0])
                self.assertEqual((raw["date_range_2"], raw["date_range"]),
                                 ("2022-2023", "2024-2025"))
                if qid != "TRD-004":                 # TRD-004 also needs a block
                    bound = _bound(qid, chips[0])
                    self.assertEqual((bound["date_range_2"], bound["date_range"]),
                                     ("2022-2023", "2024-2025"))

    def test_the_two_years_also_fill_a_list_chip_beside_it(self):
        chips = _chips_for("Planned cost between 2022-23 and 2024-25",
                           ["PLN-026", "TRD-002", "TRD-001"])
        self.assertEqual(len(chips), 3, chips)
        self.assertIn("in 2022-2023 and 2024-2025?", chips[0])
        for chip in chips[1:]:
            self.assertIn("between 2022-2023 and 2024-2025.", chip)
            self.assertNotIn("and 2022-2023 and", chip)

    def test_three_years_drop_the_comparison_chip(self):
        with self.assertLogs("query_router.router", "INFO") as logs:
            chips = _chips_for("Activities planned from 2022-23 to 2024-25",
                               ["PLN-049", "PLN-044", "TRD-001"])
        self.assertEqual(len(chips), 2, chips)
        self.assertFalse(any("Compare" in c for c in chips), chips)
        self.assertTrue(any("chip dropped: TRD-001" in m for m in logs.output), logs.output)
        for chip in chips:
            self.assertIn("2022-2023, 2023-2024 and 2024-2025", chip)

    def test_a_comparison_left_alone_says_which_two_years_it_compares(self):
        chips = _chips_for("Activities planned from 2022-23 to 2024-25", ["TRD-001"])
        self.assertEqual(chips, [
            "Compare the activities planned and started theme-wise between 2022-2023 "
            "and 2024-2025 (2022-23 and 2024-25 only)?"])
        raw = _extract("TRD-001", chips[0])
        self.assertEqual((raw["date_range_2"], raw["date_range"]), ("2022-2023", "2024-2025"))


# ── T2: a one-year template ───────────────────────────────────────────────────

ONE_YEAR = {
    "ONE-001": {
        "abstract_question": "How many activities are planned in {date_range}?",
        "param_slots": [{"name": "date_range", "entity_type": "fiscal_year"}],
    },
}


@_needs_db
class OneYearChipTests(unittest.TestCase):
    """No catalogue template today takes exactly one year outside the five
    comparisons (329 take a list), so the rule is pinned on a stand-in."""

    FILL = {"date_range": THREE}

    def _cands(self, *qids):
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        entries = {**T, **ONE_YEAR}
        return [(q, entries[q]["abstract_question"], 0.9) for q in qids]

    def test_dropped_beside_a_chip_that_carries_every_year(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        chips = router._reading_chips(self._cands("ONE-001", "PLN-024"), 3, self.FILL,
                                      {**T, **ONE_YEAR})
        self.assertEqual([c.label for c in chips], [
            "How many activities are planned under each GPDP theme in a gram panchayat "
            "in 2022-2023, 2023-2024 and 2024-2025?"])

    def test_the_only_candidate_is_offered_marked_and_its_tap_answers_one_year(self):
        from query_router import router
        chips = router._reading_chips(self._cands("ONE-001"), 3, self.FILL, ONE_YEAR)
        self.assertEqual([c.label for c in chips],
                         ["How many activities are planned in 2024-2025 (2024-25 only)?"])
        self.assertEqual(chips[0].send_text, chips[0].label)
        self.assertEqual(_years(router._fiscal_years_from_text(chips[0].send_text,
                                                               _validator())),
                         ["2024-2025"])

    def test_a_refusal_alone_does_not_hide_the_narrower_chip(self):
        from query_router import router
        from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG as U
        refusal = next(iter(U))
        cands = [(refusal, U[refusal]["question"], 0.9)] + self._cands("ONE-001")
        labels = [c.label for c in router._reading_chips(cands, 3, self.FILL, ONE_YEAR)]
        self.assertEqual(len(labels), 2, labels)
        self.assertTrue(labels[0].startswith("Why I can't answer: "))
        self.assertEqual(labels[1], "How many activities are planned in 2024-2025 (2024-25 only)?")


# ── One year, or none: as before ──────────────────────────────────────────────

@_needs_db
class SingleYearUnchangedTests(unittest.TestCase):

    QUESTIONS = (
        "How many activities were planned in Kalimela in 2024-25?",
        "Compare planned activities in 2024-25",
        "planned cost per theme",
        "Which themes grew the most last year?",
    )
    CANDIDATES = ["PLN-024", "TRD-002", "PLN-039", "PLN-026", "BUD-003"]

    def test_chips_are_what_they_were(self):
        from query_router import router
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        cands = [(q, T[q]["abstract_question"], 0.9) for q in self.CANDIDATES]
        real, router.extract_entities = router.extract_entities, _silent_extractor
        try:
            for question in self.QUESTIONS:
                with self.subTest(question=question):
                    fill = router._extract_fill_values(question, self.CANDIDATES, T,
                                                       _validator(), object())
                    self.assertFalse(isinstance(fill.get("date_range"), list), fill)
                    new = [(c.label, c.send_text)
                           for c in router._reading_chips(cands, 5, fill, T)]
                    self.assertEqual(new, _old_chips(cands, 5, fill))
        finally:
            router.extract_entities = real

    def test_a_single_year_chip_is_pinned(self):
        chips = _chips_for("How many activities were planned in 2024-25?", LIST_NEAR_MISSES)
        self.assertEqual(chips[0], "How many activities are planned under each GPDP theme "
                                   "in a gram panchayat in 2024-2025?")


# ── The answer path is unchanged ──────────────────────────────────────────────

@_needs_db
class AnswerPathTests(unittest.TestCase):
    """What a question binds when it is answered directly — the same readings the
    WP-6g report recorded. (The offline proof re-checks all 1,201 answered turns
    of the WP-6e/6f/6g replays: none binds differently.)"""

    def test_bindings(self):
        cases = (
            ("PLN-024", "How many activities were planned from 2022-23 to 2024-25?",
             {"date_range": THREE}),
            ("PLN-024", "How many activities were planned in 2023-2025?",
             {"date_range": ["2023-2024", "2024-2025"]}),
            ("PLN-024", "How many activities were planned in 2024-25?",
             {"date_range": "2024-2025"}),
            ("TRD-002", "Compare the approved cost and expenditure theme-wise between "
                        "2022-23 and 2024-25",
             {"date_range": "2024-2025", "date_range_2": "2022-2023"}),
            ("TRD-002", "Compare the approved cost and expenditure theme-wise from "
                        "2022-23 to 2024-25",
             {"date_range": "2024-2025", "date_range_2": "2022-2023"}),
        )
        for qid, question, want in cases:
            with self.subTest(question=question):
                bound = _bound(qid, question)
                for slot, value in want.items():
                    got = bound[slot]
                    self.assertEqual(_years(got) if isinstance(value, list) else got, value)


# ── T4 harness: tap the first chip, grade the eighth standing group ───────────

class HarnessTests(unittest.TestCase):

    CHIPS = {"clarification": {"options": [
        {"label": "A (2024-25 only)?", "send_text": "A (2024-25 only)?"},
        {"label": "B", "send_text": "B"}]}}

    def test_a_number_taps_the_chip_in_that_place(self):
        import run_custom_eval
        self.assertEqual(run_custom_eval._pick_chip(self.CHIPS, 1), "A (2024-25 only)?")
        self.assertEqual(run_custom_eval._pick_chip(self.CHIPS, 2), "B")
        self.assertIsNone(run_custom_eval._pick_chip(self.CHIPS, 3))
        self.assertEqual(run_custom_eval._pick_chip(self.CHIPS, "b"), "B")

    def test_the_grader_accepts_every_year_or_a_visibly_narrower_chip(self):
        import grade_eval1

        def record(chip, years):
            return {"n": 1070, "group": "WP-6h chip years", "q": "q",
                    "expect": {"years": THREE}, "tier": "clarify",
                    "clarification": {"reason": "ambiguous_templates", "options": []},
                    "turn2": {"q": chip, "tier": "tier2", "query_id": "PLN-024",
                              "entities": [{"slot": "date_range", "value": ", ".join(years),
                                            "values": years}]}}
        self.assertEqual(grade_eval1.grade(record("A?", THREE))["outcome"], "correct")
        self.assertEqual(grade_eval1.grade(record("A?", ["2024-2025"]))["outcome"], "incorrect")
        self.assertEqual(grade_eval1.grade(record("A (2024-25 only)?", ["2024-2025"]))["outcome"],
                         "correct")
        self.assertEqual(grade_eval1.grade(record("A (2024-25 only)?", THREE))["outcome"],
                         "incorrect")


if __name__ == "__main__":
    unittest.main()
