"""
End-to-end eval: replay the gold question set through the real /query endpoint
(vector retrieve -> rerank -> entity extraction -> SQL on the DuckDB sample),
one fresh session per question, and record what came back.

  python run_full_eval.py --yes

Writes eval_full_results.jsonl (one record per question, streamed as it runs).

THIS SPENDS MONEY — every question is an embed + a rerank + an extraction — so
it requires --yes (or PRDW_EVAL_CONFIRM=1) and prints its call estimate first.
See eval_spend.py for why that guard exists.

FOLLOW-UP FRAGMENTS DEPEND ON FILE ORDER. A spec carrying `"session": "prev"`
reuses the session of the IMMEDIATELY PRECEDING record, which is what puts the
frame on screen that the fragment leans on. `build_eval_questions.py --check`
enforces the ordering; do not sort this file.
"""
import argparse
import os
import sys
import io
import json
import time
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
os.chdir(HERE)

# The DuckDB sample, not AP's flat parquet drop. The previous default was
# `HERE.parent.parent / "RTGS_Data" / "flat"` — a path OUTSIDE this repo
# (WP-1 report §7.2): a stray RTGS_Data/ landing in the shared Drive parent
# would have silently pointed the eval at another project's data. The engine and
# path now match what `.env.example` documents for PR&DW.
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

QUESTIONS = json.loads((HERE / "eval_questions_full.json").read_text(encoding="utf-8"))
OUT = HERE / "eval_full_results.jsonl"


def slim_rows(rows, keep=3):
    if rows is None:
        return None, None
    return len(rows), rows[:keep]


def run(out_path: Path = OUT):
    # Imported here, AFTER the spend guard has run: importing main constructs
    # the OpenAI client and building the retriever embeds the whole catalogue,
    # so a module-scope import would spend before anyone confirmed anything.
    from fastapi.testclient import TestClient
    import main
    from query_router.llm_usage import meter

    # WP-4 could not state a token figure because nothing recorded `usage`
    # (D28.8). Reset per replay, so the consistency runner's three passes report
    # three separate totals rather than a growing sum.
    meter().reset()

    records = []
    with TestClient(main.app) as client, out_path.open("w", encoding="utf-8") as out:
        prev_session = None
        for i, spec in enumerate(QUESTIONS, 1):
            if spec.get("session") == "prev" and prev_session:
                sid = prev_session
                payload = {"message": spec["q"], "session_id": sid}
            else:
                sid = str(uuid4())
                payload = {"message": spec["q"], "session_id": sid, "reset_context": True}
            prev_session = sid

            t0 = time.time()
            rec = {"n": spec["n"], "q": spec["q"], "gold": spec.get("gold"),
                   "acc": spec.get("acc", []), "partial": spec.get("partial", False),
                   "excluded": spec.get("excluded", False), "src": spec.get("src")}
            # D30.3: carried onto the record so a results file states its own
            # direction contract. `grade_full_eval` falls back to looking the pin
            # up by `n`, so an older results file can still be re-graded.
            pin = (spec.get("expected_result") or {}).get("direction_pin")
            if pin:
                rec["gold_direction_pin"] = pin
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
            out.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            out.flush()
            label = rec.get("query_id") or rec.get("tier") or rec.get("error", "?")[:40]
            print(f"[{i:>2}/{len(QUESTIONS)}] {label:<12} {spec['q'][:70]}")

    print(f"\nWrote {out_path} ({len(records)} records)")

    # Spend and extraction outcomes, next to the results they belong to. The
    # sidecar rather than the results file itself because it is per-RUN, not
    # per-question, and because the triage reads the results file line by line.
    print(meter().report(f"{out_path.name}: token spend"))
    usage_path = out_path.with_suffix(".usage.json")
    usage_path.write_text(
        json.dumps(meter().snapshot(), indent=1), encoding="utf-8")
    print(f"Wrote {usage_path}")
    return records


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true",
                    help="confirm the paid run (or set PRDW_EVAL_CONFIRM=1)")
    ap.add_argument("--out", type=Path, default=OUT,
                    help="results file (the consistency runner passes one per replay)")
    args = ap.parse_args()

    from eval_spend import confirm_spend
    n = len(QUESTIONS)
    confirm_spend(
        "run_full_eval",
        [("catalogue embedding index (cached after the first build)", 1),
         (f"per question: 1 embed + 1 rerank + 1 extraction x {n}", 3 * n),
         ("follow-up classification on the 13 fragment rows", 13)],
        confirmed=args.yes,
    )
    run(args.out)


if __name__ == "__main__":
    main_cli()
