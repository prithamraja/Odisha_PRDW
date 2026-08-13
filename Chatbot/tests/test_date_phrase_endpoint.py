"""End-to-end proof that a period named in the question reaches the SQL.

The unit tests pin the extractor; these pin the wiring — that a derived window
survives routing, date-filter injection and parameter binding, that the UI's
explicit range still outranks it, and that the window a response *reports* is
the window its rows were *computed over*.

Runs the real app against the flat Parquet drop and the real router, so it needs
OPENAI_API_KEY and RTGS_Data/flat; it skips cleanly without them.
"""
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[1]
_FLAT = _BACKEND.parents[1] / "RTGS_Data" / "flat"

# main.py loads this on import, but the skip decision below needs the key first.
load_dotenv(_BACKEND / ".env")

# db_factory reads DATA_DIR at import time, so it must be set before `import main`.
if _FLAT.is_dir():
    os.environ["DATA_DIR"] = str(_FLAT)

_SKIP = None
if not _FLAT.is_dir():
    _SKIP = f"flat Parquet drop not present at {_FLAT}"
elif not os.environ.get("OPENAI_API_KEY"):
    _SKIP = "OPENAI_API_KEY not set — the router is disabled without it"

SUBSIDY_BY_MANDAL = "How much input subsidy went to each mandal of {} district"
KRISHNA_2024 = SUBSIDY_BY_MANDAL.format("Krishna") + " in 2024?"
KRISHNA_UNDATED = SUBSIDY_BY_MANDAL.format("Krishna") + "?"

# R03 — the one template carrying its own `LIMIT ?` alongside a date_filter.
# Its placeholders bind by position in the SQL text, so an injected date
# predicate lands ahead of the LIMIT and must be spliced, not appended. A
# question-derived window has to survive that splice like any other.
MARKFED_TOP_2024 = "Who received the 5 highest MARKFED payments in 2024?"


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class DateFromQuestionEndpointTests(unittest.TestCase):
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

    # 1 — the bug this pack closes
    def test_year_in_the_question_sets_the_window_and_changes_the_answer(self):
        derived = self.ask(KRISHNA_2024)
        self.assertEqual(derived["query_id"], "G10-D")
        self.assertEqual(derived["date_range"]["start_date"], "2024-01-01")
        self.assertEqual(derived["date_range"]["end_date"], "2024-12-31")
        self.assertTrue(derived["date_range"]["derived_from_question"])
        self.assertFalse(derived["date_range"]["is_default"])
        self.assertTrue(derived["date_filter_applied"])

        # Same question over the default window: if the rows matched, the
        # derived window would be decorative.
        default = self.ask(KRISHNA_UNDATED)
        self.assertEqual(default["query_id"], "G10-D")
        self.assertEqual(default["date_range"]["start_date"], self.default_start)
        self.assertNotEqual(derived["result"], default["result"])

        farmers = lambda rows: sum(int(r["farmers"]) for r in rows)
        self.assertLess(farmers(derived["result"]), farmers(default["result"]))

    # 2 — the UI always wins
    def test_explicit_request_range_overrides_the_question(self):
        payload = self.ask(
            KRISHNA_2024, start_date="2025-01-01", end_date="2025-12-31"
        )
        self.assertEqual(payload["date_range"]["start_date"], "2025-01-01")
        self.assertEqual(payload["date_range"]["end_date"], "2025-12-31")
        self.assertFalse(payload["date_range"].get("derived_from_question", False))
        self.assertFalse(payload["date_range"]["is_default"])

    # 3 — regression: nothing named anywhere still gets the default window
    def test_no_dates_anywhere_keeps_the_default_window(self):
        payload = self.ask(KRISHNA_UNDATED)
        self.assertEqual(payload["date_range"]["start_date"], self.default_start)
        self.assertEqual(payload["date_range"]["end_date"], self.default_end)
        self.assertTrue(payload["date_range"]["is_default"])
        self.assertFalse(payload["date_range"]["derived_from_question"])

    # 4 — compatible with the LIMIT-plus-date bind-order splice
    def test_derived_window_survives_a_template_with_its_own_limit_placeholder(self):
        payload = self.ask(MARKFED_TOP_2024)
        self.assertEqual(payload["query_id"], "R03")
        self.assertEqual(payload["date_range"]["start_date"], "2024-01-01")
        self.assertEqual(payload["date_range"]["end_date"], "2024-12-31")
        self.assertTrue(payload["date_range"]["derived_from_question"])
        self.assertTrue(payload["date_filter_applied"])
        # The LIMIT still binds to 5 — proof the date values did not displace it.
        self.assertEqual(len(payload["result"]), 5)

    # 5 — the derived window carries into follow-ups
    def test_followup_requeries_over_the_derived_window_not_the_default(self):
        session = "test-derived-window-followup"
        first = self.ask(KRISHNA_2024, session_id=session, reset_context=True)
        self.assertEqual(
            first["context_frame"]["time_range"]["start"], "2024-01-01"
        )

        followup = self.ask("compare with Guntur district", session_id=session)
        self.assertEqual(followup["tier"], "operation")
        self.assertEqual(followup["operation_mode"], "requery")

        # The re-queried comparison ran over 2024, and the response says 2024.
        self.assertEqual(followup["date_range"]["start_date"], "2024-01-01")
        self.assertEqual(followup["date_range"]["end_date"], "2024-12-31")
        self.assertFalse(followup["date_range"]["is_default"])

        # The original district's rows must be unchanged by the comparison —
        # they came from the same 2024 window, not a silently re-defaulted one.
        baseline = {r["geography"]: r["farmers"] for r in first["result"]}
        carried = {
            r["geography"]: r["farmers"]
            for r in followup["result"]
            if r.get("compared_district") == "Krishna"
        }
        self.assertTrue(carried, "comparison returned no rows for the original district")
        self.assertEqual(carried, {k: v for k, v in baseline.items() if k in carried})


if __name__ == "__main__":
    unittest.main()
