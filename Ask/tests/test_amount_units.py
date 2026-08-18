"""Indian-notation amount conversion is deterministic and lives outside the LLM.

Officers quote money in lakhs and crores; every rupee slot in the catalogue
(`$amount_threshold`, and `$threshold` on its money questions) is a plain
number. AP made exactly this mistake once with land units — the acre→hectare
conversion happened inside the extractor prompt, i.e. an LLM doing arithmetic,
which is not reproducible even at temperature 0. "Activities above 1 lakh" could
mean ₹1 on one replay and ₹100,000 on the next, with the same question and the
same routing.

These tests pin the conversion to code, and pin the two things that make it
safe: an UNKNOWN unit fails loudly rather than being read as bare rupees, and a
plain number passes through untouched so the non-money readings of `$threshold`
(percent, days, activity counts) are unaffected.

Replaces `test_land_units.py`, whose acre/cent→hectare subject is
agriculture-only. Same structure, PR&DW subject.
"""
import unittest

from query_router.entity_validator import (
    AMOUNT_UNIT_FACTORS,
    EntityValidator,
    parse_amount,
    parse_deadline,
)
from query_router.models import EntityNotFound
from query_router.router import amount_from_text


class ParseAmountTests(unittest.TestCase):
    def test_lakhs_convert(self):
        self.assertEqual(parse_amount("1 lakh"), (100000.0, "lakh"))
        self.assertEqual(parse_amount("5 lakhs"), (500000.0, "lakhs"))
        self.assertEqual(parse_amount("1.5 lakh"), (150000.0, "lakh"))

    def test_crores_convert(self):
        self.assertEqual(parse_amount("2.5 crore"), (25000000.0, "crore"))
        self.assertEqual(parse_amount("1 crore"), (10000000.0, "crore"))
        self.assertEqual(parse_amount("3 cr"), (30000000.0, "cr"))

    def test_the_spellings_that_actually_get_typed(self):
        for text in ("1 lakh", "1 lakhs", "1 lac", "1 lacs", "1 Lakh", "1LAKH"):
            with self.subTest(text=text):
                self.assertEqual(parse_amount(text)[0], 100000.0)

    def test_rupee_symbols_and_words_pass_through(self):
        self.assertEqual(parse_amount("₹50,000"), (50000.0, None))
        self.assertEqual(parse_amount("Rs. 50000"), (50000.0, None))
        self.assertEqual(parse_amount("INR 50000"), (50000.0, None))
        self.assertEqual(parse_amount("50000 rupees")[0], 50000.0)
        self.assertEqual(parse_amount("Rs. 1,00,000/-")[0], 100000.0)

    def test_a_bare_number_means_rupees(self):
        self.assertEqual(parse_amount("50000"), (50000.0, None))
        self.assertEqual(parse_amount(" 50000 "), (50000.0, None))

    def test_indian_digit_grouping(self):
        # 1,00,000 is one lakh written out — not 1,000 followed by junk.
        self.assertEqual(parse_amount("1,00,000")[0], 100000.0)
        self.assertEqual(parse_amount("50,000")[0], 50000.0)

    def test_a_multiplier_may_carry_a_prefix_and_a_suffix_at_once(self):
        self.assertEqual(parse_amount("Rs 2 lakh rupees")[0], 200000.0)
        self.assertEqual(parse_amount("₹2.5 crore")[0], 25000000.0)

    def test_an_unknown_unit_is_not_silently_rupees(self):
        for junk in ("2 bighas", "2 quintals", "2 sqft", "banana", "lakh"):
            with self.assertRaises(ValueError, msg=junk):
                parse_amount(junk)

    def test_the_scale_words_are_the_indian_ones(self):
        self.assertEqual(AMOUNT_UNIT_FACTORS["lakh"], 1e5)
        self.assertEqual(AMOUNT_UNIT_FACTORS["crore"], 1e7)
        # A crore is a hundred lakh, not a thousand — the arithmetic an LLM
        # would occasionally get wrong.
        self.assertEqual(
            AMOUNT_UNIT_FACTORS["lakh"] * 100, AMOUNT_UNIT_FACTORS["crore"]
        )


class _NoDBConn:
    """Numeric validation touches no registry, so the DB load is skipped."""

    def execute(self, *_args, **_kwargs):
        raise RuntimeError("no database in this test")


class ValidatorAmountTests(unittest.TestCase):
    def setUp(self):
        self.v = EntityValidator(_NoDBConn())

    def test_lakhs_resolve_to_rupees_and_are_flagged_converted(self):
        e = self.v.validate("1 lakh", "amount_threshold")
        self.assertEqual(e.resolved_value, "100000")
        self.assertEqual(e.raw_value, "1 lakh")
        self.assertEqual(e.confidence, "converted")

    def test_crores_resolve(self):
        e = self.v.validate("2.5 crore", "amount_threshold")
        self.assertEqual(e.resolved_value, "25000000")
        self.assertEqual(e.confidence, "converted")

    def test_a_rupee_figure_is_unchanged_and_not_flagged_converted(self):
        for text in ("₹50,000", "50,000", "50000", "Rs. 50000"):
            with self.subTest(text=text):
                e = self.v.validate(text, "amount_threshold")
                self.assertEqual(e.resolved_value, "50000")
                self.assertEqual(e.confidence, "numeric")

    def test_the_conversion_does_not_go_scientific_at_crore_scale(self):
        """'2.5e+07' in a SQL bind is a different value than the one meant."""
        e = self.v.validate("2.5 crore", "amount_threshold")
        self.assertNotIn("e", e.resolved_value.lower())

    def test_threshold_takes_amounts_too(self):
        self.assertEqual(
            self.v.validate("1 lakh", "threshold").resolved_value, "100000"
        )

    def test_thresholds_other_readings_are_untouched(self):
        """$threshold is a percent, a day count or an activity count as often as
        it is rupees. A plain number must survive verbatim."""
        for text, expected in (("50", "50"), ("50%", "50"), ("0", "0"), ("7", "7")):
            with self.subTest(text=text):
                self.assertEqual(
                    self.v.validate(text, "threshold").resolved_value, expected
                )

    def test_a_junk_unit_is_rejected(self):
        with self.assertRaises(EntityNotFound):
            self.v.validate("2 bighas", "amount_threshold")

    def test_the_range_check_still_applies_after_conversion(self):
        with self.assertRaises(EntityNotFound):
            self.v.validate("-1 lakh", "amount_threshold")

    def test_other_numeric_slots_are_untouched_by_the_amount_parser(self):
        self.assertEqual(self.v.validate("10", "top_n").resolved_value, "10")
        with self.assertRaises(EntityNotFound):
            self.v.validate("1 lakh", "top_n")

    def test_top_n_range(self):
        """The ceiling is 1,000, RATIFIED by the operator on 2026-08-13 after
        WP-3's audit (decision D11.4).

        The audit found 38 of the 91 $top_n templates whose statewide result can
        exceed it — whole-roster GP listings (~6,800) and unbounded activity-grain
        exception reports. The ruling is that those get a clarification rather
        than a 6,800-row chat answer: they are export questions, and the ceiling
        is what surfaces that instead of dumping the rows.

        Pinned here so raising it is a deliberate act, not a passing thought.
        """
        self.assertEqual(self.v.validate("1000", "top_n").resolved_value, "1000")
        for bad in ("0", "-5", "1001", "6800", "2.5"):
            with self.subTest(bad=bad):
                with self.assertRaises(EntityNotFound):
                    self.v.validate(bad, "top_n")


class AmountRegexTests(unittest.TestCase):
    """The pre-pass: plainly stated amounts never reach the LLM."""

    def test_reads_a_stated_figure_with_its_multiplier(self):
        self.assertEqual(
            amount_from_text("activities above 1 lakh"), "1 lakh")
        self.assertEqual(
            amount_from_text("works costing more than 2.5 crore"), "2.5 crore")
        self.assertEqual(
            amount_from_text("expenditure over ₹50,000"), "50,000")

    def test_a_bare_number_is_not_claimed(self):
        """$threshold's unit varies by question. A bare 'more than 50' could be
        a percent, a day count or a rupee figure, and only the sentence says
        which — so it goes to the extractor rather than being guessed here."""
        self.assertIsNone(amount_from_text("blocks with more than 50 activities"))
        self.assertIsNone(amount_from_text("GPs above 50 percent completion"))

    def test_two_figures_fall_through_to_the_llm(self):
        self.assertIsNone(amount_from_text("between 1 lakh and 5 lakh"))
        self.assertIsNone(amount_from_text("₹1 lakh or ₹2 lakh"))

    def test_no_amount_is_none(self):
        self.assertIsNone(amount_from_text("how many gram panchayats are there"))
        self.assertIsNone(amount_from_text("activities in Khordha district"))

    def test_it_does_not_fire_on_unrelated_words(self):
        # 'cr' must be a whole word, not a fragment of another one.
        self.assertIsNone(amount_from_text("12 credits"))
        self.assertIsNone(amount_from_text("3 crates"))

    def test_the_output_feeds_the_validator_unchanged(self):
        v = EntityValidator(_NoDBConn())
        got = amount_from_text("activities above 1 lakh")
        self.assertEqual(
            v.validate(got, "amount_threshold").resolved_value, "100000"
        )


class DeadlineTests(unittest.TestCase):
    """No deadline is stored anywhere in the database, so the GPDP-deadline
    questions bind whatever the user supplies — which makes the parse the only
    thing standing between a typo and a silently reclassified answer."""

    def setUp(self):
        self.v = EntityValidator(_NoDBConn())

    def test_iso_passes_through(self):
        self.assertEqual(parse_deadline("2024-06-30"), "2024-06-30")

    def test_a_named_month_is_unambiguous_and_accepted(self):
        for text in ("30 June 2024", "30 Jun 2024", "June 30, 2024"):
            with self.subTest(text=text):
                self.assertEqual(parse_deadline(text), "2024-06-30")

    def test_a_day_first_numeric_date_is_accepted_when_the_day_cannot_be_a_month(self):
        self.assertEqual(parse_deadline("30-06-2024"), "2024-06-30")
        self.assertEqual(parse_deadline("30/06/2024"), "2024-06-30")

    def test_an_ambiguous_numeric_date_is_refused_not_guessed(self):
        """06/07/2024 is 6 July to an Indian officer and 7 June to an American
        library. A deadline decides which plans count as late, so a guess here
        silently changes the answer."""
        for text in ("06/07/2024", "01-02-2024"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_deadline(text)

    def test_junk_is_refused(self):
        for text in ("", "soon", "2024-13-45", "next month"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_deadline(text)

    def test_the_validator_turns_a_bad_deadline_into_a_clarification(self):
        with self.assertRaises(EntityNotFound):
            self.v.validate("06/07/2024", "deadline")

    def test_the_validator_emits_iso(self):
        self.assertEqual(
            self.v.validate("30 June 2024", "deadline").resolved_value, "2024-06-30"
        )


if __name__ == "__main__":
    unittest.main()
