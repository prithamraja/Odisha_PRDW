"""
End-to-end eval: replay the sample-question sheet through the real /query
endpoint (vector retrieve -> rerank -> entity extraction -> SQL on the flat
parquet drop), one fresh session per question, and record what came back.

  DATA_DIR=<repo>/RTGS_Data/flat  python run_full_eval.py

Writes eval_full_results.jsonl (one record per question, streamed as it runs).
"""
import os
import sys
import io
import json
import time
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
os.environ.setdefault("DATA_DIR", str(HERE.parent.parent / "RTGS_Data" / "flat"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient

import main  # noqa: E402  (imports after env setup on purpose)

QUESTIONS = json.loads((HERE / "eval_questions_full.json").read_text(encoding="utf-8"))
OUT = HERE / "eval_full_results.jsonl"


def slim_rows(rows, keep=3):
    if rows is None:
        return None, None
    return len(rows), rows[:keep]


def run():
    records = []
    with TestClient(main.app) as client, OUT.open("w", encoding="utf-8") as out:
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

    print(f"\nWrote {OUT} ({len(records)} records)")


if __name__ == "__main__":
    run()
