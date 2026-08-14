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


def load_done() -> set:
    """(run, n) pairs already recorded, so a crashed sweep resumes."""
    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
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
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    args = ap.parse_args()

    import run_full_eval
    from eval_spend import confirm_spend

    n_q = len(run_full_eval.QUESTIONS)
    done = load_done()
    remaining = [r for r in range(1, args.runs + 1)
                 if not all((r, spec["n"]) in done for spec in run_full_eval.QUESTIONS)]
    confirm_spend(
        "run_consistency_eval",
        [(f"{len(remaining)} replay(s) x {n_q} questions x ~3 calls",
          len(remaining) * n_q * 3),
         ("already recorded (skipped)", 0)],
        confirmed=args.yes,
    )

    with OUT.open("a", encoding="utf-8") as out:
        for run_no in remaining:
            started = time.time()
            per_run = HERE / f"eval_full_results_run{run_no}.jsonl"
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
    print("DONE — now run: python aggregate_consistency.py")


if __name__ == "__main__":
    main_cli()
