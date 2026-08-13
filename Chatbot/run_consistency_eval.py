"""
Routing-consistency eval: replay eval_questions_33.json through the real
/query endpoint N_RUNS times (fresh session per question per run) and record
the query_id each run mapped to.

Routing (vector retrieve -> gpt-4.1-mini rerank -> extraction) runs fresh on
every call — only SQL results are cached in-process, and that cache sits
after the routing decision, so repeat passes still measure real routing.

Appends to consistency_results.jsonl; (run, n) pairs already present are
skipped, so the script is resumable after a crash.
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

N_RUNS = 25
QUESTIONS = json.loads((HERE / "eval_questions_33.json").read_text(encoding="utf-8"))
OUT = HERE / "consistency_results.jsonl"


def load_done() -> set:
    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done.add((r["run"], r["n"]))
            except Exception:
                pass
    return done


def run():
    done = load_done()
    if done:
        print(f"Resuming: {len(done)} records already present")
    with TestClient(main.app) as client, OUT.open("a", encoding="utf-8") as out:
        for run_no in range(1, N_RUNS + 1):
            t_run = time.time()
            n_new = 0
            for spec in QUESTIONS:
                if (run_no, spec["n"]) in done:
                    continue
                payload = {"message": spec["q"], "session_id": str(uuid4()),
                           "reset_context": True}
                rec = {"run": run_no, "n": spec["n"], "q": spec["q"]}
                t0 = time.time()
                try:
                    resp = client.post("/query", json=payload, timeout=120)
                    if resp.status_code != 200:
                        rec["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    else:
                        d = resp.json()
                        clar = d.get("clarification")
                        rec.update(
                            tier=d.get("tier"),
                            query_id=d.get("query_id"),
                            query_description=d.get("query_description"),
                            n_rows=len(d.get("result") or []) if d.get("result") is not None else None,
                            clar_reason=(clar or {}).get("reason"),
                        )
                except Exception as ex:
                    rec["error"] = f"{type(ex).__name__}: {ex}"
                rec["wall_s"] = round(time.time() - t0, 2)
                out.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                out.flush()
                n_new += 1
            print(f"run {run_no:>2}/{N_RUNS}: {n_new} questions in {time.time() - t_run:.0f}s",
                  flush=True)
    print("DONE")


if __name__ == "__main__":
    run()
