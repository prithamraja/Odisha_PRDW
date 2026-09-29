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

    def test_a_hyphen_span_is_the_consecutive_years_it_covers(self):
        """D33.7: '2023-2025' is 2023-24 AND 2024-25 — the reading '2023 to
        2025' gets. It used to read as 2023-24 and 2025-26, skipping a year."""
        self.assertEqual(
            resolve_fiscal_years("disbursements 2023-2025", LOADED_YEARS),
            ["2023-2024", "2024-2025"],
        )
        self.assertEqual(
            resolve_fiscal_years("disbursements 2023-2025", LOADED_YEARS),
            resolve_fiscal_years("disbursements 2023 to 2025", LOADED_YEARS),
        )

    def test_the_span_runs_head_to_tail_minus_one(self):
        """The direction pin: a span starts at its head, never at its tail."""
        self.assertEqual(
            resolve_fiscal_years("spend 2020-2025", LOADED_YEARS),
            ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
        )
        self.assertEqual(resolve_fiscal_years("spend 2023-25", LOADED_YEARS),
                         ["2023-2024", "2024-2025"])

    def test_a_consecutive_pair_is_still_one_year(self):
        self.assertEqual(resolve_fiscal_years("spend 2024-2025", LOADED_YEARS),
                         ["2024-2025"])

    def test_a_backwards_or_too_wide_pair_still_falls_through(self):
        """Not a span: the bare-year scan reads each year on its own, as before."""
        self.assertEqual(resolve_fiscal_years("spend 2025-2023", LOADED_YEARS),
                         ["2023-2024", "2025-2026"])
        self.assertEqual(resolve_fiscal_years("spend 2019-2025", LOADED_YEARS),
                         ["2019-2020", "2025-2026"])

    def test_a_two_digit_pair_is_never_widened(self):
        """'10-15' is a range of figures, not 2010 to 2015."""
        self.assertEqual(resolve_fiscal_years("10-15 activities", LOADED_YEARS), [])
        self.assertEqual(resolve_fiscal_years("GPs with 23-25 works", LOADED_YEARS), [])


THREE = ["2022-2023", "2023-2024", "2024-2025"]
ENDS = ["2022-2023", "2024-2025"]


class FiscalYearSpanTests(unittest.TestCase):
    """WP-6g T1: "from X to Y" between two fiscal years is every year from X to
    Y, both ends included (operator ruling 2026-09-29). It used to read as the
    two end years: pilot rows 1055 and 1057 dropped 2023-24."""

    def _years(self, text):
        return resolve_fiscal_years(text, LOADED_YEARS)

    def test_the_pilot_wording(self):
        self.assertEqual(self._years("from 2022-23 to 2024-25"), THREE)
        self.assertEqual(
            self._years("Blocks consistently delayed in GPDP approvals from "
                        "2023-24 to 2025-26"),
            ["2023-2024", "2024-2025", "2025-2026"])

    def test_each_end_form(self):
        for text in ("2022-2023 to 2024-2025", "2022-23 to 2024-25",
                     "22-23 to 24-25", "2022-23 to 24-25", "2022-2023 to 2024-25",
                     "2022/23 to 2024/25", "2022–23 to 2024–25"):
            with self.subTest(text=text):
                self.assertEqual(self._years(text), THREE)

    def test_each_label(self):
        for text in ("FY 2022-23 to FY 2024-25", "from FY 2022-23 to FY 2024-25",
                     "F.Y. 2022-23 to 2024-25", "FY22-23 to FY24-25",
                     "financial year 2022-23 to financial year 2024-25",
                     "fiscal year 2022-23 to 2024-25",
                     "plan year 2022-23 to plan year 2024-25"):
            with self.subTest(text=text):
                self.assertEqual(self._years(text), THREE)

    def test_every_link_word(self):
        for link in ("to", "till", "until", "through", "thru", "TO", "Till"):
            with self.subTest(link=link):
                self.assertEqual(self._years(f"from 2022-23 {link} 2024-25"), THREE)

    def test_a_spaced_en_or_em_dash(self):
        for text in ("2022-23 – 2024-25", "2022-23 — 2024-25",
                     "Activities planned 2022-23 – 2024-25"):
            with self.subTest(text=text):
                self.assertEqual(self._years(text), THREE)

    def test_an_unspaced_dash_or_a_spaced_hyphen_is_not_a_link(self):
        """Not in the ruled shape: each end is still read on its own."""
        for text in ("2022-23–2024-25", "2022-23 - 2024-25"):
            with self.subTest(text=text):
                self.assertEqual(self._years(text), ENDS)

    def test_from_is_neither_needed_nor_read(self):
        self.assertEqual(self._years("from 2022-23 to 2024-25"),
                         self._years("2022-23 to 2024-25"))
        self.assertEqual(self._years("expenditure 2022-23 to 2024-25 in Khordha"),
                         THREE)

    def test_both_ends_are_included(self):
        self.assertEqual(self._years("2024-25 to 2025-26"),
                         ["2024-2025", "2025-2026"])
        self.assertEqual(self._years("from 2024-25 to 2024-25"), ["2024-2025"])

    def test_it_matches_the_bare_year_span(self):
        """"2022 to 2025" already gave these three; the two spellings of one
        period can no longer disagree."""
        self.assertEqual(self._years("from 2022-23 to 2024-25"),
                         self._years("from 2022 to 2025"))

    def test_the_full_form_no_longer_reads_a_year_nobody_named(self):
        """Before, the bare span took "2023 to 2024" out of the middle and the
        bare-year scan read the ends: 2022-23, 2023-24 and 2025-26."""
        self.assertEqual(self._years("from 2022-2023 to 2024-2025"), THREE)
        self.assertEqual(
            self._years("How did Bhubaneswar's expenditure change from "
                        "2023-2024 to 2024-2025?"),
            ["2023-2024", "2024-2025"])

    def test_ten_years_is_the_widest_span(self):
        self.assertEqual(
            resolve_fiscal_years("from 2012-13 to 2021-22"),
            [f"{y}-{y + 1}" for y in range(2012, 2022)])

    def test_eleven_years_keeps_the_old_reading_and_is_logged(self):
        with self.assertLogs("query_router.date_phrase", "INFO") as logs:
            self.assertEqual(resolve_fiscal_years("from 2011-12 to 2021-22"),
                             ["2011-2012", "2021-2022"])
        self.assertIn("wider than 10", logs.output[0])

    def test_a_reversed_pair_keeps_the_old_reading_and_is_logged(self):
        with self.assertLogs("query_router.date_phrase", "INFO") as logs:
            self.assertEqual(self._years("from 2024-25 to 2022-23"), ENDS)
        self.assertIn("tail is before its head", logs.output[0])

    def test_the_money_guard_holds_at_either_end(self):
        """A figure at either end is not a year, so there is no span — each end
        is judged by the single patterns exactly as before."""
        self.assertEqual(self._years("Rs 2022-23 to 2024-25"), ["2024-2025"])
        self.assertEqual(self._years("2022-23 to 2024-25 lakh"), ENDS)
        self.assertEqual(self._years("2022-23 to ₹2024-25"), ["2022-2023"])

    def test_an_end_naming_several_years_is_not_a_span_end(self):
        self.assertEqual(self._years("2020-2022 to 2024-25"),
                         ["2020-2021", "2022-2023", "2023-2024"])

    def test_odia_digits(self):
        self.assertEqual(self._years("୨୦୨୨-୨୩ to ୨୦୨୪-୨୫"), THREE)

    # ── Mixed forms (the report says which are read and why) ──────────────────

    def test_a_bare_head_and_a_fiscal_tail_is_a_span(self):
        """A bare head is the fiscal year that starts in it under both readings
        this module has, so the span is unambiguous. It used to lose the tail:
        "2022 to 2024" was taken out of it, giving 2022-23 and 2023-24."""
        for text in ("from 2022 to 2024-25", "FY 2022 to FY 2024-25",
                     "2022 till 2024-2025", "2022 – 2024-25"):
            with self.subTest(text=text):
                self.assertEqual(self._years(text), THREE)

    def test_a_fiscal_head_and_a_bare_tail_is_left_alone(self):
        """"to 2025" ends the span at 2024-25 or names 2025-26 — the FY naming
        question awaiting the operator. Byte-identical to before WP-6g."""
        self.assertEqual(self._years("from 2022-23 to 2025"),
                         ["2022-2023", "2025-2026"])
        self.assertEqual(self._years("from 2022-2023 to 2025"), THREE)


class UnchangedYearFormTests(unittest.TestCase):
    """WP-6g §0: every reading that is not a "to" span between fiscal years is
    exactly what it was before WP-6g."""

    def test_the_brief_table(self):
        for text, expected in (
            ("from 2022 to 2025", THREE),
            ("for 2022 to 2025", THREE),
            ("in 2022-2025", THREE),
            ("between 2022-23 and 2024-25", ENDS),
            ("compare 2022-23 and 2024-25", ENDS),
            ("2022-23 and 2024-25", ENDS),
            ("2022-23 vs 2024-25", ENDS),
            ("Compare expenditure in 2022-23 and 2024-25", ENDS),
            ("Planned cost between 2022-23 and 2024-25", ENDS),
            ("Planned activities in 2023-2025", ["2023-2024", "2024-2025"]),
        ):
            with self.subTest(text=text):
                self.assertEqual(resolve_fiscal_years(text, LOADED_YEARS), expected)

    def test_single_and_relative_years(self):
        for text, expected in (
            ("FY 2024-25", ["2024-2025"]), ("2024", ["2024-2025"]),
            ("24-25", ["2024-2025"]), ("last year", ["2024-2025"]),
            ("this year", ["2025-2026"]),
            ("last two years", ["2024-2025", "2025-2026"]),
        ):
            with self.subTest(text=text):
                self.assertEqual(resolve_fiscal_years(text, LOADED_YEARS), expected)

    def test_the_calendar_window_reads_the_span_the_same_way(self):
        """`extract_date_window` spans every period it reads, so the span needs
        no change there: April 2022 to March 2025, the three fiscal years."""
        for text in ("from 2022-23 to 2024-25", "FY 2022-23 – FY 2024-25",
                     "from 2022-2023 to 2024-2025"):
            with self.subTest(text=text):
                self.assertEqual(extract_date_window(text),
                                 ("2022-04-01", "2025-03-31"))


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

    def test_a_span_is_the_window_of_the_years_it_covers(self):
        """D33.7: 2023-24 and 2024-25 end to end."""
        self.assertEqual(
            fiscal_year_window("2023-2025"), ("2023-04-01", "2025-03-31")
        )

    def test_a_backwards_or_too_wide_pair_is_not_a_window(self):
        self.assertIsNone(fiscal_year_window("2025-2023"))
        self.assertIsNone(fiscal_year_window("2019-2025"))

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

    def test_a_four_digit_hyphen_span_is_its_fiscal_years(self):
        """D33.7: the two fiscal years it names, April 2023 to March 2025 — not
        the calendar years 2023 to 2025."""
        self.assertEqual(
            extract_date_window("approvals 2023-2025"),
            ("2023-04-01", "2025-03-31"),
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
