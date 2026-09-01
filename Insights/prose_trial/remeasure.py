#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) -- one MEASUREMENT, run after the trial and kept out of its result.

Rank 1's first verifier call returned an empty string: gpt-5.5 spent all 4,000
completion tokens on reasoning and finished with reason 'length'. That is exactly
the D17 failure mode the budget check guards against, hitting the VERIFIER
ceiling the brief fixes at 4,000 rather than the writer's. Under T4 an
unparseable verdict is a fail-to-verify, so T5 regenerated the finding and the
recorded status stands.

But it leaves a question the operator should not have to guess at: was finding
1's FIRST rendering actually sound? This script re-runs that one verifier call,
at the same ceiling, on the same rendering, and records what comes back. It does
not touch results.json and does not change any status.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "Insights", "src"))

import llm, verify

PACKETS = {p["rank"]: p for p in json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))}
RESULTS = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))

TARGETS = [(1, 1)]  # (rank, attempt) whose verdict was an empty completion

out = {}
for rank, attempt in TARGETS:
    row = next(r for r in RESULTS["findings"] if r["rank"] == rank)
    a = next(x for x in row["attempts"] if x["attempt"] == attempt)
    prompt = verify.build_verifier_prompt(PACKETS[rank], a["lead"], a["detail"])
    rec = llm.call(verify.VERIFIER_MODEL, prompt, llm.VERIFIER_MAX_COMPLETION,
                   "verifier_remeasure", rank=rank, attempt=attempt)
    res = verify.parse_verdict(rec["response_text"])
    out["%d/%d" % (rank, attempt)] = {
        "lead": a["lead"], "detail": a["detail"],
        "original_verdict": a["verifier"]["verdict"],
        "original_finish_reason": a["verifier"].get("_finish_reason"),
        "original_usage": a["verifier"].get("_usage"),
        "remeasured_verdict": res["verdict"],
        "remeasured_finish_reason": rec["finish_reason"],
        "remeasured_usage": rec["usage"],
        "claim_map": res.get("claim_map", []),
        "problems": res.get("problems", []),
    }
    print("rank %d attempt %d: original=%s (finish=%s) -> remeasured=%s (finish=%s, "
          "reasoning=%s, visible_chars=%d)"
          % (rank, attempt, a["verifier"]["verdict"],
             a["verifier"].get("_finish_reason"), res["verdict"],
             rec["finish_reason"], rec["usage"]["reasoning_tokens"],
             rec["response_chars"]))

json.dump(out, open(os.path.join(HERE, "remeasure.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print("calls so far %d of %d" % (llm.calls_so_far(), llm.MAX_CALLS))
