"""VectorRetriever indexes paraphrases as extra vectors for the same query_id.

The contract that matters downstream: k is a budget of DISTINCT templates, and a
template scores as its best-matching vector. Without both, adding paraphrases
would let one template fill the reranker's candidate list with near-duplicates of
itself and crowd the real answer out.
"""
import unittest

import numpy as np

from query_router.config import VECTOR_TOP_K
from query_router.dashboard_catalog import DASHBOARD_CATALOG
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.vector_retriever import VectorRetriever


class _FakeEmbeddings:
    """Deterministic stand-in: text -> a unit vector fixed by the text's hash."""

    def __init__(self, dim=16):
        self.dim = dim
        self.seen: list[str] = []

    def create(self, model, input):  # noqa: A002 - mirrors the OpenAI signature
        data = []
        for text in input:
            self.seen.append(text)
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            data.append(type("E", (), {"embedding": rng.normal(size=self.dim).tolist()}))
        return type("R", (), {"data": data})


class _FakeClient:
    def __init__(self):
        self.embeddings = _FakeEmbeddings()


CATALOG = {
    "T1": {"abstract_question": "How many farmers are registered?",
           "paraphrases": ["Total farmer count", "Size of the roster"]},
    "T2": {"abstract_question": "What subsidy went to {district} district?",
           "paraphrases": ["District subsidy total"]},
    "T3": {"abstract_question": "Which farmers have eKYC pending?",
           "paraphrases": []},
}


class VectorRetrieverParaphraseTests(unittest.TestCase):
    def setUp(self):
        # Never touch the real on-disk index from a test.
        import query_router.vector_retriever as vr
        self._real_cache = vr._CACHE_PATH
        vr._CACHE_PATH = vr._CACHE_PATH.with_name("catalog_index_test_only.json")
        self.addCleanup(setattr, vr, "_CACHE_PATH", self._real_cache)
        self.addCleanup(lambda: vr._CACHE_PATH.unlink(missing_ok=True))

    def test_one_vector_per_question_and_paraphrase(self):
        client = _FakeClient()
        r = VectorRetriever(client, {}, CATALOG)
        self.assertEqual(r.ids, ["T1", "T2", "T3"])
        self.assertEqual(r.vec_qids, ["T1", "T1", "T1", "T2", "T2", "T3"])
        self.assertEqual(r._matrix.shape[0], 6)

    def test_paraphrases_are_embedded_cleaned(self):
        client = _FakeClient()
        VectorRetriever(client, {}, CATALOG)
        self.assertIn("Total farmer count", client.embeddings.seen)
        self.assertIn("Size of the roster", client.embeddings.seen)
        # braces stripped from the question, as before
        self.assertIn("What subsidy went to district district?", client.embeddings.seen)

    def test_retrieve_returns_distinct_qids(self):
        client = _FakeClient()
        r = VectorRetriever(client, {}, CATALOG)
        got = r.retrieve_scored("anything at all", k=10)
        ids = [qid for qid, _, _ in got]
        self.assertEqual(len(ids), len(set(ids)), "a query_id appeared twice")
        self.assertEqual(set(ids), {"T1", "T2", "T3"})

    def test_k_counts_templates_not_vectors(self):
        client = _FakeClient()
        r = VectorRetriever(client, {}, CATALOG)
        self.assertEqual(len(r.retrieve_scored("anything", k=2)), 2)

    def test_score_is_the_max_over_a_templates_vectors(self):
        client = _FakeClient()
        r = VectorRetriever(client, {}, CATALOG)
        query = "some question"
        got = dict((qid, s) for qid, _, s in r.retrieve_scored(query, k=10))

        # Recompute by hand: each template's score must equal its best row.
        qv = np.array(client.embeddings.create(None, [query]).data[0].embedding,
                      dtype=np.float32)
        qv = qv / np.linalg.norm(qv)
        raw = r._matrix @ qv
        expected: dict[str, float] = {}
        for row, qid in enumerate(r.vec_qids):
            expected[qid] = max(expected.get(qid, float("-inf")), float(raw[row]))
        for qid, score in expected.items():
            self.assertAlmostEqual(got[qid], score, places=5)

    def test_results_are_sorted_descending(self):
        client = _FakeClient()
        r = VectorRetriever(client, {}, CATALOG)
        scores = [s for _, _, s in r.retrieve_scored("anything", k=10)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_real_catalog_indexes_more_vectors_than_templates(self):
        client = _FakeClient()
        r = VectorRetriever(client, DASHBOARD_CATALOG, TEMPLATE_CATALOG)
        n_templates = len(DASHBOARD_CATALOG) + len(TEMPLATE_CATALOG)
        self.assertEqual(len(r.ids), n_templates)
        self.assertGreater(len(r.vec_qids), n_templates)
        self.assertEqual(r._matrix.shape[0], len(r.vec_qids))
        got = r.retrieve_scored("how many farmers", k=VECTOR_TOP_K)
        ids = [qid for qid, _, _ in got]
        self.assertEqual(len(ids), VECTOR_TOP_K)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
