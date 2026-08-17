"""The five paired-year templates answer the direction they were asked (D30.3).

WHAT THIS PINS, AND WHY IT IS NOT COVERED BY A ROUTING TEST. All five paired
templates bind `$date_range_2` as **year1** and `$date_range` as **year2**, and
three of them compute `$date_range - $date_range_2`. Swap the pair and PLN-039
answers "which themes showed the greatest INCREASE" with the greatest decline —
correct query_id, correct row count, plausible table, wrong sign. WP-4's eval
graded that a `hit` on every paired row in all three replays, because a
route-graded eval never looks at a value:

    run 1/2/3   PLN-039  date_range=2023-2024  date_range_2=2024-2025
                         change_in_activities = +663 for a theme that FELL by 663
    run 1/2/3   TRD-004  change_amount = +474,665.81 on a fall of the same amount

THREE LAYERS NOW CARRY THE PIN, and each catches something the others cannot:

  1. `test_fiscal_year_fallback.test_the_catalogue_binds_date_range_as_the_LATER_year`
     — the CONVENTION, read off the SQL. Fails if a future template reverses it.
  2. this file — the VALUES, by executing the SQL against the sample database.
     Fails if the SQL, the views or the data change what year1 and year2 mean.
  3. `grade_full_eval`'s `wrong_direction` bucket — the ROUTE, on every replay.
     Fails if extraction, validation or the fallback hands the slots over
     inverted, which is what was actually happening.

The gold rows are the single source for all three: `expected_result.direction_pin`
in `eval/gold/*.jsonl`, validated structurally by
`eval/gold/build_eval_questions.py --check`.

No API key and no network: the SQL is executed directly against the read-only
sample database.
"""
import json
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"
_GOLD_DIR = _BACKEND.parent / "eval" / "gold"


def _pinned_rows() -> list[dict]:
    """Every gold row carrying a `direction_pin`, read straight off the JSONL."""
    rows = []
    for path in sorted(_GOLD_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if (rec.get("expected_result") or {}).get("direction_pin"):
                rows.append(rec)
    return rows


def _num(value):
    """Decimal, float and the harness's stringified Decimal, comparably."""
    return None if value is None else float(value)


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
@unittest.skipIf(not _GOLD_DIR.exists(), f"no gold set at {_GOLD_DIR}")
class PairedYearDirectionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from db_factory import open_analytical_db
        from query_router.template_catalog import TEMPLATE_CATALOG

        cls.adapter = open_analytical_db(_DB_PATH)
        cls.templates = TEMPLATE_CATALOG
        cls.pinned = _pinned_rows()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.adapter.close()
        except Exception:                                    # pragma: no cover
            pass

    def _paired(self) -> set[str]:
        return {qid for qid, t in self.templates.items()
                if {"date_range", "date_range_2"}
                <= {s["name"] for s in t["param_slots"]}}

    def _first_row(self, qid, params) -> dict:
        import re
        sql = self.templates[qid]["sql_template"]
        cursor = self.adapter.execute(sql, params)
        rows = cursor.fetchall()
        self.assertTrue(rows, f"{qid} returned no rows for the pinned parameters")
        # The adapter's cursor description truncates names on this driver, so the
        # column names come from the SELECT list itself — the same place
        # `column_metadata` reads them.
        names = (["theme"] if "v.theme," in sql else []) + re.findall(r"AS\s+(\w+)", sql)
        return dict(zip(names, rows[0]))

    # ── The pin holds against the data ────────────────────────────────────────

    def test_every_paired_template_has_a_pinned_gold_row(self):
        """D30.3 is about the SET, not about the three rows that happened to
        exist: PLN-040 and TRD-001 had no gold row at all before WP-4c."""
        self.assertEqual({rec["gold"] for rec in self.pinned}, self._paired())

    def test_the_pinned_first_row_is_what_the_sql_returns(self):
        """Executed, not asserted from the workbook. If the SQL, the views or the
        data ever change what year1 and year2 mean, this is where it surfaces —
        loudly, and before an officer reads a sign backwards."""
        for rec in self.pinned:
            pin = rec["expected_result"]["direction_pin"]
            with self.subTest(gold=rec["gold"], row=rec["id"]):
                actual = self._first_row(rec["gold"], pin["params"])
                for column, expected in pin["first_row"].items():
                    self.assertIn(column, actual,
                                  f"{rec['gold']} no longer selects {column!r}")
                    if isinstance(expected, str):
                        self.assertEqual(actual[column], expected)
                    else:
                        self.assertAlmostEqual(
                            _num(actual[column]), float(expected), places=2,
                            msg=f"{rec['gold']}.{column}: the pinned direction no "
                                f"longer matches the data")

    def test_swapping_the_pair_changes_the_answer(self):
        """The pin is only worth having if the inversion it guards against would
        actually fail it. This runs each template with the two years exchanged
        and requires the first row to come back DIFFERENT."""
        for rec in self.pinned:
            pin = rec["expected_result"]["direction_pin"]
            inverted = dict(pin["params"])
            inverted["date_range"], inverted["date_range_2"] = (
                inverted["date_range_2"], inverted["date_range"])
            with self.subTest(gold=rec["gold"]):
                actual = self._first_row(rec["gold"], inverted)
                pinned = pin["first_row"]
                differs = any(
                    _num(actual.get(c)) != _num(v)
                    for c, v in pinned.items() if not isinstance(v, str))
                self.assertTrue(
                    differs,
                    f"{rec['gold']}: inverting the pair changed nothing the pin "
                    f"looks at, so the pin cannot catch an inversion")

    def test_the_pinned_inverted_row_is_what_the_swap_actually_returns(self):
        """`inverted_row` is what `grade_full_eval` matches against to say "the
        pair arrived swapped" POSITIVELY, rather than inferring it from a
        mismatch. It is the only check that catches PLN-039 and PLN-040 — their
        ORDER BY is on the change column, so under an inverted pair the top row is
        still a positive change for "greatest increase", just a different theme,
        and every sign test passes on an answer that is backwards.

        Which means this row has to be right, so it is executed rather than
        trusted."""
        for rec in self.pinned:
            pin = rec["expected_result"]["direction_pin"]
            inverted_params = dict(pin["params"])
            inverted_params["date_range"], inverted_params["date_range_2"] = (
                inverted_params["date_range_2"], inverted_params["date_range"])
            with self.subTest(gold=rec["gold"]):
                actual = self._first_row(rec["gold"], inverted_params)
                for column, expected in pin["inverted_row"].items():
                    if isinstance(expected, str):
                        self.assertEqual(actual[column], expected)
                    else:
                        self.assertAlmostEqual(
                            _num(actual[column]), float(expected), places=2,
                            msg=f"{rec['gold']}.{column}: inverted_row no longer "
                                f"matches what the swap returns")

    def test_a_change_column_carries_the_sign_of_the_later_year(self):
        """The property the whole thing exists for, stated once: where a template
        computes a change, it is later minus earlier."""
        for rec in self.pinned:
            row = rec["expected_result"]["direction_pin"]["first_row"]
            for change, (earlier, later) in (
                    ("change_in_activities", ("activities_year1", "activities_year2")),
                    ("change_amount", ("expenditure_year1", "expenditure_year2"))):
                if change in row and earlier in row and later in row:
                    with self.subTest(gold=rec["gold"], column=change):
                        self.assertAlmostEqual(
                            float(row[change]), float(row[later]) - float(row[earlier]),
                            places=2)

    def test_the_pins_year_columns_agree_with_the_sql_convention(self):
        """`_2` is year1 everywhere. Asserted against the pin rather than only in
        the pin, so a hand-edited gold row cannot quietly redefine the pair."""
        for rec in self.pinned:
            pin = rec["expected_result"]["direction_pin"]
            for column, slot in pin["year_columns"].items():
                with self.subTest(gold=rec["gold"], column=column):
                    expected = "date_range_2" if column.endswith("_year1") else "date_range"
                    self.assertEqual(slot, expected)


if __name__ == "__main__":
    unittest.main()
