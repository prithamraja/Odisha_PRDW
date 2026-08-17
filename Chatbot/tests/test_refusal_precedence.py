"""A documented refusal has to be reachable (D28.5, WP-4c T2c).

THE DEFECT, from WP-4's three replays. 15 of the 19 known-unanswerable gold rows
served their `UNANSWERABLE_CATALOG` entry cleanly. Four did not:

  BEN-001  3/3  "I couldn't match that exactly. Did you mean one of these?" —
                offering three Individual Household Latrine templates
  BEN-003  2/3  the same; 1/3 the broad-question elicitation ("What would you
                like to know about Khordha?")
  BEN-010  2/3  the broad-question elicitation; 1/3 the generic miss
  PLN-022  2/3  ANSWERED, with PLN-020 — whose own caveat reads
                "pending_approvals is 0 everywhere because approval_date is
                always populated". A table of zeros, served as the answer to
                "which blocks are consistently delayed in GPDP approvals".

THE MECHANISM. Whether a refusal is reached rests entirely on one LLM judgement,
and the reranker's rule set resolves against it: rule 9 says "if one of those
matches the user's intent, return it", rule 10 says "if NONE of the candidates
can answer the query exactly, return no_match". A candidate captioned CANNOT BE
ANSWERED satisfies rule 10 by construction, and rule 10 wins — which is why the
failure is 3/3 stable rather than a wobble. Both zone branches then rendered the
same entry as an ordinary question chip: a tappable suggestion of a question the
database cannot answer, whose tap reproduces the identical clarification.

THE FIX IS DETERMINISTIC, because retrieval rank is not a judgement call. If the
closest entry in the whole index to what the officer typed is the catalogue's own
statement that this question has no answer, that statement IS the answer.

No API key and no network: the retriever and reranker are stubs.
"""
import time
import unittest
from types import SimpleNamespace

from query_router import router
from query_router.config import CLARIFY_SCORE_MARGIN, NO_MATCH_LOWER_THRESHOLD
from query_router.models import RouteTier
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG

REFUSAL = "BEN-001"
NEAR_MISS = "PLN-020"           # a real template, and the one PLN-022 lost to
REFUSAL_Q = UNANSWERABLE_CATALOG[REFUSAL]["question"]


def _scored(*rows):
    """[(query_id, question, score)] as `retrieve_scored` returns it."""
    return [(qid, question, score) for qid, question, score in rows]


TOP_REFUSAL = _scored(
    (REFUSAL, REFUSAL_Q, 0.72),
    (NEAR_MISS, "Which Blocks have the highest number of pending GPDP "
                "approvals in {date_range}?", 0.55),
)


class RefusalPrecedenceTests(unittest.TestCase):
    """The rule, in isolation."""

    def test_a_rank_0_refusal_beats_a_no_match_verdict(self):
        """The alternative is a generic decline, so this can only replace
        "I failed" with "here is why this cannot be answered"."""
        self.assertEqual(
            router._refusal_precedence(TOP_REFUSAL, "no_match"), REFUSAL)
        self.assertEqual(router._refusal_precedence(TOP_REFUSAL, None), REFUSAL)

    def test_a_rank_0_refusal_beats_a_separable_rerank_pick(self):
        """PLN-022's shape: the reranker answered with a near-miss that measures
        something else, and retrieval had the refusal well clear of it."""
        self.assertEqual(
            router._refusal_precedence(TOP_REFUSAL, NEAR_MISS), REFUSAL)

    def test_a_near_tie_does_NOT_overrule_the_reranker(self):
        """Inside `CLARIFY_SCORE_MARGIN` retrieval cannot separate the two, and
        overruling the semantic layer on noise is exactly the embedding-order
        bias the reranker exists to correct."""
        tie = _scored((REFUSAL, REFUSAL_Q, 0.72),
                      (NEAR_MISS, "…?", 0.72 - CLARIFY_SCORE_MARGIN / 2))
        self.assertIsNone(router._refusal_precedence(tie, NEAR_MISS))
        # …but with nothing picked, the margin is irrelevant.
        self.assertEqual(router._refusal_precedence(tie, "no_match"), REFUSAL)

    def test_a_refusal_below_the_no_match_floor_is_not_a_match(self):
        """Below the floor nothing is a match, including this. The miss path,
        which offers the nearest questions, is the honest answer."""
        weak = _scored((REFUSAL, REFUSAL_Q, NO_MATCH_LOWER_THRESHOLD - 0.01))
        self.assertIsNone(router._refusal_precedence(weak, "no_match"))

    def test_a_refusal_below_rank_0_is_not_evidence(self):
        """The unanswerables are 30 of 376 index entries, so one is near almost
        anything. "Somewhere in the top 30" must not refuse a question."""
        buried = _scored((NEAR_MISS, "…?", 0.80), (REFUSAL, REFUSAL_Q, 0.79))
        self.assertIsNone(router._refusal_precedence(buried, NEAR_MISS))
        self.assertIsNone(router._refusal_precedence(buried, "no_match"))

    def test_the_reranker_picking_it_needs_no_override(self):
        self.assertIsNone(router._refusal_precedence(TOP_REFUSAL, REFUSAL))

    def test_an_answerable_top_hit_is_never_touched(self):
        ordinary = _scored((NEAR_MISS, "…?", 0.80))
        self.assertIsNone(router._refusal_precedence(ordinary, NEAR_MISS))

    def test_nothing_retrieved_is_handled(self):
        self.assertIsNone(router._refusal_precedence([], "no_match"))


class RefusalChipTests(unittest.TestCase):
    """"Reachable as a chip" — the other half of the brief."""

    def test_a_refusal_chip_says_what_it_is(self):
        chips = router._reading_chips(TOP_REFUSAL, 3)
        by_send = {c.send_text: c.label for c in chips}
        self.assertTrue(any(label.startswith("Why I can't answer:")
                            for label in by_send.values()),
                        "an unanswerable offered as a plain suggestion invites a "
                        "tap on a question the database cannot answer")

    def test_an_answerable_chip_is_unchanged(self):
        chips = router._reading_chips(TOP_REFUSAL, 3)
        answerable = [c for c in chips if not c.label.startswith("Why I can't")]
        self.assertTrue(answerable)
        for chip in answerable:
            self.assertEqual(chip.label, chip.send_text)

    def test_the_chip_sends_the_entrys_own_question(self):
        """Which is what closes the loop: that text retrieves at rank 0, so
        `_refusal_precedence` serves the refusal with no LLM involved."""
        chips = router._reading_chips(TOP_REFUSAL, 3)
        refusal_chip = next(c for c in chips
                            if c.label.startswith("Why I can't answer:"))
        self.assertEqual(refusal_chip.send_text, REFUSAL_Q)
        self.assertNotIn("{", refusal_chip.send_text)

    def test_placeholders_are_still_filled_in(self):
        chips = router._reading_chips(TOP_REFUSAL, 3, {"date_range": "2024-2025"})
        for chip in chips:
            self.assertNotIn("{", chip.send_text)
        self.assertTrue(any("2024-2025" in c.send_text for c in chips))


class _StubRetriever:
    def __init__(self, scored):
        self._scored = scored

    def retrieve_scored(self, query, k):
        return list(self._scored)


class RouteVectorRefusalTests(unittest.TestCase):
    """The rule where it lives: through `_route_vector`, with the two LLM calls
    stubbed out. This is the end-to-end shape of the four failing gold rows."""

    def setUp(self):
        self._real_rerank = router.rerank

    def tearDown(self):
        router.rerank = self._real_rerank

    def _route(self, scored, rerank_verdict, near_misses=()):
        router.rerank = lambda query, candidates, client: (rerank_verdict,
                                                          list(near_misses))
        return router._route_vector(
            "How many beneficiaries received benefits under Swachh Bharat "
            "Mission in Andhrua during 2024-25?",
            "normalized", time.monotonic(),
            validator=SimpleNamespace(
                validate=lambda *a, **k: (_ for _ in ()).throw(ValueError()),
                fiscal_years=lambda: ["2024-2025"]),
            openai_client=object(), retriever=_StubRetriever(scored),
            cache_conn=None, dashboard_results={},
            template_map={NEAR_MISS: {"param_slots": [],
                                      "abstract_question": "…?"}},
            dashboard_questions={}, start_date=None, end_date=None,
        )

    def test_BEN_001s_shape_now_serves_the_documented_reason(self):
        """3/3 in WP-4 this was "I couldn't match that exactly" over three IHHL
        templates. The workbook's own reason exists and was never shown."""
        result = self._route(TOP_REFUSAL, "no_match", [NEAR_MISS])
        self.assertEqual(result.query_id, REFUSAL)
        self.assertIsNone(result.result,
                          "an honest refusal has NO result set — not an empty "
                          "one (the coupling grade_full_eval asserts)")
        self.assertIn(UNANSWERABLE_CATALOG[REFUSAL]["reason"][:40],
                      result.fallback_message or "",
                      "the workbook's own reason, verbatim")

    def test_PLN_022s_shape_is_not_answered_with_a_near_miss(self):
        """The reranker picked a template; retrieval had the refusal clear of
        it. Serving the near-miss meant serving a table of zeros."""
        result = self._route(TOP_REFUSAL, NEAR_MISS)
        self.assertEqual(result.query_id, REFUSAL)
        self.assertNotEqual(result.tier, RouteTier.TIER2_TEMPLATE)

    def test_an_ambiguous_zone_asks_rather_than_refusing(self):
        """The ambiguous zone IS "the top two are inside the margin", so a
        rank-0 refusal has out-matched nothing. It becomes a labelled reading."""
        ambiguous = _scored(
            (REFUSAL, REFUSAL_Q, 0.40),
            (NEAR_MISS, "…?", 0.40 - CLARIFY_SCORE_MARGIN / 2),
        )
        result = self._route(ambiguous, "no_match")
        self.assertEqual(result.tier, RouteTier.CLARIFY)
        self.assertEqual(result.clarification.reason, "ambiguous_templates")
        self.assertTrue(any(c.label.startswith("Why I can't answer:")
                            for c in result.clarification.options))


if __name__ == "__main__":
    unittest.main()
