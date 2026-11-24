#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D17: compare two breakdown (decomposition) stores, record by record.

    python handoffs/WPD17_cautions/compare_stores.py OLD_DIR NEW_DIR --expect identical
    python handoffs/WPD17_cautions/compare_stores.py OLD_DIR NEW_DIR --expect cautions-removed

Each DIR holds decompose_corpus.json.gz, its vector parts and its stamp.

identical          T0: every record, every field, the order, and every vector
                   bit for bit the same.
cautions-removed   T3: the same ids in the same order; every changed sentence
                   is the old one minus exactly one of the four caution texts
                   from its end; every other field identical (except the
                   embed-text hash of exactly the changed records); the vector
                   of every unchanged record bit for bit the old one.

Writes <NEW_DIR>/../compare_<expect>.json next to this script's output folder
when --out is given. Exit 1 on any unexpected difference.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "Insights" / "src"))

import numpy as np                                                # noqa: E402
from phase5d_retrieval_corpus import read_corpus_json             # noqa: E402

CAUTIONS = [
    "A rise here is a rise in recording completeness unless the cashbook total "
    "rises with it; the linked share went from 2.7% to 53.2% across these six "
    "years.",
    "The sanctioned basis covers only the activities with a sanction record on "
    "file, about one in six.",
    "Only 17 completions are recorded in the whole sample, so this splits a "
    "near-empty column.",
    "A swap between the SC and ST components is suspected and unconfirmed; do "
    "not read one against the other.",
]
EXPECTED = {CAUTIONS[0]: 407, CAUTIONS[1]: 7759, CAUTIONS[2]: 1417, CAUTIONS[3]: 1685}


def load(directory: Path):
    corpus = read_corpus_json(str(directory / "decompose_corpus.json.gz"))
    stamp = json.loads((directory / "decompose_corpus_stamp.json").read_text(encoding="utf-8"))
    parts = [np.load(directory / p["file"]) for p in stamp["vector_storage"]["parts"]]
    vectors = np.concatenate(parts) if parts else None
    return corpus, stamp, vectors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--expect", choices=("identical", "cautions-removed"), required=True)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    old, old_stamp, old_v = load(Path(args.old))
    new, new_stamp, new_v = load(Path(args.new))
    o_recs, n_recs = old["records"], new["records"]
    report = {"expect": args.expect, "records_old": len(o_recs), "records_new": len(n_recs)}
    problems = []

    if [r["finding_id"] for r in o_recs] != [r["finding_id"] for r in n_recs]:
        problems.append("the ids or their order differ")
    report["same_ids_same_order"] = not problems

    top_keys = sorted(set(old) | set(new))
    report["top_level_keys_differing"] = [k for k in top_keys
                                          if k != "records" and old.get(k) != new.get(k)]

    changed_by = Counter()
    field_diffs = Counter()
    changed_ids, other_kinds = [], []
    for o, n in zip(o_recs, n_recs):
        if o == n:
            continue
        diff = sorted(k for k in set(o) | set(n) if o.get(k) != n.get(k))
        if args.expect == "identical":
            field_diffs.update(diff)
            problems.append(f"{o['finding_id']}: {diff}")
            continue
        if diff not in (["embed_text_sha256", "sentence"], ["sentence"]):
            other_kinds.append({"id": o["finding_id"], "fields": diff})
            continue
        removed = None
        for c in CAUTIONS:
            if o["sentence"] == n["sentence"] + " " + c:
                removed = c
        if removed is None:
            other_kinds.append({"id": o["finding_id"], "fields": diff,
                                "old_tail": o["sentence"][-160:], "new_tail": n["sentence"][-160:]})
            continue
        changed_by[removed] += 1
        changed_ids.append(o["finding_id"])

    report["field_differences"] = dict(field_diffs)
    if args.expect == "cautions-removed":
        report["sentences_changed"] = sum(changed_by.values())
        report["by_caution"] = {c[:60]: changed_by[c] for c in CAUTIONS}
        report["by_caution_expected"] = {c[:60]: EXPECTED[c] for c in CAUTIONS}
        report["other_changes"] = other_kinds[:50]
        report["other_changes_count"] = len(other_kinds)
        if other_kinds:
            problems.append(f"{len(other_kinds)} records changed in another way")
        if dict(changed_by) != EXPECTED:
            problems.append(f"caution counts {dict(changed_by)} != expected")
        still = sum(1 for r in n_recs for c in CAUTIONS if c in r["sentence"])
        report["new_sentences_still_holding_a_caution"] = still
        if still:
            problems.append(f"{still} new sentences still hold a caution")

    # Vectors.
    if old_v is None or new_v is None or old_v.shape != new_v.shape:
        problems.append("vector matrices missing or of different shape")
    else:
        changed = set(changed_ids)
        same = moved = 0
        moved_unchanged = []
        for i, r in enumerate(o_recs):
            identical = np.array_equal(old_v[i].view(np.uint8), new_v[i].view(np.uint8))
            if r["finding_id"] in changed:
                moved += 0 if identical else 1
            else:
                if identical:
                    same += 1
                else:
                    moved_unchanged.append(r["finding_id"])
        report["vectors_unchanged_records_bit_identical"] = same
        report["vectors_unchanged_records_that_moved"] = moved_unchanged[:20]
        report["vectors_changed_records_reembedded"] = moved
        if moved_unchanged:
            problems.append(f"{len(moved_unchanged)} unchanged records got a new vector")
        if args.expect == "cautions-removed" and moved != len(changed):
            problems.append(f"only {moved} of {len(changed)} changed records have a new vector")

    report["candidate_set_old"] = old_stamp.get("candidate_set_id")
    report["candidate_set_new"] = new_stamp.get("candidate_set_id")
    if report["candidate_set_old"] != report["candidate_set_new"]:
        problems.append("the candidate set changed")
    report["stamp_keys_differing"] = sorted(k for k in set(old_stamp) | set(new_stamp)
                                            if old_stamp.get(k) != new_stamp.get(k))
    report["problems"] = problems
    report["result"] = "PASS" if not problems else "FAIL"
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
