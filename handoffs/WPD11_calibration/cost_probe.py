"""WP-D11 T6.3 — the marginal cost of the six profile dimensions on view1.

WHY THIS EXISTS. B4 asks the operator to choose between the full seven-dimension
depth-2 view1 run and the subspace-filter-only fallback, "on the measurement".
The full re-mine's wall time alone does not support that choice: it confounds
two things, how much the new dimensions cost and how fast this machine is today
against the one WP-D2c measured 146.0 scopes/s on. A wall time that is 9x the
baseline could be a 9x dimension cost, or a 3x dimension cost on a machine
running 3x slower, and those imply opposite decisions.

So this probe runs the SAME view, the SAME depth, the SAME worker count and the
SAME number of subspaces under both dimension sets, back to back, on an
otherwise idle machine:

    A.  17 dimensions — VIEW1_CONFIG with the profile bands removed, i.e. the
        configuration WP-D2c measured
    B.  23 dimensions — VIEW1_CONFIG as WP-D11 ships it

and reports, for each: subspaces enumerated, subspaces surviving the impact
prune, data scopes behind them, scopes actually mined, and throughput. The
difference between A and B is the six dimensions and nothing else; A against
WP-D2c's 146.0 scopes/s is this machine against that one.

NOTHING IS WRITTEN to metainsights/ -- the probe calls run_engine directly and
discards the candidates. It cannot disturb a candidate set.

Usage:
    python handoffs/WPD11_calibration/cost_probe.py [--subspaces 150] [--workers 5]
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(BASE, "Insights", "src"))

import phase2_engine                                          # noqa: E402
from phase4b_engine import run_engine                         # noqa: E402

PROFILE = {"social_composition", "gp_size", "remoteness", "digital_readiness",
           "has_panchayat_bhawan", "has_csc", "plc_available"}


def variant(name, dims, args):
    cfg = phase2_engine.VIEW1_CONFIG
    original = list(cfg.dimensions)
    cfg.dimensions = dims
    print("\n" + "=" * 74)
    print(f"PROBE {name}: {len(dims)} dimensions, depth {cfg.max_subspace_depth}, "
          f"{args.workers} workers, top {args.subspaces} subspaces")
    print("=" * 74)
    t0 = time.time()
    try:
        candidates, diag = run_engine(
            cfg,
            time_budget_seconds=args.budget,
            workers=args.workers,
            subspace_limit=args.subspaces,
        )
    finally:
        cfg.dimensions = original
    el = time.time() - t0
    scopes = diag.get("scopes_evaluated") or diag.get("data_scopes_evaluated") or 0
    return {
        "name": name,
        "dims": len(dims),
        "elapsed": el,
        "scopes": scopes,
        "rate": scopes / el if el else 0,
        "candidates": len(candidates),
        "drained": diag.get("queue_drained"),
        "diag": diag,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subspaces", type=int, default=150,
                    help="mine only the N highest-impact subspaces, under each "
                         "configuration -- the probe's fixed unit of work")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--budget", type=int, default=36000)
    args = ap.parse_args()

    full = list(phase2_engine.VIEW1_CONFIG.dimensions)
    stripped = [d for d in full if d not in PROFILE]
    assert len(full) - len(stripped) in (6, 7), (len(full), len(stripped))

    a = variant("A (pre-amendment, 17 dims)", stripped, args)
    b = variant("B (WP-D11, 23 dims)", full, args)

    print("\n" + "=" * 74)
    print("MARGINAL COST OF THE PROFILE DIMENSIONS ON view1")
    print("=" * 74)
    print(f"{'':38s} {'A: 17 dims':>16s} {'B: 23 dims':>16s}")
    print(f"{'dimensions':38s} {a['dims']:>16,} {b['dims']:>16,}")
    print(f"{'subspaces mined (fixed)':38s} {args.subspaces:>16,} {args.subspaces:>16,}")
    print(f"{'data scopes behind them':38s} {a['scopes']:>16,} {b['scopes']:>16,}")
    print(f"{'elapsed (s)':38s} {a['elapsed']:>16.1f} {b['elapsed']:>16.1f}")
    print(f"{'throughput (scopes/s)':38s} {a['rate']:>16.1f} {b['rate']:>16.1f}")
    print(f"{'candidates':38s} {a['candidates']:>16,} {b['candidates']:>16,}")
    print()
    if a["scopes"] and b["scopes"]:
        print(f"  scopes per subspace:   x{b['scopes']/a['scopes']:.2f}")
    if a["rate"] and b["rate"]:
        print(f"  throughput:            x{b['rate']/a['rate']:.2f} "
              f"({'slower' if b['rate'] < a['rate'] else 'faster'} per scope)")
    if a["elapsed"]:
        print(f"  wall time, same work:  x{b['elapsed']/a['elapsed']:.2f}")
    print()
    print(f"  WP-D2c measured 146.0 scopes/s on 5 workers at 17 dimensions.")
    if a["rate"]:
        print(f"  This machine, same configuration: {a['rate']:.1f} scopes/s "
              f"(x{a['rate']/146.0:.2f} of that run).")
    print()
    print("  Read the two ratios together: the first pair is what the SIX NEW")
    print("  DIMENSIONS cost, the last line is what THIS MACHINE costs relative")
    print("  to the run the 92-minute baseline came from. B4's choice turns on")
    print("  the first; the second says how far the baseline travels.")


if __name__ == "__main__":
    sys.exit(main())
