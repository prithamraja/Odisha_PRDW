#!/usr/bin/env python
"""Run verifier v2 over the findings that fell back under v1, on their final
rendering, to measure how much of v1's catch was the advisory false positive."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "Insights", "src"))
import llm, verify, verify_v2

PACKETS = {p["rank"]: p for p in json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))}
RESULTS = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))

out = {}
for row in RESULTS:
    if row["status"] != "fell back":
        continue
    rank = row["rank"]
    last = row["attempts"][-1]
    prompt = verify_v2.build_prompt(PACKETS[rank], last["lead"], last["detail"])
    rec = llm.call(verify_v2.VERIFIER_MODEL, prompt, llm.VERIFIER_MAX_COMPLETION,
                   "verifier_v2", rank=rank, attempt=len(row["attempts"]))
    res = verify.parse_verdict(rec["response_text"])
    out[rank] = {"verdict": res["verdict"],
                 "claim_map": res.get("claim_map", []),
                 "problems": res.get("problems", []),
                 "lead": last["lead"], "detail": last["detail"]}
    print(f"rank {rank:2d}: v1=fail -> v2={res['verdict']}"
          + ("" if res["verdict"] == "pass" else
             " | " + str(res.get("problems", [{}])[0].get("drifted_claim"))[:90]))

json.dump(out, open(os.path.join(HERE, "results_v2.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print(f"\ncalls so far {llm.calls_so_far()} of {llm.MAX_CALLS}")
