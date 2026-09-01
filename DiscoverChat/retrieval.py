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
        self._query_cache: dict = {}
        self._geo_index = self._build_geo_index()
        self._measure_index = self._build_measure_index()

    @property
    def embedder(self):
        # Constructed lazily so the offline tests that supply their own vectors
        # never need a network key.
        if self._embedder is None:
            self._embedder = config.Embedder()
        return self._embedder

    def query_vector(self, text: str):
        """The query embedding, computed once per process per exact string.

        Memoisation, and it buys two things. The cheap one is time: the offline
        gate puts the same twenty questions through six checks, each a network
        call the endpoint answers in 30-100 seconds, and the suite went from
        unrunnable to a couple of minutes.

        The one that matters is DETERMINISM. The embedding endpoint is not
        bit-deterministic -- phase5d measured 1.2e-3 of drift per component
        between two calls on one string -- so the same question asked twice in
        one gate run could previously land either side of the floor and flip a
        check that nobody had touched. One vector per string per process removes
        that source of flapping entirely. Nothing is cached across processes, so
        a rebuilt corpus or a changed pin is never served a stale vector.
        """
        cached = self._query_cache.get(text)
        if cached is None:
            cached = self.embedder.query(text)
            self._query_cache[text] = cached
        return cached

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
        include_decompositions: bool = False,
    ) -> Result:
        """Rank the corpus against one question. The THRESHOLD path.

        `vectors` and `query_vector` exist for the D5.1 experiment, which runs
        THIS function against a different document matrix (the bare-sentence
        arm) rather than a second copy of the scoring logic.

        DECOMPOSITIONS ARE EXCLUDED HERE BY DEFAULT, and this is a real design
        decision rather than a convenience -- see WPD6_REPORT §D6.1.

        `RELEVANCE_THRESHOLD` is 0.62 because the D5.1 experiment measured it,
        over the findings corpus, and the property it was chosen to give is that
        an out-of-scope question clears nothing. Adding 36,218 decompositions
        breaks that property, measurably and by construction: a depth-1
        decomposition opens by naming its slice ("Within district Cuttack,
        planned cost totals ..."), so "What is the price of onions in Cuttack
        market?" reaches cosine 0.6256 against one -- above the floor on cosine
        alone -- where over findings it reached 0.488.

        A threshold carries evidence only for the corpus it was fitted on.
        Rather than move the number to fit new data, which is the manoeuvre D42
        ruling 5 exists to forbid, this path keeps the corpus the number was
        fitted on. `pool()` -- the judged path, which is production -- searches
        everything, because there the last word belongs to the judge and not to
        a comparison.

        The visible cost is stated rather than hidden: when the judge is
        unreachable and a turn falls back here, a decompose question is answered
        from findings alone. Degrading to a thinner answer is the right failure;
        degrading to a confident wrong one is not.
        """
        threshold = config.RELEVANCE_THRESHOLD if threshold is None else threshold
        floor = config.QUALITY_FLOOR if quality_floor is None else quality_floor
        matrix = self.corpus.vectors if vectors is None else vectors
        # The two corpora are concatenated findings-first, so the cut is a row
        # index rather than a per-record test inside the scoring loop.
        limit = (len(matrix) if (include_decompositions or vectors is not None)
                 else self.corpus.meta.get("findings", len(matrix)))

        slots = self.extractor.extract(question)
        if query_vector is None:
            query_vector = self.query_vector(slots.expanded)

        matrix = matrix[:limit]
        cosines = matrix @ np.asarray(query_vector, dtype=np.float32)

        if use_boost:
            boost, why = self.structural_boost(slots)
            boost = boost[:limit]
        else:
            boost, why = np.zeros(len(cosines), dtype=np.float32), {}

        total = cosines + boost
        # `best_cosine` is reported over the SAME rows that were scored, so the
        # gate's "best cosine is below the threshold" evidence describes the
        # comparison that actually happened.
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

        THE POOL IS SHARED BETWEEN THE TWO CORPORA, and it has to be, because
        truncation is not a neutral operation when one corpus is eight times the
        size of the other. Measured on the first build: for "How is Chikilli
        doing?", "Is spending on track?", "How is Barpali block doing?" and
        "Where is money planned but not spent?", the top 100 by score was
        **100% decompositions and zero findings** -- the judge never saw a mined
        pattern for any of them, so it could not have kept one. That is not the
        decomposition being ranked higher on the merits; it is 36,218 records
        crowding out 4,239 at the cut.

        So each corpus contributes up to half the slots, and whichever has fewer
        gives its unused slots back to the other. This is the SAME argument the
        diversity rule above already makes -- collapse before truncating,
        because truncation must not spend all its slots on one class of record
        -- applied to corpus membership instead of to duplicate sentences.

        It does not privilege either kind, and the distinction matters for D6.1.
        Ranking is untouched: the merged list is re-sorted by the one score, the
        judge rules on relevance alone, and it routinely keeps zero of one kind.
        What the reservation changes is only which candidates get to be
        considered.
        """
        floor = config.CANDIDATE_FLOOR if floor is None else floor
        size = config.CANDIDATE_POOL if size is None else size

        slots = self.extractor.extract(question)
        if query_vector is None:
            query_vector = self.query_vector(slots.expanded)

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
        kept = share_pool_between_corpora(hits, size)
        return Result(slots=slots, hits=kept, considered=len(cosines),
                      best_cosine=float(cosines.max()) if len(cosines) else 0.0,
                      threshold=floor, collapsed_count=collapsed, capped=capped)


def share_pool_between_corpora(hits: list, size: int) -> list:
    """Truncate `hits` to `size` without letting one corpus crowd out the other.

    Each kind may take up to half the slots; whichever has fewer than its half
    hands the remainder back, so a question that only findings can answer still
    gets a pool of `size` findings and vice versa. The survivors are returned in
    SCORE ORDER, not grouped by kind — the judge reads one ranked list and is
    never told which file a candidate came from.

    See `Retriever.pool` for the measurement that made this necessary.
    """
    if len(hits) <= size:
        return hits
    findings = [h for h in hits if not h.finding.is_decomposition]
    decompositions = [h for h in hits if h.finding.is_decomposition]

    half = size // 2
    n_find = min(len(findings), max(half, size - len(decompositions)))
    n_dec = min(len(decompositions), size - n_find)
    # A short second corpus gives its slots back to the first.
    n_find = min(len(findings), size - n_dec)

    kept = findings[:n_find] + decompositions[:n_dec]
    kept.sort(key=lambda h: -h.score)
    return kept


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
