"""The question text is the last place a wrong date window can hide: the user
sees their words echoed back and assumes the answer matched them. These tests
pin both halves of that — the phrases that MUST produce a window, and the
digit runs that must never be mistaken for one."""
import unittest

from query_router.date_phrase import extract_date_window


class ExtractsExplicitPeriodsTests(unittest.TestCase):
    def test_single_year(self):
        self.assertEqual(
            extract_date_window(
                "How much input subsidy went to each mandal of Krishna district in 2024?"
            ),
            ("2024-01-01", "2024-12-31"),
        )

    def test_between_two_years_spans_them(self):
        self.assertEqual(
            extract_date_window("enrolment between 2023 and 2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_to_range_reads_the_same_as_between(self):
        self.assertEqual(
            extract_date_window("enrolment 2023 to 2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_season_contributes_its_label_year_only(self):
        self.assertEqual(
            extract_date_window("paddy procurement in kharif 2024"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_season_case_and_vocabulary(self):
        self.assertEqual(
            extract_date_window("Rabi 2023 sowing"),
            ("2023-01-01", "2023-12-31"),
        )

    def test_crop_year_label_uses_the_label_year(self):
        self.assertEqual(
            extract_date_window("subsidy for FY 2024-25"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_crop_year_label_without_the_fy_prefix(self):
        self.assertEqual(
            extract_date_window("2024-25 disbursements"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_four_digit_range_is_a_range_not_a_crop_year(self):
        self.assertEqual(
            extract_date_window("disbursements 2023-2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_month_and_year(self):
        self.assertEqual(
            extract_date_window("payments made in March 2025"),
            ("2025-03-01", "2025-03-31"),
        )

    def test_abbreviated_month(self):
        self.assertEqual(
            extract_date_window("payments made in Mar 2025"),
            ("2025-03-01", "2025-03-31"),
        )

    def test_month_window_ends_on_the_real_last_day(self):
        self.assertEqual(
            extract_date_window("February 2024 payouts"),
            ("2024-02-01", "2024-02-29"),  # leap year
        )

    def test_years_outside_the_data_are_honoured_as_typed(self):
        # An empty result for 2031 is an honest answer; silently substituting
        # 2025 is not.
        self.assertEqual(
            extract_date_window("claims in 2031"),
            ("2031-01-01", "2031-12-31"),
        )


class NoWindowTests(unittest.TestCase):
    def test_bare_season(self):
        self.assertIsNone(extract_date_window("procurement in kharif"))

    def test_bare_month(self):
        self.assertIsNone(extract_date_window("payments made in March"))

    def test_relative_phrase(self):
        self.assertIsNone(extract_date_window("how many farmers enrolled last year"))

    def test_this_season(self):
        self.assertIsNone(extract_date_window("what was procured this season"))

    def test_rupee_amount(self):
        self.assertIsNone(extract_date_window("₹2025 was paid to the farmer"))

    def test_rs_amount(self):
        self.assertIsNone(extract_date_window("farmers who received Rs. 2025"))

    def test_quantity(self):
        self.assertIsNone(extract_date_window("farmers with over 2025 kg"))

    def test_area_quantity(self):
        self.assertIsNone(extract_date_window("holdings above 2024 acres"))

    def test_aadhaar_number(self):
        self.assertIsNone(extract_date_window("show me aadhaar 726018202483"))

    def test_mobile_number(self):
        self.assertIsNone(extract_date_window("farmer with mobile 9820241234"))

    def test_no_temporal_content_at_all(self):
        self.assertIsNone(
            extract_date_window("How many PM-KISAN beneficiaries are in Guntur?")
        )

    def test_empty_message(self):
        self.assertIsNone(extract_date_window(""))


class GuardPrecisionTests(unittest.TestCase):
    """The guards must not swallow legitimate years — a false negative here is
    the same silent-wrong-window bug this module exists to remove."""

    def test_years_does_not_read_as_a_stray_rs(self):
        self.assertEqual(
            extract_date_window("over the years 2024 saw the most claims"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_a_guarded_amount_does_not_suppress_a_real_year(self):
        self.assertEqual(
            extract_date_window("farmers paid ₹2025 during 2024"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_month_year_wins_over_the_bare_year_reading(self):
        # The year is claimed once, at the higher precision.
        self.assertEqual(
            extract_date_window("March 2025"),
            ("2025-03-01", "2025-03-31"),
        )


if __name__ == "__main__":
    unittest.main()
