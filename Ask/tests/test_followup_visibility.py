"""The reading of a message is reported, on every path that binds it.

THE DEFECT THIS SUITE PINS. `/query` decides, per message, whether the user
asked something new or refined what was already on screen. That decision changes
the answer completely, and five paths made it silently: a frame edit re-queries
the SAME template and returns an ordinary successful answer, byte-for-byte
indistinguishable from a fresh question that happened to match it. Only scope
inheritance said anything, and it said it in the answer TEXT — the string an
officer copies into a report.

`QueryResponse.interpretation` now carries which question the answer answers on
all five, and the answer text carries none of it. See
query_router/interpretation.py for the two rules (report never predict;
generated text is never a follow-up).

NO NETWORK, NO LLM, AND STILL THE REAL HANDLER. The tests below call
`main.query_endpoint` itself — the wiring is the thing under test, and a unit
test of the helpers would have passed just as well with nothing wired up. What
is stubbed is exactly the two functions that would make paid calls:
`classify_followup` (the follow-up classifier) and `route` (catalog matching).
Everything between them is real: the registry, the templates, the DuckDB sample,
the drill hop, the pending resolver, the frame store.
"""
import os
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

load_dotenv(_BACKEND / ".env")

# The handler reads its adapter through `db_factory.get_adapter()`, so the
# engine has to be chosen before the first call rather than injected after.
os.environ["DB_ENGINE"] = "duckdb_file"
os.environ.setdefault("DB_PATH", str(_DB_PATH))

from query_router.followup_classifier import (       # noqa: E402
    FollowupDecision,
    FrameEdit,
    catalog_question_patterns,
)
from query_router.fragment_reroute import geo_vocabulary_tokens   # noqa: E402
from query_router.interpretation import (            # noqa: E402
    BOUND_KINDS,
    MAX_DETAIL_CHARS,
    Interpretation,
    against_frame,
    against_pending,
    operation_detail,
    period_detail,
    readable_slot,
    slot_detail,
)
from query_router.models import (                    # noqa: E402
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    OperationRequest,
    OperationResult,
    OperationMode,
    PendingClarification,
    ResultSetReference,
    TimeRange,
)
from query_router.template_catalog import TEMPLATE_CATALOG   # noqa: E402


def _frame(template_id: str, question: str, bound: dict[str, str] | None = None):
    return ContextFrame(
        template_id=template_id,
        template_question=question,
        bound_params=bound or {},
        active_filters=[],
        time_range=TimeRange(start=None, end=None, grain="all_time"),
        grouping_dimension=None,
        result_set=ResultSetReference(
            id="rs_test", row_count=1,
            columns=[ColumnMetadata(name="gp", column_type=ColumnType.DIMENSION)],
        ),
    )


# ── The contract, on its own ─────────────────────────────────────────────────

class InterpretationContractTests(unittest.TestCase):
    def test_the_default_is_the_standalone_reading(self):
        """A path that forgets to stamp itself must report no marker rather
        than a wrong one."""
        blank = Interpretation()
        self.assertEqual(blank.kind, "new_question")
        self.assertIsNone(blank.anchor_question)
        self.assertIsNone(blank.anchor_template_id)
        self.assertIsNone(blank.detail)

    def test_every_bound_kind_carries_an_anchor(self):
        frame = _frame("EXP-001", "What was spent in 2024-25?")
        for kind in sorted(BOUND_KINDS - {"clarification_reply"}):
            with self.subTest(kind=kind):
                marker = against_frame(kind, frame, "district → Khordha")
                self.assertEqual(marker.kind, kind)
                self.assertEqual(marker.anchor_question,
                                 "What was spent in 2024-25?")
                self.assertEqual(marker.anchor_template_id, "EXP-001")

    def test_a_template_id_stands_in_for_a_missing_question(self):
        marker = against_frame("frame_edit", _frame("EXP-001", None))
        self.assertEqual(marker.anchor_question, "EXP-001")

    def test_nothing_to_anchor_to_degrades_to_standalone(self):
        """A marker with nothing to anchor to is a UI with nothing to draw."""
        self.assertEqual(against_frame("frame_edit", None).kind, "new_question")
        self.assertEqual(against_pending(None).kind, "new_question")

    def test_a_pending_anchors_to_the_paused_question(self):
        marker = against_pending(
            PendingClarification(
                query_id="PLN-006", missing_slot="district_name",
                slot_type="district", filled={},
                original_query="which blocks submitted everything?",
            ),
            "answered: district",
        )
        self.assertEqual(marker.kind, "clarification_reply")
        self.assertEqual(marker.anchor_question,
                         "which blocks submitted everything?")
        self.assertEqual(marker.anchor_template_id, "PLN-006")

    def test_detail_is_a_phrase_and_is_capped(self):
        """It rides on an answer an officer reads. The cap is enforced in the
        model, not trusted at the call sites."""
        self.assertEqual(slot_detail("district_name", "Khordha"),
                         "district → Khordha")
        self.assertEqual(readable_slot("gp_name"), "gp")
        self.assertEqual(readable_slot("date_range"), "date range")
        self.assertIsNone(slot_detail("district_name", None))
        self.assertIsNone(slot_detail(None, "Khordha"))
        self.assertEqual(period_detail("2024-04-01", "2025-03-31"),
                         "period → 2024-04-01 to 2025-03-31")
        self.assertIsNone(period_detail("2024-04-01", None))
        self.assertEqual(
            operation_detail(OperationResult(
                operation="sum", mode=OperationMode.CLIENT, answer="…",
                column="actual_expenditure")),
            "sum of actual_expenditure",
        )
        self.assertEqual(
            operation_detail(OperationResult(
                operation="sort", mode=OperationMode.CLIENT, answer="…")),
            "sort",
        )
        capped = Interpretation(kind="frame_edit", detail="x" * 200)
        self.assertLessEqual(len(capped.detail), MAX_DETAIL_CHARS)
        self.assertTrue(capped.detail.endswith("…"))


# ── The handler ──────────────────────────────────────────────────────────────

class _RouteStub:
    """Standard catalog matching, without the model.

    Defaults to refusing: a test that reaches matching unintentionally fails
    loudly instead of quietly making a paid call.
    """

    def __init__(self):
        self.result = None
        self.calls = 0

    def __call__(self, message, **kwargs):
        self.calls += 1
        if self.result is None:
            raise AssertionError(f"unexpected route of {message!r}")
        return self.result.model_copy(deep=True)


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
class HandlerReadingTests(unittest.TestCase):
    """One test per row of the pattern's backend gate."""

    @classmethod
    def setUpClass(cls):
        import main
        from db_factory import get_adapter
        from query_router.entity_validator import EntityValidator

        cls.main = main
        cls.adapter = get_adapter()
        main._openai_client = object()          # only its presence is checked
        main._validator = EntityValidator(cls.adapter)
        main._template_map = dict(TEMPLATE_CATALOG)
        main._dashboard_results = {}
        main._dashboard_questions = {}
        main._geo_tokens = set(geo_vocabulary_tokens(
            *(main._validator.registry_values(etype)
              for etype in main.GEO_ENTITY_TYPES_WIDEST_FIRST)
        ))
        main._catalog_patterns[:] = catalog_question_patterns(
            [t["abstract_question"] for t in TEMPLATE_CATALOG.values()]
        )

    def setUp(self):
        self.route = _RouteStub()
        self.decision = FollowupDecision(kind="new_question")
        self._real_route = self.main.route
        self._real_classify = self.main.classify_followup
        self.main.route = self.route
        self.main.classify_followup = (
            lambda message, frame, client: self.decision
        )
        self.session = self.id().rsplit(".", 1)[-1]
        self.main._context_store.reset(self.session)

    def tearDown(self):
        self.main.route = self._real_route
        self.main.classify_followup = self._real_classify
        self.main._context_store.reset(self.session)

    # ── helpers ──────────────────────────────────────────────────────────────

    def serve(self, query_id: str, **slot_values):
        """Execute a template directly — the same wiring the endpoint uses.

        Typing the question is not reliable enough to build a gate on (routing
        flips a few percent of questions on identical replays), and here it is
        not available at all: matching is stubbed out.
        """
        from db_factory import get_adapter
        from query_router.router import _serve_query_id, _template_slot_types

        template = self.main._template_map[query_id]
        entities = []
        for name, etype in _template_slot_types(template).items():
            if name not in slot_values:
                continue
            entity = self.main._validator.validate(slot_values[name], etype)
            entity.slot_name = name
            entities.append(entity)

        result = _serve_query_id(
            query_id, entities, None,
            user_query=template["abstract_question"],
            normalized=template["abstract_question"], start=time.monotonic(),
            cache_conn=get_adapter(), dashboard_results=self.main._dashboard_results,
            template_map=self.main._template_map,
            dashboard_questions=self.main._dashboard_questions,
            start_date=self.main._default_start_date,
            end_date=self.main._default_end_date,
        )
        self.assertEqual(result.tier.value, "tier2", result.fallback_message)
        return result

    def seed_frame(self, query_id: str, **slot_values) -> ContextFrame:
        """Put an answered table on screen. Returns the frame, so a test can
        assert the anchor is THAT question and not the one it gets back."""
        from query_router.context_store import build_context_frame

        result = self.serve(query_id, **slot_values)
        frame = build_context_frame(
            result, self.main._catalog_column_metadata.get(query_id),
            self.main._catalog_question(query_id),
        )
        self.assertIsNotNone(frame)
        return self.main._context_store.set_frame(
            self.session, frame, rows=result.result
        )

    def ask(self, message: str, **body):
        return self.main.query_endpoint(
            self.main.QueryRequest(message=message, session_id=self.session, **body)
        )

    def assertBound(self, payload, kind: str):
        marker = payload.interpretation
        self.assertEqual(marker.kind, kind, payload.answer)
        self.assertTrue(marker.anchor_question,
                        "a bound reading with nothing to anchor to draws nothing")
        self.assertTrue(marker.anchor_template_id)
        if marker.detail:
            self.assertLessEqual(len(marker.detail), MAX_DETAIL_CHARS)
        return marker

    def assertStandalone(self, payload):
        marker = payload.interpretation
        self.assertEqual(marker.kind, "new_question", payload.answer)
        self.assertIsNone(marker.anchor_question)
        self.assertIsNone(marker.anchor_template_id)
        self.assertIsNone(marker.detail)

    # ── gate rows ────────────────────────────────────────────────────────────

    def test_a_fragment_against_a_live_frame_reports_the_reroute(self):
        """"in khordha?" carries a district and no subject. The anchor is the
        question it was read against — the PREVIOUS one, captured before the
        handler replaced the frame."""
        before = self.seed_frame("EXP-001", date_range="2024-2025")
        payload = self.ask("in khordha?")

        marker = self.assertBound(payload, "fragment_reroute")
        self.assertEqual(marker.anchor_question, before.template_question)
        self.assertEqual(marker.anchor_template_id, "EXP-001")
        self.assertNotIn("Khordha", marker.anchor_question,
                         "the anchor is the state-wide question, not the answer's own")
        self.assertEqual(marker.detail, "district → Khordha")
        self.assertEqual(self.route.calls, 0,
                         "the deterministic hop must not reach matching")

    def test_the_classifier_route_to_the_same_place_reports_it_too(self):
        """The same fragment, when the LLM classifier does produce the edit."""
        before = self.seed_frame("PLN-006", date_range="2024-2025")
        self.decision = FollowupDecision(
            kind="unexecutable_edit",
            edit=FrameEdit(slot="district_name", value="Khordha"),
        )
        payload = self.ask("in khordha?")

        marker = self.assertBound(payload, "fragment_reroute")
        self.assertEqual(marker.anchor_template_id, before.template_id)
        self.assertEqual(marker.detail, "district → Khordha")

    def test_a_word_for_word_catalogue_question_is_standalone(self):
        """The guard that stops "How many GPs…?" being read as a count also
        stops it being reported as a follow-up — it never met the classifier."""
        self.seed_frame("EXP-001", date_range="2024-2025")
        self.route.result = self.serve("PLN-006", date_range="2024-2025")
        question = TEMPLATE_CATALOG["PLN-006"]["abstract_question"].format(
            date_range="2024-2025"
        )
        payload = self.ask(question)
        self.assertEqual(self.route.calls, 1, "it must reach standard matching")
        self.assertStandalone(payload)

    def test_a_tapped_chip_is_standalone(self):
        """Rule 2: generated text bypasses the classifier by construction, so a
        marker on it would be a false one — and a false marker on a chip tap
        teaches the user to distrust the true ones."""
        self.seed_frame("EXP-001", date_range="2024-2025")
        self.route.result = self.serve("PLN-006", date_range="2024-2025")
        payload = self.ask("anything at all, we generated it", from_chip=True)
        self.assertStandalone(payload)

    def test_an_operation_names_the_operation(self):
        before = self.seed_frame("EXP-001", date_range="2024-2025")
        self.decision = FollowupDecision(
            kind="operation", operation=OperationRequest(operation="sum"),
        )
        payload = self.ask("total?")

        self.assertEqual(payload.tier, "operation", payload.answer)
        marker = self.assertBound(payload, "operation")
        self.assertEqual(marker.anchor_question, before.template_question)
        self.assertTrue(marker.detail.startswith("sum"), marker.detail)

    def test_a_frame_edit_reports_the_swap(self):
        """The path no frontend could ever infer: same template, ordinary
        answer, nothing in the payload that differs from a fresh question."""
        before = self.seed_frame("EXP-001", date_range="2024-2025",
                                 district_name="Khordha")
        self.decision = FollowupDecision(
            kind="frame_edit",
            edit=FrameEdit(slot="district_name", value="Ganjam"),
        )
        payload = self.ask("and ganjam?")

        marker = self.assertBound(payload, "frame_edit")
        self.assertEqual(marker.anchor_question, before.template_question)
        self.assertIn("Khordha", marker.anchor_question)
        self.assertEqual(marker.detail, "district → Ganjam")
        self.assertIn("Ganjam", payload.query_description or "")

    def test_the_first_message_of_a_session_is_standalone(self):
        self.route.result = self.serve("EXP-001", date_range="2024-2025")
        payload = self.ask("how much was actually spent in 2024-25?")
        self.assertStandalone(payload)

    def test_a_clarification_reply_anchors_to_the_paused_question(self):
        """Not to the frame: what the user is answering is the question the
        router paused on, which may be nothing like the last answered one."""
        self.main._context_store.set_pending(self.session, PendingClarification(
            query_id="PLN-006", missing_slot="district_name",
            slot_type="district", filled={"date_range": "2024-2025"},
            original_query="which blocks submitted every plan?",
        ))
        payload = self.ask("Khordha")

        marker = self.assertBound(payload, "clarification_reply")
        self.assertEqual(marker.anchor_question, "which blocks submitted every plan?")
        self.assertEqual(marker.anchor_template_id, "PLN-006")
        self.assertEqual(marker.detail, "answered: district")

    def test_a_reply_we_could_not_use_is_still_a_reply(self):
        """The re-ask is a reading of the message against the paused question
        just as much as a served answer is."""
        self.main._context_store.set_pending(self.session, PendingClarification(
            query_id="PLN-006", missing_slot="district_name",
            slot_type="district", filled={"date_range": "2024-2025"},
            original_query="which blocks submitted every plan?",
        ))
        payload = self.ask("zzzz")

        self.assertEqual(payload.tier, "clarify", payload.answer)
        marker = self.assertBound(payload, "clarification_reply")
        self.assertEqual(marker.anchor_question, "which blocks submitted every plan?")

    def test_scope_inheritance_reports_the_carry_and_the_prose_is_gone(self):
        """The one path that already announced itself — in the answer TEXT.
        The sentence is retired; the marker replaces it, and the path's own
        escape chip stays."""
        before = self.seed_frame("PLN-006", date_range="2024-2025",
                                 district_name="Khordha")
        self.route.result = self.serve("EXP-001", date_range="2024-2025")
        payload = self.ask("how much money was actually spent in 2024-25?")

        marker = self.assertBound(payload, "scope_inherited")
        self.assertEqual(marker.anchor_question, before.template_question)
        self.assertEqual(marker.detail, "district → Khordha")
        self.assertNotIn("carried over", payload.answer)
        self.assertNotIn("Answered for", payload.answer)
        self.assertIn("Khordha", payload.query_description or "")
        self.assertTrue(
            payload.suggestions
            and "whole state" in payload.suggestions[0].label,
            "the sharper escape from an inherited scope must survive",
        )

    def test_the_same_question_with_the_context_reset_is_standalone(self):
        self.seed_frame("PLN-006", date_range="2024-2025", district_name="Khordha")
        self.route.result = self.serve("EXP-001", date_range="2024-2025")
        payload = self.ask("how much money was actually spent in 2024-25?",
                           reset_context=True)
        self.assertStandalone(payload)
        self.assertNotIn("Khordha", payload.query_description or "",
                         "a reset frame cannot lend its scope")

    def test_the_back_endpoint_is_standalone(self):
        """Restoration is not a follow-up: there is no new message to have been
        read one way or the other."""
        self.seed_frame("EXP-001", date_range="2024-2025")
        self.seed_frame("PLN-006", date_range="2024-2025")
        payload = self.main.context_pop(
            self.main.ContextRequest(session_id=self.session)
        )
        self.assertEqual(payload.query_id, "EXP-001")
        self.assertStandalone(payload)

    def test_the_operation_endpoint_is_standalone(self):
        """A control tapped ON a table names the table it computes over —
        nothing was classified, so there is no reading to report."""
        frame = self.seed_frame("EXP-001", date_range="2024-2025")
        payload = self.main.operation_endpoint(self.main.OperationCallRequest(
            session_id=self.session, result_set_id=frame.result_set.id,
            operation="sum",
        ))
        self.assertEqual(payload.tier, "operation")
        self.assertStandalone(payload)


if __name__ == "__main__":
    unittest.main()
