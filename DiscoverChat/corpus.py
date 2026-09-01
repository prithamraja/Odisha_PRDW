"""The retrieval corpus, loaded once and held read-only (WP-D5).

Nothing in this module computes anything about the data. Every sentence and
every figure it hands out was written by the engine and frozen by
`phase5d_retrieval_corpus`; the chatbot's job is to choose which of them to
show, never to restate one in its own words.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from . import config


@dataclass(frozen=True)
class Finding:
    """One corpus record. Read-only; the fields are the engine's, not ours."""
    row: int
    data: dict

    @property
    def id(self) -> str:            return self.data["finding_id"]
    @property
    def sentence(self) -> str:      return self.data["sentence"]
    @property
    def view(self) -> str:          return self.data["view"]
    @property
    def view_title(self) -> str:    return self.data["view_title"]
    @property
    def score(self) -> float:       return self.data["score"]
    @property
    def in_feed(self) -> bool:      return self.data["in_feed"]
    @property
    def view_rank(self):            return self.data["view_rank"]
    @property
    def measures(self) -> list:     return self.data["measures"]
    @property
    def geography(self) -> dict:    return self.data["geography"]

    def coverage_line(self) -> str:
        """How this finding stood in the analysis — stated, never implied.

        D42's operator question 4: indexing candidates that failed ranking is
        acceptable *with their coverage stated*. This is that statement, and it
        is deterministic text, not a model's characterisation.
        """
        if self.in_feed:
            return f"ranked {self.data['feed_rank']} of 32 in the current feed"
        if self.view_rank:
            return f"ranked {self.view_rank} within {self.view_title}"
        return ("not in the ranked shortlist — one of the wider set of patterns "
                "the analysis found but did not promote")


@dataclass
class Corpus:
    records: list = field(default_factory=list)
    vectors: np.ndarray = None
    stamp: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    _by_id: dict = field(default_factory=dict, repr=False)

    def __len__(self) -> int:
        return len(self.records)

    def get(self, finding_id: str) -> Finding | None:
        return self._by_id.get(finding_id)

    def finding(self, row: int) -> Finding:
        return Finding(row, self.records[row])

    def all(self):
        return (Finding(i, r) for i, r in enumerate(self.records))


_CACHE: Corpus | None = None


def load(force: bool = False) -> Corpus:
    """Load the corpus once per process, pin-checked."""
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    stamp = config.assert_pin_matches_corpus()
    with open(config.CORPUS_PATH, encoding="utf-8") as fh:
        payload = json.load(fh)
    vectors = np.load(config.VECTORS_PATH)

    records = payload["records"]
    if len(records) != len(vectors):
        raise SystemExit(
            f"STOP: corpus/vector mismatch — {len(records)} records, "
            f"{len(vectors)} vectors. The two files are not from one build."
        )
    if vectors.shape[1] != config.EMBED_DIMS:
        raise SystemExit(
            f"STOP: vectors are {vectors.shape[1]}-dimensional, the pin says "
            f"{config.EMBED_DIMS}."
        )

    corpus = Corpus(
        records=records,
        vectors=np.asarray(vectors, dtype=np.float32),
        stamp=stamp,
        meta={k: v for k, v in payload.items() if k != "records"},
    )
    corpus._by_id = {r["finding_id"]: Finding(i, r)
                     for i, r in enumerate(records)}
    _CACHE = corpus
    return corpus
