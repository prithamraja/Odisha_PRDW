"""
Aggregate a consistency_results*.jsonl into a per-question x per-run mapping
table:

  consistency_table*.csv — one row per question, one column per run
  (query_id mapped to), then consistency (modal count / runs), modal
  query_id, and the NL wording of the modal template for validation.

Cells: query_id; "CLARIFY:<reason>" when the pipeline asked instead of
answering; "ERR" on transport/HTTP errors.

  python aggregate_consistency.py                              # WP-4's file
  python aggregate_consistency.py consistency_results_wp4c.jsonl

The argument exists because `run_consistency_eval --tag` keeps one work
package's replays out of another's file, and the two must not be aggregated
together: replay 1 of a 209-question gold set and replay 1 of a 211-question one
would read as instability on two questions that were simply not asked yet.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "consistency_results.jsonl"
if not IN.is_absolute():
    IN = HERE / IN
OUT = HERE / (IN.stem.replace("consistency_results", "consistency_table") + ".csv")

records = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]

runs = sorted({r["run"] for r in records})
questions = {}
cells = defaultdict(dict)          # n -> run -> cell label
descriptions = defaultdict(Counter)  # query_id -> Counter of query_description

for r in records:
    n = r["n"]
    questions[n] = r["q"]
    if r.get("error"):
        label = "ERR"
    elif r.get("query_id"):
        label = r["query_id"]
        if r.get("clar_reason"):
            label += f"?clarify:{r['clar_reason']}"
        if r.get("query_description"):
            descriptions[r["query_id"]][r["query_description"]] += 1
    elif r.get("clar_reason"):
        label = f"CLARIFY:{r['clar_reason']}"
    else:
        label = r.get("tier") or "?"
    cells[n][r["run"]] = label

rows = []
for n in sorted(questions):
    counts = Counter(cells[n].get(run, "MISSING") for run in runs)
    modal, modal_count = counts.most_common(1)[0]
    modal_qid = modal.split("?")[0]
    nl = ""
    if descriptions.get(modal_qid):
        nl = descriptions[modal_qid].most_common(1)[0][0]
    elif modal.startswith("CLARIFY"):
        nl = "(pipeline asked a clarifying question)"
    row = {"n": n, "question": questions[n]}
    for run in runs:
        row[f"run_{run}"] = cells[n].get(run, "MISSING")
    row["consistency"] = f"{modal_count}/{len(runs)}"
    row["modal_query_id"] = modal
    row["modal_nl_question"] = nl
    rows.append(row)

fieldnames = ["n", "question"] + [f"run_{r}" for r in runs] + [
    "consistency", "modal_query_id", "modal_nl_question"]
with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {OUT} ({len(rows)} questions x {len(runs)} runs)")
print()
unstable = [r for r in rows if not r["consistency"].startswith(str(len(runs)))]
if not unstable:
    print("All questions mapped 100% consistently.")
for r in rows:
    variant_counts = Counter(cells[r["n"]].get(run, "MISSING") for run in runs)
    variants = ", ".join(f"{k} x{v}" for k, v in variant_counts.most_common())
    flag = " " if len(variant_counts) == 1 else "*"
    print(f"{flag} Q{r['n']:>2} {r['consistency']:>6} {variants}")
