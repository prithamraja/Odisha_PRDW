"""
Custom eval: replay a question file through the real /query endpoint (vector
retrieve -> rerank -> entity extraction -> SQL on the DuckDB sample), one fresh
session per question, and record what came back.

  python run_custom_eval.py --yes                                   # eval_questions_custom.json
  python run_custom_eval.py --questions <file.json> --out <file.jsonl> --yes

The Eval_1 standing regression (WP-6b T6) runs this over the 314 officer
phrasings in `handoffs/WP6_eval1_questions.json`; `grade_eval1.py` grades it.

THIS SPENDS MONEY — every question is an embed + a rerank + an extraction, and
a clarification adds one more extraction for its chips — so it requires --yes
(or PRDW_EVAL_CONFIRM=1) and prints its call estimate first (eval_spend.py).
Before WP-6b it had no guard at all, which is how the 2026-09-14 PM replay of
Eval_1 was run unmetered.
"""
import argparse
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
# The DuckDB sample, not AP's flat parquet drop. The previous default was
# `HERE.parent.parent / "RTGS_Data" / "flat"` — a path OUTSIDE this repo
# (WP-1 report §7.2), so a stray RTGS_Data/ in the shared Drive parent would
# have pointed this at another project's data. Fixed alongside run_full_eval's
# copy of the same line (WP-4 T4e).
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

QUESTIONS_DEFAULT = HERE / "eval_questions_custom.json"
OUT_DEFAULT = HERE / "eval_custom_results.jsonl"


def slim_rows(rows, keep=3):
    if rows is None:
        return None, None
    return len(rows), rows[:keep]


def _capture_router_log(out_path: Path) -> logging.Handler:
    """`query_router`'s INFO records beside the results — the subject reader's
    prefills (WP-6b T2) and the year reader's are recorded only there."""
    handler = logging.FileHandler(out_path.with_suffix(".router.log"), mode="w",
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("query_router")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return handler


def run(questions: list[dict], out: Path):
    # Imported here, AFTER the spend guard: importing main constructs the
    # OpenAI client, and building the retriever can embed the catalogue.
    from fastapi.testclient import TestClient
    import main

    handler = _capture_router_log(out)
    records = []
    with TestClient(main.app) as client, out.open("w", encoding="utf-8") as sink:
        for i, spec in enumerate(questions, 1):
            sid = str(uuid4())
            payload = {"message": spec["q"], "session_id": sid, "reset_context": True}

            t0 = time.time()
            rec = {"n": spec["n"], "q": spec["q"]}
            try:
                resp = client.post("/query", json=payload, timeout=120)
                if resp.status_code != 200:
                    rec.update(error=f"HTTP {resp.status_code}: {resp.text[:300]}")
                else:
                    d = resp.json()
                    n_rows, sample = slim_rows(d.get("result"))
                    clar = d.get("clarification")
                    rec.update(
                        tier=d.get("tier"),
                        query_id=d.get("query_id"),
                        query_description=d.get("query_description"),
                        answer=(d.get("answer") or "")[:400],
                        entities=d.get("entities"),
                        n_rows=n_rows,
                        rows_sample=sample,
                        date_range=d.get("date_range"),
                        date_filter_applied=d.get("date_filter_applied"),
                        clarification=(
                            {"reason": clar.get("reason"),
                             "prompt": (clar.get("prompt") or "")[:200],
                             "options": [
                                 {k: v for k, v in (o or {}).items()
                                  if k in ("label", "query", "query_id", "message")}
                                 for o in (clar.get("options") or [])
                             ]} if clar else None),
                    )
            except Exception as ex:
                rec.update(error=f"{type(ex).__name__}: {ex}")

            rec["wall_s"] = round(time.time() - t0, 2)
            records.append(rec)
            sink.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            sink.flush()
            label = rec.get("query_id") or rec.get("tier") or rec.get("error", "?")[:40]
            print(f"[{i:>3}/{len(questions)}] {label:<12} {spec['q'][:70]}")

    logging.getLogger("query_router").removeHandler(handler)
    handler.close()
    print(f"\nWrote {out} ({len(records)} records)")


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, default=QUESTIONS_DEFAULT,
                    help="a JSON list of {n, q} (default: eval_questions_custom.json)")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT,
                    help="results file, one JSON record per question")
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    args = ap.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    from eval_spend import confirm_spend
    n = len(questions)
    confirm_spend(
        "run_custom_eval",
        [("catalogue embedding index (cached after the first build)", 1),
         (f"per question: 1 embed + 1 rerank + 1 extraction x {n}", 3 * n),
         (f"chip pre-fill extraction on clarifications (at most {n})", n)],
        confirmed=args.yes,
    )
    run(questions, args.out)


if __name__ == "__main__":
    main_cli()
