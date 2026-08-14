"""End-to-end proof that a period named in the question reaches the SQL.

The unit tests pin `date_phrase` in isolation; these pin the WIRING — that a
fiscal year an officer states survives routing, validation and parameter
binding, and that the window a response reports is the window its rows were
computed over.

PORTED FROM AP, AND HALF OF IT RETIRED (WP-4 T4e)
    The AP suite proved a `date_filter` INJECTION: the router appended a
    `BETWEEN ? AND ?` predicate to the SQL and spliced the two date values ahead
    of a trailing `LIMIT ?`. Decision D9 removes that machinery here. Odisha's
    fiscal year is the VARCHAR `'2024-2025'`, `date_kind: "year"` compares
    integers, and `tests/test_catalog_execution.py` asserts that not one of the
    346 templates carries a `date_filter` at all. So three of the five AP tests
    had nothing to test:

      · "a year in the question sets the window and changes the answer"  →  the
        PR&DW analogue is the same officer intent served a different way: the
        year binds as the ORDINARY `$date_range` SLOT. Rewritten, not dropped.
      · "the derived window survives a template with its own LIMIT placeholder"
        →  retired. `$top_n` and `$date_range` are both NAMED parameters bound
        from a dict; there is no positional splice left to get wrong, and
        test_param_binding.py covers the binding itself.
      · "a follow-up requeries over the derived window"  →  retired here and
        covered better elsewhere: with no date_filter, a follow-up carries the
        year as a bound param, which test_zones_and_followups.py pins.

    What survives is the request-window contract, which is real on both paths:
    the UI's explicit range always wins, and an unstated period gets the
    documented default.

THE PATH LANDMINE IS GONE (WP-1 report §7.2). This file used to compute
`parents[1].parents[1] / "RTGS_Data" / "flat"`, which since the Chatbot/
flattening resolves OUTSIDE this repo — a stray RTGS_Data/ landing in the shared
Drive parent would have silently pointed these tests at another project's data,
and the suite would have "passed". It now reads this repo's own DuckDB sample.

OPT-IN, like test_followup_fragment.py: these drive the real router, which
embeds, reranks and extracts through the OpenAI API. A suite that quietly makes
paid calls whenever a key happens to sit in `.env` is not one anyone can run
freely (WP-2 report §7.1).
"""
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

load_dotenv(_BACKEND / ".env")

# db_factory reads these at import time, so they must be set before `import main`.
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

_LIVE = os.environ.get("PRDW_LIVE_ROUTING") == "1"
_SKIP = None
if not _LIVE:
    _SKIP = ("live routing is opt-in: set PRDW_LIVE_ROUTING=1 (costs money, "
             "requires OPENAI_API_KEY)")
elif not _DB_PATH.exists():
    _SKIP = f"no sample database at {_DB_PATH}"
elif not os.environ.get("OPENAI_API_KEY"):
    _SKIP = "OPENAI_API_KEY not set — the router is disabled without it"

# EXP-001: total actual expenditure, filterable at every tier, `$date_range`
# required. The fiscal year is the whole subject of these tests, so the question
# names one and nothing else that could move the answer.
EXPENDITURE_BY_GP = "What is the total actual expenditure incurred by each GP"
FY_2024 = EXPENDITURE_BY_GP + " in 2024-25?"
FY_2023 = EXPENDITURE_BY_GP + " in 2023-24?"


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class FiscalYearFromQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import main

        cls._client_ctx = TestClient(main.app)
        cls.client = cls._client_ctx.__enter__()
        cls.default_start = main._default_start_date
        cls.default_end = main._default_end_date

    @classmethod
    def tearDownClass(cls):
        cls._client_ctx.__exit__(None, None, None)

    def ask(self, message: str, **body) -> dict:
        response = self.client.post("/query", json={"message": message, **body})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # 1 — the D9 analogue of the AP "year sets the window" test
    def test_an_abbreviated_year_binds_the_full_stored_string(self):
        """`'2024-25'` matches NOTHING in a column holding `'2024-2025'` — it
        binds successfully and returns zero rows with no error anywhere. That
        silent failure is why date_phrase exists, and this is the proof it runs
        on the serving path and not only in the unit tests."""
        payload = self.ask(FY_2024)
        bound = {e["slot"]: e["value"] for e in payload.get("entities") or []}
        self.assertEqual(bound.get("date_range"), "2024-2025")
        self.assertTrue(payload["result"], "the bound year matched no rows")

    def test_a_different_year_changes_the_answer(self):
        """If both years returned the same rows the binding would be
        decorative — the filter has to actually be doing something."""
        this_year = self.ask(FY_2024)
        last_year = self.ask(FY_2023)
        self.assertEqual(this_year["query_id"], last_year["query_id"])
        self.assertNotEqual(this_year["result"], last_year["result"])

    def test_the_echoed_question_names_the_year_that_was_bound(self):
        """The user reads their own words back and assumes the answer matched
        them (T2d). A `{date_range}` surviving into the echo, or a year other
        than the bound one, is the same class of defect as the wrong rows."""
        payload = self.ask(FY_2024)
        description = payload.get("query_description") or ""
        self.assertIn("2024-2025", description)
        self.assertNotIn("{", description)

    # 2 — the UI always wins (unchanged from AP; the contract is the same)
    def test_an_explicit_request_range_is_reported_as_the_window(self):
        payload = self.ask(FY_2024, start_date="2025-01-01", end_date="2025-12-31")
        self.assertEqual(payload["date_range"]["start_date"], "2025-01-01")
        self.assertEqual(payload["date_range"]["end_date"], "2025-12-31")
        self.assertFalse(payload["date_range"]["is_default"])

    # 3 — regression: nothing named anywhere still gets the default window
    def test_no_dates_anywhere_keeps_the_default_window(self):
        payload = self.ask("How many activities are planned?")
        self.assertEqual(payload["date_range"]["start_date"], self.default_start)
        self.assertEqual(payload["date_range"]["end_date"], self.default_end)
        self.assertTrue(payload["date_range"]["is_default"])

    def test_no_template_applies_a_date_filter_on_the_serving_path(self):
        """Decision D9, asserted where it would actually bite. `date_kind:
        "year"` compares INTEGERS against a column holding '2024-2025'; an
        injection here raises a binder error rather than answering wrongly, but
        only once someone asks."""
        for message in (FY_2024, FY_2023, "How many activities are planned?"):
            with self.subTest(message=message):
                self.assertFalse(self.ask(message).get("date_filter_applied"))


if __name__ == "__main__":
    unittest.main()
