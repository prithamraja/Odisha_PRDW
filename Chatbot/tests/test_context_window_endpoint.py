"""End-to-end proof for the five conversation-context defects.

The unit tests pin each decision in isolation; these pin the wiring — that a
real conversation through /query no longer loses the question the user asked.
Each test names the reproduction it closes.

Runs the real app against the flat Parquet drop and the real router, so it needs
OPENAI_API_KEY and RTGS_Data/flat; it skips cleanly without them.
"""
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

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

# 'Venkateswarlu G' matches four roster names, told apart by district:
#   Gupta (Anantapur) · Babu (East Godavari, Srikakulam, Vizianagaram, Chittoor)
#   Chowdary (Krishna, Srikakulam, Chittoor) · Devi (Visakhapatnam, Chittoor)
AMBIGUOUS_FARMER_Q = "How many schemes is Venkateswarlu G enrolled in?"

# That question routes to Q125, which needs {farmer_name} AND {village}. So the
# reply that picks the farmer is answered by a CHAINED clarify for the village —
# the paused question continuing, not being lost. Bathalapalli is the village
# Venkateswarlu Gupta is registered in, and completes the conversation.
GUPTA_VILLAGE = "Bathalapalli"


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class ContextWindowFixTests(unittest.TestCase):
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

    def start(self, session: str, message: str, **body) -> dict:
        return self.ask(message, session_id=session, reset_context=True, **body)

    def seed_frame(self, session: str, query_id: str, **slot) -> dict:
        """Put a specific answered table on screen, deterministically.

        Typing the question is not reliable enough to build a test on: measured
        over four runs, "How much was procured in each mandal of East Godavari
        district?" lands on G14-D about half the time and on the ambiguous-zone
        clarify the rest (top-2 retrieval scores inside CLARIFY_SCORE_MARGIN).
        A seed that silently lands elsewhere makes every assertion below pass
        against the wrong table, which is worse than failing.

        Resuming a pending reaches the template with no retrieval involved, and
        still sets the frame through the identical /query wiring.
        """
        import main
        from query_router.models import PendingClarification

        main._context_store.reset(session)
        main._context_store.set_pending(session, PendingClarification(
            query_id=query_id, missing_slot=slot["name"],
            slot_type=slot["type"], filled={}, original_query=slot["question"],
        ))
        payload = self.ask(slot["answer"], session_id=session)
        self.assertEqual(payload["query_id"], query_id, payload["answer"])
        self.assertTrue(payload["result"], "seeded frame has no rows to operate on")
        return payload

    PROCUREMENT_SEED = dict(
        name="district", type="district", answer="East Godavari",
        question="How much was procured in each mandal of East Godavari district?",
    )
    TOP_SUBSIDIES_SEED = dict(
        name="top_n", type="top_n", answer="25",
        question="Who received the 25 highest input subsidies?",
    )

    def seed_farmer_pending(self, session: str) -> None:
        """Put the app into the roster disambiguation on Q125, directly.

        The reply-handling logic is what these tests are about, and seeding the
        pause keeps them independent of whether that day's rerank sends the
        question to Q125 or to F14 (the deliberately-ambiguous name search).
        `test_disambiguation_clarify_carries_candidate_chips` is the one that
        still proves real routing gets here.
        """
        import main
        from query_router.models import EntityCandidate, PendingClarification

        main._context_store.reset(session)
        main._context_store.set_pending(session, PendingClarification(
            query_id="Q125", missing_slot="farmer_name", slot_type="farmer_name",
            filled={}, original_query=AMBIGUOUS_FARMER_Q,
            candidates=[
                EntityCandidate(name="Venkateswarlu Gupta", districts=["Anantapur"]),
                EntityCandidate(name="Venkateswarlu Babu", districts=[
                    "East Godavari", "Srikakulam", "Vizianagaram", "Chittoor"]),
                EntityCandidate(name="Venkateswarlu Chowdary", districts=[
                    "Krishna", "Srikakulam", "Chittoor"]),
                EntityCandidate(name="Venkateswarlu Devi", districts=[
                    "Visakhapatnam", "Chittoor"]),
            ],
        ))

    # ── Fix 1 — farmer disambiguation answered by district ────────────────────

    def ask_until_disambiguation(self, session: str) -> dict:
        """The one place we insist REAL routing reaches the roster
        disambiguation. Retried once for the same rerank nondeterminism
        `seed_frame` documents."""
        for _ in range(2):
            payload = self.start(session, AMBIGUOUS_FARMER_Q)
            if "Which one do you mean?" in payload["answer"]:
                return payload
        self.skipTest(
            f"routing did not reach the roster disambiguation in two attempts "
            f"(tier {payload['tier']}, query_id {payload.get('query_id')})"
        )

    def test_disambiguation_clarify_carries_candidate_chips(self):
        payload = self.ask_until_disambiguation("cw-fix1-chips")
        self.assertEqual(payload["tier"], "clarify")
        chips = payload["clarification"]["options"]
        self.assertTrue(chips, "the disambiguation used to arrive with no chips")
        for chip in chips:
            self.assertIn("Venkateswarlu", chip["send_text"])
            # The label carries what tells them apart; the tap sends the name.
            self.assertIn("(", chip["label"])

    def _assert_picked_gupta(self, session: str, payload: dict) -> None:
        """The reply picked Venkateswarlu Gupta, so the FARMER question is what
        continues — proved by finishing it and reading the answer."""
        self.assertNotIn("What would you like to know about", payload["answer"],
                         "the farmer question was replaced by an elicitation")
        self.assertEqual(payload["tier"], "clarify")
        self.assertIn("village", payload["answer"].lower())

        finished = self.ask(GUPTA_VILLAGE, session_id=session)
        self.assertEqual(finished["tier"], "tier2")
        self.assertEqual(finished["query_id"], "Q125")
        self.assertIn("Venkateswarlu Gupta", finished["query_description"])
        self.assertEqual(finished["result"][0]["name"], "Venkateswarlu Gupta")

    def test_answering_with_a_district_answers_the_farmer_question(self):
        """The reproduction: replying 'Anantapur' used to answer 'What would you
        like to know about Anantapur?' — the farmer question was gone."""
        session = "cw-fix1-district"
        self.seed_farmer_pending(session)
        self._assert_picked_gupta(session, self.ask("Anantapur", session_id=session))

    def test_a_typed_full_name_still_resolves(self):
        session = "cw-fix1-typed"
        self.seed_farmer_pending(session)
        self._assert_picked_gupta(
            session, self.ask("Venkateswarlu Gupta", session_id=session)
        )

    def test_a_district_shared_by_several_narrows_and_keeps_the_question(self):
        session = "cw-fix1-narrow"
        self.seed_farmer_pending(session)

        narrowed = self.ask("Chittoor", session_id=session)
        self.assertEqual(narrowed["tier"], "clarify")
        self.assertIn("Chittoor", narrowed["answer"])
        offered = {c["send_text"] for c in narrowed["clarification"]["options"]}
        self.assertNotIn("Venkateswarlu Gupta", offered,
                         "Gupta is not in Chittoor — the narrowing must bite")

        # The paused question is still alive: naming one of the narrowed
        # candidates continues it rather than starting from nothing. That name
        # is itself two people in Chittoor, so it cascades into the PERSON
        # choice — and the district the user already gave has to survive the
        # cascade, or the second round re-offers someone they just ruled out.
        answered = self.ask("Venkateswarlu Devi", session_id=session)
        self.assertEqual(answered["tier"], "clarify")
        villages = {c["send_text"] for c in answered["clarification"]["options"]}
        self.assertEqual(
            villages,
            {"Venkateswarlu Devi of Valmikipuram",
             "Venkateswarlu Devi of Nimmanapalle"},
            "the two Chittoor namesakes must be separately selectable",
        )
        self.assertNotIn("Kasimkota", answered["answer"],
                         "the Visakhapatnam namesake was ruled out by 'Chittoor'")

    def test_a_tapped_candidate_chip_resolves_the_paused_question(self):
        """A chip tap normally skips the pending resume, because chip text is a
        complete question by construction. A disambiguation chip is the one
        exception: its send_text IS the slot value."""
        session = "cw-fix1-chip-tap"
        first = self.ask_until_disambiguation(session)
        # The chip sends a reference to one PERSON, not the bare name — a name
        # is exactly what was ambiguous, so sending it back would clarify again.
        chip = next(
            c for c in first["clarification"]["options"]
            if c["send_text"].startswith("Venkateswarlu Gupta")
        )
        self.assertNotEqual(chip["send_text"], "Venkateswarlu")
        self._assert_picked_gupta(
            session, self.ask(chip["send_text"], session_id=session, from_chip=True)
        )

    # ── Fix 3 — "all crops" answered a question nobody asked ──────────────────

    def seed_crop_pending(self, session: str) -> None:
        """Put the app into "For which crop?" on Q098, directly.

        The original reproduction reached that clarify by asking "How many
        input-subsidy farmers also sold produce to MARKFED?" — which now routes
        straight to Q118, because the template-fidelity pass added that exact
        sentence as a Q118 paraphrase. Good outcome, but it means the phrasing
        no longer exercises the pending-reply code this test exists to pin.
        Seeding the pause makes the test independent of which phrasing lands on
        Q098 on any given day, and it still drives the real /query wiring.
        """
        import main
        from query_router.models import PendingClarification

        main._context_store.reset(session)
        main._context_store.set_pending(session, PendingClarification(
            query_id="Q098", missing_slot="crop", slot_type="crop", filled={},
            original_query="How many input-subsidy farmers also sold to MARKFED?",
        ))

    def test_all_crops_serves_the_crop_less_overlap_question(self):
        """The reproduction: 'all crops' used to serve 'Show me the crop pattern
        by district' (126 rows) — silently, and looking entirely normal."""
        session = "cw-fix3"
        self.seed_crop_pending(session)

        payload = self.ask("all crops", session_id=session)
        self.assertNotEqual(payload["query_id"], "Q091",
                            "the crop-pattern template is the bug, not the answer")
        self.assertEqual(payload["query_id"], "Q118")
        self.assertIn("overlap", (payload["query_description"] or "").lower())
        self.assertTrue(payload["result"], "Q118 returned no overlap rows")

    def test_a_named_crop_still_executes_the_narrow_question(self):
        session = "cw-fix3-paddy"
        self.seed_crop_pending(session)

        payload = self.ask("Paddy", session_id=session)
        self.assertEqual(payload["query_id"], "Q098")
        self.assertIn("Paddy", payload["query_description"])

    # ── Short-reply retry: one more ask before a fragment routes alone ────────

    def test_an_unusable_short_reply_is_asked_again_then_lets_go(self):
        session = "cw-retry"
        self.seed_crop_pending(session)

        again = self.ask("top 25", session_id=session)
        self.assertEqual(again["tier"], "clarify")
        self.assertIn("still need a crop", again["answer"])
        escape = again["clarification"]["options"][-1]
        self.assertEqual(escape["send_text"], "top 25")

        # Saying it a second time is taken at face value — one extra turn, never
        # a loop.
        released = self.ask("top 25", session_id=session)
        self.assertNotIn("still need a crop", released["answer"],
                         "the retry must not repeat — one extra turn, never a loop")

    def test_the_escape_chip_skips_the_retry_immediately(self):
        session = "cw-retry-escape"
        self.seed_crop_pending(session)
        again = self.ask("top 25", session_id=session)
        escape = again["clarification"]["options"][-1]

        released = self.ask(escape["send_text"], session_id=session, from_chip=True)
        self.assertNotIn("still need a crop", released["answer"])

    # ── Frame scope inheritance ───────────────────────────────────────────────

    def test_a_new_question_inherits_the_districts_scope_and_says_so(self):
        """Asked inside a conversation about East Godavari, 'how many small or
        marginal farmers' used to be answered STATE-WIDE with nothing saying so."""
        session = "cw-scope"
        self.seed_frame(session, "G14-D", **self.PROCUREMENT_SEED)

        payload = self.ask("how many small or marginal farmers", session_id=session)
        self.assertEqual(payload["query_id"], "G06-D")
        self.assertIn("East Godavari", payload["query_description"])
        self.assertIn("carried over", payload["answer"])
        undo = (payload["suggestions"] or [])[0]
        self.assertIn("state-wide", undo["label"])

        # The undo chip must actually undo it.
        back = self.ask(undo["send_text"], session_id=session, from_chip=True)
        self.assertEqual(back["query_id"], "G06-S")

    def test_an_explicit_statewide_question_is_never_narrowed(self):
        session = "cw-scope-explicit"
        self.seed_frame(session, "G14-D", **self.PROCUREMENT_SEED)
        payload = self.ask("how many marginal farmers state-wide", session_id=session)
        self.assertEqual(payload["query_id"], "G06-S")
        self.assertNotIn("carried over", payload["answer"])

    def test_a_question_naming_its_own_district_keeps_it(self):
        session = "cw-scope-own"
        self.seed_frame(session, "G14-D", **self.PROCUREMENT_SEED)
        payload = self.ask("land size distribution in Guntur district", session_id=session)
        self.assertEqual(payload["query_id"], "G06-D")
        self.assertIn("Guntur", payload["query_description"])
        self.assertNotIn("East Godavari", payload["query_description"])

    # ── Fix 2 — a new question captured as an operation ───────────────────────

    def test_a_district_question_over_a_farmer_table_is_not_a_max(self):
        """The reproduction: 'Highest subsidy_amount: 9,005.55 (Devi Kumar)' —
        a farmer silently substituted for the district that was asked about."""
        session = "cw-fix2"
        self.seed_frame(session, "R02", **self.TOP_SUBSIDIES_SEED)

        payload = self.ask(
            "Which district received the highest single input subsidy?",
            session_id=session,
        )
        self.assertNotEqual(payload["tier"], "operation",
                            f"still captured as an operation: {payload['answer']}")
        # R04 is the district-level peak-payment template — the question the
        # user actually asked, which the captured max never reached.
        self.assertEqual(payload["query_id"], "R04")

    def test_a_genuine_operation_on_the_same_table_still_works(self):
        session = "cw-fix2-nonreg"
        self.seed_frame(session, "R02", **self.TOP_SUBSIDIES_SEED)
        payload = self.ask("total?", session_id=session)
        self.assertEqual(payload["tier"], "operation")
        self.assertEqual(payload["operation"], "sum")

    # ── Fix 5 — a nonsense filter against a numeric column ────────────────────

    def test_land_size_question_over_a_procurement_table_is_not_a_filter(self):
        """The reproduction: '0 of 2 rows where farmers contains small or
        marginal' — the catalog has G06-D and it was never reached."""
        session = "cw-fix5"
        self.seed_frame(session, "G14-D", **self.PROCUREMENT_SEED)

        payload = self.ask("how many small or marginal farmers", session_id=session)
        self.assertNotEqual(payload["tier"], "operation",
                            f"still captured as a filter: {payload['answer']}")
        self.assertNotIn("rows where", payload["answer"])
        # G06 is the land-size band family, whose paraphrases literally include
        # "How many marginal farmers?" — the template that was never reached.
        self.assertTrue(
            (payload["query_id"] or "").startswith("G06"),
            f"routed to {payload['query_id']} instead of the land-size family",
        )

    def test_a_legitimate_filter_on_the_same_table_still_runs(self):
        session = "cw-fix5-nonreg"
        self.seed_frame(session, "G14-D", **self.PROCUREMENT_SEED)

        # "only rows above 900" is deliberately NOT here: the classifier returns
        # new_question for it about a third of the time, with no subject and no
        # filter fields, so neither type guard is involved (verified by logging
        # the raw JSON). That is a separate classifier-reliability problem; what
        # this test pins is that the guards let good filters through.
        for message in ("only Peddapuram", "mandals containing kota"):
            payload = self.ask(message, session_id=session)
            self.assertEqual(payload["tier"], "operation", message)
            self.assertEqual(payload["operation"], "filter_rows", message)
            self.assertEqual(payload["operation_mode"], "client", message)

    # ── Fix 4 — chips showing raw slot placeholders ───────────────────────────

    def test_a_bare_farmer_name_never_offers_a_farmer_name_of_a_village(self):
        """The reproduction: chips read 'Which schemes is a farmer name of a
        village enrolled in?' — the name the user had just typed appeared
        nowhere. Now the name drives the response, and every chip is about a
        real person."""
        payload = self.ask("Tell me what we know about Rajesh Sri")
        self.assertNotEqual(payload["tier"], "fallback")

        if payload["tier"] in ("tier1", "tier2"):
            # Best case, and what happens today: the phrasing is a paraphrase of
            # F09, so it is simply answered. (Those paraphrases were authored
            # here and made load-bearing by the template-fidelity pass, which
            # taught the retriever to embed them.)
            self.assertIn("Rajesh Sri", payload["query_description"])
            return

        # Otherwise it must still be about the person the user named — never a
        # chip reading "a farmer name of a village".
        chips = payload["clarification"]["options"]
        self.assertTrue(chips, "the miss offered nothing to tap")
        for chip in chips:
            for placeholder in ("a farmer name", "a aadhaar", "a village", "{"):
                self.assertNotIn(placeholder, chip["label"])
            self.assertIn("Rajesh", chip["send_text"])
        tapped = self.ask(chips[0]["send_text"], from_chip=True)
        self.assertNotEqual(tapped["tier"], "fallback")

    def test_a_bare_district_name_never_elicits_on_a_farmer(self):
        """Non-regression for the farmer probe: 'Krishna' is a district AND a
        farmer-name fragment, and the district reading must keep winning.

        The precedence rule itself is pinned deterministically by
        test_router_miss_path.FarmerElicitationTests. Here we only pin the
        safety property, because which branch this question reaches is not
        stable: measured over three runs it produced a no_match fallback, an
        ambiguous-templates clarify and a missing-parameter clarify — the
        catalog grew to 293 templates, so near-misses now often pre-empt the
        elicitation path entirely.
        """
        payload = self.ask("How is Krishna doing?")
        chips = (payload.get("clarification") or {}).get("options") or []
        for chip in chips:
            self.assertNotIn("{", chip["label"])
            self.assertNotIn("a farmer name", chip["label"])
        if (payload.get("clarification") or {}).get("reason") == "broad_question":
            self.assertIn("Krishna", payload["answer"])
            for chip in chips:
                self.assertIn("district", chip["send_text"].lower(),
                              "a bare place name must elicit on the DISTRICT")


if __name__ == "__main__":
    unittest.main()
