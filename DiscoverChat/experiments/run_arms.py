#!/usr/bin/env python
"""WP-D5 D5.1 — the experiment that decides the retrieval design.

Three arms, one scoring function:

  A  bare        the engine sentence embedded alone
  B  enriched    the enriched retrieval text (D42 ruling 7)
  C  hybrid      enriched + the structural slot-hit boost (D42 ruling 4)

Every arm calls `retrieval.Retriever.score`, the SHIPPED function, with a
different document matrix and `use_boost` on or off. Nothing here re-implements
scoring, so what is measured is the code that will run in production.

WHAT IS MEASURED MECHANICALLY, AND WHY THAT IS HONEST
-----------------------------------------------------
Three of the six question kinds have a gold set that is a property of the
CORPUS, not of anybody's opinion, so they are scored here and the numbers stand
on their own:

  geo      does the answer contain a finding where the officer's own place is
           the subject in its own right (hit-rate), and what share of what was
           shown names the place at all (the irrelevant-shown counterpart)
  measure  what share of what was shown was actually mined on the measure asked
           about
  none     did anything at all come back (any answer is a false answer)

The remaining three kinds -- vague, open, why -- have no mechanical right
answer, and the brief is explicit that the operator labels the FULL relevant set
per question. `label_sheet.py` emits those, pooled across all three arms so the
labelling is arm-blind.

A NOTE ON CIRCULARITY, STATED RATHER THAN HIDDEN
------------------------------------------------
Arm C boosts findings whose geography matches the question, and the geo gold is
"findings whose geography matches the question". Arm C is therefore expected to
win the hit-rate; that is not evidence, it is arithmetic. The evidence is in the
two numbers beside it: whether arm B ALREADY reaches the place-specific findings
without help (in which case the boost buys nothing and D42 says drop it), and
what the boost costs in irrelevant-shown rate. A boost that lifts hit-rate and
leaves precision alone has earned its place; one that lifts hit-rate by flooding
the answer with findings that merely mention the place has not.

Run from the repo root, in the LOCAL MIRROR (D6):
    python DiscoverChat/experiments/run_arms.py
    python DiscoverChat/experiments/run_arms.py --no-cache   (re-embed everything)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.ERROR)

from DiscoverChat import config, corpus as corpus_mod          # noqa: E402
from DiscoverChat.retrieval import Retriever                    # noqa: E402

QUESTIONS_PATH = HERE / "questions.json"
CACHE_DIR = HERE / ".cache"
RESULTS_PATH = HERE / "arm_results.json"

# The threshold sweep. The experiment's job is to SET the operating point, so it
# cannot assume one: every arm is reported across the whole range and the
# chosen value is argued from the table, not from config.py.
SWEEP = [round(0.40 + 0.01 * i, 2) for i in range(41)]      # 0.40 .. 0.80


# ── arm document matrices ────────────────────────────────────────────────────

def _cache_path(name: str, texts: list) -> Path:
    sig = hashlib.sha256()
    sig.update(f"{config.EMBED_MODEL}|{config.EMBED_DIMS}|{name}".encode())
    for t in texts:
        sig.update(b"\x00")
        sig.update(t.encode("utf-8"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}_{sig.hexdigest()[:16]}.npy"


def bare_matrix(corpus, embedder, use_cache=True) -> np.ndarray:
    """Arm A's document matrix: the engine sentence, embedded alone.

    Only the 1,775 DISTINCT sentences are embedded; the 4,239 rows are filled
    from that map. That is not an optimisation -- it is the arm's own finding
    made concrete. 2,464 records have no vector of their own under arm A
    because they have no text of their own, and retrieval cannot separate what
    the text does not separate.
    """
    texts = [r["bare_text"] for r in corpus.records]
    path = _cache_path("bare", texts)
    if use_cache and path.exists():
        return np.load(path)

    distinct = sorted({t for t in texts})
    print(f"    arm A: embedding {len(distinct):,} distinct sentences "
          f"for {len(texts):,} records")
    vectors = embedder.documents(distinct)
    by_text = {t: v for t, v in zip(distinct, vectors)}
    matrix = np.stack([by_text[t] for t in texts]).astype(np.float32)
    np.save(path, matrix)
    return matrix


# ── mechanical gold ──────────────────────────────────────────────────────────

def geo_gold(corpus, place: str) -> tuple:
    """(specific rows, any rows) for a place. See questions.json gold_kinds."""
    specific, any_row = set(), set()
    for finding in corpus.all():
        geo = finding.geography
        keys = list(geo["gp_names"]) + list(geo["blocks"]) + list(geo["districts"])
        if place not in keys:
            continue
        any_row.add(finding.row)
        # Roles are keyed by LGD code for GPs and by canonical name otherwise.
        role_key = place
        if place in geo["gp_names"]:
            role_key = geo["gp_lgd_codes"][geo["gp_names"].index(place)]
        if geo["roles"].get(role_key) != "follows_pattern":
            specific.add(finding.row)
    return specific, any_row


def measure_gold(corpus, measures: list) -> set:
    wanted = set(measures)
    return {f.row for f in corpus.all() if wanted & set(f.measures)}


# ── the run ──────────────────────────────────────────────────────────────────

def run(no_cache: bool = False) -> dict:
    corpus = corpus_mod.load()
    retriever = Retriever()
    embedder = retriever.embedder

    questions = json.load(open(QUESTIONS_PATH, encoding="utf-8"))["questions"]
    print(f"  corpus {len(corpus):,} records; {len(questions)} questions")

    print("  building arm document matrices ...")
    matrices = {
        "A_bare":     bare_matrix(corpus, embedder, use_cache=not no_cache),
        "B_enriched": corpus.vectors,
        "C_hybrid":   corpus.vectors,
    }
    use_boost = {"A_bare": False, "B_enriched": False, "C_hybrid": True}

    # ONE query vector per question, shared by all three arms. The arms differ
    # in the DOCUMENT text and in the boost; embedding the query three times
    # would add the endpoint's own 1.2e-3 non-determinism to the comparison.
    print("  embedding queries ...")
    qvecs = {}
    for q in questions:
        slots = retriever.extractor.extract(q["text"])
        qvecs[q["id"]] = (slots, embedder.query(slots.expanded))

    rows = []
    for q in questions:
        slots, qv = qvecs[q["id"]]
        record = {"id": q["id"], "kind": q["kind"], "text": q["text"],
                  "expanded": slots.expanded,
                  "slots": {"gp": slots.gp_names, "blocks": slots.blocks,
                            "districts": slots.districts,
                            "measures": slots.measures},
                  "arms": {}}
        for arm, matrix in matrices.items():
            # Threshold 0 and no cap: the sweep is applied afterwards, so one
            # scoring pass serves every operating point.
            result = retriever.score(
                q["text"], use_boost=use_boost[arm], threshold=-1.0,
                query_vector=qv, vectors=matrix, collapse=True,
            )
            record["arms"][arm] = [
                {"row": h.finding.row, "id": h.finding.id, "score": h.score,
                 "cosine": h.cosine, "boost": h.boost,
                 "collapsed": len(h.collapsed)}
                for h in result.hits[:60]
            ]
        rows.append(record)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_records": len(corpus),
        "candidate_set_id": corpus.meta.get("candidate_set_id"),
        "embedding_pin": corpus.meta.get("embedding_pin"),
        "knobs": config.knobs(),
        "sweep": SWEEP,
        "questions": rows,
        "metrics": metrics(corpus, questions, rows),
    }


def metrics(corpus, questions, rows) -> dict:
    """The three mechanically-scored kinds, per arm, across the sweep."""
    by_id = {q["id"]: q for q in questions}
    gold_geo, gold_measure = {}, {}
    for q in questions:
        if q["kind"] == "geo":
            gold_geo[q["id"]] = geo_gold(corpus, q["place"])
        elif q["kind"] == "measure":
            gold_measure[q["id"]] = measure_gold(corpus, q["measures"])

    out = {}
    for arm in ("A_bare", "B_enriched", "C_hybrid"):
        per_threshold = []
        for threshold in SWEEP:
            geo_hits = geo_shown = geo_named = geo_specific_shown = 0
            geo_n = 0
            mea_shown = mea_right = 0
            mea_answered = mea_n = 0
            none_answered = none_n = 0
            for row in rows:
                shown = [h for h in row["arms"][arm]
                         if h["score"] >= threshold][:config.ANSWER_CAP]
                kind = by_id[row["id"]]["kind"]
                if kind == "geo":
                    geo_n += 1
                    specific, any_row = gold_geo[row["id"]]
                    rows_shown = {h["row"] for h in shown}
                    if rows_shown & specific:
                        geo_hits += 1
                    geo_shown += len(rows_shown)
                    geo_named += len(rows_shown & any_row)
                    geo_specific_shown += len(rows_shown & specific)
                elif kind == "measure":
                    mea_n += 1
                    gold = gold_measure[row["id"]]
                    rows_shown = {h["row"] for h in shown}
                    mea_shown += len(rows_shown)
                    mea_right += len(rows_shown & gold)
                    if rows_shown:
                        mea_answered += 1
                elif kind == "none":
                    none_n += 1
                    if shown:
                        none_answered += 1
            per_threshold.append({
                "threshold": threshold,
                "geo_hit_rate": _ratio(geo_hits, geo_n),
                "geo_place_named_precision": _ratio(geo_named, geo_shown),
                "geo_specific_per_question": round(geo_specific_shown / geo_n, 2)
                if geo_n else 0.0,
                "geo_shown_per_question": round(geo_shown / geo_n, 2) if geo_n else 0.0,
                "measure_precision": _ratio(mea_right, mea_shown),
                "measure_answered_rate": _ratio(mea_answered, mea_n),
                "none_false_answer_rate": _ratio(none_answered, none_n),
            })
        out[arm] = per_threshold
    return out


def _ratio(num, den):
    return round(num / den, 4) if den else 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    payload = run(no_cache=args.no_cache)
    RESULTS_PATH.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"  wrote {RESULTS_PATH}")

    print("\n  ---- mechanically scored, at a range of thresholds ----")
    header = ("  thr  | arm         | geo hit | place-named | measure prec | "
              "false answers | shown/q")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for threshold in (0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70):
        for arm in ("A_bare", "B_enriched", "C_hybrid"):
            m = next(x for x in payload["metrics"][arm]
                     if abs(x["threshold"] - threshold) < 1e-9)
            print(f"  {threshold:.2f} | {arm:<11} | {m['geo_hit_rate']:>7.1%} | "
                  f"{m['geo_place_named_precision']:>11.1%} | "
                  f"{m['measure_precision']:>12.1%} | "
                  f"{m['none_false_answer_rate']:>13.1%} | "
                  f"{m['geo_shown_per_question']:>7.1f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
