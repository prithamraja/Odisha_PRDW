"""
Custom eval: replay a question file through the real /query endpoint (vector
retrieve -> rerank -> entity extraction -> SQL on the DuckDB sample), one fresh
session per question, and record what came back.

  python run_custom_eval.py --yes                                   # eval_questions_custom.json
  python run_custom_eval.py --questions <file.json> --out <file.jsonl> --yes

The Eval_1 standing regression (WP-6b T6) runs this over the 314 officer
phrasings in `handoffs/WP6_eval1_questions.json`; `grade_eval1.py` grades it.

TWO-TURN ROWS (WP-6c T3). A question spec may carry a `reply`: it is sent in
the SAME session straight after the first answer, the way an officer answers
"Above what planned cost?", and recorded under `turn2`. Any other keys on the
spec (`group`, `expect`) are copied into the record for the grader. Each turn
also records the retriever's top three ids (`retrieved`), because whether a
per-funding-source or a tied/untied template ranks first is something only a
live run can show.

CHIP TAPS (WP-6d T8). A spec may carry a `chip` instead: the second turn sends
the first offered chip whose label contains that wording, with `from_chip`, the
way an officer taps it. No such chip is recorded as an error on `turn2`.

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


def _turn(client, message: str, session_id: str, *, reset: bool, retrieved: list,
          from_chip: bool = False) -> dict:
    """One /query call, recorded the way the graders read it."""
    rec: dict = {}
    retrieved.clear()
    payload = {"message": message, "session_id": session_id, "reset_context": reset,
               "from_chip": from_chip}
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
                          if k in ("label", "send_text", "query", "query_id", "message")}
                         for o in (clar.get("options") or [])
                     ]} if clar else None),
            )
    except Exception as ex:
        rec.update(error=f"{type(ex).__name__}: {ex}")
    if retrieved:
        rec["retrieved"] = list(retrieved[0])
    return rec


def _pick_chip(record: dict, wording: str) -> str | None:
    """The send_text of the first chip whose label contains `wording` (WP-6d T8)."""
    for option in ((record.get("clarification") or {}).get("options") or []):
        if wording.lower() in (option.get("label") or "").lower():
            return option.get("send_text") or option.get("label")
    return None


def _trace_retrieval(main_module) -> list:
    """Record the top three ids of every retrieval, without changing it."""
    seen: list = []
    retriever = getattr(main_module, "_retriever", None)
    if retriever is None or not hasattr(retriever, "retrieve_scored"):
        return seen
    real = retriever.retrieve_scored

    def traced(*args, **kwargs):
        scored = real(*args, **kwargs)
        if not seen:
            seen.append([qid for qid, _, _ in scored[:3]])
        return scored

    retriever.retrieve_scored = traced
    return seen


def run(questions: list[dict], out: Path):
    # Imported here, AFTER the spend guard: importing main constructs the
    # OpenAI client, and building the retriever can embed the catalogue.
    from fastapi.testclient import TestClient
    import main

    handler = _capture_router_log(out)
    records = []
    with TestClient(main.app) as client, out.open("w", encoding="utf-8") as sink:
        retrieved = _trace_retrieval(main)
        for i, spec in enumerate(questions, 1):
            sid = str(uuid4())
            t0 = time.time()
            rec = {"n": spec["n"], "q": spec["q"],
                   **{k: v for k, v in spec.items() if k not in ("n", "q", "reply")}}
            rec.update(_turn(client, spec["q"], sid, reset=True, retrieved=retrieved))
            if spec.get("reply"):
                rec["turn2"] = {"q": spec["reply"],
                                **_turn(client, spec["reply"], sid, reset=False,
                                        retrieved=retrieved)}
            elif spec.get("chip"):
                chip = _pick_chip(rec, spec["chip"])
                rec["turn2"] = ({"q": chip, "from_chip": True,
                                 **_turn(client, chip, sid, reset=False,
                                         retrieved=retrieved, from_chip=True)}
                                if chip else
                                {"q": None, "error": f"no chip containing {spec['chip']!r}"})
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
    replies = sum(1 for q in questions if q.get("reply") or q.get("chip"))
    confirm_spend(
        "run_custom_eval",
        [("catalogue embedding index (cached after the first build)", 1),
         (f"per question: 1 embed + 1 rerank + 1 extraction x {n}", 3 * n),
         (f"chip pre-fill extraction on clarifications (at most {n})", n),
         (f"second turns: a reply read, or routed, at most 3 calls x {replies}",
          3 * replies)],
        confirmed=args.yes,
    )
    run(questions, args.out)


if __name__ == "__main__":
    main_cli()
