"""Scoring a question against the corpus (WP-D5, stage D5.1).

    score = cosine(query, finding) + structural slot-hit boost

**A FLOOR, NOT A TOP-N** (D42 ruling 5). Everything above `RELEVANCE_THRESHOLD`
is the answer set; if nothing clears it the caller says the analysis has nothing
on this. The threshold is never relaxed to manufacture an answer, and there is
no "best of a bad list" path anywhere in this module. The one cap that exists
(`ANSWER_CAP`) limits how much of a very broad sweep is written out at once, not
which findings qualify, and the answer says when it has been applied.

**THE BOOST IS ON TRIAL.** D42 ruling 4 admits it only if the D5.1 experiment
shows it beats cosine alone. `score()` therefore takes `use_boost`, and the
experiment runs the same code with it off — so what is measured is the shipped
path, not a second implementation of it.

**THE DIVERSITY RULE** collapses near-duplicates BEFORE the count is taken,
because the count drives presentation. 2,464 of the 4,239 records share a
sentence with some other record — `generate_nl_summary` never mentions the base
subspace, so eight findings about eight different slices render identically. An
answer that showed the same sentence eight times would look like eight findings
and be one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import config, corpus as corpus_mod
from .slots import SlotExtractor, Slots


@dataclass
class Hit:
    finding: object                    # corpus.Finding
    cosine: float
    boost: float
    score: float
    why: list = field(default_factory=list)      # what the boost fired on
    collapsed: list = field(default_factory=list)  # ids of near-duplicates dropped

    def as_dict(self) -> dict:
        return {
            "finding_id": self.finding.id,
            "cosine": round(self.cosine, 4),
            "boost": round(self.boost, 4),
            "score": round(self.score, 4),
            "why": self.why,
            "collapsed": self.collapsed,
            "in_feed": self.finding.in_feed,
            "view": self.finding.view,
            "engine_score": self.finding.score,
        }


@dataclass
class Result:
    slots: Slots
    hits: list                         # above the floor, best first
    considered: int
    best_cosine: float
    threshold: float
    collapsed_count: int
    capped: bool = False

    @property
    def empty(self) -> bool:
        return not self.hits


class Retriever:
    """One per process: holds the corpus, the vectors and Ask's registry open."""

    def __init__(self, embedder=None, extractor=None):
        self.corpus = corpus_mod.load()
        self.extractor = extractor if extractor is not None else SlotExtractor()
        self._embedder = embedder
        self._geo_index = self._build_geo_index()
        self._measure_index = self._build_measure_index()

    @property
    def embedder(self):
        # Constructed lazily so the offline tests that supply their own vectors
        # never need a network key.
        if self._embedder is None:
            self._embedder = config.Embedder()
        return self._embedder

    # ── structural indexes (built once, from the corpus's own fields) ────────
    def _build_geo_index(self) -> dict:
        """LGD code / canonical place name -> {row: role}."""
        index = {}
        for finding in self.corpus.all():
            geo = finding.geography
            roles = geo.get("roles", {})
            for key in (geo["gp_lgd_codes"] + geo["blocks"] + geo["districts"]):
                index.setdefault(key, {})[finding.row] = roles.get(key, "named")
        return index

    def _build_measure_index(self) -> dict:
        index = {}
        for finding in self.corpus.all():
            for measure in finding.measures:
                index.setdefault(measure, set()).add(finding.row)
        return index

    # ── the boost ───────────────────────────────────────────────────────────
    def structural_boost(self, slots: Slots) -> tuple:
        """(boost vector over all rows, {row: [reasons]}).

        Geography is matched on LGD CODES for Gram Panchayats and on the
        registry's canonical strings for blocks and districts — the roster
        carries `gp_lgd_code` and nothing else, so the block/district half is a
        canonical-name match, reached through the same validator. Neither half
        is string similarity on what the user typed.
        """
        boost = np.zeros(len(self.corpus), dtype=np.float32)
        why: dict = {}

        def note(row, reason):
            why.setdefault(row, []).append(reason)

        for code, label in zip(slots.gp_lgd_codes, slots.gp_names):
            for row, role in self._geo_index.get(code, {}).items():
                boost[row] += config.GEO_BOOST
                note(row, f"names {label} ({role})")
                if role == "subspace":
                    boost[row] += config.GEO_SUBSPACE_BONUS
        for place in slots.blocks + slots.districts:
            for row, role in self._geo_index.get(place, {}).items():
                boost[row] += config.GEO_BOOST
                note(row, f"names {place} ({role})")
                if role == "subspace":
                    boost[row] += config.GEO_SUBSPACE_BONUS

        # A question that names several measures gets ONE measure boost per
        # finding, not one per matching keyword: 'spending' and 'expenditure'
        # in the same sentence are one intent, and letting them stack would
        # make a wordy question outrank a precise one.
        measure_rows: dict = {}
        for measure in slots.measures:
            for row in self._measure_index.get(measure, ()):
                measure_rows.setdefault(row, measure)
        for row, measure in measure_rows.items():
            boost[row] += config.MEASURE_BOOST
            note(row, f"mined on {measure}")

        return boost, why

    # ── scoring ─────────────────────────────────────────────────────────────
    def score(
        self,
        question: str,
        *,
        use_boost: bool = True,
        threshold: float | None = None,
        quality_floor: float | None = None,
        query_vector: np.ndarray | None = None,
        vectors: np.ndarray | None = None,
        collapse: bool = True,
    ) -> Result:
        """Rank the corpus against one question. The shipped path.

        `vectors` and `query_vector` exist for the D5.1 experiment, which runs
        THIS function against a different document matrix (the bare-sentence
        arm) rather than a second copy of the scoring logic.
        """
        threshold = config.RELEVANCE_THRESHOLD if threshold is None else threshold
        floor = config.QUALITY_FLOOR if quality_floor is None else quality_floor
        matrix = self.corpus.vectors if vectors is None else vectors

        slots = self.extractor.extract(question)
        if query_vector is None:
            query_vector = self.embedder.query(slots.expanded)

        cosines = matrix @ np.asarray(query_vector, dtype=np.float32)

        if use_boost:
            boost, why = self.structural_boost(slots)
        else:
            boost, why = np.zeros(len(cosines), dtype=np.float32), {}

        total = cosines + boost
        best_cosine = float(cosines.max()) if len(cosines) else 0.0

        order = np.argsort(-total)
        hits = []
        for row in order:
            if float(total[row]) < threshold:
                break                       # sorted: nothing below can qualify
            finding = self.corpus.finding(int(row))
            if finding.score < floor:
                continue
            hits.append(Hit(finding=finding, cosine=float(cosines[row]),
                            boost=float(boost[row]), score=float(total[row]),
                            why=why.get(int(row), [])))

        collapsed_count = 0
        if collapse:
            hits, collapsed_count = collapse_near_duplicates(hits)

        capped = len(hits) > config.ANSWER_CAP
        if capped:
            hits = hits[:config.ANSWER_CAP]

        return Result(slots=slots, hits=hits, considered=len(cosines),
                      best_cosine=best_cosine, threshold=threshold,
                      collapsed_count=collapsed_count, capped=capped)

    def pool(
        self,
        question: str,
        *,
        floor: float | None = None,
        size: int | None = None,
        query_vector: np.ndarray | None = None,
    ) -> Result:
        """The judged path's CANDIDATE POOL — not an answer.

        Everything above `CANDIDATE_FLOOR`, near-duplicates collapsed FIRST and
        only then truncated to `CANDIDATE_POOL`. The order matters: collapsing
        after the cut would spend pool slots on sentences the reader could not
        tell apart, and on a broad question 493 of the top hits are duplicates
        of each other.

        `ANSWER_CAP` is deliberately NOT applied. It caps how much is written
        out; this is what the judge reads.
        """
        floor = config.CANDIDATE_FLOOR if floor is None else floor
        size = config.CANDIDATE_POOL if size is None else size

        slots = self.extractor.extract(question)
        if query_vector is None:
            query_vector = self.embedder.query(slots.expanded)

        cosines = self.corpus.vectors @ np.asarray(query_vector, dtype=np.float32)
        boost, why = self.structural_boost(slots)
        total = cosines + boost

        hits = []
        for row in np.argsort(-total):
            if float(total[row]) < floor:
                break
            finding = self.corpus.finding(int(row))
            if finding.score < config.QUALITY_FLOOR:
                continue
            hits.append(Hit(finding=finding, cosine=float(cosines[row]),
                            boost=float(boost[row]), score=float(total[row]),
                            why=why.get(int(row), [])))

        hits, collapsed = collapse_near_duplicates(hits)
        capped = len(hits) > size
        return Result(slots=slots, hits=hits[:size], considered=len(cosines),
                      best_cosine=float(cosines.max()) if len(cosines) else 0.0,
                      threshold=floor, collapsed_count=collapsed, capped=capped)


def collapse_near_duplicates(hits: list) -> tuple:
    """Collapse findings the reader could not tell apart. Returns (kept, dropped).

    The rule is IDENTITY OF THE DISPLAYED SENTENCE, not vector proximity. Two
    justifications, and the first is the one that matters: the sentence is what
    the reader sees, so two records with the same sentence are, to them, the
    same answer printed twice. The second is that a cosine-radius rule needs a
    radius, which would be one more unratified constant standing between the
    corpus and the officer.

    The survivor is the best-scoring member, and it carries the others' ids so a
    follow-up can still reach them and so the audit trail is complete.
    """
    kept, by_sentence = [], {}
    dropped = 0
    for hit in hits:
        sentence = hit.finding.sentence
        incumbent = by_sentence.get(sentence)
        if incumbent is None:
            by_sentence[sentence] = hit
            kept.append(hit)
        else:
            incumbent.collapsed.append(hit.finding.id)
            dropped += 1
    return kept, dropped
