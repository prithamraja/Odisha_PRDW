"""WP-6f: three reranker notes, a plain count as one figure, and the refusals
whose data or definition exists turned into templates.

    T1  BUD-003 / BUD-005 carry the sanctioned-amount-by-scheme note, BUD-002 the
        cashbook contrast; pilot 1005 / 1007 / 1009 grade on the measure asked.
    T2  EXP-009 (and its twin EXP-011) own "compare / sector-wise tied spending
        across focus areas"; TRD-008 hands a TIED-funds question to EXP-009.
    T3  a plain count of planned activities served by PLN-024 is ONE figure —
        declared on PLN-024 only, never a global cue.

No API key and no network: the extractor is stubbed, and every router path runs
against the sample database.
"""
import time
import unittest
from pathlib import Path

from query_router.rerank_context import DESC_BY_QID

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"
_STATE: dict = {}


def _adapter():
    if "adapter" not in _STATE:
        from db_factory import open_analytical_db
        _STATE["adapter"] = open_analytical_db(_DB_PATH)
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


def _needs_db(test):
    return unittest.skipUnless(_DB_PATH.exists(), "no sample database")(test)


def _answer(qid: str, question: str, extractor_says: dict):
    """(entities, clarify, served result or None): the vector path from extraction
    on, with the extractor stubbed to `extractor_says`."""
    from query_router import breakdown, router, threshold_reply
    from query_router.template_catalog import TEMPLATE_CATALOG as T
    template = T[qid]
    slots = template["param_slots"]
    real = router.extract_entities
    router.extract_entities = lambda q, asked, c, intent=None: {
        s: extractor_says.get(s) for s in asked}
    try:
        raw = router._extract_slot_values(
            question, router._template_slot_types(template), object(),
            validator=_validator(), list_slots=router._list_slots(slots),
            superlative_lists=router.superlative_list_slots(slots))
    finally:
        router.extract_entities = real
    entities, clarify = router._fill_slots_or_clarify(
        qid, router._template_slot_types(template), raw, _validator(),
        question, "n", time.monotonic(),
        optional=router.optional_slots(slots),
        defaults=router.slot_defaults(slots),
        list_slots=router._list_slots(slots),
        splits=breakdown.slots_the_statement_splits(template),
        numeric=threshold_reply.numeric_meta(slots),
        check_direction=True)
    if clarify is not None:
        return entities, clarify, None
    result = router._serve_query_id(
        qid, entities, None, user_query=question, normalized=question,
        start=time.monotonic(), cache_conn=_adapter(), dashboard_results={},
        template_map=T, dashboard_questions={}, start_date=None, end_date=None)
    return entities, None, result


class T1SanctionedBySchemeNotes(unittest.TestCase):

    def test_bud003_names_the_sanctioned_amount_by_scheme(self):
        desc = DESC_BY_QID["BUD-003"]
        self.assertIn("SANCTIONED AMOUNT BY SCHEME", desc)
        self.assertIn("split the sanctioned funds into SFC and Own Funds", desc)
        self.assertIn("BUD-002, a different measure", desc)

    def test_bud005_names_the_share_by_scheme(self):
        desc = DESC_BY_QID["BUD-005"]
        self.assertIn("SHARE of the SANCTIONED budget BY SCHEME", desc)
        self.assertIn("BUD-002", desc)

    def test_bud002_points_the_sanctioned_measure_away(self):
        desc = DESC_BY_QID["BUD-002"]
        self.assertIn("CASHBOOK funding recorded per source", desc)
        self.assertIn("BUD-003 (amount) or BUD-005 (share)", desc)


class T1PilotGradingNarrowed(unittest.TestCase):
    """1009 answered from the cashbook used to pass as "per scheme"."""

    @staticmethod
    def _record(query_id, expect, rows=None):
        return {"n": 1009, "group": "fund split by scheme", "q": "q", "expect": expect,
                "tier": "tier1", "query_id": query_id, "n_rows": len(rows or []) or 1,
                "rows_sample": rows or [{"funding_source": "SFC", "amount": 1}],
                "entities": [], "retrieved": [query_id]}

    def test_a_cashbook_answer_to_a_sanctioned_question_is_wrong(self):
        from grade_eval1 import grade
        row = grade(self._record("BUD-002", {"scheme": "5TH STATE FINANCE COMMISSION",
                                             "accept": ["BUD-003", "SAN-013"]}))
        self.assertEqual(row["outcome"], "incorrect")
        self.assertIn("a different measure", row["note"])

    def test_the_sanctioned_template_per_scheme_is_right(self):
        from grade_eval1 import grade
        row = grade(self._record("BUD-003", {"per_scheme": True,
                                             "accept": ["BUD-003", "SAN-013"]},
                                 rows=[{"group_label": "SFC", "scheme_name": "SFC"}]))
        self.assertEqual(row["outcome"], "correct")

    def test_the_amount_is_not_the_share(self):
        from grade_eval1 import grade
        row = grade(self._record("BUD-003", {"per_scheme": True, "accept": ["BUD-005"]},
                                 rows=[{"scheme_name": "SFC"}]))
        self.assertEqual(row["outcome"], "incorrect")

    def test_rows_without_accept_grade_as_before(self):
        from grade_eval1 import grade
        row = grade(self._record("BUD-002", {"per_scheme": True}))
        self.assertEqual(row["outcome"], "correct")


class T2TiedSpendAcrossFocusAreas(unittest.TestCase):

    def test_exp009_and_its_twin_carry_the_note(self):
        for qid in ("EXP-009", "EXP-011"):
            with self.subTest(qid=qid):
                desc = DESC_BY_QID[qid]
                self.assertIn("ACROSS FOCUS AREAS", desc)
                self.assertIn("sector-wise expenditure of tied funds for water and "
                              "sanitation", desc)
                self.assertIn("is TRD-002", desc)
                self.assertIn("is TRD-008", desc)

    def test_trd008_keeps_its_sentence_and_names_the_tied_point(self):
        desc = DESC_BY_QID["TRD-008"]
        self.assertIn("'Tied-fund expenditure, water vs sanitation' is EXP-009", desc)
        self.assertIn("A question about TIED funds is EXP-009, even when it says "
                      "'sector-wise'.", desc)

    def test_trd002_is_unchanged(self):
        self.assertTrue(DESC_BY_QID["TRD-002"].endswith(
            "tied-fund spending on water vs sanitation for a year is EXP-009."))


class T3PlainCountIsOneFigure(unittest.TestCase):

    def test_the_phrase_reading(self):
        from query_router.breakdown import plain_count_total
        for text in ("What is the count of planned activities in Barpali in 2024-25?",
                     "count of planned activities in Attabira in 2025-26",
                     "How many activities are planned in Kalimela in 2024-25?",
                     "Count of all planned activities inside main GPDPs for 2021 to 2022."):
            with self.subTest(text=text):
                self.assertTrue(plain_count_total(text))
        for text in ("Which GP has the highest number of planned activities in 2024-25?",
                     "How many activities are planned under each GPDP theme in Barpali?",
                     "Theme-wise count of planned activities in 2024-25",
                     "What is the total number of activities planned in 2024-25?",
                     "Top 5 blocks by number of planned activities",
                     "What is the planned cost in Barpali in 2024-25?"):
            with self.subTest(text=text):
                self.assertFalse(plain_count_total(text))

    def test_declared_on_pln024_only(self):
        from query_router.breakdown import declares_plain_count_total
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        self.assertEqual(sorted(q for q, t in T.items() if declares_plain_count_total(t)),
                         ["PLN-024"])

    def test_the_contract_refuses_it_elsewhere(self):
        import copy
        from tools import derive_catalog as dc
        from query_router.template_catalog import TEMPLATE_CATALOG as T
        other = copy.deepcopy(T["BUD-006"])
        for slot in other["param_slots"]:
            if slot["name"] == "group_by":
                slot["plain_count_total"] = True
        problems = dc.contract_problems({"BUD-006": other})
        self.assertTrue(any("plain_count_total" in p for p in problems), problems)

    @_needs_db
    def test_barpali_answers_one_figure_with_the_echo(self):
        entities, clarify, result = _answer(
            "PLN-024", "What is the count of planned activities in Barpali in 2024-25?",
            {"block_name": "Barpali"})
        self.assertIsNone(clarify)
        self.assertEqual(len(result.result), 1)
        self.assertIn("(as one total)", result.query_description)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("group_by"), "total")
        total = _adapter().execute(
            "SELECT COUNT(*) FROM v_activity WHERE block_name = 'Barpali' "
            "AND fiscal_year = '2024-2025'").fetchone()[0]
        self.assertEqual(result.result[0]["planned_activities"], total)

    @_needs_db
    def test_a_ranking_or_a_breakdown_keeps_its_rows(self):
        _, _, result = _answer(
            "PLN-024", "How many activities are planned under each GPDP theme in "
                       "Barpali in 2024-25?", {"block_name": "Barpali"})
        self.assertGreater(len(result.result), 1)
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("group_by"), "theme")

    @_needs_db
    def test_two_named_places_still_get_a_row_each(self):
        _, _, result = _answer(
            "PLN-024", "What is the count of planned activities in Barpali and "
                       "Attabira in 2024-25?", {"block_name": ["Barpali", "Attabira"]})
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertEqual(bound.get("group_by"), "block")
        self.assertEqual(len(result.result), 2)

    @_needs_db
    def test_another_template_is_untouched(self):
        _, _, result = _answer(
            "BUD-006", "What is the count of planned activities in Barpali in 2024-25?",
            {"block_name": "Barpali"})
        bound = {e.slot_name: e.resolved_value for e in result.entities}
        self.assertNotIn("group_by", bound)


if __name__ == "__main__":
    unittest.main()
