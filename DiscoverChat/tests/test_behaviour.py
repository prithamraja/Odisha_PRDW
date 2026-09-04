# -*- coding: utf-8 -*-
"""The conversational behaviours — no model calls, no network.

    python -m unittest DiscoverChat.tests.test_behaviour

Everything here runs with `allow_model=False`, which is not a shortcut: the
behaviours the brief gates on are the ones that must not depend on a model
flipping between identical replays.
"""
import unittest

from DiscoverChat import assemble, causal_gate, checks, classifier
from DiscoverChat.retrieval import Retriever
from DiscoverChat.session import SessionStore


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever()
        cls.assembler = assemble.Assembler(cls.retriever, allow_model=False)


class RoutingTests(_Base):
    def test_number_lookup_declines_and_names_ask(self):
        answer = self.assembler.answer("How much was spent in Khordha?")
        self.assertEqual(answer.move, classifier.LOOKUP)
        self.assertIn("Ask", answer.text)
        self.assertEqual(answer.findings, [])

    def test_the_decline_carries_no_figure_of_its_own(self):
        answer = self.assembler.answer("How many activities are ongoing?")
        self.assertEqual(checks.numerals(answer.text.replace(answer.stamp, "")), [])

    def test_why_is_reframed_not_answered(self):
        answer = self.assembler.answer("Why is spending low in Chikilli?")
        self.assertEqual(answer.move, classifier.WHY)
        self.assertIn("cannot establish what causes what", answer.text)

    def test_why_beats_lookup_when_a_question_looks_like_both(self):
        """'Why is so much unspent' contains quantity wording. A why-question
        misrouted to the Ask decline loses the D41 reframe entirely."""
        routing = classifier.rule_route("Why is so much money unspent?")
        self.assertEqual(routing.move, classifier.WHY)

    def test_routing_is_logged_with_its_source(self):
        answer = self.assembler.answer("How much was spent?")
        self.assertIn(answer.routing["source"], ("rule", "model", "default"))
        self.assertTrue(answer.routing["reason"])


class FloorTests(_Base):
    def test_out_of_scope_says_nothing_on_this(self):
        answer = self.assembler.answer(
            "What is the price of onions in Cuttack market?")
        self.assertEqual(answer.findings, [])
        self.assertIn("nothing on this", answer.text)

    def test_the_floor_is_never_relaxed(self):
        result = self.retriever.score(
            "What is the rainfall forecast for Koraput next week?")
        for hit in result.hits:
            self.assertGreaterEqual(hit.score, result.threshold)


class RenderingTests(_Base):
    def test_finding_sentences_are_verbatim(self):
        """The shown sentence is the corpus's, with only its column names
        translated (WP-D6 D6.1).

        The numeral assertion is what keeps this strong. The rendered string is
        no longer byte-identical to the stored one -- the glossary swaps
        `fund_sanctioned_total` for "sanctioned amount" -- so containment alone
        would no longer pin the text to the corpus. Requiring the numerals to
        match exactly, in order, means no substitution can alter a figure or
        reorder two clauses so their figures swap.
        """
        from DiscoverChat import checks
        answer = self.assembler.answer("How is Chikilli doing?")
        self.assertTrue(answer.findings)
        for finding in answer.findings:
            self.assertIn(finding.display_sentence(), answer.text)
            self.assertEqual(checks.numerals(finding.display_sentence()),
                             checks.numerals(finding.sentence))

    def test_every_answer_carries_the_run_stamp(self):
        for question in ("How is Chikilli doing?", "How much was spent?",
                         "Why is spending low?", "price of onions"):
            self.assertIn("as of ", self.assembler.answer(question).text)

    def test_unranked_findings_state_their_coverage(self):
        answer = self.assembler.answer("Is spending on track?")
        for finding in answer.findings:
            self.assertIn(finding.coverage_line(), answer.text)

    def test_no_answer_asserts_a_cause(self):
        for question in ("How is Chikilli doing?", "Why is spending low?",
                         "How much was spent?", "Is spending on track?"):
            answer = self.assembler.answer(question)
            self.assertTrue(causal_gate.check(answer.text)["pass"],
                            f"causal wording in the answer to {question!r}")


class CausalGateTests(unittest.TestCase):
    def test_it_catches_causal_claims(self):
        for text in ("The underspend is caused by late sanctions.",
                     "Weak uploads are driving the gap.",
                     "Spending fell because of the backlog.",
                     "This explains the spike.",
                     "Delays result in unspent funds."):
            self.assertFalse(causal_gate.check(text)["pass"], text)

    def test_it_lets_an_honest_limit_through(self):
        for text in ("The analysis cannot say what causes this.",
                     "Nothing here establishes which way this runs.",
                     "These blocks are associated with lower spending."):
            self.assertTrue(causal_gate.check(text)["pass"], text)

    def test_it_offers_the_replacement_vocabulary(self):
        reason = causal_gate.failure_reason(
            causal_gate.check("Late approvals caused the shortfall."))
        self.assertIn("associated with", reason)


class NavigationTests(_Base):
    def test_a_follow_up_walks_to_an_exception_member(self):
        answer = self.assembler.answer("How is Chikilli doing?")
        self.assertTrue(answer.findings)
        exceptions = [e["member_label"] for f in answer.findings
                      for e in f.data.get("exceptions", [])]
        if not exceptions:
            self.skipTest("no exception member on this answer to walk to")
        follow_up = self.assembler.answer(
            f"what about {exceptions[0]}?", anchors=answer.findings,
            previous_question="How is Chikilli doing?")
        self.assertTrue(follow_up.text)

    def test_contextualise_is_self_contained(self):
        from DiscoverChat import navigate
        answer = self.assembler.answer("How is Chikilli doing?")
        rewritten = navigate.contextualise(
            "and elsewhere?", "How is Chikilli doing?", answer.findings)
        self.assertIn("and elsewhere?", rewritten)
        self.assertIn("How is Chikilli doing?", rewritten)
        self.assertGreater(len(rewritten), len("and elsewhere?"))


class SessionTests(unittest.TestCase):
    def test_anchors_survive_a_turn_that_found_nothing(self):
        """A follow-up after a miss must still be able to walk from what is on
        screen; clearing the anchors would strand the officer."""
        class _F:
            id = "1-00001"
        store = SessionStore()
        session = store.get("s1")
        session.record("first", "retrieve", [_F()])
        session.record("miss", "retrieve", [])
        self.assertEqual([f.id for f in session.anchors], ["1-00001"])

    def test_the_store_is_bounded(self):
        store = SessionStore(max_sessions=3)
        for i in range(10):
            store.get(f"s{i}")
        self.assertLessEqual(len(store._sessions), 3)



class JudgeTests(_Base):
    """The judged path's guarantees, tested WITHOUT a model call.

    `judge.select` is exercised through a stubbed `llm.call`, so what is tested
    is the code that decides what a judge's reply is allowed to do — which is
    the part that must hold whatever the model says.
    """

    def _stub(self, reply, finish_reason="stop"):
        from DiscoverChat import llm

        def fake_call(model, prompt, max_completion, purpose, **kw):
            return {"response_text": reply, "finish_reason": finish_reason,
                    "usage": {}}
        return fake_call

    def _pool(self, n=5):
        result = self.retriever.pool("How is Chikilli doing?")
        return [h.finding for h in result.hits[:n]]

    def test_an_id_outside_the_pool_is_dropped_not_resolved(self):
        """The judge selects; it never gets to name a finding it was not shown."""
        from DiscoverChat import judge, llm
        pool = self._pool()
        real = pool[0].id
        original = llm.call
        llm.call = self._stub(
            '{"keep": ["%s", "9-99999"], "note": "n"}' % real)
        try:
            sel = judge.select("q", pool, corpus_size=4239)
        finally:
            llm.call = original
        self.assertEqual(sel.kept_ids, [real])
        self.assertEqual(sel.hallucinated_ids, ["9-99999"])

    def test_an_empty_keep_list_is_a_valid_answer(self):
        from DiscoverChat import judge, llm
        original = llm.call
        llm.call = self._stub('{"keep": [], "note": "nothing bears on this"}')
        try:
            sel = judge.select("q", self._pool(), corpus_size=4239)
        finally:
            llm.call = original
        self.assertEqual(sel.kept_ids, [])
        self.assertEqual(sel.source, "judge")   # a real decision, not a failure

    def test_an_unparseable_reply_falls_back_to_the_threshold(self):
        from DiscoverChat import judge, llm
        original = llm.call
        llm.call = self._stub("I think findings 1 and 2 are good")
        try:
            sel = judge.select("q", self._pool(), corpus_size=4239)
        finally:
            llm.call = original
        self.assertEqual(sel.source, "fallback-threshold")

    def test_a_starved_reply_is_retried_once(self):
        from DiscoverChat import judge, llm
        calls = []
        original = llm.call

        def fake(model, prompt, max_completion, purpose, **kw):
            calls.append(kw.get("attempt"))
            if len(calls) == 1:
                return {"response_text": "", "finish_reason": "length",
                        "usage": {}}
            return {"response_text": '{"keep": [], "note": "ok"}',
                    "finish_reason": "stop", "usage": {}}
        llm.call = fake
        try:
            sel = judge.select("q", self._pool(), corpus_size=4239)
        finally:
            llm.call = original
        self.assertEqual(len(calls), 2)
        self.assertEqual(sel.source, "judge")

    def test_the_pool_never_reaches_below_the_candidate_floor(self):
        from DiscoverChat import config
        result = self.retriever.pool("How is Chikilli doing?")
        self.assertLessEqual(len(result.hits), config.CANDIDATE_POOL)
        for hit in result.hits:
            self.assertGreaterEqual(hit.score, config.CANDIDATE_FLOOR)

    def test_the_pool_collapses_duplicates_before_it_truncates(self):
        """Otherwise pool slots are spent on sentences the reader cannot tell
        apart — on a broad question, hundreds of the top hits are duplicates."""
        result = self.retriever.pool("Is spending on track?")
        sentences = [h.finding.sentence for h in result.hits]
        self.assertEqual(len(sentences), len(set(sentences)))

    def test_allow_model_false_forces_the_threshold_path(self):
        """The offline gate must not silently depend on a judge."""
        from DiscoverChat import assemble
        offline = assemble.Assembler(self.retriever, allow_model=False,
                                     use_judge=True)
        _result, meta = offline._retrieve("How is Chikilli doing?")
        self.assertFalse(meta["used"])


class JudgePromptBindingTests(unittest.TestCase):
    """WP-D9 D9.0 — the prompt is evidence, and the binding says which one."""

    def test_both_instructions_stay_reachable(self):
        """D9.1 reverts by configuration, so "minimal" must not be deleted."""
        from DiscoverChat import judge
        self.assertEqual(sorted(judge.PROMPT_VARIANTS), ["complete", "minimal"])

    def test_the_variants_differ_only_in_the_instruction(self):
        """Everything outside the changed bullets is held identical, so a
        measured difference is attributable to the instruction and not to
        some other drift in the prompt."""
        from DiscoverChat import judge
        minimal = judge.PROMPT_VARIANTS["minimal"]
        complete = judge.PROMPT_VARIANTS["complete"]
        self.assertNotEqual(minimal, complete)
        for shared in ("An officer asked:",
                       "Choose the ones an officer asking this question would "
                       "count as part of the answer.",
                       "Returning nothing is a correct answer",
                       "Reply with JSON only, no other text:"):
            self.assertIn(shared, minimal)
            self.assertIn(shared, complete)
        self.assertIn("Keep the smallest set that fully answers", minimal)
        self.assertNotIn("Keep the smallest set that fully answers", complete)
        self.assertIn("adds distinct information", complete)

    def test_the_hash_is_of_the_template_not_a_rendered_prompt(self):
        """A rendered prompt carries 100 candidates and could never be pinned."""
        from DiscoverChat import judge
        self.assertEqual(judge.prompt_sha256(),
                         judge.prompt_sha256(judge.PROMPT))
        self.assertNotEqual(judge.prompt_sha256(judge.PROMPT_VARIANTS["minimal"]),
                            judge.prompt_sha256(judge.PROMPT_VARIANTS["complete"]))

    def test_the_evidence_records_a_prompt_hash(self):
        """Without it `judge-prompt-evidenced` has nothing to compare against."""
        from DiscoverChat import config
        sha, reference = config.evidenced_judge_prompt()
        self.assertTrue(sha)
        self.assertEqual(len(sha), 64)
        self.assertIn("judge_arm_results.json", reference)


if __name__ == "__main__":
    unittest.main()
