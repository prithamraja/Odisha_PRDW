"""WP-D2c T3: the determinism gate on the mining engine.

Two claims have to hold before a parallel or bounded run may be trusted, and
both are checked here by running the engine rather than by reading it.

  1. HASH STABILITY. Two runs of the same view, same settings, produce the
     same candidates. This is D26c: view2's candidate file hashed differently
     on every run while view1's and view3's reproduced exactly. The cause was
     not in the engine -- DuckDB writes view2's zero-filled cross join in a
     different ROW ORDER on every build -- so the fix is that the engine sorts
     its frame into a canonical order on load and orders its output by content
     rather than by arrival. This checks that both runs agree.

  2. SINGLE-PROCESS == PARALLEL. Sharding the priority queue across processes
     changes the order subspaces are visited in and gives each worker its own
     caches and its own HDP-dedup set. None of that may change the answer. The
     comparison is made on a fixed subset for the wide view, which is what the
     brief asks for -- the point is that order does not matter, and it takes
     the whole queue to prove nothing about that which a subset does not.

The comparison is on the CONTENT hash (phase2_engine.candidates_content_hash:
every candidate's canonical key and score, order-independent) and, for the
stability check, on the bytes of the written file as well.

Usage:
    python check_determinism.py --base <Insights dir> [--workers 4]
        [--views view1,view2,view3] [--subset 40]

Exits non-zero on any failure, so it can gate a run.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import tempfile

fails = []


def check(ok, label, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)


def file_hash(path: str) -> str:
    with io.open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--views", default="view1,view2,view3")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--subset", type=int, default=40,
                    help="subspaces mined for the parallel comparison on view1")
    ap.add_argument("--alt-parquet", default=None,
                    help="view=path -- mine the view from a SECOND build of the "
                         "same view and require the same candidates. This is "
                         "the direct test for D26c: two builds of view2 have "
                         "identical content in a different row order.")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    sys.path.insert(0, os.path.join(base, "src"))

    import phase4b_engine as p4b
    from phase2_engine import (VIEW1_CONFIG, candidates_content_hash,
                               save_candidates)
    from phase4a_engine import VIEW2_CONFIG, VIEW3_CONFIG

    CFG = {"view1": VIEW1_CONFIG, "view2": VIEW2_CONFIG, "view3": VIEW3_CONFIG}
    views = args.views.split(",")
    # view1 is the wide one; the two small views are cheap enough to run whole
    SUBSET = {"view1": args.subset}
    results = {}

    print("\n=== 1. two runs of the same view agree, byte for byte ===")
    tmp = tempfile.mkdtemp(prefix="wpd2c_determinism_")
    for view in views:
        limit = SUBSET.get(view)
        hashes, files = [], []
        for run in (1, 2):
            cands, diag = p4b.run_engine(
                CFG[view], time_budget_seconds=36000, workers=1,
                subspace_limit=limit)
            path = os.path.join(tmp, f"{view}_run{run}.json")
            save_candidates(cands, path)
            hashes.append(diag["content_hash"])
            files.append(file_hash(path))
        results[view] = (hashes[0], len(cands))
        check(hashes[0] == hashes[1], f"{view}: content hash stable across two runs",
              f"{hashes[0][:16]} vs {hashes[1][:16]}")
        check(files[0] == files[1], f"{view}: candidate FILE identical across two runs",
              f"{files[0][:16]} vs {files[1][:16]}")

    print(f"\n=== 2. {args.workers} workers produce what one process produces ===")
    for view in views:
        limit = SUBSET.get(view)
        cands, diag = p4b.run_engine(
            CFG[view], time_budget_seconds=36000, workers=args.workers,
            subspace_limit=limit)
        expected_hash, expected_n = results[view]
        check(diag["content_hash"] == expected_hash,
              f"{view}: parallel content hash equals the single-process one"
              + (f" (subset of {limit} subspaces)" if limit else ""),
              f"{diag['content_hash'][:16]} vs {expected_hash[:16]}")
        check(len(cands) == expected_n,
              f"{view}: same candidate count", f"{len(cands)} vs {expected_n}")

    if args.alt_parquet:
        print("\n=== 3. a second BUILD of the same view mines the same candidates ===")
        view, _, alt = args.alt_parquet.partition("=")
        cfg = CFG[view]
        original = cfg.parquet_path
        print(f"  build A {file_hash(original)[:16]}  {os.path.basename(original)}")
        print(f"  build B {file_hash(alt)[:16]}  {os.path.basename(alt)}")
        check(file_hash(original) != file_hash(alt),
              f"{view}: the two builds really are different files "
              f"(otherwise this proves nothing)")
        try:
            cfg.parquet_path = alt
            cands, diag = p4b.run_engine(cfg, time_budget_seconds=36000, workers=1,
                                         subspace_limit=SUBSET.get(view))
        finally:
            cfg.parquet_path = original
        expected_hash, expected_n = results.get(view, (None, None))
        check(expected_hash is not None and diag["content_hash"] == expected_hash,
              f"{view}: candidates are identical across two builds",
              f"{diag['content_hash'][:16]} vs "
              f"{(expected_hash or '')[:16]}")

    print(f"\n{'=' * 60}")
    print(f"{len(fails)} failure(s)" + (": " + "; ".join(fails) if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
