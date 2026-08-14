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
    executable_geo_slots,
    fragment_place_phrase,
    geo_vocabulary_tokens,
    is_slot_only_fragment,
    templates_share_subject,
)
from query_router.router import (
    TIER_NOUNS,
    ambiguous_fragment_clarify,
    name_the_tier,
    tier_collision_clarify,
)
from query_router.followup_classifier import parse_decision
from query_router.models import (
    ColumnMetadata,
    ColumnType,
    ContextFrame,
    ResultSetReference,
    RouteTier,
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


class ExecutableGeoSlotTests(unittest.TestCase):
    """T2(e)(i). The tier a fragment is read as must be chosen from the tiers
    the FRAME can execute, not filtered afterwards.

    36 of the 346 templates carry an incomplete tier set — PLN-006 filters only
    by district, PLN-003 by district and block — so "widest tier that validates,
    then check" abandons hops the catalogue could have served.
    """

    def test_a_full_tier_template_offers_all_three(self):
        self.assertEqual(
            executable_geo_slots("PLN-001"),
            {"district_name", "block_name", "gp_name"},
        )

    def test_a_partial_tier_template_offers_only_what_it_filters(self):
        self.assertEqual(executable_geo_slots("PLN-003"),
                         {"district_name", "block_name"})
        self.assertEqual(executable_geo_slots("PLN-006"), {"district_name"})

    def test_an_unknown_or_missing_id_offers_nothing(self):
        self.assertEqual(executable_geo_slots("NOPE-999"), set())
        self.assertEqual(executable_geo_slots(None), set())

    def test_it_agrees_with_drill_target_on_every_template(self):
        """The two must not drift: a slot in this set is exactly a slot
        `drill_target` will hop on."""
        for qid in TEMPLATE_CATALOG:
            for slot in GEO_SLOTS:
                with self.subTest(qid=qid, slot=slot):
                    self.assertEqual(
                        slot in executable_geo_slots(qid),
                        drill_target(qid, slot) is not None,
                    )


class TierCollisionClarifyTests(unittest.TestCase):
    """T2(e)(iii). D18.P3 rules that GP/block collisions CLARIFY in v1, and the
    question to ask is WHICH PLACE — not the generic "narrowed, or a new
    question?", which asks about an intent that was never in doubt and leaves
    the officer retyping the name that was ambiguous."""

    def test_the_prompt_is_about_the_place_not_the_intent(self):
        result = tier_collision_clarify(
            frame_question="What is the total actual expenditure incurred by "
                           "Andhrua in 2024-2025?",
            readings=[("Laxmipur (block)", "…in Laxmipur block?"),
                      ("Laxmipur (GP)", "…in Laxmipur GP?")],
            user_query="what about Laxmipur?",
        )
        self.assertEqual(result.tier, RouteTier.CLARIFY)
        self.assertEqual(result.clarification.reason, "tier_collision")
        self.assertIn("more than one place", result.clarification.prompt)
        self.assertNotIn("new question", result.clarification.prompt)

    def test_every_reading_is_a_tier_qualified_chip(self):
        result = tier_collision_clarify(
            frame_question="Q?",
            readings=[("Laxmipur (block)", "a"), ("Laxmipur (GP)", "b")],
            user_query="what about Laxmipur?",
        )
        labels = [c.label for c in result.clarification.options]
        self.assertEqual(labels, ["Laxmipur (block)", "Laxmipur (GP)",
                                  "Something else"])

    def test_the_tier_nouns_cover_every_geography_slot(self):
        self.assertEqual(set(TIER_NOUNS), set(GEO_SLOTS))


class TierNamingTests(unittest.TestCase):
    """T2(e)(ii). When one tier was picked for the user, the echo says which —
    "Laxmipur" alone is exactly the string that was ambiguous."""

    def test_the_served_tier_is_named(self):
        self.assertEqual(
            name_the_tier(
                "What is the total actual expenditure incurred by Laxmipur in "
                "2024-2025?", "Laxmipur", "gp_name"),
            "What is the total actual expenditure incurred by Laxmipur (GP) in "
            "2024-2025?",
        )

    def test_only_the_first_occurrence_is_annotated(self):
        self.assertEqual(
            name_the_tier("Compare Laxmipur with Laxmipur?", "Laxmipur", "block_name"),
            "Compare Laxmipur (block) with Laxmipur?",
        )

    def test_nothing_to_name_leaves_the_question_alone(self):
        self.assertEqual(name_the_tier("Q?", "X", "theme"), "Q?")
        self.assertIsNone(name_the_tier(None, "X", "gp_name"))
        self.assertEqual(name_the_tier("Q?", None, "gp_name"), "Q?")


class AmbiguousFragmentChipTests(unittest.TestCase):
    """T2(e)(iv). Retrieval on a bare place name matches on the NAME. A chip
    whose only tie to what the user said is a place name is noise dressed as a
    reading, and tapping it silently changes the subject."""

    def _clarify(self, fragment_id):
        return ambiguous_fragment_clarify(
            frame_question="What percentage of GPs in Khordha uploaded the GPDP?",
            value="Laxmipur",
            contextual_question="…narrowed to Laxmipur?",
            fragment_question="…some question that merely says Laxmipur?",
            user_query="what about Laxmipur?",
            frame_query_id="PLN-001",
            fragment_query_id=fragment_id,
        )

    def test_a_subject_sharing_match_is_still_offered(self):
        texts = [c.send_text for c in self._clarify("PLN-005").clarification.options]
        self.assertIn("…some question that merely says Laxmipur?", texts)

    def test_a_name_only_match_is_dropped(self):
        self.assertTrue(templates_share_subject("PLN-001", "EXP-001") is False)
        texts = [c.send_text for c in self._clarify("EXP-001").clarification.options]
        self.assertNotIn("…some question that merely says Laxmipur?", texts)
        self.assertIn("…narrowed to Laxmipur?", texts)

    def test_the_fragment_chip_survives_when_nothing_else_would(self):
        """An empty clarification is worse than a noisy one."""
        result = ambiguous_fragment_clarify(
            frame_question="Q?", value="Laxmipur",
            contextual_question=None,
            fragment_question="the only reading on offer?",
            user_query="what about Laxmipur?",
            frame_query_id="PLN-001", fragment_query_id="EXP-001",
        )
        texts = [c.send_text for c in result.clarification.options]
        self.assertIn("the only reading on offer?", texts)


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
class FragmentTierSelectionTests(unittest.TestCase):
    """The whole of T2(e) against the REAL registry — no LLM, no network.

    Laxmipur, Bheden and Kalimela are each both a block and a GP in the 20-GP
    sample, so the collision class is exercisable today rather than only
    statewide (WP-4a §2).
    """

    @classmethod
    def setUpClass(cls):
        import main
        from db_factory import open_analytical_db
        from query_router.entity_validator import EntityValidator

        cls.adapter = open_analytical_db(_DB_PATH)
        cls.main = main
        main._validator = EntityValidator(cls.adapter)
        main._template_map = dict(TEMPLATE_CATALOG)
        main._geo_tokens = set(geo_vocabulary_tokens(
            *(main._validator.registry_values(etype)
              for etype in main.GEO_ENTITY_TYPES_WIDEST_FIRST)
        ))

    @classmethod
    def tearDownClass(cls):
        try:
            cls.adapter.close()
        except Exception:                                    # pragma: no cover
            pass

    def test_a_colliding_name_is_read_at_both_tiers(self):
        tiers = self.main._fragment_tiers(
            _frame("EXP-001", {"date_range": "2024-2025"}), "what about Laxmipur?")
        self.assertEqual([slot for slot, _ in tiers], ["block_name", "gp_name"])

    def test_a_colliding_name_clarifies_instead_of_picking(self):
        """Both tiers resolve AND both fit EXP-001, so serving either would be
        a coin flip presented as an answer."""
        edit, clarify, name_tier = self.main._fragment_reading(
            _frame("EXP-001", {"date_range": "2024-2025"}), "what about Laxmipur?")
        self.assertIsNone(edit)
        self.assertIsNotNone(clarify)
        self.assertEqual(clarify.clarification.reason, "tier_collision")
        labels = [c.label for c in clarify.clarification.options]
        self.assertEqual(labels[:2], ["Laxmipur (block)", "Laxmipur (GP)"])
        for chip in clarify.clarification.options[:2]:
            self.assertNotIn("{", chip.send_text)
            self.assertIn("Laxmipur", chip.send_text)

    def test_an_unambiguous_name_still_serves_without_asking(self):
        edit, clarify, name_tier = self.main._fragment_reading(
            _frame("PLN-001", {"date_range": "2024-2025"}), "in Khordha?")
        self.assertIsNone(clarify)
        self.assertEqual((edit.slot, edit.value), ("district_name", "Khordha"))
        self.assertFalse(name_tier, "one tier resolved — nothing to disambiguate")

    def test_only_executable_tiers_compete(self):
        """PLN-006 filters by district alone. A GP-and-block name must not be
        read at a tier the template cannot bind — the old walk stopped at the
        first tier that VALIDATED and the hop then died at drill_target."""
        edit, clarify, _ = self.main._fragment_reading(
            _frame("PLN-006", {"date_range": "2024-2025"}), "what about Laxmipur?")
        self.assertIsNone(clarify, "neither tier is executable, so nothing to ask")
        self.assertNotIn(edit.slot, executable_geo_slots("PLN-006"))

    def test_a_single_fitting_tier_is_auto_slotted_and_named(self):
        """Only `gp_name` fits, but the NAME was ambiguous — so the hop is
        served and the echo has to say which Laxmipur it served."""
        gp_only = [q for q in TEMPLATE_CATALOG
                   if executable_geo_slots(q) == {"gp_name"}]
        self.assertTrue(gp_only, "no gp-only template left to pin this on")
        edit, clarify, name_tier = self.main._fragment_reading(
            _frame(gp_only[0], {"date_range": "2024-2025"}), "what about Laxmipur?")
        self.assertIsNone(clarify)
        self.assertEqual(edit.slot, "gp_name")
        self.assertTrue(name_tier)


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
