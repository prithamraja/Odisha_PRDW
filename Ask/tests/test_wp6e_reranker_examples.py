"""WP-6e — the reranker is shown the phrasings that found each candidate, pinned.

    T1  search hands back the phrasings it walked through, and the candidates
        are exactly `retrieve_scored`'s
    T2  the reranker shows them as "found by:" lines; config switch at 0 sends
        the WP-6d prompt byte-for-byte

No API key and no network: the embedding client and the reranker's chat client
are stubs. One test reads the real index from `.tmp/catalog_index.json` and is
skipped where that cache is absent.

Test note — the size of one real listing (o200k_base): the recall query
"Khordha jillare 2024-2025 re kete GP GPDP upload karichanti?" is 5,699 prompt
tokens with the switch at 0 and 6,749 at 4 (38 phrasings under 30 candidates).
Over all 237 cached recall queries the switch at 4 adds a mean of 1,170 tokens
(p90 1,755, max 2,142), 52 of them the one new rule in the system prompt.
"""
import hashlib
import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from query_router import config
from query_router import reranker
from query_router.config import VECTOR_TOP_K
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.unanswerable_catalog import UNANSWERABLE_CATALOG
from query_router import vector_retriever as vr
from query_router.vector_retriever import VectorRetriever

_REAL_INDEX = Path(__file__).resolve().parents[1] / ".tmp" / "catalog_index.json"
_RECALL_VECTORS = Path(__file__).resolve().parents[1] / ".tmp" / "recall_query_vectors.json"

# sha256 of `_RERANK_SYS` at WP-6d (3721862).
_WP6D_SYSTEM_SHA256 = "48aa4780e5528e2faa2784ef65e816bf75fbe65787bec305f0c07544c19859ed"


def _wp6d_user_msg(query, candidates):
    """WP-6d's listing, copied verbatim from `rerank` at 3721862."""
    lines = []
    for qid, question in candidates:
        ctx = reranker._QID_TO_CONTEXT.get(qid)
        if ctx:
            desc, filters = ctx
            line = f"{qid}: {question}"
            if desc:
                line += f"\n    ↳ {desc}"
            lines.append(f"{line}\n    accepts filters: {filters}")
        else:
            lines.append(f"{qid}: {question}")
    listing = "\n".join(lines)
    return f'Candidates:\n{listing}\n\nUser question: "{query}"\nJSON:'


class _Recorder:
    """A chat client that keeps what it was sent and declines."""

    def __init__(self):
        self.kwargs = None
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.kwargs = kwargs
        msg = SimpleNamespace(content='{"query_id": "no_match", "candidates": []}')
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                               usage=None)


class _FakeEmbeddings:
    def __init__(self, dim=8):
        self.dim = dim
        self.calls = 0

    def create(self, model, input):  # noqa: A002 - mirrors the OpenAI signature
        self.calls += 1
        data = []
        for text in input:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            data.append(SimpleNamespace(embedding=rng.normal(size=self.dim).tolist()))
        return SimpleNamespace(data=data)


def _all_candidate_lists():
    """Every indexed id, in lists of 30 — templates, dashboards and refusals."""
    ids = [(qid, e["question"]) for qid, e in DASHBOARD_CATALOG.items()]
    ids += [(qid, e["abstract_question"]) for qid, e in TEMPLATE_CATALOG.items()]
    ids += [(qid, e["question"]) for qid, e in UNANSWERABLE_CATALOG.items()]
    return [ids[i:i + 30] for i in range(0, len(ids), 30)]


# ── The switch at 0 ───────────────────────────────────────────────────────────

class SwitchAtZeroTests(unittest.TestCase):
    QUERY = 'Split the "sanctioned" funds into SFC and Own Funds in 2024-25'

    def test_the_default_is_four(self):
        self.assertEqual(config.RERANK_EXAMPLES_PER_CANDIDATE, 4)

    def test_system_prompt_is_wp6d_byte_for_byte(self):
        self.assertEqual(
            hashlib.sha256(reranker._RERANK_SYS.encode()).hexdigest(),
            _WP6D_SYSTEM_SHA256)

    def test_listing_is_wp6d_byte_for_byte_for_every_indexed_id(self):
        for cands in _all_candidate_lists():
            msgs = reranker.build_messages(self.QUERY, cands, None)
            self.assertEqual(msgs[0]["content"], reranker._RERANK_SYS)
            self.assertEqual(msgs[1]["content"], _wp6d_user_msg(self.QUERY, cands))

    def test_rerank_without_examples_sends_the_wp6d_messages(self):
        cands = _all_candidate_lists()[3]
        client = _Recorder()
        reranker.rerank(self.QUERY, cands, client)
        self.assertEqual(client.kwargs["messages"], [
            {"role": "system", "content": reranker._RERANK_SYS},
            {"role": "user", "content": _wp6d_user_msg(self.QUERY, cands)},
        ])
        self.assertNotIn("found by", json.dumps(client.kwargs["messages"]))


# ── T1: the retriever ─────────────────────────────────────────────────────────

# Five phrasings of A outrank B's best; A's own question sits among them.
CATALOG = {
    "A": {"abstract_question": "How much was sanctioned per {scheme}?",
          "paraphrases": ["a1 in {district}", "a2", "a3", "a4", "a5", "a6", "a7",
                          "How much was sanctioned per scheme?"]},
    "B": {"abstract_question": "B question", "paraphrases": ["b1"]},
    "C": {"abstract_question": "C question", "paraphrases": ["c1"]},
}
# Vector rows, in index order: A_q a1 a2 a3 a4 a5 a6 a7 A_dup | B_q b1 | C_q c1
SCORES = np.array([
    0.935,                                  # A_q — the catalogue question itself
    0.95, 0.94, 0.93, 0.92, 0.91,           # a1..a5 — five above B's best
    0.55,                                   # a6 — below C's first vector
    0.70,                                   # a7 — after B begins, before C does
    0.945,                                  # A's paraphrase that repeats its question
    0.50, 0.89,                             # B_q, b1
    0.60, 0.40,                             # C_q, c1 — C is the (k+1)-th template
], dtype=np.float32)


class RetrieverExampleTests(unittest.TestCase):
    def setUp(self):
        self._real_cache = vr._CACHE_PATH
        vr._CACHE_PATH = vr._CACHE_PATH.with_name("catalog_index_wp6e_test_only.json")
        self.addCleanup(setattr, vr, "_CACHE_PATH", self._real_cache)
        self.addCleanup(lambda: vr._CACHE_PATH.unlink(missing_ok=True))
        self.embeddings = _FakeEmbeddings()
        self.r = VectorRetriever(SimpleNamespace(embeddings=self.embeddings), {}, CATALOG)
        self.assertEqual(len(self.r.vec_qids), len(SCORES))
        self.r._vector_scores = lambda query: SCORES

    def test_four_best_first_never_the_question(self):
        _, examples = self.r.retrieve_with_examples("q", k=2, per_candidate=4)
        self.assertEqual(examples["A"], ["a1 in {district}", "a2", "a3", "a4"])
        self.assertEqual(examples["B"], ["b1"])
        for texts in examples.values():
            self.assertNotIn("How much was sanctioned per {scheme}?", texts)
            self.assertNotIn("How much was sanctioned per scheme?", texts)

    def test_the_phrasing_is_returned_as_written(self):
        _, examples = self.r.retrieve_with_examples("q", k=2, per_candidate=4)
        self.assertIn("a1 in {district}", examples["A"])     # not the _clean-ed text

    def test_the_walk_stops_where_the_next_template_begins(self):
        _, examples = self.r.retrieve_with_examples("q", k=2, per_candidate=50)
        # a7 (0.70) comes after B's first vector but before C's: walked.
        # a6 (0.55) comes after C's first vector (0.60): not walked.
        self.assertEqual(examples["A"], ["a1 in {district}", "a2", "a3", "a4", "a5", "a7"])
        self.assertNotIn("C", examples)

    def test_candidates_are_retrieve_scoreds_in_both_states(self):
        want = self.r.retrieve_scored("q", k=2)
        self.assertEqual([q for q, _, _ in want], ["A", "B"])
        for n in (0, 1, 4, 50):
            scored, examples = self.r.retrieve_with_examples("q", k=2, per_candidate=n)
            self.assertEqual(scored, want)
            if n == 0:
                self.assertEqual(examples, {})

    def test_a_candidate_with_no_walked_phrasing_has_no_entry(self):
        _, examples = self.r.retrieve_with_examples("q", k=3, per_candidate=4)
        # k=3: C is a candidate; its best vector is its question, and the walk
        # ends at the list's end, so c1 (0.40) is still walked.
        self.assertEqual(examples["C"], ["c1"])

    def test_one_embedding_call(self):
        r = VectorRetriever(SimpleNamespace(embeddings=self.embeddings), {}, CATALOG)
        before = self.embeddings.calls
        r.retrieve_with_examples("anything", k=2, per_candidate=4)
        self.assertEqual(self.embeddings.calls - before, 1)

    def test_dashboards_and_refusals_are_treated_like_templates(self):
        r = VectorRetriever(
            SimpleNamespace(embeddings=self.embeddings),
            {"D1": {"question": "Dashboard question", "paraphrases": ["d-para"]}},
            {"T1": {"abstract_question": "Template question", "paraphrases": ["t-para"]}},
            {"R1": {"question": "Refusal question", "paraphrases": ["r-para"]}})
        self.assertEqual(r.vec_examples,
                         [None, "d-para", None, "t-para", None, "r-para"])
        r._vector_scores = lambda q: np.array([.9, .8, .7, .6, .5, .4], dtype=np.float32)
        _, examples = r.retrieve_with_examples("q", k=3, per_candidate=4)
        self.assertEqual(examples, {"D1": ["d-para"], "T1": ["t-para"], "R1": ["r-para"]})


# ── T2: the listing ───────────────────────────────────────────────────────────

class FoundByListingTests(unittest.TestCase):
    CANDS = [("BUD-003", TEMPLATE_CATALOG["BUD-003"]["abstract_question"]),
             ("X-9", "A candidate with no context")]
    EXAMPLES = {"BUD-003": ["How much of the sanctioned amount came from a given scheme in a given year?",
                            "Split the sanctioned funds into SFC and Own Funds in a given year"]}

    def test_found_by_follows_the_filters_line(self):
        user = reranker.build_messages("q", self.CANDS, self.EXAMPLES)[1]["content"]
        filters = reranker._QID_TO_CONTEXT["BUD-003"][1]
        self.assertIn(
            f"    accepts filters: {filters}\n"
            '    found by: "How much of the sanctioned amount came from a given scheme in a given year?"\n'
            '              "Split the sanctioned funds into SFC and Own Funds in a given year"\n'
            "X-9: A candidate with no context\n", user)

    def test_the_rule_joins_the_system_prompt_only_with_examples(self):
        with_ex = reranker.build_messages("q", self.CANDS, self.EXAMPLES)[0]["content"]
        empty = reranker.build_messages("q", self.CANDS, {})[0]["content"]
        without = reranker.build_messages("q", self.CANDS, None)[0]["content"]
        self.assertIn(reranker._EXAMPLES_RULE, with_ex)
        self.assertEqual(with_ex, empty)
        self.assertNotIn("found by", without)
        # Beside the "judge by the ↳ description" rule, and nothing else moved.
        self.assertEqual(with_ex.replace("\n\n" + reranker._EXAMPLES_RULE, ""), without)
        self.assertIn('with "accepts filters:".\n\n"found by:" lines are', with_ex)

    def test_stubbed_index_end_to_end_shows_exactly_four(self):
        """Five phrasings of A rank above B's best: the reranker sees four,
        best first, and never A's catalogue question under "found by"."""
        setup = RetrieverExampleTests("test_four_best_first_never_the_question")
        setup.setUp()
        try:
            scored, examples = setup.r.retrieve_with_examples("q", k=2, per_candidate=4)
        finally:
            setup.doCleanups()
        user = reranker.build_messages("q", [(q, d) for q, d, _ in scored],
                                       examples)[1]["content"]
        block = user.split("A: How much was sanctioned per {scheme}?", 1)[1].split("\nB:", 1)[0]
        self.assertEqual(block,
                         '\n    found by: "a1 in {district}"\n'
                         '              "a2"\n              "a3"\n              "a4"')


# ── The router ────────────────────────────────────────────────────────────────

class RouterSwitchTests(unittest.TestCase):
    SCORED = [("BUD-003", TEMPLATE_CATALOG["BUD-003"]["abstract_question"], 0.80),
              ("BUD-002", TEMPLATE_CATALOG["BUD-002"]["abstract_question"], 0.60)]

    def _route(self, per_candidate):
        from query_router import router
        seen = {}

        class Retriever:
            def retrieve_scored(_, query, k):
                seen["method"] = "retrieve_scored"
                return list(self.SCORED)

            def retrieve_with_examples(_, query, k, n):
                seen["method"] = "retrieve_with_examples"
                seen["n"] = n
                return list(self.SCORED), {"BUD-003": ["a phrasing"]}

        def fake_rerank(query, candidates, client, examples=None):
            seen["candidates"] = candidates
            seen["examples"] = examples
            return "no_match", []

        real_rerank, real_n = router.rerank, config.RERANK_EXAMPLES_PER_CANDIDATE
        router.rerank = fake_rerank
        config.RERANK_EXAMPLES_PER_CANDIDATE = per_candidate
        try:
            router._route_vector(
                "How much of the sanctioned amount came from SFC in 2024-25?",
                "normalized", time.monotonic(),
                validator=SimpleNamespace(validate=lambda *a, **k: None,
                                          fiscal_years=lambda: ["2024-2025"]),
                openai_client=object(), retriever=Retriever(), cache_conn=None,
                dashboard_results={}, template_map=dict(TEMPLATE_CATALOG),
                dashboard_questions={}, start_date=None, end_date=None)
        finally:
            router.rerank = real_rerank
            config.RERANK_EXAMPLES_PER_CANDIDATE = real_n
        return seen

    def test_at_zero_the_router_is_wp6d(self):
        seen = self._route(0)
        self.assertEqual(seen["method"], "retrieve_scored")
        self.assertIsNone(seen["examples"])

    def test_at_four_the_examples_are_passed_and_the_candidates_unchanged(self):
        at0, at4 = self._route(0), self._route(4)
        self.assertEqual(at4["method"], "retrieve_with_examples")
        self.assertEqual(at4["n"], 4)
        self.assertEqual(at4["examples"], {"BUD-003": ["a phrasing"]})
        self.assertEqual(at4["candidates"], at0["candidates"])


# ── The real index ────────────────────────────────────────────────────────────

@unittest.skipUnless(_REAL_INDEX.exists() and _RECALL_VECTORS.exists(),
                     "needs the cached catalogue index and recall query vectors")
class RealIndexTests(unittest.TestCase):
    """The shipped catalogue, the cached recall query vectors, no API call."""

    @classmethod
    def setUpClass(cls):
        class NoEmbed:
            def create(self, **kw):
                raise AssertionError("the index must come from the cache")

        cls.r = VectorRetriever(SimpleNamespace(embeddings=NoEmbed()), DASHBOARD_CATALOG,
                                TEMPLATE_CATALOG, UNANSWERABLE_CATALOG)
        vectors = json.loads(_RECALL_VECTORS.read_text(encoding="utf-8"))["vectors"]
        cls.queries = list(vectors.items())[:40]

    def test_candidates_identical_and_no_catalogue_question_shown(self):
        for text, vec in self.queries:
            qv = np.array(vec, dtype=np.float32)
            scores = self.r._matrix @ (qv / np.linalg.norm(qv))
            self.r._vector_scores = lambda q, _s=scores: _s
            scored = self.r.retrieve_scored(text, VECTOR_TOP_K)
            scored4, examples = self.r.retrieve_with_examples(text, VECTOR_TOP_K, 4)
            self.assertEqual(scored4, scored)
            self.assertLessEqual(set(examples), {q for q, _, _ in scored})
            for qid, texts in examples.items():
                self.assertLessEqual(len(texts), 4)
                self.assertNotIn(self.r.display[qid], texts)


if __name__ == "__main__":
    unittest.main()
