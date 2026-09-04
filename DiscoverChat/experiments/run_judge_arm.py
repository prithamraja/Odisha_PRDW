#!/usr/bin/env python
"""WP-D5 D5.1b — arm D: floor 0.50, top 100, an LLM judge decides.

Arm C (the shipped path) answers a place question when a finding clears 0.62.
Arm D drops the floor to 0.50, pools the top 100 after the diversity collapse,
and asks a judge which of them actually answer the question.

Scored on the SAME 60 questions and the SAME mechanical gold as arms A–C, so the
comparison is like for like. The three numbers that decide it:

  geo hit rate            does the answer contain a finding where the officer's
                          own place is the subject in its own right
  place-named precision   of what was shown, how much names the place at all
  FALSE ANSWER RATE       of the 5 questions the analysis has nothing on, how
                          many got an answer. **This is the one that matters.**
                          Arm C scores 0% here by construction -- a threshold
                          cannot be talked round. Arm D's floor no longer stops
                          4 of those 5, so the judge is the only guard left, and
                          this number is what it costs or saves.

Run:  python DiscoverChat/experiments/run_judge_arm.py
Out:  DiscoverChat/experiments/judge_arm_results.json
"""
from __future__ import annotations

import json
import logging
import statistics
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import config, corpus as corpus_mod, judge   # noqa: E402
from DiscoverChat.retrieval import Retriever                    # noqa: E402
from DiscoverChat.experiments.run_arms import (                 # noqa: E402
    QUESTIONS_PATH, CACHE_DIR, geo_gold, measure_gold, _ratio,
)

OUT = HERE / "judge_arm_results.json"
QVEC_CACHE = CACHE_DIR / "query_vectors.npz"


def main() -> int:
    corpus = corpus_mod.load()
    retriever = Retriever()
    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))["questions"]

    qvecs = None
    if QVEC_CACHE.exists():
        loaded = np.load(QVEC_CACHE)
        if set(loaded.files) == {q["id"] for q in questions}:
            qvecs = {k: loaded[k] for k in loaded.files}
    if qvecs is None:
        qvecs = {}
        for q in questions:
            slots = retriever.extractor.extract(q["text"])
            qvecs[q["id"]] = retriever.embedder.query(slots.expanded)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(QVEC_CACHE, **qvecs)

    rows = []
    for i, q in enumerate(questions, start=1):
        pooled = retriever.pool(q["text"], query_vector=qvecs[q["id"]])
        by_id = {h.finding.id: h for h in pooled.hits}
        selection = judge.select(q["text"], [h.finding for h in pooled.hits],
                                 corpus_size=len(corpus),
                                 turn_id=f"armD-{q['id']}")
        kept_rows = [by_id[i].finding.row for i in selection.kept_ids
                     if i in by_id]
        rows.append({
            "id": q["id"], "kind": q["kind"], "text": q["text"],
            "pool": len(pooled.hits),
            "pool_min_score": round(min((h.score for h in pooled.hits),
                                        default=0.0), 4),
            "kept": selection.kept_ids, "kept_rows": kept_rows,
            "judge": selection.as_dict(),
        })
        print(f"  {i:>2}/{len(questions)} {q['text'][:42]:<42} "
              f"pool {len(pooled.hits):>3} -> kept {len(kept_rows):>2} "
              f"[{selection.source}]")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "judge_model": config.JUDGE_MODEL,
        # WP-D9: the wording is evidence too, not just the id.
        "judge_prompt_variant": config.JUDGE_PROMPT_VARIANT,
        "judge_prompt_sha256": judge.prompt_sha256(),
        "candidate_floor": config.CANDIDATE_FLOOR,
        "candidate_pool": config.CANDIDATE_POOL,
        "questions": rows,
        "metrics": metrics(corpus, questions, rows),
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    m = payload["metrics"]
    print("\n  ---- arm D (floor 0.50, top 100, judged) ----")
    print(f"  geo hit rate ................ {m['geo_hit_rate']:.1%}"
          f"   (arm C at 0.62: 52.9%)")
    print(f"  place-named precision ....... {m['geo_place_named_precision']:.1%}"
          f"   (arm C: 98.5%)")
    print(f"  measure precision ........... {m['measure_precision']:.1%}"
          f"   (arm C: 94.1%)")
    print(f"  FALSE ANSWER RATE ........... {m['none_false_answer_rate']:.1%}"
          f"   (arm C: 0.0%)  <- the one that matters")
    print(f"  findings shown per question . {m['shown_per_geo_question']:.1f}"
          f"   (arm C: 4.0)")
    print(f"  judge fell back to threshold  {m['judge_fallbacks']} of "
          f"{len(rows)} turns")
    print(f"  ids invented by the judge ... {m['hallucinated_ids']}")
    print(f"\n  wrote {OUT}")
    return 0



# ── WP-D9 (d): are the kept findings distinct, or the same point re-sliced? ──
# The brief's key: (measure, breakdown, pattern type). A decomposition has no
# pattern_type and calls its breakdown `dimension`, so it is normalised onto the
# same three-part key rather than excluded -- an answer that keeps six
# decompositions of one measure over one dimension is restating exactly as much
# as one that keeps six findings.
def restatement_key(record) -> tuple:
    d = record.data
    if record.is_decomposition:
        return (d.get("measure"), d.get("dimension"), "DECOMPOSITION")
    return (d.get("measure"), d.get("breakdown"), d.get("pattern_type"))


def restatement_share(corpus, rows) -> tuple:
    """Fraction of kept findings that share a key with another KEPT finding in
    the SAME answer. Counted over answers with 2+ kept findings: a single-finding
    answer cannot restate itself, and including it would dilute the measure
    toward zero exactly when the judge is being most selective."""
    shared = total = 0
    for row in rows:
        # `get` takes a finding id; these are row indices, so `finding` it is.
        kept = [corpus.finding(r) for r in row["kept_rows"]]
        if len(kept) < 2:
            continue
        keys = [restatement_key(k) for k in kept]
        for key in keys:
            total += 1
            if keys.count(key) > 1:
                shared += 1
    return _ratio(shared, total), shared, total


def metrics(corpus, questions, rows) -> dict:
    by_id = {q["id"]: q for q in questions}
    geo_hits = geo_n = geo_shown = geo_named = 0
    mea_shown = mea_right = 0
    none_answered = none_n = 0
    fallbacks = hallucinated = 0

    for row in rows:
        q = by_id[row["id"]]
        shown = set(row["kept_rows"])
        if row["judge"]["source"] != "judge":
            fallbacks += 1
        hallucinated += len(row["judge"]["hallucinated_ids"])
        if q["kind"] == "geo":
            geo_n += 1
            specific, any_row = geo_gold(corpus, q["place"])
            if shown & specific:
                geo_hits += 1
            geo_shown += len(shown)
            geo_named += len(shown & any_row)
        elif q["kind"] == "measure":
            gold = measure_gold(corpus, q["measures"])
            mea_shown += len(shown)
            mea_right += len(shown & gold)
        elif q["kind"] == "none":
            none_n += 1
            if shown:
                none_answered += 1

    # WP-D9: what the completeness instruction is expected to move.
    kept_counts = [len(row["kept_rows"]) for row in rows]
    answered = [n for n in kept_counts if n]
    cap_bound = sum(1 for n in kept_counts if n >= config.ANSWER_CAP)
    share, share_shared, share_total = restatement_share(corpus, rows)

    return {
        "geo_hit_rate": _ratio(geo_hits, geo_n),
        "geo_place_named_precision": _ratio(geo_named, geo_shown),
        "measure_precision": _ratio(mea_right, mea_shown),
        "none_false_answer_rate": _ratio(none_answered, none_n),
        "shown_per_geo_question": round(geo_shown / geo_n, 2) if geo_n else 0.0,
        "judge_fallbacks": fallbacks,
        "hallucinated_ids": hallucinated,
        # WP-D9 D9.1
        "answer_cap": config.ANSWER_CAP,
        # Two medians on purpose: over ANSWERED questions, and over all
        # of them. WP-D5 quoted 3 (all 61, empties included); the same
        # set reads 4 over the 51 that kept anything. Reporting one
        # without saying which is how a baseline gets misread.
        "kept_median": (statistics.median(answered) if answered else 0),
        "kept_median_all": (statistics.median(kept_counts) if kept_counts else 0),
        "answers_with_findings": len(answered),
        "kept_max": (max(kept_counts) if kept_counts else 0),
        "kept_mean": round(sum(kept_counts) / len(kept_counts), 2) if rows else 0,
        "cap_binding_rate": _ratio(cap_bound, len(rows)),
        "restatement_share": share,
        "restatement_counts": {"shared": share_shared, "of_kept": share_total},
    }


if __name__ == "__main__":
    sys.exit(main())
