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
        """The rewire actually reaches the listing builder, for all 278."""
        self.assertEqual(set(_QID_TO_CONTEXT), set(TEMPLATE_CATALOG))
        for qid, (desc, filters) in _QID_TO_CONTEXT.items():
            self.assertTrue(desc.strip(), f"{qid} reaches the reranker with no ↳ line")
            self.assertTrue(filters.strip(), f"{qid} has no accepted-filters line")

    def test_scheme_set_logic_families_state_their_relation(self):
        """The defect that motivated this layer: difference vs intersection.

        S02 must say it is a difference and Q122 must say it is an intersection,
        or the reranker is back to matching on the nouns alone.
        """
        self.assertIn("DIFFERENCE", DESC_BY_QID["S02"])
        self.assertIn("but NOT", DESC_BY_QID["S02"])
        self.assertIn("INTERSECTION", DESC_BY_QID["Q122"])

    def test_scheme_slot_families_name_pm_kisan_as_an_operand(self):
        """PM-KISAN is the seventh scheme; the {scheme} families must say so."""
        for qid in ("S02", "S07"):
            self.assertIn("PM-KISAN", DESC_BY_QID[qid])

    def test_keep_six_families_say_they_measure_state_schemes(self):
        """G35/Q015/Q029/Q059 compare the six state schemes AGAINST the roster.

        Without that contrast in the description the reranker cannot separate
        them from a scheme-difference question that names PM-KISAN.
        """
        for qid in ("G35-S", "Q015", "Q029", "Q059"):
            self.assertIn("STATE", DESC_BY_QID[qid].upper())

    def test_siblings_share_one_description_verbatim(self):
        """The prompt promises variants of a family repeat it word-for-word."""
        for triple in (("G01-S", "G01-D", "G01-M"), ("G35-S", "G35-D", "G35-M")):
            descs = {DESC_BY_QID[qid] for qid in triple}
            self.assertEqual(len(descs), 1, f"{triple} must share one description")


if __name__ == "__main__":
    unittest.main()
