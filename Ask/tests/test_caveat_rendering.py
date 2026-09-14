"""Caveat plumbing: a caveat, when a template has one, reaches the user on EVERY
path that serves rows.

Operator ruling 2026-09-14: the catalogue's caveats were removed — the "Note: …"
under each answer confused officers and was almost never helpful — so no shipped
template carries one today (`tools/migrations/m4_drop_caveats.py`). The plumbing
stays, because the lossy-alias sentence (Swachh Bharat -> Sanitation) still uses
it and a caveat may be put back on one template by hand. These tests therefore
give PLN-002 a caveat of their own and check it travels.

"Served" includes the two paths that hand back rows WITHOUT re-routing: a
breadcrumb hop back, and an operation recomputed on the table already on screen.
A caveat is a property of the question the rows answer, so neither may quietly
drop it.

VERBATIM, AND OUTSIDE ANY MODEL. The text is asserted to appear unchanged and to
be appended after the answer rather than woven into it. No LLM runs on this
path — `echo_answer` composes the answer deterministically.

No API key and no network: the endpoint handlers are called directly with a
seeded context store.
"""
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

CAVEATED_ID = "PLN-002"
TEST_CAVEAT = "Approval is proxied by a date every loaded plan has."


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
        cls.caveat = TEST_CAVEAT

        # main.startup() is never called — it builds the vector index and needs
        # an API key. The two maps the endpoints read are populated directly,
        # with PLN-002 given a caveat the shipped catalogue no longer has.
        main._template_map = dict(TEMPLATE_CATALOG)
        main._template_map[CAVEATED_ID] = {
            **TEMPLATE_CATALOG[CAVEATED_ID], "caveat": TEST_CAVEAT}
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

    # ── The shipped catalogue: no notes ──────────────────────────────────────

    def test_no_shipped_template_carries_a_caveat(self):
        from query_router.template_catalog import TEMPLATE_CATALOG
        carrying = sorted(qid for qid, entry in TEMPLATE_CATALOG.items()
                          if (entry.get("caveat") or "").strip())
        self.assertEqual(carrying, [])

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
        The caveat qualifies those rows, so it qualifies the recomputation."""
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
        uncaveated = next(
            qid for qid, entry in self.main._template_map.items()
            if not (entry.get("caveat") or "").strip()
        )
        self.assertIsNone(self.main._catalog_caveat(uncaveated))

        from query_router.echo import append_caveat
        self.assertEqual(append_caveat("answer", None), "answer")
        self.assertEqual(append_caveat("answer", "   "), "answer")


if __name__ == "__main__":
    unittest.main()
