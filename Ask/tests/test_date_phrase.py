"""The question text is the last place a wrong year can hide: the user sees
their words echoed back and assumes the answer matched them.

Two halves are pinned here.

**Fiscal-year strings** — the load-bearing half for PR&DW. `fiscal_year` is a
VARCHAR equality filter holding `'2024-2025'`, so the abbreviated label an
officer actually says ('FY 24-25') binds *successfully* and matches *nothing*:
zero rows, no error, no clue. Every phrasing must land on the stored full form.

**Calendar windows** — `extract_date_window`, which under decision D9 serves
only the genuine DATE questions (`plan.approval_date` vs a `$deadline`). Its
digit-run guards are kept from the AP build because the trap is identical: a
rupee figure or an LGD code must never be read as a year.

Fixtures swapped from the AP set (agricultural seasons, crop years) to PR&DW
ones; the test logic is unchanged in shape. The seasons tests are gone outright
— kharif/rabi are not a PR&DW concept — and are replaced by the fiscal-year
cases below.
"""
import unittest

from query_router.date_phrase import (
    extract_date_window,
    fiscal_year_window,
    resolve_fiscal_year,
    resolve_fiscal_years,
)

# The six values in planned_activity.fiscal_year on the shipped sample.
LOADED_YEARS = [
    "2020-2021", "2021-2022", "2022-2023",
    "2023-2024", "2024-2025", "2025-2026",
]


class FiscalYearStringTests(unittest.TestCase):
    """Every way an officer names a year, mapped onto the nine stored characters."""

    def test_the_stored_form_resolves_to_itself(self):
        self.assertEqual(resolve_fiscal_year("2024-2025", LOADED_YEARS), "2024-2025")

    def test_the_abbreviated_form_expands(self):
        # THE bug this module exists for: '2024-25' binds and matches nothing.
        self.assertEqual(resolve_fiscal_year("2024-25", LOADED_YEARS), "2024-2025")

    def test_the_fy_prefix_in_its_common_spellings(self):
        for text in ("FY 24-25", "F.Y. 2024-25", "FY2024-25",
                     "financial year 2024-25", "fiscal year 2024-25"):
            with self.subTest(text=text):
                self.assertEqual(resolve_fiscal_year(text, LOADED_YEARS), "2024-2025")

    def test_the_two_digit_form(self):
        self.assertEqual(resolve_fiscal_year("24-25", LOADED_YEARS), "2024-2025")
        self.assertEqual(resolve_fiscal_year("23-24", LOADED_YEARS), "2023-2024")

    def test_an_en_dash_reads_the_same_as_a_hyphen(self):
        self.assertEqual(resolve_fiscal_year("2024–25", LOADED_YEARS), "2024-2025")

    def test_a_bare_year_labels_the_fiscal_year_that_starts_in_it(self):
        # "the 2024 plan" is the 2024-2025 plan. Flagged as an operator decision
        # in WP2_REPORT; pinned here so a change to it is deliberate.
        self.assertEqual(resolve_fiscal_year("expenditure in 2024", LOADED_YEARS),
                         "2024-2025")

    def test_inside_a_whole_question(self):
        self.assertEqual(
            resolve_fiscal_year(
                "How many activities did Andhrua complete in FY 24-25?", LOADED_YEARS
            ),
            "2024-2025",
        )


class RelativeYearTests(unittest.TestCase):
    """Relative phrases resolve against the DATA, never the wall clock.

    The sample's newest year is 2025-2026 whatever today's date is; answering
    "this year" with a year nobody loaded is the same silent-wrong failure the
    module exists to prevent.
    """

    def test_this_year_is_the_newest_loaded_year(self):
        for text in ("this year", "the current financial year", "this FY"):
            with self.subTest(text=text):
                self.assertEqual(resolve_fiscal_year(text, LOADED_YEARS), "2025-2026")

    def test_last_year_is_the_one_before_it(self):
        for text in ("last year", "previous financial year", "the last FY"):
            with self.subTest(text=text):
                self.assertEqual(resolve_fiscal_year(text, LOADED_YEARS), "2024-2025")

    def test_last_two_years_is_a_pair_oldest_first(self):
        self.assertEqual(
            resolve_fiscal_years("spending over the last two years", LOADED_YEARS),
            ["2024-2025", "2025-2026"],
        )

    def test_last_three_years_and_the_digit_form(self):
        self.assertEqual(
            resolve_fiscal_years("last three years", LOADED_YEARS),
            ["2023-2024", "2024-2025", "2025-2026"],
        )
        self.assertEqual(
            resolve_fiscal_years("past 3 financial years", LOADED_YEARS),
            ["2023-2024", "2024-2025", "2025-2026"],
        )

    def test_a_pair_is_not_a_single_year(self):
        """A slot binds one value; picking the first of two would answer a
        different question than the one asked."""
        self.assertIsNone(resolve_fiscal_year("last two years", LOADED_YEARS))

    def test_relative_phrases_need_an_axis(self):
        """With no years loaded there is nothing for 'last year' to mean, and a
        guess would be indistinguishable from an answer."""
        self.assertEqual(resolve_fiscal_years("last year", []), [])


class NoFiscalYearTests(unittest.TestCase):
    def test_a_question_with_no_year(self):
        # Decision D9: an absent year is a required-slot clarification, which
        # can only happen if nothing is invented here.
        self.assertEqual(resolve_fiscal_years("How many GPs are in Khordha?",
                                              LOADED_YEARS), [])

    def test_an_lgd_code_is_not_a_year(self):
        self.assertEqual(resolve_fiscal_years("show me GP 119598", LOADED_YEARS), [])

    def test_a_rupee_figure_is_not_a_year(self):
        self.assertEqual(resolve_fiscal_years("activities above ₹2025", LOADED_YEARS), [])

    def test_a_quantity_is_not_a_year(self):
        self.assertEqual(resolve_fiscal_years("more than 2024 households",
                                              LOADED_YEARS), [])

    def test_empty_message(self):
        self.assertEqual(resolve_fiscal_years("", LOADED_YEARS), [])

    def test_a_non_consecutive_pair_is_a_range_not_a_fiscal_year(self):
        """'2023-2025' names two fiscal years, not one nine-character label."""
        self.assertEqual(
            resolve_fiscal_years("disbursements 2023-2025", LOADED_YEARS),
            ["2023-2024", "2025-2026"],
        )


class OdiaNumeralTests(unittest.TestCase):
    """Decision D18.P5. Odia is an official language of the state and its
    numerals are U+0B66..U+0B6F, which the ASCII-only `_YEAR` pattern read as no
    year at all — so under D9 a perfectly clear question became a
    required-slot clarification (WP-4a §6.2).
    """

    def test_the_two_digit_form_in_odia_digits(self):
        self.assertEqual(
            resolve_fiscal_years("୨୦୨୪-୨୫", LOADED_YEARS), ["2024-2025"]
        )

    def test_the_stored_full_form_in_odia_digits(self):
        self.assertEqual(
            resolve_fiscal_years("୨୦୨୪-୨୦୨୫", LOADED_YEARS), ["2024-2025"]
        )

    def test_a_bare_odia_year(self):
        self.assertEqual(
            resolve_fiscal_years("୨୦୨୪", LOADED_YEARS), ["2024-2025"]
        )

    def test_inside_a_whole_odia_question(self):
        """G1008's own phrasing: 'How much was spent in Odisha in 2024-25?'"""
        self.assertEqual(
            resolve_fiscal_year("ଓଡ଼ିଶାରେ ୨୦୨୪-୨୫ରେ କେତେ ଖର୍ଚ୍ଚ ହୋଇଛି?",
                                LOADED_YEARS),
            "2024-2025",
        )

    def test_an_ascii_label_in_front_of_odia_digits(self):
        self.assertEqual(
            resolve_fiscal_years("FY ୨୦୨୪-୨୫", LOADED_YEARS), ["2024-2025"]
        )

    def test_the_calendar_window_reads_odia_digits_too(self):
        self.assertEqual(
            extract_date_window("FY ୨୦୨୪-୨୫"), ("2024-04-01", "2025-03-31")
        )
        self.assertEqual(
            extract_date_window("March ୨୦୨୫"), ("2025-03-01", "2025-03-31")
        )

    def test_an_odia_month_name_is_not_translated(self):
        """The scope of D18.P5 is DIGITS. `_MONTHS` is an English vocabulary, so
        'ମାର୍ଚ୍ଚ ୨୦୨୫' degrades to the bare-year window rather than the March
        one — honest, and the alternative (an Odia month lexicon) is a larger
        change than the ruling asked for."""
        self.assertEqual(
            extract_date_window("ମାର୍ଚ୍ଚ ୨୦୨୫"), ("2025-01-01", "2025-12-31")
        )

    def test_normalisation_preserves_length_and_offsets(self):
        """The property the span bookkeeping depends on: `consumed` ranges and
        the money/quantity guards index into the SAME positions after
        translation, so a 1:1 code-point map is the only safe kind here."""
        from query_router.date_phrase import normalize_digits
        source = "ଓଡ଼ିଶାରେ ୨୦୨୪-୨୫ରେ କେତେ ଖର୍ଚ୍ଚ?"
        self.assertEqual(len(normalize_digits(source)), len(source))
        self.assertEqual(normalize_digits("୨୦୨୪-୨୫"), "2024-25")

    def test_the_guards_still_hold_in_odia_digits(self):
        """A rupee figure written in Odia numerals is still not a year."""
        self.assertEqual(
            resolve_fiscal_years("₹୨୦୨୫ ରୁ ଅଧିକ", LOADED_YEARS), []
        )


class YearOutsideTheDataTests(unittest.TestCase):
    """Canonicalised, not suppressed. The REGISTRY refuses an unloaded year by
    name and offers the loaded ones; silently reading it as a year that IS
    loaded would be the wrong answer."""

    def test_an_unloaded_year_still_canonicalises(self):
        self.assertEqual(resolve_fiscal_year("FY 2019-20", LOADED_YEARS), "2019-2020")


class FiscalWindowTests(unittest.TestCase):
    def test_a_label_becomes_the_real_april_to_march_window(self):
        self.assertEqual(
            fiscal_year_window("2024-2025"), ("2024-04-01", "2025-03-31")
        )

    def test_a_non_consecutive_pair_is_not_a_fiscal_year(self):
        self.assertIsNone(fiscal_year_window("2023-2025"))

    def test_junk_is_none(self):
        self.assertIsNone(fiscal_year_window("last year"))


class ExtractsExplicitPeriodsTests(unittest.TestCase):
    def test_single_year(self):
        self.assertEqual(
            extract_date_window(
                "How many plans were approved in each block of Khordha in 2024?"
            ),
            ("2024-01-01", "2024-12-31"),
        )

    def test_between_two_years_spans_them(self):
        self.assertEqual(
            extract_date_window("plans approved between 2023 and 2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_to_range_reads_the_same_as_between(self):
        self.assertEqual(
            extract_date_window("plans approved 2023 to 2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_a_fiscal_label_is_the_real_fiscal_window(self):
        # Not the head calendar year: three missing months at each end would be
        # a wrong answer against a real approval_date column.
        self.assertEqual(
            extract_date_window("approvals for FY 2024-25"),
            ("2024-04-01", "2025-03-31"),
        )

    def test_the_full_form_does_not_also_read_as_a_bare_year(self):
        """'2024-2025' claims both halves; a stray bare-2025 reading would
        stretch the window to 2025-12-31."""
        self.assertEqual(
            extract_date_window("approvals for 2024-2025"),
            ("2024-04-01", "2025-03-31"),
        )

    def test_four_digit_range_is_a_range_not_a_fiscal_year(self):
        self.assertEqual(
            extract_date_window("approvals 2023-2025"),
            ("2023-01-01", "2025-12-31"),
        )

    def test_month_and_year(self):
        self.assertEqual(
            extract_date_window("plans approved in March 2025"),
            ("2025-03-01", "2025-03-31"),
        )

    def test_abbreviated_month(self):
        self.assertEqual(
            extract_date_window("plans approved in Mar 2025"),
            ("2025-03-01", "2025-03-31"),
        )

    def test_month_window_ends_on_the_real_last_day(self):
        self.assertEqual(
            extract_date_window("February 2024 approvals"),
            ("2024-02-01", "2024-02-29"),  # leap year
        )

    def test_years_outside_the_data_are_honoured_as_typed(self):
        # An empty result for 2031 is an honest answer; silently substituting
        # 2025 is not.
        self.assertEqual(
            extract_date_window("approvals in 2031"),
            ("2031-01-01", "2031-12-31"),
        )


class NoWindowTests(unittest.TestCase):
    def test_bare_month(self):
        self.assertIsNone(extract_date_window("plans approved in March"))

    def test_relative_phrase(self):
        # Relative phrases resolve against the loaded years, which this function
        # cannot see — resolve_fiscal_years owns them.
        self.assertIsNone(extract_date_window("how many plans were approved last year"))

    def test_this_year(self):
        self.assertIsNone(extract_date_window("what was spent this financial year"))

    def test_rupee_amount(self):
        self.assertIsNone(extract_date_window("₹2025 was spent on the work"))

    def test_rs_amount(self):
        self.assertIsNone(extract_date_window("activities that cost Rs. 2025"))

    def test_quantity(self):
        self.assertIsNone(extract_date_window("blocks with over 2025 households"))

    def test_lakh_quantity(self):
        self.assertIsNone(extract_date_window("works above 2024 lakh"))

    def test_lgd_code(self):
        self.assertIsNone(extract_date_window("show me gram panchayat 119598"))

    def test_mobile_number(self):
        self.assertIsNone(extract_date_window("sarpanch with mobile 9820241234"))

    def test_no_temporal_content_at_all(self):
        self.assertIsNone(
            extract_date_window("How many gram panchayats are there in Ganjam?")
        )

    def test_empty_message(self):
        self.assertIsNone(extract_date_window(""))


class GuardPrecisionTests(unittest.TestCase):
    """The guards must not swallow legitimate years — a false negative here is
    the same silent-wrong-window bug this module exists to remove."""

    def test_years_does_not_read_as_a_stray_rs(self):
        self.assertEqual(
            extract_date_window("over the years 2024 saw the most approvals"),
            ("2024-01-01", "2024-12-31"),
        )

    def test_a_guarded_amount_does_not_suppress_a_real_year(self):
        self.assertEqual(
            extract_date_window("works costing ₹2025 approved during 2024"),
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
