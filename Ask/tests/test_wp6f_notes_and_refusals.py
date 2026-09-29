"""WP-6f: three reranker notes, a plain count as one figure, and the refusals
whose data or definition exists turned into templates.

    T1  BUD-003 / BUD-005 carry the sanctioned-amount-by-scheme note, BUD-002 the
        cashbook contrast; pilot 1005 / 1007 / 1009 grade on the measure asked.
    T2  EXP-009 (and its twin EXP-011) own "compare / sector-wise tied spending
        across focus areas"; TRD-008 hands a TIED-funds question to EXP-009.
"""
import unittest

from query_router.rerank_context import DESC_BY_QID


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


if __name__ == "__main__":
    unittest.main()
