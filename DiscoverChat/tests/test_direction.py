# -*- coding: utf-8 -*-
"""WP-D13 Fix 1 (D63): signed figures in words, and the direction check.

Offline -- no model calls. Run:
    python -m pytest DiscoverChat/tests/test_direction.py -q
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from DiscoverChat import checks, glossary, corpus as corpus_mod   # noqa: E402
from phase5f_decompose import _SIGNED_DIRECTION                   # noqa: E402

_CORPUS = None


def _corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = corpus_mod.load()
    return _CORPUS


def _signed(record) -> bool:
    return (record.is_decomposition
            and record.data.get("measure") in _SIGNED_DIRECTION)


class HelperTests(unittest.TestCase):
    """The token rewrite on a bare value, as WP-D12's cards will call it."""

    def test_bare_values(self):
        cases = {
            ("Rs -51.96 crore", "overspend_vs_plan"): "Rs 51.96 crore below plan",
            ("Rs -98.42 lakh", "overspend_vs_plan"): "Rs 98.42 lakh below plan",
            ("Rs -78,028", "overspend_vs_sanction"): "Rs 78,028 below sanction",
            ("Rs 1.73 lakh", "overspend_vs_plan"): "Rs 1.73 lakh",
            ("Rs -51.96 crore", "planned_cost"): "Rs -51.96 crore",
        }
        for (value, measure), want in cases.items():
            self.assertEqual(glossary.signed_money(value, measure), want)

    def test_fiscal_year_is_not_touched(self):
        text = "In 2023-24, spending totals Rs -3.18 crore."
        self.assertEqual(glossary.signed_money(text, "overspend_vs_plan"),
                         "In 2023-24, spending totals Rs 3.18 crore below plan.")


class CorpusSweepTests(unittest.TestCase):
    """§1.4 test 1 -- every record of both corpora."""

    def test_signed_records(self):
        counts = {"records": 0, "minus_tokens": 0, "added": 0}
        problems = []
        for record in _corpus().all():
            if not _signed(record):
                continue
            counts["records"] += 1
            measure, signs = record.data["measure"], record.data["signs"]
            below = glossary.signed_below(measure)
            note = glossary.signed_note(measure)
            before = glossary.render(record.sentence, record.view)
            shown = record.display_sentence()
            self.assertIn(note, before,
                          f"{record.id}: the builder's sign sentence changed "
                          f"wording; glossary.signed_note must follow it")
            minus = len(re.findall(r"Rs -\d", record.sentence))
            removed_note_below = (note.count(below)
                                  if signs == "all_negative" else 0)
            added = shown.count(below) - (before.count(below)
                                          - removed_note_below)
            counts["minus_tokens"] += minus
            counts["added"] += added
            if "Rs -" in shown:
                problems.append((record.id, "minus left"))
            if added != minus:
                problems.append((record.id, f"added {added} for {minus}"))
            if checks.numerals(shown) != checks.numerals(record.sentence):
                problems.append((record.id, "numerals changed"))
            if (note in shown) == (signs == "all_negative"):
                problems.append((record.id, f"sign sentence wrong for {signs}"))
        self.assertEqual(problems, [])
        self.assertEqual(counts["records"], 5717)
        self.assertEqual(counts["added"], counts["minus_tokens"])

    def test_every_other_record_unchanged(self):
        changed = [record.id for record in _corpus().all()
                   if not _signed(record)
                   and record.display_sentence()
                   != glossary.render(record.sentence, record.view)]
        self.assertEqual(changed, [])


class FiveSentenceTests(unittest.TestCase):
    """§1.4 test 2 -- the PM's five sentences on d1-00248, in block mode."""

    def setUp(self):
        self.record = _corpus().get("d1-00248")

    def run_check(self, prose):
        return checks.check_citations(prose, [self.record],
                                      direction_mode="block")

    def test_raw_minus_fails_on_r2(self):
        r = self.run_check("Spending measured against plan totals "
                           "Rs -51.96 crore [d1-00248].")
        self.assertFalse(r["all_pass"])
        rules = r["5_direction"]["failures"][0]["rules"]
        self.assertTrue(any(rule.startswith("R2") for rule in rules), rules)

    def test_true_sentence_passes(self):
        r = self.run_check("Recorded spending is Rs 51.96 crore below plan "
                           "[d1-00248].")
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))
        self.assertEqual(r["5_direction"]["checked"], 1)

    def test_above_plan_fails(self):
        r = self.run_check("Recorded spending is Rs 51.96 crore above plan "
                           "[d1-00248].")
        self.assertFalse(r["all_pass"])
        self.assertTrue(r["2_numerals_cited"]["pass"])
        self.assertFalse(r["5_direction"]["pass"])

    def test_exceeded_fails_on_r1(self):
        r = self.run_check("Spending exceeded the plan by Rs 51.96 crore "
                           "[d1-00248].")
        self.assertFalse(r["all_pass"])
        rules = r["5_direction"]["failures"][0]["rules"]
        self.assertTrue(any(rule.startswith("R1") for rule in rules), rules)

    def test_wrong_number_fails_on_step_2(self):
        r = self.run_check("Recorded spending is Rs 61.96 crore below plan "
                           "[d1-00248].")
        self.assertFalse(r["all_pass"])
        self.assertFalse(r["2_numerals_cited"]["pass"])


class ShapeTests(unittest.TestCase):
    """§1.4 test 3."""

    def check(self, prose, ids):
        records = [_corpus().get(i) for i in ids]
        return checks.check_citations(prose, records, direction_mode="block")

    def test_several_figures_one_below(self):
        r = self.check("Spending is Rs 51.96 crore below plan, of which "
                       "Rs 46.90 crore sits with rows of no grant type and "
                       "Rs 5.06 crore with the rest [d1-00248].", ["d1-00248"])
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))

    def test_shares_only_not_checked(self):
        r = self.check("Rows with no grant type on file hold 90.3% of the "
                       "gap [d1-00248].", ["d1-00248"])
        self.assertTrue(r["all_pass"])
        self.assertEqual(r["5_direction"]["checked"], 0)

    def test_follow_on_sentence_fails_and_is_named(self):
        r = self.check("Spending is Rs 51.96 crore below plan [d1-00248]. "
                       "Most of it, Rs 46.90 crore, has no grant type on "
                       "file [d1-00248].", ["d1-00248"])
        self.assertFalse(r["all_pass"])
        failures = r["5_direction"]["failures"]
        self.assertEqual([f["sentence_index"] for f in failures], [1])
        reason = checks.citation_failure_reason(r)
        self.assertIn("Most of it, Rs 46.90 crore", reason)
        self.assertIn("Rs 46.90 crore below plan", reason)

    def test_positive_and_negative_both_phrased(self):
        # d1-00108 is mixed: "1 of them add Rs 1.73 lakh" (positive) and
        # "Sanitation at Rs -1.33 crore" (negative), measured against sanction.
        record = _corpus().get("d1-00108")
        self.assertEqual(record.data["signs"], "mixed")
        r = self.check("One focus area ran Rs 1.73 lakh above sanction, while "
                       "Sanitation was Rs 1.33 crore below sanction "
                       "[d1-00108].", ["d1-00108"])
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))
        self.assertEqual(r["5_direction"]["checked"], 1)

    def test_fiscal_year_is_not_a_minus(self):
        r = self.check("In 2023-24 spending was Rs 51.96 crore below plan "
                       "[d1-00248].", ["d1-00248"])
        self.assertTrue(r["5_direction"]["pass"],
                        r["5_direction"]["failures"])

    def test_ambiguous_token_skipped_and_counted(self):
        record = next(
            f for f in _corpus().all() if _signed(f)
            and (checks.signed_facts(f) or {}).get("ambiguous"))
        facts = checks.signed_facts(record)
        token = sorted(facts["ambiguous"])[0]
        r = checks.check_citations(f"The figure is {token} [{record.id}].",
                                   [record], direction_mode="block")
        self.assertEqual(r["5_direction"]["skipped_ambiguous"], 1)
        self.assertEqual(r["5_direction"]["checked"], 0)


class ModeTests(unittest.TestCase):
    """§1.4 test 4."""

    WRONG = "Recorded spending is Rs 51.96 crore above plan [d1-00248]."

    def setUp(self):
        self.record = _corpus().get("d1-00248")

    def test_log_does_not_count(self):
        off = checks.check_citations(self.WRONG, [self.record],
                                     direction_mode="off")
        log = checks.check_citations(self.WRONG, [self.record],
                                     direction_mode="log")
        self.assertEqual(log["all_pass"], off["all_pass"])
        self.assertTrue(log["all_pass"])
        self.assertFalse(log["5_direction"]["pass"])
        self.assertFalse(log["5_direction"]["counts"])
        self.assertNotIn("direction", checks.citation_failure_reason(log))

    def test_off_omits_the_step(self):
        off = checks.check_citations(self.WRONG, [self.record],
                                     direction_mode="off")
        self.assertNotIn("5_direction", off)

    def test_block_counts(self):
        block = checks.check_citations(self.WRONG, [self.record],
                                       direction_mode="block")
        self.assertFalse(block["all_pass"])
        self.assertIn("below plan", checks.citation_failure_reason(block))

    def test_configured_mode_read_at_call_time(self):
        from DiscoverChat import config
        saved = config.DIRECTION_CHECK
        try:
            config.DIRECTION_CHECK = "block"
            self.assertFalse(checks.check_citations(
                self.WRONG, [self.record])["all_pass"])
            config.DIRECTION_CHECK = "off"
            self.assertNotIn("5_direction", checks.check_citations(
                self.WRONG, [self.record]))
        finally:
            config.DIRECTION_CHECK = saved


if __name__ == "__main__":
    unittest.main()
