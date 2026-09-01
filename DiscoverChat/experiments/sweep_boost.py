#!/usr/bin/env python
"""WP-D5 D5.1 — boost-weight sweep, on top of run_arms.

`run_arms.py` answers "does the boost help at all". This answers the follow-up
the first table raises: the operating point at threshold 0.62 leaves 47% of
place questions with nothing place-specific, so is a HEAVIER boost the fix?

The question is whether the boost SEPARATES legitimate place questions from
out-of-scope ones that merely name a place. It cannot separate them if it moves
both by the same amount -- and the binding case is real: "Who is the current
Sarpanch of Chikilli?" is a question the analysis has nothing on, and it names a
Gram Panchayat, so every point of geography boost lifts it exactly as far as it
lifts "How is Chikilli doing?".

Query vectors are cached, so a sweep costs nothing after the first run.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import config, corpus as corpus_mod          # noqa: E402
from DiscoverChat.retrieval import Retriever                    # noqa: E402
from DiscoverChat.experiments.run_arms import (                 # noqa: E402
    QUESTIONS_PATH, CACHE_DIR, geo_gold, measure_gold, _ratio,
)

QVEC_CACHE = CACHE_DIR / "query_vectors.npz"
OUT_PATH = HERE / "boost_sweep.json"

GEO_WEIGHTS = [0.00, 0.03, 0.06, 0.09, 0.12, 0.16, 0.20]
THRESHOLDS = [round(0.56 + 0.01 * i, 2) for i in range(15)]     # 0.56 .. 0.70


def query_vectors(retriever, questions) -> dict:
    if QVEC_CACHE.exists():
        loaded = np.load(QVEC_CACHE)
        if set(loaded.files) == {q["id"] for q in questions}:
            return {k: loaded[k] for k in loaded.files}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for q in questions:
        slots = retriever.extractor.extract(q["text"])
        out[q["id"]] = retriever.embedder.query(slots.expanded)
    np.savez(QVEC_CACHE, **out)
    return out


def main() -> int:
    corpus = corpus_mod.load()
    retriever = Retriever()
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))["questions"]
    qvecs = query_vectors(retriever, questions)

    gold_geo = {q["id"]: geo_gold(corpus, q["place"])
                for q in questions if q["kind"] == "geo"}
    gold_measure = {q["id"]: measure_gold(corpus, q["measures"])
                    for q in questions if q["kind"] == "measure"}

    results = []
    for geo_w in GEO_WEIGHTS:
        config.GEO_BOOST = geo_w
        config.GEO_SUBSPACE_BONUS = geo_w / 3.0
        scored = {}
        for q in questions:
            result = retriever.score(q["text"], use_boost=True, threshold=-1.0,
                                     query_vector=qvecs[q["id"]], collapse=True)
            scored[q["id"]] = [(h.finding.row, h.score) for h in result.hits[:60]]

        for threshold in THRESHOLDS:
            geo_hits = geo_n = geo_shown = geo_named = 0
            none_answered = none_n = 0
            mea_shown = mea_right = 0
            worst_none = 0.0
            for q in questions:
                shown = {row for row, s in scored[q["id"]]
                         if s >= threshold}
                shown = set(list(shown)[:config.ANSWER_CAP])
                if q["kind"] == "geo":
                    geo_n += 1
                    specific, any_row = gold_geo[q["id"]]
                    if shown & specific:
                        geo_hits += 1
                    geo_shown += len(shown)
                    geo_named += len(shown & any_row)
                elif q["kind"] == "none":
                    none_n += 1
                    top = scored[q["id"]][0][1] if scored[q["id"]] else 0.0
                    worst_none = max(worst_none, top)
                    if shown:
                        none_answered += 1
                elif q["kind"] == "measure":
                    gold = gold_measure[q["id"]]
                    mea_shown += len(shown)
                    mea_right += len(shown & gold)
            results.append({
                "geo_boost": geo_w, "threshold": threshold,
                "geo_hit_rate": _ratio(geo_hits, geo_n),
                "geo_place_named_precision": _ratio(geo_named, geo_shown),
                "measure_precision": _ratio(mea_right, mea_shown),
                "none_false_answer_rate": _ratio(none_answered, none_n),
                "highest_out_of_scope_score": round(worst_none, 4),
            })

    OUT_PATH.write_text(json.dumps(results, indent=1), encoding="utf-8")

    print("  The question: can a heavier boost buy geo recall without buying")
    print("  false answers? For each boost weight, the best geo hit-rate that")
    print("  still keeps the out-of-scope questions silent.\n")
    print("   geo boost | safe threshold | geo hit | place-named | measure prec | "
          "top out-of-scope")
    print("   " + "-" * 88)
    for geo_w in GEO_WEIGHTS:
        rows = [r for r in results
                if r["geo_boost"] == geo_w and r["none_false_answer_rate"] == 0.0]
        if not rows:
            print(f"   {geo_w:>9.2f} | none in range -- every threshold answers "
                  f"an out-of-scope question")
            continue
        best = max(rows, key=lambda r: (r["geo_hit_rate"], -r["threshold"]))
        print(f"   {geo_w:>9.2f} | {best['threshold']:>14.2f} | "
              f"{best['geo_hit_rate']:>7.1%} | "
              f"{best['geo_place_named_precision']:>11.1%} | "
              f"{best['measure_precision']:>12.1%} | "
              f"{best['highest_out_of_scope_score']:>16.3f}")
    print(f"\n  wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
