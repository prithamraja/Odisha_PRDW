"""The truncated-table guard, wired end to end (WP-4c 5.2, decision D31.2).

WHAT THE UNIT TESTS CANNOT PROVE. `tests/test_operations.py` pins the guard
against a stub re-query hook, which is the right level for the decision logic
and says nothing about whether the hook the SERVER passes actually works. The
defect it closes was never a logic error - `frame.bound_params` carried
`top_n: '1'` the whole time - it was a wire that was never run. So this drives
the real /operation endpoint against the real sample database: real template,
real binder, real SQL, real validator. No API key and no LLM: /operation is the
typed path, invoked from a UI control, so nothing here is classified.

THE SHAPE, from the replay record:

    #1403 "Which focus area has the highest planned expenditure in 2024-25?"
          -> BUD-022 with $top_n = 1, and the table on screen is ONE ROW.
    #1404 "and the lowest?"
          -> the minimum of that one row, which is the MAXIMUM of the question.

#1042 ("aur sabse kam?") is the same operation reached in Hinglish; the register
changes which classifier branch fires, not what the operations layer is asked
for, so `bottom_n` is exercised here beside `min`.
"""
import os
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

# db_factory reads these at import time, so they must be set before `import main`.
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

QID = "BUD-022"
SESSION = "truncation-session"


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
class TruncatedTableEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import main
        from db_factory import get_adapter
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG

        # NO KEY, DELIBERATELY, AND THIS IS THE POINT (standing discipline 3a).
        # Entering a TestClient runs `main.startup()`, which builds the vector
        # index - 376 entries, two embedding calls on a cold cache. WP-2 found a
        # suite quietly spending whenever a key happened to sit in `.env`, and an
        # always-on test that drives the app is that trap one layer up. Blanking
        # the key makes startup return before it constructs a client at all, so
        # this file cannot spend on any machine. /operation needs no retriever:
        # it is the TYPED path, invoked from a control on a table, and nothing
        # about it is classified or embedded.
        cls._saved_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""

        # What startup would have populated, populated directly instead.
        main._template_map = dict(TEMPLATE_CATALOG)
        main._dashboard_questions = {}
        main._validator = EntityValidator(get_adapter())
        main._openai_client = object()   # only checked for None by the endpoint

        cls.main = main
        cls.templates = TEMPLATE_CATALOG
        cls._client_ctx = TestClient(main.app)
        cls.client = cls._client_ctx.__enter__()
        assert main._retriever is None, (
            "startup built a vector index — this test is meant to be free")

    @classmethod
    def tearDownClass(cls):
        try:
            cls._client_ctx.__exit__(None, None, None)
        except Exception:                                    # pragma: no cover
            pass
        if cls._saved_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = cls._saved_key

    def setUp(self):
        self.main._context_store.reset(SESSION)
        self.frame, self.rows = self._seed_top_one()

    def _seed_top_one(self):
        """Serve BUD-022 with $top_n = 1 and store the frame, exactly as the
        /query path does for "which focus area has the HIGHEST ...?"."""
        from db_factory import get_adapter
        from query_router.context_store import build_context_frame
        from query_router.models import ExtractedEntity, RouteResult, RouteTier
        from query_router.router import _serve_query_id

        entities = [
            ExtractedEntity(entity_type="fiscal_year", raw_value="2024-2025",
                            resolved_value="2024-2025", confidence="exact",
                            slot_name="date_range"),
            ExtractedEntity(entity_type="top_n", raw_value="1",
                            resolved_value="1", confidence="numeric",
                            slot_name="top_n"),
        ]
        result = _serve_query_id(
            QID, entities, None,
            user_query="Which focus area has the highest planned expenditure "
                       "in 2024-25?",
            normalized="x", start=0.0,
            cache_conn=get_adapter(), dashboard_results={},
            template_map=self.main._template_map, dashboard_questions={},
            start_date=None, end_date=None,
        )
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE)
        self.assertEqual(len(result.result), 1,
                         "the premise: $top_n = 1 leaves one row on screen")
        frame = build_context_frame(
            result, self.main._catalog_column_metadata.get(QID),
            self.templates[QID]["abstract_question"])
        stored = self.main._context_store.set_frame(SESSION, frame,
                                                    rows=result.result)
        return stored, result.result

    def _operate(self, **payload):
        response = self.client.post("/operation", json={
            "session_id": SESSION,
            "result_set_id": self.frame.result_set.id,
            **payload,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # -- The defect, closed on the real wire ---------------------------------

    def test_the_displayed_row_is_the_maximum_of_the_population(self):
        """The premise of the whole defect, asserted rather than assumed: the
        single row `LIMIT 1` leaves on screen is the HIGHEST, so a minimum taken
        over it is guaranteed to name the highest."""
        from db_factory import get_adapter
        rel = get_adapter().execute(
            "SELECT focus_area_name, SUM(COALESCE(total_cost,0)) AS c "
            "FROM v_activity WHERE fiscal_year = '2024-2025' "
            "GROUP BY 1 ORDER BY c DESC")
        population = rel.fetchall()
        self.assertGreater(len(population), 1,
                           "a one-row population cannot demonstrate anything")
        self.assertEqual(self.rows[0]["focus_area_name"], population[0][0])

    def test_1404_the_lowest_never_returns_the_displayed_row(self):
        payload = self._operate(operation="min", column="planned_cost")
        displayed = str(self.rows[0]["focus_area_name"])
        self.assertIn(payload["operation_mode"], ("requery", "rejected"))
        if payload["operation_mode"] == "requery":
            self.assertNotIn(displayed, payload["answer"],
                             "the highest focus area came back as the lowest")

    def test_1042_bottom_n_never_returns_the_displayed_row(self):
        payload = self._operate(operation="bottom_n", column="planned_cost", n=1)
        displayed = str(self.rows[0]["focus_area_name"])
        self.assertIn(payload["operation_mode"], ("requery", "rejected"))
        if payload["operation_mode"] == "requery":
            names = [r["focus_area_name"] for r in (payload["result"] or [])]
            self.assertNotIn(displayed, names)

    def test_the_requery_reaches_the_whole_population(self):
        """`LIMIT 1` lifted to the ceiling returns every focus area the sample
        holds - proof the re-query ran through the template and not around it."""
        from db_factory import get_adapter
        rel = get_adapter().execute(
            "SELECT COUNT(DISTINCT focus_area_name) FROM v_activity "
            "WHERE fiscal_year = '2024-2025'")
        population = rel.fetchall()[0][0]
        payload = self._operate(operation="bottom_n", column="planned_cost",
                                n=population)
        self.assertEqual(payload["operation_mode"], "requery")
        self.assertEqual(len(payload["result"]), population)

    # -- The echo and the caveat (D31.2 second half) --------------------------

    def test_a_served_operation_carries_an_echo(self):
        """`query_description` was None on this path, which is why #1404
        arrived with nothing beside it."""
        payload = self._operate(operation="min", column="planned_cost")
        self.assertTrue((payload.get("query_description") or "").strip())
        self.assertIn("Lowest", payload["query_description"])
        self.assertTrue(payload["answer"].startswith(
            payload["query_description"]))

    def test_the_echo_names_the_scope_the_number_was_taken_over(self):
        payload = self._operate(operation="min", column="planned_cost")
        self.assertIn("among all", payload["query_description"],
                      "a re-queried number is taken over the whole population "
                      "and the echo has to say so")

    def test_an_unguarded_operation_still_answers_and_still_echoes(self):
        """`count` states the table's own row count, so it is not guarded -
        but it is still a served answer and still has to restate itself."""
        payload = self._operate(operation="count")
        self.assertEqual(payload["operation_mode"], "client")
        self.assertTrue((payload.get("query_description") or "").strip())

    def test_the_caveat_travels_with_the_recomputation(self):
        """Whatever qualifies the rows qualifies a number taken from them."""
        caveat = self.templates[QID].get("caveat")
        payload = self._operate(operation="min", column="planned_cost")
        self.assertEqual(payload.get("caveat") or None, caveat or None)
        if caveat:
            self.assertIn(caveat, payload["answer"])


if __name__ == "__main__":
    unittest.main()
