#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) T2-T5 -- budget check, the writer batch, the safety net, results.

T2  one batch of all 15 (split by view only if the 16,000-token input cap would
    be exceeded -- a size rule, not content curation)
T3  mechanical checks, in checks.py
T4  the different-model verifier, in verify.py
T5  any T3 or T4 failure regenerates that ONE finding once; a second failure
    falls back to the current feed sentence, marked FELL BACK

Every call goes through llm.call, which enforces the spend guard and writes the
request, the response and `usage` to logs/calls.jsonl. A re-run reuses the writer
batch already in the log rather than re-spending it.
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "Insights", "src"))

import llm, checks, verify
from prompts import build_writer_prompt, build_single_prompt
from context import CONTEXT
from discover_config import DISCOVER_PROSE_MODEL

PACKETS = json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))
RESULTS = os.path.join(HERE, "results.json")

_BLOCK = re.compile(r"===\s*FINDING\s*(\d+)\s*===(.*?)(?====\s*FINDING\s*\d+\s*===|\Z)", re.S | re.I)


def parse_renderings(text):
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


def find_call(purpose):
    if not os.path.exists(llm.LOG):
        return None
    for line in open(llm.LOG, encoding="utf-8"):
        rec = json.loads(line)
        if rec["purpose"] == purpose:
            return rec
    return None


def budget_check():
    """D17: these are reasoning models. Reasoning tokens are drawn from the same
    completion budget as the visible answer, so a budget that looks generous can
    still return an EMPTY string with finish_reason='length' and nothing failing
    loudly. Probe the real prompt shape at the real ceiling before the batch."""
    rec = find_call("budget_check")
    if rec is None:
        prompt = build_writer_prompt(PACKETS[:1])
        rec = llm.call(DISCOVER_PROSE_MODEL, prompt, llm.WRITER_MAX_COMPLETION,
                       "budget_check", rank=1, attempt=1)
    u = rec["usage"]
    reasoning = u["reasoning_tokens"] or 0
    headroom = llm.WRITER_MAX_COMPLETION - u["completion_tokens"]
    print("budget check: model=%s finish=%s reasoning=%s visible_chars=%d "
          "completion=%d of %d, headroom=%d"
          % (rec["model"], rec["finish_reason"], reasoning, rec["response_chars"],
             u["completion_tokens"], llm.WRITER_MAX_COMPLETION, headroom))
    if not rec["response_text"].strip():
        raise SystemExit("STOP: budget check returned EMPTY prose (D17 failure mode)")
    if rec["finish_reason"] != "stop":
        raise SystemExit("STOP: budget check finish_reason=%s" % rec["finish_reason"])
    return {"model": rec["model"], "finish_reason": rec["finish_reason"],
            "reasoning_tokens": reasoning, "visible_chars": rec["response_chars"],
            "completion_tokens": u["completion_tokens"],
            "ceiling": llm.WRITER_MAX_COMPLETION, "headroom": headroom}


def batches():
    """One batch of all 15 unless the input cap would be exceeded; then split by
    view so same-view findings stay together (brief T2 -- a size rule)."""
    full = build_writer_prompt(PACKETS)
    if llm.count_tokens(full) <= llm.MAX_INPUT_TOKENS:
        return [("all15", PACKETS)]
    by_view = {}
    for p in PACKETS:
        by_view.setdefault(p["view"], []).append(p)
    return [(v, ps) for v, ps in sorted(by_view.items())]


def writer_pass():
    renderings, structure = {}, []
    for name, packets in batches():
        purpose = "writer_batch_" + name
        rec = find_call(purpose)
        prompt = build_writer_prompt(packets)
        tok_in = llm.count_tokens(prompt)
        if rec is None:
            rec = llm.call(DISCOVER_PROSE_MODEL, prompt, llm.WRITER_MAX_COMPLETION,
                           purpose, attempt=1)
        got = parse_renderings(rec["response_text"])
        want = [p["rank"] for p in packets]
        structure.append({
            "batch": name, "ranks_sent": want,
            "input_tokens_estimated": tok_in,
            "finish_reason": rec["finish_reason"],
            "usage": rec["usage"],
            "ranks_returned": sorted(got),
            "missing": [r for r in want if r not in got],
        })
        print("batch %-8s ranks %s -> got %s, finish=%s, in=%d out=%d reasoning=%s"
              % (name, want, sorted(got), rec["finish_reason"],
                 rec["usage"]["prompt_tokens"], rec["usage"]["completion_tokens"],
                 rec["usage"]["reasoning_tokens"]))
        if structure[-1]["missing"]:
            print("  WARNING: missing ranks %s" % structure[-1]["missing"])
        renderings.update(got)
    return renderings, structure


def run_verifier(packet, lead, detail, attempt):
    prompt = verify.build_verifier_prompt(packet, lead, detail)
    rec = llm.call(verify.VERIFIER_MODEL, prompt, llm.VERIFIER_MAX_COMPLETION,
                   "verifier", rank=packet["rank"], attempt=attempt)
    res = verify.parse_verdict(rec["response_text"])
    res["_usage"] = rec["usage"]
    res["_finish_reason"] = rec["finish_reason"]
    res["_model"] = rec["model"]
    return res


def main():
    budget = budget_check()
    roster = checks.build_name_roster()
    first, structure = writer_pass()

    results = []
    for packet in PACKETS:
        rank = packet["rank"]
        row = {"rank": rank, "view": packet["view"],
               "feed_sentence": packet["feed_sentence"],
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
            lead, detail = again.get(rank, ("", ""))

        last = row["attempts"][-1]
        if status == "fell back":
            row["final_lead"] = packet["feed_sentence"]
            row["final_detail"] = ""
        else:
            row["final_lead"], row["final_detail"] = last["lead"], last["detail"]
        row["status"] = status
        results.append(row)
        print("rank %2d: %-12s checks=%s verifier=%s"
              % (rank, status, "PASS" if last["checks"]["all_pass"] else "FAIL",
                 last["verifier"]["verdict"]))

    payload = {
        "budget_check": budget,
        "writer_model": DISCOVER_PROSE_MODEL,
        "verifier_model": verify.VERIFIER_MODEL,
        "batch_structure": structure,
        "context_sha_len": len(CONTEXT),
        "findings": results,
    }
    json.dump(payload, open(RESULTS, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\nwrote %s; calls so far %d of %d"
          % (RESULTS, llm.calls_so_far(), llm.MAX_CALLS))


if __name__ == "__main__":
    main()
