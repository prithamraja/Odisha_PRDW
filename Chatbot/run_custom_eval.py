"""
Custom eval: replay eval_questions_custom.json through the real /query
endpoint (vector retrieve -> rerank -> entity extraction -> SQL on the flat
parquet drop), one fresh session per question, and record what came back.

Writes eval_custom_results.jsonl (one record per question, streamed as it runs).
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
# The DuckDB sample, not AP's flat parquet drop. The previous default was
# `HERE.parent.parent / "RTGS_Data" / "flat"` — a path OUTSIDE this repo
# (WP-1 report §7.2), so a stray RTGS_Data/ in the shared Drive parent would
# have pointed this at another project's data. Fixed alongside run_full_eval's
# copy of the same line (WP-4 T4e); `eval_questions_custom.json` does not exist
# in this repo, so this harness is dormant until someone writes one.
os.environ.setdefault("DB_ENGINE", "duckdb_file")
os.environ.setdefault("DB_PATH", "data/panchayat_1.duckdb")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient

import main  # noqa: E402  (imports after env setup on purpose)

QUESTIONS = json.loads((HERE / "eval_questions_custom.json").read_text(encoding="utf-8"))
OUT = HERE / "eval_custom_results.jsonl"


def slim_rows(rows, keep=3):
    if rows is None:
        return None, None
    return len(rows), rows[:keep]


def run():
    records = []
    with TestClient(main.app) as client, OUT.open("w", encoding="utf-8") as out:
        for i, spec in enumerate(QUESTIONS, 1):
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
            out.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            out.flush()
            label = rec.get("query_id") or rec.get("tier") or rec.get("error", "?")[:40]
            print(f"[{i:>2}/{len(QUESTIONS)}] {label:<12} {spec['q'][:70]}")

    print(f"\nWrote {OUT} ({len(records)} records)")


if __name__ == "__main__":
    run()
