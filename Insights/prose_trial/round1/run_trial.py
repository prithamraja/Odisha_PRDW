#!/usr/bin/env python
"""WP-D4 T2-T5 -- run the trial and write results.json.

Reuses the writer batch already logged in logs/calls.jsonl (so a re-run does
not re-spend); regenerations and verifier calls go through llm.call as usual.
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "Insights", "src"))

import llm, checks, verify
from prompts import build_single_prompt
from discover_config import DISCOVER_PROSE_MODEL

PACKETS = json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))
RESULTS = os.path.join(HERE, "results.json")

_BLOCK = re.compile(r"===\s*FINDING\s*(\d+)\s*===(.*?)(?====\s*FINDING\s*\d+\s*===|\Z)", re.S | re.I)


def parse_renderings(text: str) -> dict:
    """{rank: (lead, detail)} from the delimited writer output."""
    out = {}
    for m in _BLOCK.finditer(text):
        rank = int(m.group(1))
        body = m.group(2)
        lm = re.search(r"LEAD:\s*(.*?)(?=\n\s*DETAIL:|\Z)", body, re.S | re.I)
        dm = re.search(r"DETAIL:\s*(.*)", body, re.S | re.I)
        if lm and dm:
            out[rank] = (lm.group(1).strip(), dm.group(1).strip())
    return out


def load_writer_batch() -> dict:
    for line in open(llm.LOG, encoding="utf-8"):
        rec = json.loads(line)
        if rec["purpose"] == "writer_batch_all15":
            return rec
    raise SystemExit("STOP: no writer batch in the log")


def run_verifier(packet, lead, detail, attempt):
    prompt = verify.build_verifier_prompt(packet, lead, detail)
    rec = llm.call(verify.VERIFIER_MODEL, prompt, llm.VERIFIER_MAX_COMPLETION,
                   "verifier", rank=packet["rank"], attempt=attempt)
    res = verify.parse_verdict(rec["response_text"])
    res["_usage"] = rec["usage"]
    res["_finish_reason"] = rec["finish_reason"]
    return res


def main():
    roster = checks.build_name_roster()
    batch = load_writer_batch()
    first = parse_renderings(batch["response_text"])
    missing = [p["rank"] for p in PACKETS if p["rank"] not in first]
    if missing:
        print(f"WARNING: writer batch missing ranks {missing}")

    results = []
    for packet in PACKETS:
        rank = packet["rank"]
        row = {"rank": rank, "feed_sentence": packet["feed_sentence"],
               "thin_packet": packet["thin"], "attempts": []}

        lead, detail = first.get(rank, ("", ""))
        status = None

        for attempt in (1, 2):
            chk = checks.check_finding(packet, lead, detail, roster)
            # The verifier runs whether or not the code checks passed, so the two
            # layers are measured independently -- which is half the point of the
            # trial (brief T3/T4, and the cut line that makes T4 uncuttable).
            ver = run_verifier(packet, lead, detail, attempt)

            ok = chk["all_pass"] and ver["verdict"] == "pass"
            row["attempts"].append({
                "attempt": attempt, "lead": lead, "detail": detail,
                "checks": chk, "verifier": ver, "ok": ok,
            })
            if ok:
                status = "first-pass" if attempt == 1 else "regenerated"
                break
            if attempt == 2:
                status = "fell back"
                break

            reason = " ".join(x for x in
                              [checks.failure_reason(chk) if not chk["all_pass"] else "",
                               verify.verifier_reason(ver) if ver["verdict"] != "pass" else ""]
                              if x).strip()
            row["regeneration_reason"] = reason
            rec = llm.call(DISCOVER_PROSE_MODEL,
                           build_single_prompt(packet, reason),
                           llm.WRITER_MAX_COMPLETION, "regenerate",
                           rank=rank, attempt=2)
            again = parse_renderings(rec["response_text"])
            if rank in again:
                lead, detail = again[rank]
            else:
                lead, detail = "", ""

        last = row["attempts"][-1]
        if status == "fell back":
            row["final_lead"] = packet["feed_sentence"]
            row["final_detail"] = ""
        else:
            row["final_lead"], row["final_detail"] = last["lead"], last["detail"]
        row["status"] = status
        results.append(row)
        print(f"rank {rank:2d}: {status:12s} "
              f"checks={'PASS' if last['checks']['all_pass'] else 'FAIL'} "
              f"verifier={last['verifier']['verdict']}")

    json.dump(results, open(RESULTS, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\nwrote {RESULTS}; calls so far {llm.calls_so_far()} of {llm.MAX_CALLS}")


if __name__ == "__main__":
    main()
