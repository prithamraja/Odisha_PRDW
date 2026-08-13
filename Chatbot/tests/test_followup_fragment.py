"""Follow-up fragments keep the question they follow on from.

The reproduction: "Distribution of declared area_hectares by category
(SC/ST/BC/OC)" answers with Q027 (average landholding by social category,
state-wide), and the follow-up "in kurnool?" came back with a MARKFED
procurement table for Kurnool. Q027 has no district slot, so the edit was
refused and the bare fragment routed on its own — and a fragment carries no
subject, so it landed wherever the district name pointed.

The unit tests here pin the deterministic pieces (the drill map, the combined
question, the subject test, the fragment test). The endpoint tests pin the
wiring through the real /query handler, so they need OPENAI_API_KEY and the flat
Parquet drop; they skip cleanly without them.
"""
import os
import time
import unittest
from pathlib import Path

from dotenv import load_dotenv

from query_router.fragment_reroute import (
    DRILL_MAP,
    combined_question,
    drill_target,
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
_FLAT = _BACKEND.parents[1] / "RTGS_Data" / "flat"

load_dotenv(_BACKEND / ".env")

# db_factory reads DATA_DIR at import time, so it must be set before `import main`.
if _FLAT.is_dir():
    os.environ["DATA_DIR"] = str(_FLAT)

_SKIP = None
if not _FLAT.is_dir():
    _SKIP = f"flat Parquet drop not present at {_FLAT}"
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
        grouping_dimension="category",
        result_set=ResultSetReference(
            id="rs_test", row_count=4,
            columns=[ColumnMetadata(name="category", column_type=ColumnType.DIMENSION)],
        ),
    )


class DrillMapTests(unittest.TestCase):
    def test_every_geo_family_maps_to_its_narrower_siblings(self):
        # 46 Gnn families, each with -S/-D/-M: -S drills to both, -D to the mandal.
        self.assertEqual(drill_target("G01-S", "district"), "G01-D")
        self.assertEqual(drill_target("G01-S", "mandal"), "G01-M")
        self.assertEqual(drill_target("G01-D", "mandal"), "G01-M")
        self.assertEqual(drill_target("G06-S", "district"), "G06-D")

    def test_the_authored_non_suffix_pairs_are_present(self):
        self.assertEqual(drill_target("Q027", "district"), "G04-D")
        self.assertEqual(drill_target("Q027", "mandal"), "G04-M")
        self.assertEqual(drill_target("Q019", "district"), "G04-D")

    def test_every_mapped_target_exists_and_takes_the_slot(self):
        for wider, targets in DRILL_MAP.items():
            self.assertIn(wider, TEMPLATE_CATALOG, wider)
            for slot, target in targets.items():
                self.assertIn(target, TEMPLATE_CATALOG, target)
                slots = {s["name"] for s in TEMPLATE_CATALOG[target]["param_slots"]}
                self.assertIn(slot, slots, f"{target} has no {slot} parameter")

    def test_nothing_maps_to_itself_or_to_a_wider_scope(self):
        for wider, targets in DRILL_MAP.items():
            for target in targets.values():
                self.assertNotEqual(wider, target)
                self.assertFalse(target.endswith("-S"), f"{wider} -> {target} widens")


class CombinedQuestionTests(unittest.TestCase):
    def test_the_frame_question_carries_the_subject(self):
        self.assertEqual(
            combined_question(
                "What is the average landholding by social category?", "in kurnool?"
            ),
            "What is the average landholding by social category? in kurnool",
        )

    def test_a_question_mark_is_added_when_the_frame_has_none(self):
        self.assertEqual(combined_question("Land by category", "for Guntur"),
                         "Land by category? for Guntur")

    def test_a_missing_frame_question_degrades_to_the_fragment(self):
        self.assertEqual(combined_question(None, "in kurnool?"), "in kurnool")


class SubjectOverlapTests(unittest.TestCase):
    def test_the_observed_misroutes_do_not_share_a_subject(self):
        self.assertFalse(templates_share_subject("Q027", "G14-D"))  # MARKFED
        self.assertFalse(templates_share_subject("Q027", "G01-D"))  # coverage

    def test_the_right_target_does_share_a_subject(self):
        self.assertTrue(templates_share_subject("Q027", "G04-D"))

    def test_an_unknown_id_is_never_evidence_of_a_different_subject(self):
        self.assertTrue(templates_share_subject("Q027", "D01"))
        self.assertTrue(templates_share_subject(None, "G04-D"))


class SlotOnlyFragmentTests(unittest.TestCase):
    GEO = {"kurnool", "guntur", "east", "godavari", "peddapuram"}

    def test_a_bare_place_is_a_fragment(self):
        for message in ("in kurnool?", "for Guntur?", "what about 2024 in Kurnool?",
                        "in east godavari district"):
            self.assertTrue(is_slot_only_fragment(message, self.GEO), message)

    def test_anything_with_a_measure_word_is_not(self):
        for message in ("how many fishers are registered?",
                        "how many small or marginal farmers",
                        "input subsidy in Kurnool",
                        "total?", ""):
            self.assertFalse(is_slot_only_fragment(message, self.GEO), message)

    def test_the_vocabulary_is_tokenised(self):
        tokens = geo_vocabulary_tokens(["East Godavari", "YSR Kadapa"])
        self.assertEqual(tokens, {"east", "godavari", "ysr", "kadapa"})


class UnexecutableEditTests(unittest.TestCase):
    """parse_decision must say WHY a frame edit was refused."""

    def test_a_slot_the_question_lacks_is_an_unexecutable_edit(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Kurnool"},
            _frame("Q027"),
        )
        self.assertEqual(decision.kind, "unexecutable_edit")
        self.assertEqual(decision.edit.slot, "district")
        self.assertEqual(decision.edit.value, "Kurnool")

    def test_an_invented_slot_is_still_a_new_question(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "hospital", "value": "X"}, _frame("Q027")
        )
        self.assertEqual(decision.kind, "new_question")

    def test_a_noop_swap_is_still_a_new_question(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Kurnool"},
            _frame("G04-D", {"district": "Kurnool"}),
        )
        self.assertEqual(decision.kind, "new_question")

    def test_an_executable_swap_is_still_a_frame_edit(self):
        decision = parse_decision(
            {"kind": "frame_edit", "slot": "district", "value": "Guntur"},
            _frame("G04-D", {"district": "Kurnool"}),
        )
        self.assertEqual(decision.kind, "frame_edit")


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class FragmentEndpointTests(unittest.TestCase):
    """The gates, through the real /query handler."""

    @classmethod
    def setUpClass(cls):
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

        Typing the question is not reliable enough to build a gate on (measured
        at 293 templates, near-misses inside CLARIFY_SCORE_MARGIN divert it), and
        the seed helper in test_context_window_endpoint.py resumes a PENDING,
        which needs a template with a missing slot — Q027 has none. This executes
        the template directly through the same _serve_query_id + frame wiring the
        endpoint uses.
        """
        import main
        from db_factory import get_adapter
        from query_router.context_store import build_context_frame
        from query_router.router import _serve_query_id, _template_slot_types

        template = main._template_map[query_id]
        entities = []
        for name, etype in _template_slot_types(template).items():
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

    # ── Gate 2a / 1a — the reproduction ───────────────────────────────────────

    def test_gate_2a_statewide_frame_drills_without_a_rerank_call(self):
        from query_router import reranker

        session = "frag-2a"
        self.seed_frame(session, "Q027")
        before = reranker.rerank_call_count()

        payload = self.ask("in kurnool?", session_id=session)

        self.assertEqual(payload["query_id"], "G04-D", payload["answer"])
        self.assertEqual(
            [(e["slot"], e["value"]) for e in payload["entities"]],
            [("district", "Kurnool")],
        )
        self.assertEqual(reranker.rerank_call_count(), before,
                         "the drill hop must be deterministic — no rerank call")
        # Gate 1a's negative half: never a procurement/MARKFED answer.
        self.assertNotIn("procure", (payload["query_description"] or "").lower())

    def test_gate_1b_a_complete_question_still_routes_on_its_own(self):
        session = "frag-1b"
        self.seed_frame(session, "Q027")
        payload = self.ask("how many fishers are registered?", session_id=session)
        self.assertEqual(payload["query_id"], "Q010", payload["answer"])

    # ── Gate 2b — another statewide family ────────────────────────────────────

    def test_gate_2b_land_size_bands_drill_to_the_district(self):
        session = "frag-2b"
        self.seed_frame(session, "G06-S")
        payload = self.ask("in guntur?", session_id=session)
        self.assertEqual(payload["query_id"], "G06-D", payload["answer"])
        self.assertIn("Guntur", payload["query_description"])

    # ── Gate 2c — district frame drills to the mandal, but only for a mandal ──

    def test_gate_2c_a_district_frame_drills_to_the_mandal(self):
        session = "frag-2c"
        self.seed_frame(session, "G01-D", district="East Godavari")
        payload = self.ask("in peddapuram?", session_id=session)
        self.assertEqual(payload["query_id"], "G01-M", payload["answer"])
        bound = {e["slot"]: e["value"] for e in payload["entities"]}
        self.assertEqual(bound.get("mandal"), "Peddapuram")
        self.assertEqual(bound.get("district"), "East Godavari")

    def test_gate_2c_a_value_that_is_not_a_mandal_does_not_hop(self):
        """The half that can't be typed: serve_drill_hop refuses outright, which
        is what sends the message on to the contextual re-route."""
        import main
        from db_factory import get_adapter
        from query_router.context_store import build_context_frame
        from query_router.router import serve_drill_hop

        session = "frag-2c-neg"
        self.seed_frame(session, "G01-D", district="East Godavari")
        frame = main._context_store.get(session)

        hopped = serve_drill_hop(
            frame, "mandal", "Zzzzqqq Notaplace",
            template_map=main._template_map, cache_conn=get_adapter(),
            validator=main._validator, dashboard_results=main._dashboard_results,
            dashboard_questions=main._dashboard_questions,
            user_query="in zzzzqqq notaplace?",
            start_date=main._default_start_date, end_date=main._default_end_date,
        )
        self.assertIsNone(hopped)

    def test_a_mandal_of_another_district_is_never_served_as_an_empty_table(self):
        """'in tenali?' inside an East Godavari conversation. Tenali is a real
        mandal — of Guntur — so the hop binds cleanly and returns nothing. An
        empty table presented as the answer is the silent wrong answer this path
        exists to remove."""
        session = "frag-cross"
        self.seed_frame(session, "G01-D", district="East Godavari")
        payload = self.ask("in tenali?", session_id=session)
        self.assertEqual(payload["tier"], "clarify", payload["answer"])
        self.assertEqual(payload["clarification"]["reason"], "ambiguous_fragment")
        self.assertFalse(payload["result"])

    # ── Gate 3 — no sibling, no same-subject match: ask, don't serve ──────────

    def test_gate_3_a_fragment_with_nowhere_to_drill_clarifies(self):
        session = "frag-3"
        self.seed_frame(session, "Q067", aadhaar_length="12")
        payload = self.ask("in kurnool?", session_id=session)

        self.assertEqual(payload["tier"], "clarify", payload["answer"])
        self.assertEqual(payload["clarification"]["reason"], "ambiguous_fragment")
        self.assertIn("Kurnool", payload["clarification"]["prompt"])
        options = payload["clarification"]["options"]
        self.assertGreaterEqual(len(options), 2)
        for chip in options:
            self.assertNotIn("{", chip["label"])
        self.assertEqual(options[-1]["label"], "Something else")

    # ── Regression — the catalog-question guard is untouched ──────────────────

    def test_a_word_for_word_catalog_question_still_routes_to_matching(self):
        session = "frag-catalog"
        self.seed_frame(session, "Q027")
        question = TEMPLATE_CATALOG["G04-D"]["abstract_question"].format(
            district="Kurnool"
        )
        payload = self.ask(question, session_id=session)
        self.assertEqual(payload["tier"], "tier2", payload["answer"])
        self.assertIn("Kurnool", payload["query_description"])

    def test_an_operation_on_a_statewide_frame_still_classifies(self):
        session = "frag-op"
        self.seed_frame(session, "Q027")
        payload = self.ask("total?", session_id=session)
        self.assertEqual(payload["tier"], "operation", payload["answer"])
        self.assertEqual(payload["operation"], "sum")


if __name__ == "__main__":
    unittest.main()
