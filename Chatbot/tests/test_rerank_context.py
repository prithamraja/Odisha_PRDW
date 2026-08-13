"""
Structural checks on the reranker's family-description layer.

These are cheap invariants that break loudly when someone adds a template to the
catalog and forgets its description, splits a family in half, or pastes a
multi-line description into a listing that is parsed line by line.
"""
import unittest
from collections import Counter

from query_router.rerank_context import DESC_BY_QID, FAMILY_DESCRIPTIONS
from query_router.reranker import _QID_TO_CONTEXT
from query_router.template_catalog import TEMPLATE_CATALOG


class RerankContextTests(unittest.TestCase):
    def test_every_member_id_exists_in_the_catalog(self):
        unknown = sorted(
            qid
            for family in FAMILY_DESCRIPTIONS.values()
            for qid in family["members"]
            if qid not in TEMPLATE_CATALOG
        )
        self.assertEqual(unknown, [], "family members that are not real template ids")

    def test_no_template_appears_in_two_families(self):
        counts = Counter(
            qid
            for family in FAMILY_DESCRIPTIONS.values()
            for qid in family["members"]
        )
        duplicated = sorted(qid for qid, n in counts.items() if n > 1)
        self.assertEqual(duplicated, [], "a template may belong to exactly one family")

    def test_every_template_has_a_non_empty_description(self):
        missing = sorted(
            qid for qid in TEMPLATE_CATALOG
            if not (DESC_BY_QID.get(qid) or "").strip()
        )
        self.assertEqual(missing, [], "templates with no family description")

    def test_no_description_contains_a_newline(self):
        """The candidate listing is line-oriented: one line per field."""
        multiline = sorted(
            name for name, family in FAMILY_DESCRIPTIONS.items()
            if "\n" in family["desc"] or "\r" in family["desc"]
        )
        self.assertEqual(multiline, [], "descriptions must be a single line")

    def test_every_family_declares_at_least_one_member(self):
        empty = sorted(
            name for name, family in FAMILY_DESCRIPTIONS.items()
            if not family["members"]
        )
        self.assertEqual(empty, [], "a family with no members is dead weight")

    def test_reranker_context_carries_the_descriptions_through(self):
        """The rewire actually reaches the listing builder, for all 376.

        Both catalogues: the 346 templates AND the 30 known-unanswerables, which
        the retriever also indexes. An unanswerable candidate shown to the model
        with no ↳ line reads like any other question, and the one thing the model
        has to know about it is precisely that it cannot be answered.
        """
        from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
        self.assertEqual(
            set(_QID_TO_CONTEXT), set(TEMPLATE_CATALOG) | set(UNANSWERABLE_CATALOG)
        )
        for qid, (desc, filters) in _QID_TO_CONTEXT.items():
            self.assertTrue(desc.strip(), f"{qid} reaches the reranker with no ↳ line")
            self.assertTrue(filters.strip(), f"{qid} has no accepted-filters line")

    def test_the_unanswerables_say_so_in_their_description(self):
        from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
        for qid in UNANSWERABLE_CATALOG:
            with self.subTest(qid=qid):
                self.assertIn("CANNOT BE ANSWERED", _QID_TO_CONTEXT[qid][0])

    def test_the_two_expenditure_conventions_are_named(self):
        """PR&DW's equivalent of AP's difference-vs-intersection collision.

        The data dictionary's central trap: this database holds expenditure on
        TWO bases — plan basis (activity_expenditure, on v_activity) and cash
        basis (the voucher cashbook, on v_voucher) — and they do not agree.
        Answering a cashbook question from the plan basis, or the reverse, is a
        wrong number that looks entirely right. Nothing in the two questions'
        WORDING separates them, so the ↳ line has to.
        """
        self.assertIn("PLAN basis", DESC_BY_QID["EXP-001"])
        for qid in ("EXP-024", "ALR-013"):
            with self.subTest(qid=qid):
                self.assertIn("CASHBOOK", DESC_BY_QID[qid])

    def test_uploaded_and_approved_plans_are_told_apart(self):
        """PLN-001 counts every plan row; PLN-002 counts the approved subset.

        They currently return the SAME figure, because plan_code_status is
        entirely NULL and approval is proxied by a date every loaded plan has.
        Two questions that agree by accident are exactly where a reranker
        mis-picks without anyone noticing.
        """
        self.assertIn("not the approved subset", DESC_BY_QID["PLN-001"])
        self.assertIn("proxied", DESC_BY_QID["PLN-002"].lower())

    def test_absence_families_say_they_read_the_roster(self):
        """The bootstrap's keep-the-zero-rows lesson, as a routing rule.

        "Which GPs planned nothing under this theme" is answered FROM
        gram_panchayat; no query over v_activity can return those rows, because
        the rows do not exist there. Without that contrast the reranker cannot
        keep them apart from the activity-side counting questions they are
        worded like.
        """
        for qid in ("PLN-005", "PLN-032", "PLN-059", "SCH-006"):
            with self.subTest(qid=qid):
                self.assertIn("ROSTER", DESC_BY_QID[qid].upper())

    def test_sbm_families_state_the_keyword_pattern_they_match_on(self):
        """The SBM templates accept IDENTICAL filters and differ only in a regex
        frozen inside their SQL, so `accepts filters:` cannot separate them and
        the description must carry the pattern itself.

        SBM-OM-010 is the one exception and is asserted as such: it is the only
        SBM question that identifies its subject from a coded column
        (`work_type`) rather than by searching activity text, so it is also the
        only one whose number does not carry the keyword-coverage caveat.
        """
        from query_router.template_catalog import TEMPLATE_CATALOG as catalog
        sbm = sorted(q for q, e in catalog.items()
                     if e["bracket"] == "Sanitation (SBM)")
        self.assertEqual(len(sbm), 85)

        keyword_matched = [q for q in sbm
                           if "regexp_matches" in catalog[q]["sql_template"]]
        self.assertEqual(sorted(set(sbm) - set(keyword_matched)), ["SBM-OM-010"])
        for qid in keyword_matched:
            with self.subTest(qid=qid):
                self.assertIn("KEYWORD MATCH", DESC_BY_QID[qid])
        self.assertNotIn("KEYWORD MATCH", DESC_BY_QID["SBM-OM-010"])

    def test_siblings_share_one_description_verbatim(self):
        """The prompt promises variants of a family repeat it word-for-word.

        These triples are the workbook's own scope variants, which decision D2's
        optional filters collapse into ONE executable query — PLN-025/027/029
        have byte-identical SQL and identical slots. Sharing a description is
        not a convenience there; it is the truth about them.
        """
        for triple in (("PLN-025", "PLN-027", "PLN-029"),
                       ("PLN-052", "PLN-054", "PLN-056")):
            descs = {DESC_BY_QID[qid] for qid in triple}
            self.assertEqual(len(descs), 1, f"{triple} must share one description")


if __name__ == "__main__":
    unittest.main()
