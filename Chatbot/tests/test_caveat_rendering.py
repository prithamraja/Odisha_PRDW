"""Decision D3: a caveat reaches the user on EVERY path that serves rows.

296 of the 346 templates carry one, because 251 of the signed-off questions are
only partially answerable — a proxy column, a coverage gap, a denominator that
is the 20 loaded GPs rather than the official roster. A Partial answer served
without its caveat is the confidently-wrong failure mode the caveat layer exists
to prevent, and "served" includes the two paths that hand back rows WITHOUT
re-routing: a breadcrumb hop back, and an operation recomputed on the table
already on screen. A caveat is a property of the question the rows answer, so
neither may quietly drop it.

VERBATIM, AND OUTSIDE ANY MODEL. The text is asserted to appear unchanged and to
be appended after the answer rather than woven into it. No LLM runs on this
path — `echo_answer` composes the answer deterministically — which is precisely
what makes appending safe: there is no later step that could paraphrase it away.

No API key and no network: the endpoint handlers are called directly with a
seeded context store.
"""
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

# PLN-002 is the sharpest example in the catalogue: it reports GPs with an
# APPROVED plan, but plan_code_status is entirely NULL so approval is proxied by
# a date every loaded plan has — the number is real and means something other
# than it appears to. Without the caveat it is a wrong answer with correct rows.
CAVEATED_ID = "PLN-002"


def _skip_reason():
    if not _DB_PATH.exists():
        return f"no sample database at {_DB_PATH}"
    return None


class CaveatRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reason = _skip_reason()
        if reason:
            raise unittest.SkipTest(reason)
        import os
        os.environ.setdefault("DB_ENGINE", "duckdb_file")
        os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

        import main
        from query_router.models import (
            ActiveFilter, ColumnMetadata, ColumnType, ContextFrame,
            ResultSetReference, TimeRange,
        )
        from query_router.template_catalog import TEMPLATE_CATALOG

        cls.main = main
        cls.caveat = TEMPLATE_CATALOG[CAVEATED_ID]["caveat"]
        cls.assertTruthy = bool(cls.caveat)

        # main.startup() is never called — it builds the vector index and needs
        # an API key. The two maps the endpoints read are populated directly.
        main._template_map = dict(TEMPLATE_CATALOG)
        main._dashboard_questions = {}

        cls.rows = [{"gps_approved": 20}]
        cls.frame = ContextFrame(
            template_id=CAVEATED_ID,
            template_question=TEMPLATE_CATALOG[CAVEATED_ID]["abstract_question"],
            bound_params={"date_range": "2024-2025"},
            active_filters=[ActiveFilter(dimension="date_range", value="2024-2025")],
            time_range=TimeRange(start=None, end=None, grain="all_time"),
            grouping_dimension=None,
            result_set=ResultSetReference(
                id="rs_caveat", row_count=1,
                columns=[ColumnMetadata(name="gps_approved",
                                        column_type=ColumnType.ADDITIVE_COUNT)],
            ),
        )

    def setUp(self):
        self.main._context_store.reset("caveat-session")

    def _assert_carried(self, payload, where: str):
        """Both halves: the field a styled frontend reads, and the text a plain
        one shows. Either alone is a caveat somebody does not see."""
        self.assertEqual(payload.caveat, self.caveat, f"{where}: caveat field")
        self.assertIn(self.caveat, payload.answer, f"{where}: answer text")
        self.assertTrue(payload.answer.rstrip().endswith(self.caveat),
                        f"{where}: the caveat must come last, not be woven in")

    # ── Path 1 of 3: /query ──────────────────────────────────────────────────

    def test_the_query_path_carries_the_caveat(self):
        from query_router.echo import echo_answer
        from query_router.models import RouteResult, RouteTier

        result = RouteResult(
            tier=RouteTier.TIER2_TEMPLATE,
            query_id=CAVEATED_ID,
            query_description="How many GPs had their GPDP approved in 2024-2025?",
            result=self.rows,
            caveat=self.caveat,
            raw_query="x", normalized_query="x", total_latency_ms=1.0,
        )
        answer = echo_answer(result)
        self.assertIn(self.caveat, answer)
        self.assertTrue(answer.rstrip().endswith(self.caveat))

    def test_the_query_path_carries_it_even_when_no_rows_matched(self):
        """Zero rows is exactly when a reader starts inventing reasons."""
        from query_router.echo import echo_answer
        from query_router.models import RouteResult, RouteTier

        result = RouteResult(
            tier=RouteTier.TIER2_TEMPLATE, query_id=CAVEATED_ID,
            query_description="…", result=[], caveat=self.caveat,
            raw_query="x", normalized_query="x", total_latency_ms=1.0,
        )
        answer = echo_answer(result)
        self.assertIn("No records matched", answer)
        self.assertTrue(answer.rstrip().endswith(self.caveat))

    # ── Path 2 of 3: /context/pop ────────────────────────────────────────────

    def test_the_breadcrumb_path_carries_the_caveat(self):
        """Going back restores the rows, so it must restore what qualifies them."""
        from main import ContextRequest

        self.main._context_store.set_frame(
            "caveat-session", self.frame, rows=self.rows
        )
        # A second frame, so there is something to pop BACK from.
        self.main._context_store.set_frame(
            "caveat-session", self.frame.model_copy(deep=True), rows=self.rows
        )
        payload = self.main.context_pop(ContextRequest(session_id="caveat-session"))
        self._assert_carried(payload, "/context/pop")

    # ── Path 3 of 3: /operation ──────────────────────────────────────────────

    def test_the_operation_path_carries_the_caveat(self):
        """An operation recomputes on the same rows — a sum, a share, a top-N.
        The caveat qualifies those rows, so it qualifies the recomputation: a
        percentage of a 17%-covered population is as misleading as the count."""
        from main import OperationCallRequest

        self.main._context_store.set_frame(
            "caveat-session", self.frame, rows=self.rows
        )
        previous_client = self.main._openai_client
        # The guard only exists because a REQUERY operation may need the router.
        # A client-side sum does not; this keeps the test off the network.
        self.main._openai_client = object()
        try:
            payload = self.main.operation_endpoint(OperationCallRequest(
                session_id="caveat-session",
                result_set_id=self.frame.result_set.id,
                operation="sum",
                column="gps_approved",
            ))
        finally:
            self.main._openai_client = previous_client
        self._assert_carried(payload, "/operation")

    # ── The negative: no caveat, no note ─────────────────────────────────────

    def test_an_uncaveated_question_gains_no_note_on_any_path(self):
        from query_router.template_catalog import TEMPLATE_CATALOG
        uncaveated = next(
            qid for qid, entry in TEMPLATE_CATALOG.items()
            if not (entry.get("caveat") or "").strip()
        )
        self.assertIsNone(self.main._catalog_caveat(uncaveated))

        from query_router.echo import append_caveat
        self.assertEqual(append_caveat("answer", None), "answer")
        self.assertEqual(append_caveat("answer", "   "), "answer")


if __name__ == "__main__":
    unittest.main()
