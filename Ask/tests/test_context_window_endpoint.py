"""End-to-end proof for the conversation-context defects.

The unit tests pin each decision in isolation; these pin the WIRING — that a
real conversation through /query no longer loses the question the user asked.
Each test names the reproduction it closes.

PORTED FROM AP (WP-4 T4e), AND SPLIT IN TWO
    The AP file was 18 tests over a PM-KISAN farmer roster (`Venkateswarlu G`,
    village `Bathalapalli`, crop `Paddy`) against query_ids — `Q125`, `Q098`,
    `G14-D`, `R02` — that do not exist in this catalogue. Every one of them
    would have errored on a lookup, so they were dead weight rather than
    coverage.

    They are re-authored here on PR&DW ids, in two classes:

      PendingResolutionTests   NO NETWORK. The pending-clarification machinery
                               is deterministic — a closed vocabulary and
                               registry lookups, no LLM (see pending_resolver's
                               docstring) — so the pause is SEEDED and the
                               reply resolved directly. These run in the normal
                               suite, which is the point: the AP versions could
                               only ever run on a machine with a key and a
                               parquet drop, so in practice they never ran.

      ConversationEndpointTests  OPT-IN live routing, the
                               test_followup_fragment.py pattern. Scope
                               inheritance and the operation type-guards need
                               the classifier, and the classifier costs money.

WHAT WAS RETIRED, AND WHY
    · The FARMER-DISAMBIGUATION group (5 tests). Its PR&DW analogue is the D4
      GP-name collision, which the 20-GP sample cannot exercise: every loaded GP
      name is unique, which is exactly why WP-2 wrote the collision test with
      SYNTHETIC duplicates. Covered deterministically by test_gp_collisions.py.
      The collision that IS live in the sample is the TIER collision (Laxmipur
      is both a block and a GP), and that has its own coverage in
      test_followup_fragment.py.
    · The "bare farmer name" chip tests. PR&DW's analogue is elicitation on a
      bare place name, pinned deterministically in test_router_miss_path.py —
      and the AP versions already admitted they were unstable across runs.

THE PATH LANDMINE IS GONE (WP-1 report §7.2). This file used to compute
`parents[1].parents[1] / "RTGS_Data" / "flat"`, which since the Chatbot/
flattening resolves OUTSIDE this repo — a stray RTGS_Data/ landing in the shared
Drive parent would have silently pointed these tests at another project's data.
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
_LIVE_SKIP = None
if not _LIVE:
    _LIVE_SKIP = ("live routing is opt-in: set PRDW_LIVE_ROUTING=1 (costs money, "
                  "requires OPENAI_API_KEY)")
elif not _DB_PATH.exists():
    _LIVE_SKIP = f"no sample database at {_DB_PATH}"
elif not os.environ.get("OPENAI_API_KEY"):
    _LIVE_SKIP = "OPENAI_API_KEY not set — the router is disabled without it"

# SCH-006 asks which GPs planned nothing under a named scheme. Its `$scheme` is
# REQUIRED — the SQL has no `IS NULL OR` guard, because without the scheme there
# is no question — so it is the natural place to pause for a slot value, which
# is what these tests need a pause on.
PENDING_ID = "SCH-006"
PENDING_SLOT = "scheme"


@unittest.skipIf(not _DB_PATH.exists(), f"no sample database at {_DB_PATH}")
class PendingResolutionTests(unittest.TestCase):
    """A paused question survives the reply — deterministically, no network.

    The reproduction, transplanted: the app asks "for which scheme?", the user
    answers, and the ANSWER gets routed as if it were a fresh question. The
    original question is gone and what comes back looks entirely normal.
    """

    @classmethod
    def setUpClass(cls):
        from db_factory import open_analytical_db
        from query_router.entity_validator import EntityValidator
        from query_router.template_catalog import TEMPLATE_CATALOG

        cls.adapter = open_analytical_db(_DB_PATH)
        cls.validator = EntityValidator(cls.adapter)
        cls.templates = TEMPLATE_CATALOG
        cls.schemes = cls.validator.registry_values("scheme")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.adapter.close()
        except Exception:                                    # pragma: no cover
            pass

    def _pending(self):
        from query_router.models import PendingClarification
        return PendingClarification(
            query_id=PENDING_ID, missing_slot=PENDING_SLOT, slot_type="scheme",
            filled={"date_range": "2024-2025"},
            original_query="Which GPs planned nothing under a scheme in 2024-25?",
        )

    def _resolve(self, reply: str):
        from query_router.pending_resolver import resolve_pending_reply
        return resolve_pending_reply(reply, self._pending(), self.validator)

    def test_the_slot_this_test_leans_on_is_still_required(self):
        """If SCH-006's `$scheme` ever became optional there would be no pause
        to resolve, and every test below would pass vacuously."""
        slot = next(s for s in self.templates[PENDING_ID]["param_slots"]
                    if s["name"] == PENDING_SLOT)
        self.assertFalse(slot.get("optional"))

    def test_a_named_value_resumes_the_paused_question(self):
        from query_router.pending_resolver import RESUME
        scheme = self.schemes[0]
        resolution = self._resolve(scheme)
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, scheme)

    def test_a_scope_widening_reply_is_not_routed_as_a_new_question(self):
        """"all schemes" is an answer a slot cannot hold. The AP defect: it
        routed alone and confidently served an unrelated template."""
        from query_router.pending_resolver import FALLTHROUGH, RESUME
        for reply in ("all schemes", "all", "doesn't matter"):
            with self.subTest(reply=reply):
                resolution = self._resolve(reply)
                self.assertNotEqual(
                    resolution.kind, FALLTHROUGH,
                    "a scope-widening reply must be understood, not re-routed")
                if resolution.kind == RESUME:
                    self.assertIsNone(resolution.value,
                                      "widening binds NULL, not a scheme named 'all'")

    def test_an_unusable_reply_is_asked_again_before_it_is_let_go(self):
        """One extra turn, never a loop — and the re-ask must still be about the
        question that was paused."""
        from query_router.pending_resolver import REASK
        resolution = self._resolve("top 25")
        self.assertEqual(resolution.kind, REASK)
        self.assertIsNotNone(resolution.pending,
                             "a re-ask must carry the pause forward or the "
                             "question is lost on the next message")
        self.assertEqual(resolution.pending.query_id, PENDING_ID)
        self.assertTrue(resolution.options, "the re-ask offered nothing to tap")

    def test_the_escape_chip_sends_the_users_own_words_back(self):
        """The way out of the retry: tapping it means "no, I meant that as a new
        question", so the chip has to carry the message verbatim."""
        resolution = self._resolve("top 25")
        self.assertIn("top 25",
                      [chip.send_text for chip in resolution.options])

    def test_a_repeated_unusable_reply_is_taken_at_face_value(self):
        """Said twice, it is a new question — the retry may not repeat."""
        from query_router.pending_resolver import FALLTHROUGH, REASK
        pending = self._pending()
        pending.retried = True
        from query_router.pending_resolver import resolve_pending_reply
        resolution = resolve_pending_reply("top 25", pending, self.validator)
        self.assertNotEqual(resolution.kind, REASK,
                            "one extra turn, never a loop")
        self.assertEqual(resolution.kind, FALLTHROUGH)


@unittest.skipIf(_LIVE_SKIP is not None, _LIVE_SKIP or "")
class ConversationEndpointTests(unittest.TestCase):
    """The parts that genuinely need the classifier, through the real /query."""

    # A district-scoped frame: the scope a following question should inherit.
    SCOPED_FRAME = ("PLN-004", {"district_name": "Khordha",
                                "date_range": "2024-2025"})

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import main

        cls.main = main
        cls._client_ctx = TestClient(main.app)
        cls.client = cls._client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_ctx.__exit__(None, None, None)

    def ask(self, message: str, **body) -> dict:
        response = self.client.post("/query", json={"message": message, **body})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def seed_frame(self, session: str) -> dict:
        """Put a real answered question on screen by asking one."""
        self.main._context_store.reset(session)
        template_id, params = self.SCOPED_FRAME
        payload = self.ask(
            "What percentage of Gram Panchayats in Khordha uploaded their "
            "GPDP in 2024-25?",
            session_id=session, reset_context=True,
        )
        self.assertEqual(payload["tier"], "tier2", payload.get("answer"))
        return payload

    # ── Frame scope inheritance ───────────────────────────────────────────────

    def test_a_new_question_inherits_the_scope_and_says_so(self):
        """The reproduction: asked inside a conversation about Khordha, a new
        question was answered STATE-WIDE with nothing saying so. Narrowing
        silently would trade one invisible mismatch for another, so the carry
        is named and the chips lead with the way out.

        WHERE IT IS NAMED MOVED. This used to assert the sentence "…carried
        over from your previous question" inside `answer`; that prose is
        retired (see query_router/interpretation.py) because the answer body is
        what an officer copies into a report. The same fact is now the
        `interpretation` field, which every binding path stamps rather than
        this one alone. The undo chip below is unchanged.
        """
        session = "cw-scope"
        self.seed_frame(session)

        payload = self.ask("how much was actually spent?", session_id=session)
        self.assertEqual(payload["tier"], "tier2", payload.get("answer"))
        self.assertIn("Khordha", payload["query_description"] or "")
        self.assertNotIn("carried over", payload["answer"],
                         "the scope note belongs beside the answer, not in it")
        self.assertEqual(payload["interpretation"]["kind"], "scope_inherited")
        self.assertIn("Khordha", payload["interpretation"]["detail"] or "")
        self.assertTrue(payload["interpretation"]["anchor_question"])

        undo = (payload["suggestions"] or [])[0]
        self.assertIn("state-wide", undo["label"].lower())
        back = self.ask(undo["send_text"], session_id=session, from_chip=True)
        self.assertNotIn("Khordha", back["query_description"] or "",
                         "the undo chip did not undo the narrowing")

    def test_a_question_naming_its_own_scope_keeps_it(self):
        session = "cw-scope-own"
        self.seed_frame(session)
        payload = self.ask("how much was actually spent in Ganjam district?",
                           session_id=session)
        description = payload["query_description"] or ""
        self.assertIn("Ganjam", description)
        self.assertNotIn("Khordha", description)

    # ── A new question captured as an operation ───────────────────────────────

    def test_a_new_subject_over_the_table_on_screen_is_not_an_operation(self):
        """The reproduction shape: a question about a DIFFERENT measure gets
        captured as a max/filter over the rows already on screen, and a number
        from the wrong column is presented as the answer."""
        session = "cw-op-guard"
        self.seed_frame(session)
        payload = self.ask(
            "which activities have the highest expenditure in 2024-25?",
            session_id=session)
        self.assertNotEqual(
            payload["tier"], "operation",
            f"captured as an operation over the GPDP table: {payload['answer']}")

    def test_a_genuine_operation_on_the_same_table_still_works(self):
        session = "cw-op-nonreg"
        self.seed_frame(session)
        payload = self.ask("total?", session_id=session)
        self.assertEqual(payload["tier"], "operation")
        self.assertEqual(payload["operation"], "sum")

    # ── Chips never leak a slot placeholder ───────────────────────────────────

    def test_no_chip_anywhere_shows_a_raw_placeholder(self):
        """The AP reproduction read "Which schemes is a farmer name of a village
        enrolled in?". T2(d) is the answer-side of the same rule; this is the
        chip side, on the live path."""
        for message in ("How is Khordha doing?",
                        "Tell me about Andhrua",
                        "GPDP status?"):
            with self.subTest(message=message):
                payload = self.ask(message)
                chips = (payload.get("clarification") or {}).get("options") or []
                chips += payload.get("suggestions") or []
                for chip in chips:
                    self.assertNotIn("{", chip["label"])
                    self.assertNotIn("{", chip["send_text"])


if __name__ == "__main__":
    unittest.main()
