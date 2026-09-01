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

    @property
    def is_decomposition(self) -> bool:
        return self.data.get("record_type") == "decomposition"

    def display_sentence(self) -> str:
        """The sentence as an officer reads it (D6.1's render-time glossary).

        The stored sentence keeps the engine's column names, because that is
        what the labelling sheet and every audit trail compare against. What
        reaches an answer is this. The substitution is a dictionary and a
        regular expression -- no model, and no figure altered.
        """
        from . import glossary
        return glossary.render(self.sentence, self.view)

    def coverage_line(self) -> str:
        """How this record stood in the analysis — stated, never implied.

        D42's operator question 4: indexing candidates that failed ranking is
        acceptable *with their coverage stated*. This is that statement, and it
        is deterministic text, not a model's characterisation.

        A DECOMPOSITION gets its own line and must, because the findings line
        would be false about it twice over: it never entered the ranking, so
        "did not promote" implies a judgement nobody made, and it is not a
        pattern the engine found at all. It is arithmetic over the same rows,
        and saying so is what stops a reader taking a breakdown for a finding.
        """
        if self.is_decomposition:
            return ("a breakdown of the recorded totals, not a mined pattern — "
                    "the parts add up to the whole")
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


def _read(corpus_path, vectors_path, what: str) -> tuple:
    """One corpus file and its vectors, checked for the mismatches that matter."""
    with open(corpus_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    vectors = np.load(vectors_path)
    records = payload["records"]
    if len(records) != len(vectors):
        raise SystemExit(
            f"STOP: {what} record/vector mismatch — {len(records)} records, "
            f"{len(vectors)} vectors. The two files are not from one build."
        )
    if vectors.shape[1] != config.EMBED_DIMS:
        raise SystemExit(
            f"STOP: {what} vectors are {vectors.shape[1]}-dimensional, the pin "
            f"says {config.EMBED_DIMS}."
        )
    return payload, records, np.asarray(vectors, dtype=np.float32)


def load(force: bool = False) -> Corpus:
    """Load the corpus once per process, pin-checked.

    ONE VECTOR SPACE, TWO KINDS OF RECORD (D6.1). The decomposition sidecar is
    concatenated onto the findings rather than held apart and searched
    separately, and that is the design decision that makes the brief's "ranked
    by the same relevance score, not privileged" true by construction: there is
    no second ranking to privilege. `Retriever`, the judge, the diversity
    collapse and the floor all operate on one matrix and never learn that two
    files fed it.

    Ids cannot collide — the findings builder writes `1-00042` and the
    decomposition builder writes `d1-00042` — so one `_by_id` map serves both.
    """
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    stamp = config.assert_pin_matches_corpus()
    payload, records, vectors = _read(
        config.CORPUS_PATH, config.VECTORS_PATH, "corpus")

    meta = {k: v for k, v in payload.items() if k != "records"}
    meta["findings"] = len(records)
    meta["decompositions"] = 0

    d_stamp = config.decompose_stamp()
    if d_stamp is not None and config.DECOMPOSE_CORPUS_PATH.exists():
        d_payload, d_records, d_vectors = _read(
            config.DECOMPOSE_CORPUS_PATH, config.DECOMPOSE_VECTORS_PATH,
            "decomposition sidecar")
        if d_payload.get("candidate_set_id") != payload.get("candidate_set_id"):
            raise SystemExit(
                "STOP: the decomposition sidecar was built from a different "
                f"candidate set ({d_payload.get('candidate_set_id')}) than the "
                f"findings corpus ({payload.get('candidate_set_id')}). Two run "
                "stamps in one answer would date it wrongly whichever one it "
                "printed."
            )
        records = records + d_records
        vectors = np.vstack([vectors, d_vectors])
        meta["decompositions"] = len(d_records)
        meta["decompose_stamp"] = d_stamp

    corpus = Corpus(
        records=records,
        vectors=vectors,
        stamp=stamp,
        meta=meta,
    )
    corpus._by_id = {r["finding_id"]: Finding(i, r)
                     for i, r in enumerate(records)}
    if len(corpus._by_id) != len(records):
        raise SystemExit(
            f"STOP: {len(records) - len(corpus._by_id)} duplicate record ids "
            f"across the two corpora — one would shadow the other."
        )
    _CACHE = corpus
    return corpus
