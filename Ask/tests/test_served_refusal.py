"""A served refusal is not an empty answer.

The 30 known-unanswerable questions are in the retrieval index deliberately:
officers WILL ask them (13 of the 30 are beneficiary questions), and returning
the workbook's own reason beats a generic miss that reads as the bot failing.

THE COUPLING THIS FILE EXISTS FOR (WP-4a §5, WP-4 T3, destined for WP-5's
`prdw_gates.py`). `grade_full_eval.grade()` decides "was this an answer?" partly
on whether the record carries a result set. A refusal that set `result = []`
instead of `result = None` would therefore be read as a TEMPLATE ANSWER whose
query_id is not a template — and all 19 unanswerable gold rows would flip to a
failure bucket in one move, with nothing in the eval output saying why. It is
one line of surface area between the router and the harness, so it is asserted
directly rather than inferred from an eval number.

The 19 gold rows now name the UNANSWERABLE_CATALOG id as their `gold` rather
than `no_match`, which is what makes "declined for the RIGHT documented reason"
distinguishable from "declined generically" — a distinction `no_match` cannot
express and which the refusal catalogue exists to make.

No API key and no network: `_serve_unanswerable` is a pure function over the
generated catalogue.
"""
import unittest

from query_router.models import RouteTier
from query_router.router import _serve_unanswerable
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG


def _serve(query_id: str):
    return _serve_unanswerable(
        query_id, user_query="how many pensioners are there?",
        normalized="how many pensioners are there", start=0.0,
        template_map=TEMPLATE_CATALOG,
    )


class ServedRefusalShapeTests(unittest.TestCase):

    def test_every_refusal_leaves_result_as_none_never_empty(self):
        """The whole file in one assertion, over all 30."""
        for qid in UNANSWERABLE_CATALOG:
            with self.subTest(qid=qid):
                result = _serve(qid)
                self.assertIsNone(
                    result.result,
                    "a served refusal must leave `result` as None — an empty "
                    "list reads as a template answer with zero rows and flips "
                    "every unanswerable gold row to wrong_template",
                )

    def test_every_refusal_returns_its_own_query_id(self):
        """Without the id, "declined for the right documented reason" and
        "declined generically" are the same event to the grader."""
        for qid in UNANSWERABLE_CATALOG:
            with self.subTest(qid=qid):
                self.assertEqual(_serve(qid).query_id, qid)

    def test_a_refusal_is_served_as_a_fallback_not_a_template_tier(self):
        for qid in UNANSWERABLE_CATALOG:
            with self.subTest(qid=qid):
                self.assertEqual(_serve(qid).tier, RouteTier.FALLBACK)

    def test_the_reason_is_the_workbooks_own_text(self):
        for qid, entry in UNANSWERABLE_CATALOG.items():
            with self.subTest(qid=qid):
                self.assertIn(entry["reason"].strip(), _serve(qid).fallback_message)

    def test_no_unanswerable_id_collides_with_a_template_id(self):
        """The grader routes on the id alone, so an id in both catalogues would
        be graded as whichever branch ran first."""
        self.assertEqual(set(UNANSWERABLE_CATALOG) & set(TEMPLATE_CATALOG), set())


class RefusalGradingTests(unittest.TestCase):
    """The other half of the coupling: what `grade_full_eval` makes of it."""

    def setUp(self):
        import grade_full_eval
        self.grade = grade_full_eval.grade
        self.qid = next(iter(UNANSWERABLE_CATALOG))

    def _record(self, **over):
        rec = {"n": 1, "q": "how many pensioners?", "gold": self.qid, "acc": [],
               "partial": False, "excluded": False, "tier": "fallback",
               "query_id": self.qid, "n_rows": None, "clarification": None}
        rec.update(over)
        return rec

    def test_the_documented_refusal_is_a_hit(self):
        self.assertEqual(self.grade(self._record()), "hit")

    def test_the_wrong_documented_refusal_is_not(self):
        other = [q for q in UNANSWERABLE_CATALOG if q != self.qid][0]
        self.assertEqual(self.grade(self._record(query_id=other)), "wrong_refusal")

    def test_declining_without_the_reason_is_its_own_bucket(self):
        """Right outcome, wrong reason — and worth seeing separately, because
        it is the failure the refusal catalogue was built to remove."""
        self.assertEqual(
            self.grade(self._record(query_id=None)), "declined_generically")

    def test_a_refusal_carrying_rows_is_flagged_not_mis_bucketed(self):
        """If this ever fires, the router regressed `result` from None to [] —
        the single change that would silently flip all 19 rows at once."""
        self.assertEqual(
            self.grade(self._record(n_rows=0)), "refusal_with_rows")

    def test_a_template_answer_with_no_rows_is_still_graded_as_an_answer(self):
        """WP-4a §6.4 — the stale tier tuple. `main.py` emits "tier2", not the
        enum MEMBER name the AP build tested for, so this record used to reach
        the answer branch only through the `n_rows is not None` fallback; a
        template answer that legitimately returns None rows was misgraded. 21 of
        the 346 templates return zero rows by design."""
        rec = {"n": 2, "q": "which GPs uploaded no plan?", "gold": "PLN-005",
               "acc": [], "partial": False, "excluded": False,
               "tier": "tier2", "query_id": "PLN-005", "n_rows": None,
               "clarification": None}
        self.assertEqual(self.grade(rec), "hit")
        rec["query_id"] = "PLN-001"
        self.assertEqual(self.grade(rec), "wrong_template")


if __name__ == "__main__":
    unittest.main()
