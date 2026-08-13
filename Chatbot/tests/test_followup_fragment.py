"""Follow-up fragments keep the question they follow on from.

The reproduction (AP, and the same shape here): a state-wide answer on screen,
then the fragment "in Ganjam?". The follow-up classifier reads it as a
geography edit, the frame has no such value bound, and the bare fragment then
routes on its own — carrying no subject, so it lands wherever the district name
points. Confident, and about the wrong thing.

WHAT WP-3 CHANGED, AND WHY THESE TESTS LOOK DIFFERENT FROM THE AP ONES
    The AP catalogue spelled geographic scope into the id (G01-S state / -D
    district / -M mandal), so narrowing a state-wide answer meant HOPPING TO A
    NARROWER SIBLING TEMPLATE, and `DRILL_MAP` was the table of those hops. That
    table is gone, because decision D2 removed the siblings: one PR&DW template
    answers at every scope and narrowing it means binding its optional geography
    slot. `drill_target` therefore returns the template ITSELF when it can take
    the named tier, and None when it cannot.

    The unit tests below pin the new contract; the endpoint tests pin the wiring
    through the real /query handler and are OPT-IN, because they route for real
    and routing costs money (see PRDW_LIVE_ROUTING).
"""
import os
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv

from query_router.fragment_reroute import (
    GEO_SLOTS,
    combined_question,
    drill_target,
    fragment_place_phrase,
    geo_vocabulary_tokens,
    is_slot_only_fragment,
    templates_share_subject,
)
from query_router.followup_classifier import parse_decision
from query_router.models import (
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    ResultSetReference,
    TimeRange,
)
from query_router.template_catalog import TEMPLATE_CATALOG

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

load_dotenv(_BACKEND / ".env")

# OPT-IN, for the reason WP-2 report §7.1 gives: these tests drive the real
# /query handler, which embeds, reranks and extracts through the OpenAI API. A
# suite that quietly makes paid calls whenever a key happens to sit in .env is
# not a suite anyone can run freely — and at T0 of WP-2 this repo was doing
# exactly that.
#
# The AP version was guarded by needing a flat Parquet drop that does not exist
# here, so it skipped by accident rather than by decision. It also computed that
# path as `parents[1].parents[1]`, which since the Chatbot/ flattening resolves
# OUTSIDE this repo (WP-1 report §7.2) — so a stray RTGS_Data/ landing in the
# shared parent would have silently pointed these tests at another project's
# data. Both are fixed here: the guard is explicit and the path is this repo's.
_LIVE = os.environ.get("PRDW_LIVE_ROUTING") == "1"
_SKIP = None
if not _LIVE:
    _SKIP = ("live routing is opt-in: set PRDW_LIVE_ROUTING=1 (costs money, "
             "requires OPENAI_API_KEY)")
elif not _DB_PATH.exists():
    _SKIP = f"no sample database at {_DB_PATH}"
elif not os.environ.get("OPENAI_API_KEY"):
    _SKIP = "OPENAI_API_KEY not set — the router is disabled without it"


def _frame(template_id: str, bound: dict[str, str] | None = None) -> ContextFrame:
    """A minimal frame for the pure decision tests."""
    return ContextFrame(
        template_id=template_id,
        template_question=TEMPLATE_CATALOG[template_id]["abstract_question"],
        bound_params=bound or {},
        active_filters=[],
        time_range=TimeRange(start=None, end=None, grain="all_time"),
        grouping_dimension="theme",
        result_set=ResultSetReference(
            id="rs_test", row_count=4,
            columns=[ColumnMetadata(name="theme", column_type=ColumnType.DIMENSION)],
        ),
    )


class DrillTargetTests(unittest.TestCase):
    """Decision D2: the narrowed question is the SAME template with one more
    optional parameter bound, so a hop is a self-hop or nothing."""

    def test_a_template_with_the_tier_hops_to_itself(self):
        # PLN-001 takes all three tiers as optional filters.
        for slot in ("district_name", "block_name", "gp_name"):
            with self.subTest(slot=slot):
                self.assertEqual(drill_target("PLN-001", slot), "PLN-001")

    def test_a_template_without_the_tier_refuses(self):
        """TRD-012 compares one district against the state benchmark and has no
        block or GP filter. Returning a hop it cannot bind would serve an
        unrelated table; None sends the message on to ordinary matching."""
        self.assertEqual(drill_target("TRD-012", "district_name"), "TRD-012")
        self.assertIsNone(drill_target("TRD-012", "block_name"))
        self.assertIsNone(drill_target("TRD-012", "gp_name"))

    def test_an_unknown_id_or_slot_refuses(self):
        self.assertIsNone(drill_target("NOPE-999", "district_name"))
        self.assertIsNone(drill_target("PLN-001", None))
        self.assertIsNone(drill_target(None, "district_name"))
        self.assertIsNone(drill_target("PLN-001", "ward_name"))

    def test_the_geo_slots_are_the_workbook_bind_names(self):
        """`param_slots` carries bind names, so GEO_SLOTS must too — the entity
        types (`district`, `block`, `gp`) are a different vocabulary and mixing
        them yields a silent no-op rather than an error."""
        self.assertEqual(GEO_SLOTS, ("gp_name", "block_name", "district_name"))
        slots = {s["name"] for s in TEMPLATE_CATALOG["PLN-001"]["param_slots"]}
        for slot in GEO_SLOTS:
            self.assertIn(slot, slots)


class CombinedQuestionTests(unittest.TestCase):
    def test_the_frame_question_carries_the_subject(self):
        self.assertEqual(
            combined_question(
                "How many activities are abandoned?", "in ganjam?"
            ),
            "How many activities are abandoned? in ganjam",
        )

    def test_a_question_mark_is_added_when_the_frame_has_none(self):
        self.assertEqual(combined_question("Abandoned activities", "for Barpali"),
                         "Abandoned activities? for Barpali")

    def test_a_missing_frame_question_degrades_to_the_fragment(self):
        self.assertEqual(combined_question(None, "in ganjam?"), "in ganjam")


class SubjectOverlapTests(unittest.TestCase):
    """The guard: bracket AND module, the workbook's own classification."""

    def test_a_different_module_is_a_different_subject(self):
        # Planning/GPDP against Expenditure/GPDP — the same module word, and the
        # exact slide a subjectless fragment makes.
        self.assertFalse(templates_share_subject("PLN-001", "EXP-001"))
        self.assertFalse(templates_share_subject("PLN-001", "SAN-001"))

    def test_the_same_bracket_and_module_do_share_a_subject(self):
        self.assertTrue(templates_share_subject("PLN-001", "PLN-005"))

    def test_an_unknown_id_is_never_evidence_of_a_different_subject(self):
        self.assertTrue(templates_share_subject("PLN-001", "D01"))
        self.assertTrue(templates_share_subject(None, "PLN-005"))


class SlotOnlyFragmentTests(unittest.TestCase):
    GEO = {"ganjam", "khordha", "barpali", "tangi", "choudwar", "andhrua"}

    def test_a_bare_place_is_a_fragment(self):
        for message in ("in ganjam?", "for Barpali?", "what about 2024 in Khordha?",
                        "in tangi choudwar block", "for Andhrua GP",
                        "in Barpali panchayat samiti"):
            self.assertTrue(is_slot_only_fragment(message, self.GEO), message)

    def test_anything_with_a_measure_word_is_not(self):
        for message in ("how many activities are abandoned?",
                        "how much was spent in Khordha",
                        "which GPs uploaded a plan",
                        "total?", ""):
            self.assertFalse(is_slot_only_fragment(message, self.GEO), message)

    def test_the_vocabulary_is_tokenised(self):
        """Multi-word places have to match word by word, or "Tangi Choudwar"
        needs an exact-string scan of every message."""
        tokens = geo_vocabulary_tokens(["Tangi Choudwar", "Kalyansingpur"])
        self.assertEqual(tokens, {"tangi", "choudwar", "kalyansingpur"})

    def test_the_place_phrase_drops_the_unit_noun(self):
        self.assertEqual(
            fragment_place_phrase("in tangi choudwar block", self.GEO),
            "tangi choudwar",
        )
        self.assertEqual(fragment_place_phrase("for Andhrua GP", self.GEO), "andhrua")


class UnexecutableEditTests(unittest.TestCase):
    """parse_decision must say WHY a frame edit was refused."""

    def test_a_slot_the_question_lacks_is_an_unexecutable_edit(self):
        # TRD-012 has a district filter but no block one.
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "block_name", "value": "Barpali"},
            _frame("TRD-012"),
        )
        self.assertEqual(decision.kind, "unexecutable_edit")
        self.assertEqual(decision.edit.slot, "block_name")
        self.assertEqual(decision.edit.value, "Barpali")

    def test_an_invented_slot_is_still_a_new_question(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "hospital", "value": "X"},
            _frame("TRD-012"),
        )
        self.assertEqual(decision.kind, "new_question")

    def test_a_noop_swap_is_still_a_new_question(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district_name", "value": "Khordha"},
            _frame("PLN-004", {"district_name": "Khordha"}),
        )
        self.assertEqual(decision.kind, "new_question")

    def test_an_executable_swap_is_still_a_frame_edit(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district_name", "value": "Ganjam"},
            _frame("PLN-004", {"district_name": "Khordha"}),
        )
        self.assertEqual(decision.kind, "frame_edit")


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class FragmentEndpointTests(unittest.TestCase):
    """The gates, through the real /query handler. Opt-in — see _LIVE above."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DB_ENGINE", "duckdb_file")
        os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")
        from fastapi.testclient import TestClient
        import main

        cls._client_ctx = TestClient(main.app)
        cls.client = cls._client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_ctx.__exit__(None, None, None)

    def ask(self, message: str, **body) -> dict:
        response = self.client.post("/query", json={"message": message, **body})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def seed_frame(self, session: str, query_id: str, **slot_values) -> None:
        """Put an answered table on screen without going through matching.

        Typing the question is not reliable enough to build a gate on — routing
        flips ~3% of questions on identical replays — so this executes the
        template directly through the same _serve_query_id + frame wiring the
        endpoint uses.
        """
        import main
        from db_factory import get_adapter
        from query_router.context_store import build_context_frame
        from query_router.router import _serve_query_id, _template_slot_types

        template = main._template_map[query_id]
        entities = []
        for name, etype in _template_slot_types(template).items():
            if name not in slot_values:
                continue
            entity = main._validator.validate(slot_values[name], etype)
            entity.slot_name = name
            entities.append(entity)

        result = _serve_query_id(
            query_id, entities, None,
            user_query=template["abstract_question"],
            normalized=template["abstract_question"], start=time.monotonic(),
            cache_conn=get_adapter(), dashboard_results=main._dashboard_results,
            template_map=main._template_map,
            dashboard_questions=main._dashboard_questions,
            start_date=main._default_start_date, end_date=main._default_end_date,
        )
        self.assertEqual(result.tier.value, "tier2", result.fallback_message)
        frame = build_context_frame(
            result, main._catalog_column_metadata.get(query_id),
            main._catalog_question(query_id),
        )
        self.assertIsNotNone(frame)
        main._context_store.reset(session)
        main._context_store.set_frame(session, frame, rows=result.result)

    def test_a_statewide_frame_narrows_without_a_rerank_call(self):
        """The whole point of the deterministic path: a bare place fragment must
        not reach the reranker, which has no subject to work from."""
        from query_router import reranker

        session = "frag-narrow"
        self.seed_frame(session, "EXP-001", date_range="2024-2025")
        before = reranker.rerank_call_count()

        payload = self.ask("in khordha?", session_id=session)

        self.assertEqual(payload["query_id"], "EXP-001", payload["answer"])
        bound = {e["slot"]: e["value"] for e in payload["entities"]}
        self.assertEqual(bound.get("district_name"), "Khordha")
        self.assertEqual(reranker.rerank_call_count(), before,
                         "the narrowing hop must be deterministic — no rerank call")

    def test_a_complete_question_still_routes_on_its_own(self):
        session = "frag-complete"
        self.seed_frame(session, "EXP-001", date_range="2024-2025")
        payload = self.ask(
            "how many gram panchayats uploaded their GPDP in 2024-2025?",
            session_id=session,
        )
        self.assertNotEqual(payload["query_id"], "EXP-001", payload["answer"])

    def test_an_operation_on_a_statewide_frame_still_classifies(self):
        session = "frag-op"
        self.seed_frame(session, "EXP-001", date_range="2024-2025")
        payload = self.ask("total?", session_id=session)
        self.assertEqual(payload["tier"], "operation", payload["answer"])
        self.assertEqual(payload["operation"], "sum")

    def test_a_caveated_answer_carries_its_caveat_on_the_query_path(self):
        """T7, path 1 of 3. PLN-002's note says approval is PROXIED by a date —
        without it the answer reads as a real approval count."""
        session = "frag-caveat"
        payload = self.ask(
            "how many GPs had their GPDP approved in 2024-2025?", session_id=session
        )
        if payload.get("query_id") != "PLN-002":
            self.skipTest(f"routed to {payload.get('query_id')}, not PLN-002")
        caveat = TEMPLATE_CATALOG["PLN-002"]["caveat"]
        self.assertEqual(payload["caveat"], caveat)
        self.assertIn(caveat, payload["answer"])


if __name__ == "__main__":
    unittest.main()
