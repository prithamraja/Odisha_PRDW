"""Land-unit conversion is deterministic and lives outside the LLM.

Users say acres, and in AP small plots are quoted in cents (1 acre = 100 cents),
but every threshold_hectares slot is in hectares. The conversion used to happen
inside the extractor prompt; these tests pin it to code.
"""
import unittest

from query_router.entity_validator import (
    EntityValidator,
    LAND_UNIT_FACTORS,
    parse_land_value,
)
from query_router.models import EntityNotFound
from query_router.router import land_threshold_from_text


class ParseLandValueTests(unittest.TestCase):
    def test_acres_convert(self):
        self.assertEqual(parse_land_value("1 acre"), (0.4047, "acre"))
        self.assertEqual(parse_land_value("2 acres"), (0.8094, "acres"))
        self.assertEqual(parse_land_value("5 acres"), (2.0234, "acres"))
        self.assertEqual(parse_land_value("7.25 acres"), (2.934, "acres"))

    def test_cents_convert(self):
        self.assertEqual(parse_land_value("50 cents"), (0.2023, "cents"))
        self.assertEqual(parse_land_value("100 cents"), (0.4047, "cents"))
        self.assertEqual(parse_land_value("1 cent"), (0.004, "cent"))

    def test_hectares_pass_through(self):
        self.assertEqual(parse_land_value("1.5 hectares"), (1.5, "hectares"))
        self.assertEqual(parse_land_value("2 ha"), (2.0, "ha"))

    def test_a_bare_number_means_hectares(self):
        self.assertEqual(parse_land_value("1.5"), (1.5, None))
        self.assertEqual(parse_land_value(" 2 "), (2.0, None))

    def test_abbreviations_and_case(self):
        self.assertEqual(parse_land_value("3 AC"), (1.2141, "ac"))
        self.assertEqual(parse_land_value("3Acres"), (1.2141, "acres"))

    def test_commas_are_tolerated(self):
        self.assertEqual(parse_land_value("1,000 acres"), (404.686, "acres"))

    def test_an_unknown_unit_is_not_silently_hectares(self):
        for junk in ("2 bighas", "2 furlongs", "2 sqft", "banana"):
            with self.assertRaises(ValueError, msg=junk):
                parse_land_value(junk)

    def test_one_acre_matches_the_figure_the_eval_pins(self):
        # Full-sheet row #52 answers 62 farmers at this threshold.
        self.assertEqual(parse_land_value("1 acre")[0], 0.4047)

    def test_cents_are_a_hundredth_of_an_acre(self):
        self.assertAlmostEqual(
            LAND_UNIT_FACTORS["cent"] * 100, LAND_UNIT_FACTORS["acre"], places=9
        )


class _NoDbValidator(EntityValidator):
    """Numeric validation touches no registry, so the DB load is skipped."""

    def __init__(self):
        self._registry = {}
        self._farmer_districts = {}


class ValidatorLandUnitTests(unittest.TestCase):
    def setUp(self):
        self.v = _NoDbValidator()

    def test_acres_resolve_to_hectares_and_are_flagged_converted(self):
        e = self.v.validate("2 acres", "threshold_hectares")
        self.assertEqual(e.resolved_value, "0.8094")
        self.assertEqual(e.raw_value, "2 acres")
        self.assertEqual(e.confidence, "converted")

    def test_cents_resolve(self):
        e = self.v.validate("50 cents", "threshold_hectares")
        self.assertEqual(e.resolved_value, "0.2023")
        self.assertEqual(e.confidence, "converted")

    def test_hectares_are_unchanged_and_not_flagged_converted(self):
        e = self.v.validate("1.5", "threshold_hectares")
        self.assertEqual(e.resolved_value, "1.5")
        self.assertEqual(e.confidence, "numeric")

    def test_explicit_hectares_resolve_to_themselves(self):
        e = self.v.validate("1.5 hectares", "threshold_hectares")
        self.assertEqual(e.resolved_value, "1.5")

    def test_explicit_hectares_are_not_flagged_converted(self):
        # else the description echoes the redundant "1.5 hectares (1.5 ha)"
        for text in ("1.5 hectares", "2 ha", "3 hectare"):
            self.assertEqual(
                self.v.validate(text, "threshold_hectares").confidence, "numeric", text)

    def test_a_junk_unit_is_rejected(self):
        with self.assertRaises(EntityNotFound):
            self.v.validate("2 bighas", "threshold_hectares")

    def test_the_range_check_still_applies_after_conversion(self):
        # exclusive_min = 0, so a zero-or-negative threshold is still refused
        with self.assertRaises(EntityNotFound):
            self.v.validate("0 acres", "threshold_hectares")

    def test_other_numeric_slots_are_untouched_by_the_unit_parser(self):
        self.assertEqual(self.v.validate("10", "top_n").resolved_value, "10")
        self.assertEqual(self.v.validate("2024", "crop_year").resolved_value, "2024")
        with self.assertRaises(EntityNotFound):
            self.v.validate("10 acres", "top_n")


class LandThresholdRegexTests(unittest.TestCase):
    """The pre-pass: plainly stated thresholds never reach the LLM."""

    def test_reads_a_stated_figure_with_its_unit(self):
        self.assertEqual(
            land_threshold_from_text("farmers with less than 2 acres"), "2 acres")
        self.assertEqual(
            land_threshold_from_text("list farmers under 50 cents"), "50 cents")
        self.assertEqual(
            land_threshold_from_text("who holds below 1.5 ha"), "1.5 ha")

    def test_reads_the_policy_bands(self):
        self.assertEqual(land_threshold_from_text("give me all marginal farmers list"), "1")
        self.assertEqual(land_threshold_from_text("small farmers list"), "2")
        self.assertEqual(land_threshold_from_text("small and marginal farmers"), "2")

    def test_a_stated_figure_beats_a_band_word(self):
        self.assertEqual(
            land_threshold_from_text("marginal farmers under 2 acres"), "2 acres")

    def test_two_figures_fall_through_to_the_llm(self):
        self.assertIsNone(land_threshold_from_text("between 1 and 2 acres"))

    def test_no_threshold_is_none(self):
        self.assertIsNone(land_threshold_from_text("how many farmers are there"))
        self.assertIsNone(land_threshold_from_text("farmers in Krishna district"))

    def test_it_does_not_fire_on_unrelated_words(self):
        # 'ha' and 'ac' must be whole words, not fragments of another one
        self.assertIsNone(land_threshold_from_text("12 hackathons"))
        self.assertIsNone(land_threshold_from_text("3 accounts"))

    def test_the_output_feeds_the_validator_unchanged(self):
        v = _NoDbValidator()
        got = land_threshold_from_text("farmers with less than 2 acres")
        self.assertEqual(v.validate(got, "threshold_hectares").resolved_value, "0.8094")


if __name__ == "__main__":
    unittest.main()
