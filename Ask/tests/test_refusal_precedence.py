"""A refusal is served only when the reranker picks it (WP-6g T1b).

WP-4c's "refusal wins" rule (D28.5, `_refusal_precedence`) overrode the reranker
in three cases: a no-match verdict with a refusal at search rank 0; a no-match
verdict naming a refusal among the near misses; and an answerable pick with a
rank-0 refusal ahead by more than `CLARIFY_SCORE_MARGIN`. Since WP-4c it only
misfired — the last time on a tester's "Barimunda planned activities 2025-2026 —
count?", where the reranker picked PLN-024 correctly and case 3 served the
ALR-007 refusal instead. The reranker call logs show every correct refusal in
WP-6e (16) and WP-6f (10) was the reranker's own pick; the rule forced one, and
it was wrong. Operator ruling 2026-09-29: "yes remove the rule."

These tests pin the behaviour that replaces it:
  - a reranker pick stands, even when a refusal is search rank 0 and far ahead;
  - a no-match verdict with a refusal at rank 0 asks, the refusal labelled;
  - a refusal the reranker picks is served.

No API key and no network: the retriever and reranker are stubs. BEN-010 is one
of the fifteen entries that are still refusals after WP-6f (M7).
"""
import time
import unittest
from types import SimpleNamespace

from query_router import router
from query_router.config import CLARIFY_SCORE_MARGIN
from query_router.models import RouteTier
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG

REFUSAL = "BEN-010"             # still a refusal after WP-6f M7
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


class RefusalRetrievalSurfaceTests(unittest.TestCase):
    """The actual root cause: a refusal that is not RETRIEVED cannot be reached
    by anything downstream, however good the reranker's instructions are.

    Measured in WP-4c against the gold questions that are almost word-for-word
    the entries' own, over a 30-candidate window on a 376-entry index:

        BEN-001  rank 51 of 376   BEN-003  rank 64   PLN-022  rank 46

    all outside the window, so the reranker never saw them. The cause is an
    asymmetry of index surface, not of wording quality: a template carries 6.1
    vectors on average (abstract question, example question with real values, one
    scope line per tier — D2), while the 13 Dropped rows carried exactly one, and
    that one is mostly the workbook's "a given Scheme in a given GP Name during a
    given Plan Year" filler. `tools/derive_catalog.scope_free_question` adds the
    missing shape. After: rank 1, rank 12, rank 0.
    """

    def test_every_unanswerable_has_more_than_one_index_vector(self):
        """One vector of workbook prose is what put BEN-001 at rank 51."""
        thin = [qid for qid, e in UNANSWERABLE_CATALOG.items()
                if not (e.get("paraphrases") or [])]
        self.assertEqual(thin, [], "these entries have a single index vector, "
                                   "which is how a documented refusal becomes "
                                   "unreachable")

    def test_the_scope_free_line_drops_the_place_and_the_period(self):
        from tools.derive_catalog import scope_free_question
        self.assertEqual(
            scope_free_question("How many beneficiaries received benefits under "
                                "a given Scheme in a given GP Name during a "
                                "given Plan Year?"),
            "How many beneficiaries received benefits under a given Scheme?")

    def test_it_keeps_the_measure_and_the_non_geographic_parameters(self):
        """Only geography and period go. The SCHEME is the subject of BEN-001 and
        removing it would leave a question about nothing."""
        from tools.derive_catalog import scope_free_question
        stripped = scope_free_question(
            "Which assets in a given Block have not advanced a stage in the "
            "last a given Threshold days?")
        self.assertIn("Threshold days", stripped)
        self.assertNotIn("Block", stripped)

    def test_a_question_naming_no_parameter_gets_no_second_line(self):
        """PLN-041 says "over the last five years" in words — there is no second
        shape of it, and inventing one would be padding the index."""
        from tools.derive_catalog import scope_free_question
        self.assertIsNone(scope_free_question(
            "Which themes have remained consistently among the top priorities "
            "over the last five years?"))

    def test_paraphrases_are_deduplicated_against_the_question(self):
        for qid, entry in UNANSWERABLE_CATALOG.items():
            with self.subTest(qid=qid):
                texts = [entry["question"], *entry["paraphrases"]]
                lowered = [t.strip().lower() for t in texts]
                self.assertEqual(len(lowered), len(set(lowered)),
                                 "a duplicate vector is index weight for nothing")


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
        """Which is what closes the loop: the reranker picks the entry's own
        question on the way back in, and the refusal is served (WP-6g T1b)."""
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

    def retrieve_with_examples(self, query, k, per_candidate):
        return list(self._scored), {}


class RouteVectorRefusalTests(unittest.TestCase):
    """Through `_route_vector`, with the two LLM calls stubbed out."""

    def setUp(self):
        self._real_rerank = router.rerank

    def tearDown(self):
        router.rerank = self._real_rerank

    def _route(self, scored, rerank_verdict, near_misses=()):
        router.rerank = lambda query, candidates, client, examples=None: (
            rerank_verdict, list(near_misses))
        return router._route_vector(
            "How many beneficiaries are recorded under each pension scheme in "
            "Attabira for 2024-25?",
            "normalized", time.monotonic(),
            validator=SimpleNamespace(
                validate=lambda *a, **k: (_ for _ in ()).throw(ValueError()),
                fiscal_years=lambda: ["2024-2025"]),
            openai_client=object(), retriever=_StubRetriever(scored),
            cache_conn=None, dashboard_results={},
            template_map={NEAR_MISS: {"param_slots": [],
                                      "abstract_question": "…?",
                                      "sql_template": "SELECT 1 AS n"}},
            dashboard_questions={}, start_date=None, end_date=None,
        )

    def test_the_rule_is_gone(self):
        self.assertFalse(hasattr(router, "_refusal_precedence"))

    def test_a_reranker_pick_stands_against_a_rank_0_refusal_far_ahead(self):
        """Case 3 of the old rule — the Barimunda shape: the reranker picked the
        answerable template and a refusal was search rank 0, well clear of it.
        The pick is served."""
        far_ahead = _scored(
            (REFUSAL, REFUSAL_Q, 0.80),
            (NEAR_MISS, "…?", 0.80 - 3 * CLARIFY_SCORE_MARGIN),
        )
        served = []
        real = router._serve_query_id
        router._serve_query_id = lambda qid, *a, **k: served.append(qid) or "served"
        try:
            result = self._route(far_ahead, NEAR_MISS)
        finally:
            router._serve_query_id = real
        self.assertEqual(served, [NEAR_MISS])
        self.assertEqual(result, "served")

    def test_a_no_match_with_a_rank_0_refusal_asks_with_the_refusal_labelled(self):
        """Cases 1 and 2 of the old rule: the reranker declined and named the
        refusal as a near miss. Now it is a labelled chip, not the answer."""
        result = self._route(TOP_REFUSAL, "no_match", [REFUSAL, NEAR_MISS])
        self.assertEqual(result.tier, RouteTier.CLARIFY)
        self.assertEqual(result.clarification.reason, "ambiguous_templates")
        labels = [c.label for c in result.clarification.options]
        self.assertTrue(labels[0].startswith("Why I can't answer:"), labels)
        self.assertEqual(result.clarification.options[0].send_text, REFUSAL_Q)
        self.assertNotEqual(result.query_id, REFUSAL)

    def test_a_refusal_the_reranker_picks_is_served(self):
        result = self._route(TOP_REFUSAL, REFUSAL)
        self.assertEqual(result.query_id, REFUSAL)
        self.assertIsNone(result.result,
                          "an honest refusal has NO result set — not an empty "
                          "one (the coupling grade_full_eval asserts)")
        self.assertIn(UNANSWERABLE_CATALOG[REFUSAL]["reason"][:40],
                      result.fallback_message or "",
                      "the catalogue's own reason, verbatim")

    def test_a_refusal_below_rank_0_that_the_reranker_picks_is_served(self):
        buried = _scored((NEAR_MISS, "…?", 0.63), (REFUSAL, REFUSAL_Q, 0.60))
        self.assertEqual(self._route(buried, REFUSAL).query_id, REFUSAL)

    def test_an_ambiguous_zone_asks_rather_than_refusing(self):
        """The zone is decided before the reranker; a rank-0 refusal there is a
        labelled reading, as before."""
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
