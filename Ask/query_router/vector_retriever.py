"""
Template-direct vector retrieval.

Embeds every catalog question (D dashboards + T templates) once, then for a user
query returns the top-K nearest catalog entries by cosine similarity. An LLM
re-ranker (reranker.py) picks the final query_id from these candidates.

Design notes:
  - We embed a CLEANED question ('input subsidy in district?') so the {brace}
    tokens don't pollute the vector, but we hand the re-ranker the ORIGINAL
    ('input subsidy in {district}?') so it can see the parameter structure and
    pick the right entity variant (e.g. G10-D district-scoped vs G10-M mandal-scoped).
  - MANY VECTORS PER TEMPLATE. Each entry contributes one vector for its
    question and one for every `paraphrases` string, all mapped to the same
    query_id. A question phrased like a paraphrase then retrieves the template
    even when it shares few words with the abstract_question — the four
    surviving eval misses were all of that shape. Scoring keeps the MAX over a
    template's vectors, and k counts DISTINCT query_ids, so adding paraphrases
    can never crowd the candidate list with duplicates of one template.
  - Catalog embeddings are cached to .tmp/catalog_index.json keyed by a hash of
    (model + cleaned texts). Editing a catalog question OR a paraphrase
    invalidates the cache automatically; restarts are otherwise free.
  - THE PHRASINGS THAT FOUND A CANDIDATE (WP-6e). The reranker sees each
    candidate's catalogue question, but for almost every candidate the vector
    that brought it in is a paraphrase. `retrieve_with_examples` returns the
    same candidates as `retrieve_scored` plus, per candidate, the paraphrases
    search walked through on the way — so the reranker can be shown them.
"""
import re
import json
import hashlib
from pathlib import Path

import numpy as np

from .config import EMBEDDING_MODEL
from .llm_usage import record_call

_CACHE_PATH = Path(__file__).parent.parent / ".tmp" / "catalog_index.json"


def _clean(text: str) -> str:
    """'input subsidy in {district}?' -> 'input subsidy in district?'"""
    return re.sub(r"\{(\w+?)\}", r"\1", text)


class VectorRetriever:
    def __init__(
        self,
        client,
        dashboard_catalog: dict,
        template_catalog: dict,
        unanswerable_catalog: dict | None = None,
    ):
        self.client = client
        self.ids: list[str] = []             # distinct query_ids, catalog order
        self.display: dict[str, str] = {}    # qid -> original question (braced)
        self.vec_qids: list[str] = []        # one entry per embedded vector
        # Per vector: the paraphrase as the catalogue writes it, or None for the
        # vector that IS the catalogue question (the reranker already sees it).
        self.vec_examples: list[str | None] = []
        embed_texts: list[str] = []

        def add(qid: str, question: str, paraphrases) -> None:
            self.ids.append(qid)
            self.display[qid] = question
            question_cleaned = _clean(question).strip()
            for text in (question, *(paraphrases or [])):
                cleaned = _clean(text).strip()
                if not cleaned:
                    continue
                self.vec_qids.append(qid)
                self.vec_examples.append(
                    None if cleaned == question_cleaned else text.strip())
                embed_texts.append(cleaned)

        for qid, entry in dashboard_catalog.items():
            add(qid, entry["question"], entry.get("paraphrases"))
        for tid, entry in template_catalog.items():
            add(tid, entry["abstract_question"], entry.get("paraphrases"))
        # The questions the database CANNOT answer are indexed too. They have to
        # be retrievable to be refused with a reason — an officer's beneficiary
        # question that retrieves nothing gets the generic miss message, which
        # reads as the bot failing rather than as the data being absent. The
        # router refuses them; nothing here executes.
        for qid, entry in (unanswerable_catalog or {}).items():
            add(qid, entry["question"], entry.get("paraphrases"))

        self._matrix = self._load_or_build(embed_texts)   # (V, dim) L2-normalised

    # ── Embedding index ───────────────────────────────────────────────────────
    def _signature(self, embed_texts: list[str]) -> str:
        h = hashlib.sha256()
        h.update(EMBEDDING_MODEL.encode())
        for t in embed_texts:
            h.update(b"\x00")
            h.update(t.encode())
        return h.hexdigest()

    def _load_or_build(self, embed_texts: list[str]) -> np.ndarray:
        sig = self._signature(embed_texts)
        if _CACHE_PATH.exists():
            try:
                cached = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
                # vec_qids is checked as well as ids: a cache written before the
                # per-paraphrase index existed has the right signature only if the
                # texts match, but never the right row-to-template mapping.
                if (cached.get("signature") == sig
                        and cached.get("ids") == self.ids
                        and cached.get("vec_qids") == self.vec_qids):
                    return self._normalise(np.array(cached["vectors"], dtype=np.float32))
            except Exception:
                pass  # rebuild on any cache problem

        vectors = self._embed(embed_texts)
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps({
            "signature": sig,
            "ids": self.ids,
            "vec_qids": self.vec_qids,
            "vectors": [v.tolist() for v in vectors],
        }), encoding="utf-8")
        return self._normalise(vectors)

    def _embed(self, texts: list[str]) -> np.ndarray:
        out: list[list[float]] = []
        B = 256
        for i in range(0, len(texts), B):
            resp = self.client.embeddings.create(
                model=EMBEDDING_MODEL, input=texts[i:i + B])
            record_call("embed_index", EMBEDDING_MODEL, resp)
            out.extend(d.embedding for d in resp.data)
        return np.array(out, dtype=np.float32)

    @staticmethod
    def _normalise(m: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return m / norms

    # ── Query-time retrieval ──────────────────────────────────────────────────
    def _vector_scores(self, query: str) -> np.ndarray:
        """Cosine of the query against every embedded vector. One embedding call."""
        resp = self.client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
        record_call("embed_query", EMBEDDING_MODEL, resp)
        qv = np.array(resp.data[0].embedding, dtype=np.float32)
        qv = qv / (np.linalg.norm(qv) or 1.0)
        return self._matrix @ qv                         # cosine (rows normalised)

    def retrieve_scored(self, query: str, k: int) -> list[tuple[str, str, float]]:
        """Up to k DISTINCT (query_id, display_question, cosine_score), best first.

        A template scores as its best-matching vector — question or paraphrase —
        so k is a budget of candidate templates, not of embedded strings.
        """
        return self._ranked(self._vector_scores(query), k)

    def retrieve_with_examples(
        self, query: str, k: int, per_candidate: int,
    ) -> tuple[list[tuple[str, str, float]], dict[str, list[str]]]:
        """`retrieve_scored`'s candidates, plus the paraphrases that found them.

        The candidate list is computed exactly as `retrieve_scored` computes it;
        the examples are extra information handed along, never a re-ranking.

        The walk goes down the vectors in descending score and stops where the
        (k+1)-th distinct template would begin — the vectors `crowding_extra`
        counts, plus any further ones of the k candidates that still outrank
        every template outside them. Each candidate keeps up to `per_candidate`
        of its walked vectors, best first, as the catalogue writes them. The
        vector that IS the catalogue question is skipped: the reranker already
        sees that text as the candidate itself.
        """
        scores = self._vector_scores(query)
        scored = self._ranked(scores, k)
        if per_candidate <= 0:
            return scored, {}
        candidates = {qid for qid, _, _ in scored}
        examples: dict[str, list[str]] = {}
        seen: set[str] = set()
        for row in np.argsort(-scores, kind="stable"):
            qid = self.vec_qids[row]
            if qid not in seen:
                if len(seen) == len(scored):
                    break                  # the (k+1)-th template begins here
                seen.add(qid)
            text = self.vec_examples[row]
            if text is None or qid not in candidates:
                continue
            kept = examples.setdefault(qid, [])
            if len(kept) < per_candidate and text not in kept:
                kept.append(text)
        return scored, examples

    def _ranked(self, scores: np.ndarray, k: int) -> list[tuple[str, str, float]]:
        best: dict[str, float] = {}
        for row, qid in enumerate(self.vec_qids):
            score = float(scores[row])
            if score > best.get(qid, float("-inf")):
                best[qid] = score

        ranked = sorted(best.items(), key=lambda kv: -kv[1])[:k]
        return [(qid, self.display[qid], score) for qid, score in ranked]

    def retrieve(self, query: str, k: int) -> list[tuple[str, str]]:
        """Returns up to k (query_id, display_question) pairs, most similar first."""
        return [(qid, q) for qid, q, _ in self.retrieve_scored(query, k)]
