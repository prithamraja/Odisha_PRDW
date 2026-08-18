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
import logging
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

from eval_artefacts import local_twin, publish, streamed_artefact  # noqa: E402

QUESTIONS = json.loads((HERE / "eval_questions_full.json").read_text(encoding="utf-8"))
OUT = HERE / "eval_full_results.jsonl"


def slim_rows(rows, keep=3):
    if rows is None:
        return None, None
    return len(rows), rows[:keep]


def _capture_router_log(out_path: Path) -> logging.Handler:
    """Route `query_router`'s INFO records to a file beside the results.

    WITHOUT THIS, HALF OF WHAT T4 IS ASKED TO REPORT DOES NOT EXIST. Three of the
    router's decisions are recorded only as `logging.info`, and nothing in this
    harness ever configured logging — so the default WARNING level dropped every
    one of them, silently:

      * `_fiscal_year_from_text` — every `$date_range` the deterministic reader
        supplied as a PREFILL (D30.4, promoted in WP-5 T1), and its counterpart
        line for every one the reader could not read and the extractor
        rescued — which is the measurement of whether keeping the extractor as
        the slot's fallback still earns its place;
      * `_log_fiscal_year_disagreement` — the evidence that promoted the reader.
        Quiet is now its RESULT rather than its input: with the reader running
        first, a disagreement is structurally unreachable, so a line here means
        some new path is supplying the slot from somewhere else;
      * `_refusal_precedence` — which documented refusals were reached, and
        whether by rank or by the reranker's own near-miss list.

    `_order_paired_fiscal_years` used to be the second item on this list. It is
    deleted (WP-5 T1): the reader's own split IS the catalogue's chronological
    convention, so the inversion it corrected can no longer be produced.

    A `logging.info` nobody collects is a measurement that was never taken.
    """
    # The router log is appended to on every decision for the length of the
    # replay, which is the same streaming-into-Drive shape as the results file
    # (D31.7). Written locally; `run()` publishes it once the handler is closed.
    log_path = local_twin(out_path.with_suffix(".router.log"))
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    handler.setLevel(logging.INFO)
    logger = logging.getLogger("query_router")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    # The extraction-unavailable warnings live under the same package, so they
    # land here too; `propagate` is left alone so nothing else changes.
    print(f"router log -> {log_path}")
    return handler


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
    log_handler = _capture_router_log(out_path)

    records = []
    # STREAMED TO A LOCAL PATH, COPIED IN AT THE END (D31.7). The per-question
    # flush below is what survives a crash mid-replay; doing it inside a
    # Drive-synced folder is what damaged all three of WP-4c's results files.
    # See eval_artefacts.py.
    with TestClient(main.app) as client, \
            streamed_artefact(out_path, encoding="utf-8") as out:
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
            # D31.3 — the clarification reason this row ratifies as its own
            # outcome, carried onto the record for the same reason the pin is:
            # a results file that needs the gold set beside it to be graded is
            # a results file that will one day be graded against the wrong one.
            if spec.get("expected_clarification"):
                rec["expected_clarification"] = spec["expected_clarification"]
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

    logging.getLogger("query_router").removeHandler(log_handler)
    log_handler.close()
    publish(Path(log_handler.baseFilename), out_path.with_suffix(".router.log"))

    # REWRITTEN FROM MEMORY AT THE END, and this is not belt-and-braces. The
    # streamed append above is what survives a crash mid-replay, but this repo
    # lives in a Google Drive folder (D6) and the sync layer mangled the streamed
    # file on both of WP-4c's first two replays: replay 1 came back with a record
    # written twice plus an orphan fragment, replay 2 lost FOUR questions to two
    # unrecoverable fragments. `records` is authoritative — it is what actually
    # ran — so the file is replaced with it once the run is over. A results file
    # that silently holds 207 of 211 questions is an accuracy figure that lies.
    # REWRITTEN FROM MEMORY, LOCALLY, THEN PUBLISHED. `records` is authoritative
    # — it is what actually ran — so the local file is replaced with it and the
    # repo copy is made from that, in one operation.
    local = local_twin(out_path)
    local.write_text(
        "".join(json.dumps(r, ensure_ascii=False, default=str) + "\n"
                for r in records),
        encoding="utf-8")
    publish(local, out_path)

    print(f"\nWrote {out_path} ({len(records)} records, streamed via {local})")

    # Spend and extraction outcomes, next to the results they belong to. The
    # sidecar rather than the results file itself because it is per-RUN, not
    # per-question, and because the triage reads the results file line by line.
    print(meter().report(f"{out_path.name}: token spend"))
    usage_path = out_path.with_suffix(".usage.json")
    usage_local = local_twin(usage_path)
    usage_local.write_text(
        json.dumps(meter().snapshot(), indent=1), encoding="utf-8")
    publish(usage_local, usage_path)
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
