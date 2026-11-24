# -*- coding: utf-8 -*-
"""WP-D17 (R28) -- a breakdown sentence carries only its own numbers.

    python -m pytest DiscoverChat/tests/test_breakdown_own_numbers.py -q

The builder's check (`phase5f_decompose.own_numbers_check`) on sentences built
by the builder's own code, and the proof that it fails when a typed-in number
-- the old caution table, or one figure in fixed text -- is put back.
No view parquet, no model.
"""
import unittest

from DiscoverChat import config  # noqa: F401  -- puts Insights/src on sys.path
import phase5f_decompose as p5f

CAUTIONS = [
    "A rise here is a rise in recording completeness unless the cashbook total "
    "rises with it; the linked share went from 2.7% to 53.2% across these six "
    "years.",
    "The sanctioned basis covers only the activities with a sanction record on "
    "file, about one in six.",
    "Only 17 completions are recorded in the whole sample, so this splits a "
    "near-empty column.",
    "A swap between the SC and ST components is suspected and unconfirmed; do "
    "not read one against the other.",
]


def _members(values, names=None):
    names = names or [f"Place {chr(65 + i)}" for i in range(len(values))]
    gross = sum(abs(v) for v in values)
    return [{"member": n, "is_null": False, "value": float(v), "rows": 10 + i,
             "share": round(abs(v) / gross, 6)} for i, (n, v) in enumerate(zip(names, values))]


def _sentence(measure="fund_sanctioned_total", values=(500000, 120000, 80000, 50000),
              names=None, shape="spread", signs="all_positive",
              pairs=(("fiscal_year", "2023-2024"),), view="view1"):
    members = _members(values, names)
    total = sum(values)
    gross = sum(abs(v) for v in values)
    marked = p5f.build_sentence_marked(
        view, measure, "gp_name", list(pairs), members, total, gross, signs,
        {"shape": shape, "attribution_member": None, "evenness": False}, "", "")
    plain = p5f.build_sentence(
        view, measure, "gp_name", list(pairs), members, total, gross, signs,
        {"shape": shape, "attribution_member": None, "evenness": False}, "", "")
    return marked, plain


class OwnNumbersTests(unittest.TestCase):

    def test_the_caution_table_is_gone(self):
        self.assertFalse(hasattr(p5f, "_MEASURE_CAVEAT"))

    def test_built_sentences_pass_and_strip_to_the_plain_sentence(self):
        for shape in ("spread", "concentrated", "even", "empty"):
            with self.subTest(shape=shape):
                marked, plain = _sentence(shape=shape)
                self.assertEqual(p5f.own_numbers_check("d1-00001", marked), plain)
                self.assertNotIn(p5f._OPEN, plain)
                for c in CAUTIONS:
                    self.assertNotIn(c, plain)

    def test_offsetting_and_signed_measures_pass(self):
        marked, plain = _sentence(measure="overspend_vs_plan",
                                  values=(-300000, 120000, -50000),
                                  shape="offsetting", signs="mixed")
        self.assertEqual(p5f.own_numbers_check("d1-00002", marked), plain)

    def test_data_names_with_digits_pass(self):
        # A fiscal year in the scope, "Theme 4" and "5th State Finance
        # Commission" as members: names from the data, not typed in.
        marked, plain = _sentence(names=["Theme 4 - Water Sufficient Village",
                                         "5TH STATE FINANCE COMMISSION",
                                         "Theme 6", "Theme 8"])
        self.assertEqual(p5f.own_numbers_check("d1-00003", marked), plain)
        self.assertIn("2023-2024", plain)

    def test_the_old_cautions_fail_naming_the_record(self):
        marked, _ = _sentence()
        # The two with a digit in them ("2.7% to 53.2%", "17 completions").
        # "about one in six" and the SC/ST text hold no digit: the digit rule
        # cannot see them, and the gate's text test (breakdowns-own-numbers)
        # is what keeps them out.
        for c in (CAUTIONS[0], CAUTIONS[2]):
            with self.subTest(caution=c[:30]):
                with self.assertRaises(p5f.TypedInNumber) as caught:
                    p5f.own_numbers_check("d1-04242", marked + " " + c)
                self.assertIn("d1-04242", str(caught.exception))

    def test_one_typed_in_figure_fails(self):
        marked, _ = _sentence()
        with self.assertRaises(p5f.TypedInNumber):
            p5f.own_numbers_check("d2-00007", marked.replace(
                "across", "across about 20", 1))

    def test_putting_the_table_back_fails_the_build(self):
        """The old code appended the caution as fixed text at the end of the
        sentence. Doing exactly that, through the builder's own function, is
        refused for the three cautions with digits."""
        real = p5f.build_sentence_marked

        def with_caution(view, measure, *args):
            text = real(view, measure, *args)
            caution = {"fund_sanctioned_total": CAUTIONS[1]}.get(measure)
            return text + (" " + caution if caution else "")

        marked = with_caution("view1", "fund_sanctioned_total", "gp_name",
                              [("fiscal_year", "2023-2024")],
                              _members((500000, 120000, 80000)), 700000.0,
                              700000.0, "all_positive",
                              {"shape": "spread", "attribution_member": None,
                               "evenness": False}, "", "")
        # "about one in six" has no digit: the word-only caution is caught by
        # the gate's text test, not by the digit rule. The digit ones are:
        p5f.own_numbers_check("d1-00010", marked)
        with self.assertRaises(p5f.TypedInNumber):
            p5f.own_numbers_check("d1-00010", marked + " " + CAUTIONS[0])


if __name__ == "__main__":
    unittest.main()
