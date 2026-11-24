#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D17 T3: what removing the cautions does to search.

    python handoffs/WPD17_cautions/pools.py <mirror> <out.json>

Run once in a mirror holding the OLD breakdown store and once in one holding
the NEW; compare with --compare A.json B.json. Query vectors are never
embedded twice: the 76 offline gate questions use the vectors stored by
WP-D15 (handoffs/WPD15_trial/offline_baseline_vectors.npy); the 53 held
questions use query_vectors_held.pkl beside this script (embedded once).
For each question: the top-100 pool of the judged path (ids, in order) and
the threshold path's hits (what the offline gate shows).
"""
import gzip
import json
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(mirror: str, out: str):
    sys.path.insert(0, mirror)
    import logging
    logging.basicConfig(level=logging.ERROR)
    import numpy as np
    from DiscoverChat.retrieval import Retriever
    from DiscoverChat import gates
    trial = Path(mirror) / "handoffs" / "WPD15_trial"
    with gzip.open(trial / "offline_baseline_answers.json.gz", "rt", encoding="utf-8") as fh:
        base = json.load(fh)
    vecs = np.load(trial / "offline_baseline_vectors.npy")
    cache = {t: vecs[i] for i, t in enumerate(base["vector_texts"])}
    held = json.loads((Path(mirror) / "DiscoverChat" / "experiments" / "judge_picks.json")
                      .read_text(encoding="utf-8"))["entries"]
    hv_path = HERE / "query_vectors_held.pkl"
    held_vecs = pickle.load(open(hv_path, "rb")) if hv_path.exists() else {}
    r = Retriever()
    for text, v in held_vecs.items():
        cache.setdefault(text, v)
    r._query_cache = cache
    questions = [("gate", q) for q in base["questions"]] + [("held:" + e["id"], e["question"]) for e in held]
    result = {}
    for kind, q in questions:
        pool = r.pool(q)
        score = r.score(q)
        result[q] = {"kind": kind, "pool": [h.finding.id for h in pool.hits],
                     "threshold_hits": [h.finding.id for h in score.hits],
                     "best_cosine": round(float(score.best_cosine), 6)}
    for e in held:                      # keep the vectors the run had to embed
        held_vecs.setdefault(e["question"], r._query_cache.get(e["question"]))
    pickle.dump({k: v for k, v in held_vecs.items() if v is not None}, open(hv_path, "wb"))
    result["_no_match"] = list(gates.NO_MATCH_QUESTIONS)
    result["_held"] = {e["question"]: [f["id"] for f in e.get("findings", [])] for e in held}
    Path(out).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(len(questions), "questions ->", out)


def compare(a_path: str, b_path: str, out: str):
    a = json.loads(Path(a_path).read_text(encoding="utf-8"))
    b = json.loads(Path(b_path).read_text(encoding="utf-8"))
    rows, left = [], []
    for q, x in a.items():
        if q.startswith("_"):
            continue
        y = b[q]
        sa, sb = set(x["pool"]), set(y["pool"])
        overlap = len(sa & sb) / max(1, len(sa | sb))
        same_top = len(sa & sb) / max(1, len(sa)) if sa else 1.0
        rows.append({"q": q, "kind": x["kind"], "pool_old": len(sa), "pool_new": len(sb),
                     "kept_share": round(same_top, 4), "jaccard": round(overlap, 4),
                     "threshold_old": len(x["threshold_hits"]),
                     "threshold_new": len(y["threshold_hits"])})
        if q in a["_held"]:
            gone = [i for i in a["_held"][q] if i not in sb]
            if gone:
                left.append({"q": q, "held_insights_out_of_pool": gone})
    no_match = []
    for q in a["_no_match"]:
        no_match.append({"q": q, "threshold_old": len(a[q]["threshold_hits"]),
                         "threshold_new": len(b[q]["threshold_hits"]),
                         "pool_old": len(a[q]["pool"]), "pool_new": len(b[q]["pool"])})
    import statistics
    summary = {
        "questions": len(rows),
        "pool_kept_share_middle": statistics.median(r["kept_share"] for r in rows),
        "pool_kept_share_lowest": min(r["kept_share"] for r in rows),
        "pools_identical": sum(1 for r in rows if r["jaccard"] == 1.0),
        "threshold_hits_changed": sum(1 for r in rows if r["threshold_old"] != r["threshold_new"]),
        "held_insights_out_of_pool": sum(len(x["held_insights_out_of_pool"]) for x in left),
        "held_questions_losing_an_insight": len(left),
        "no_match": no_match,
        "no_match_now_finds_something": [x["q"] for x in no_match
                                         if x["threshold_new"] > 0 and x["threshold_old"] == 0],
    }
    Path(out).write_text(json.dumps({"summary": summary, "left": left, "rows": rows},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        run(sys.argv[1], sys.argv[2])
