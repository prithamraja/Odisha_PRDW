"""
Routing-consistency eval: replay the WHOLE gold set through /query N times and
record the query_id each run mapped to.

  python run_consistency_eval.py --runs 3 --yes

Routing (vector retrieve -> rerank -> extraction) runs fresh on every call —
only SQL results are cached in-process, and that cache sits AFTER the routing
decision, so repeat passes still measure real routing.

WHY THIS EXISTS AT ALL (standing risk, PROJECT_PLAN §6): routing flips on
roughly 3% of questions between identical replays. A single miss is therefore
not evidence of anything, and WP-4's own rule is that no failure may be reported
as a regression without appearing in at least 2 of 3 replays. This harness is
what makes that rule checkable.

WHAT CHANGED FOR PR&DW (WP-4 T4c). The AP version replayed `eval_questions_33.json`
— a file that does not exist in this repo — 25 times, with a fresh session per
question, and defaulted DATA_DIR to a path outside the repo. Fresh-session-per-
question is the part that mattered: 13 of the gold rows are FOLLOW-UP FRAGMENTS
that only mean anything with the previous question's frame on screen, so
replaying them standalone would have measured the wrong thing and called the
result instability. This now drives `run_full_eval.run()` itself, once per
replay, so consistency is measured over exactly the pass whose accuracy is
reported.

Writes consistency_results.jsonl (append-only, resumable: a replay whose records
are already present is skipped) and per-replay eval_full_results_run<N>.jsonl.
"""
import argparse
import json
import os
import sys
import io
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUT = HERE / "consistency_results.jsonl"


def load_done(path: Path = OUT) -> set:
    """(run, n) pairs already recorded, so a crashed sweep resumes."""
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done.add((r["run"], r["n"]))
            except Exception:
                pass
    return done


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3,
                    help="replays (WP-4 T5c asks for 3)")
    ap.add_argument("--tag", default="",
                    help="suffix the artefacts, so one work package's replays "
                         "never append to another's (WP-4c: --tag wp4c)")
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    args = ap.parse_args()

    # ONE PACKAGE'S REPLAYS MUST NOT APPEND TO ANOTHER'S. This file is
    # append-only and resumable, keyed on (run, n), and `aggregate_consistency`
    # groups by run number — so re-running after the gold set changed would have
    # mixed WP-4's 209-question replay 1 with WP-4c's 211-question replay 1 and
    # reported the difference as routing instability. `--tag` keeps the
    # generations separate, and leaves the earlier package's raw files exactly as
    # they were committed, which is what a before/after needs.
    tag = f"_{args.tag}" if args.tag else ""
    out_path = HERE / f"consistency_results{tag}.jsonl"

    import run_full_eval
    from eval_artefacts import appended_artefact
    from eval_spend import confirm_spend

    n_q = len(run_full_eval.QUESTIONS)
    done = load_done(out_path)
    remaining = [r for r in range(1, args.runs + 1)
                 if not all((r, spec["n"]) in done for spec in run_full_eval.QUESTIONS)]
    confirm_spend(
        "run_consistency_eval",
        [(f"{len(remaining)} replay(s) x {n_q} questions x ~3 calls",
          len(remaining) * n_q * 3),
         ("already recorded (skipped)", 0)],
        confirmed=args.yes,
    )

    # D31.7 — appended on the scratch disk, copied into the repo at the end.
    # This file is flushed once per replay rather than once per question, but it
    # is still a streamed write into a Drive-synced folder, which is what
    # damaged all three of WP-4c's results files.
    with appended_artefact(out_path, encoding="utf-8") as out:
        for run_no in remaining:
            started = time.time()
            per_run = HERE / f"eval_full_results{tag}_run{run_no}.jsonl"
            # run_full_eval.run() resets the usage meter itself and writes a
            # per-replay sidecar, so three replays report three totals (D28.8).
            records = run_full_eval.run(per_run)
            for rec in records:
                if (run_no, rec["n"]) in done:
                    continue
                clar = rec.get("clarification") or {}
                out.write(json.dumps({
                    "run": run_no,
                    "n": rec["n"],
                    "q": rec["q"],
                    "tier": rec.get("tier"),
                    "query_id": rec.get("query_id"),
                    "query_description": rec.get("query_description"),
                    "n_rows": rec.get("n_rows"),
                    "clar_reason": clar.get("reason"),
                    "error": rec.get("error"),
                }, ensure_ascii=False, default=str) + "\n")
            out.flush()
            print(f"replay {run_no}/{args.runs}: {len(records)} questions in "
                  f"{time.time() - started:.0f}s", flush=True)
    print(f"DONE — now run: python aggregate_consistency.py {out_path.name}")


if __name__ == "__main__":
    main_cli()
