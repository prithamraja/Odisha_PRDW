"""
Collapse consistency_results.jsonl into consistency_summary.csv:
original question, modal mapped query_id, how many of the 25 runs mapped
there, and the NL wording of that template.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
IN = HERE / "consistency_results.jsonl"
OUT = HERE / "consistency_summary.csv"

records = [json.loads(l) for l in IN.read_text(encoding="utf-8").splitlines() if l.strip()]

questions = {}
mapped = defaultdict(Counter)        # n -> Counter of query_id / CLARIFY label
descriptions = defaultdict(Counter)  # query_id -> Counter of query_description

for r in records:
    n = r["n"]
    questions[n] = r["q"]
    if r.get("error"):
        label = "ERR"
    elif r.get("query_id"):
        label = r["query_id"]
        if r.get("query_description"):
            descriptions[label][r["query_description"]] += 1
    elif r.get("clar_reason"):
        label = f"CLARIFY:{r['clar_reason']}"
    else:
        label = r.get("tier") or "?"
    mapped[n][label] += 1

NL_OVERRIDES = {
    1: "No template — asks which farmer is meant: several match 'Anjamma' "
       "(Anjamma Babu / Chowdary / Devi / Kumar). Answers F12-style once one is picked.",
}

rows = []
for n in sorted(questions):
    modal, count = mapped[n].most_common(1)[0]
    nl = NL_OVERRIDES.get(n, "")
    if not nl and descriptions.get(modal):
        nl = descriptions[modal].most_common(1)[0][0]
    rows.append({
        "original_question": questions[n],
        "mapped_query_id": modal,
        "times_mapped": count,
        "nl_question_of_mapped_type": nl,
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["original_question", "mapped_query_id",
                                      "times_mapped", "nl_question_of_mapped_type"])
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {OUT} ({len(rows)} rows)")
