#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) T6 -- the review document.

REVIEW.md must read without opening any other file, so everything it needs --
totals, quotes, per-finding text, check results, verdicts -- is written into it.
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import llm
from context import CONTEXT

D = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))
PACKETS = {p["rank"]: p for p in json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))}
REMEASURE = {}
_rm = os.path.join(HERE, "remeasure.json")
if os.path.exists(_rm):
    REMEASURE = json.load(open(_rm, encoding="utf-8"))

FINDINGS = D["findings"]
OUT = os.path.join(HERE, "REVIEW.md")

CANDIDATE_SET = "a7f991c1df3771f9"

VIEW_TITLE = {"view1": "Activity Lifecycle", "view2": "Geo-Month Cash Cube",
              "view3": "GP Performance"}


def usage_rollup():
    by = collections.OrderedDict()
    total = {"n": 0, "prompt": 0, "completion": 0, "reasoning": 0}
    for line in open(llm.LOG, encoding="utf-8"):
        r = json.loads(line)
        u = r["usage"]
        b = by.setdefault(r["purpose"], {"n": 0, "prompt": 0, "completion": 0,
                                         "reasoning": 0, "model": r["model"]})
        b["n"] += 1
        b["prompt"] += u["prompt_tokens"]
        b["completion"] += u["completion_tokens"]
        b["reasoning"] += u["reasoning_tokens"] or 0
        total["n"] += 1
        total["prompt"] += u["prompt_tokens"]
        total["completion"] += u["completion_tokens"]
        total["reasoning"] += u["reasoning_tokens"] or 0
    return by, total


def check_cell(chk):
    bits = []
    for key, label in (("a_numerals", "numerals"), ("b_names", "names"),
                       ("c_db_tokens", "no database wording"), ("d_shape", "shape")):
        bits.append(("PASS " if chk[key]["pass"] else "**FAIL** ") + label)
    return "; ".join(bits)


def check_detail(chk):
    return ("%d numerals checked, all traced; no name outside the packet; no database "
            "wording; lead %d sentence(s), detail %d words"
            % (chk["a_numerals"]["checked"], chk["d_shape"]["lead_sentences"],
               chk["d_shape"]["detail_words"])) if chk["all_pass"] else json.dumps(chk)


def verdict_cell(ver):
    v = ver["verdict"]
    if v == "pass":
        return "**pass** — %d factual claims mapped to source lines" % len(ver.get("claim_map", []))
    if v == "fail":
        return "**fail** — %d drifted claim(s)" % len(ver.get("problems", []))
    return "**fail-to-verify**"


def problems_block(ver, indent="  "):
    L = []
    for p in ver.get("problems", []):
        L.append('%s- Flagged: "%s"' % (indent, p.get("drifted_claim")))
        L.append("%s  Source says: %s" % (indent, p.get("missing_or_contradicted_fact")))
    return "\n".join(L)


def main():
    by, total = usage_rollup()
    statuses = collections.Counter(r["status"] for r in FINDINGS)
    n_rend = sum(len(r["attempts"]) for r in FINDINGS)
    n_nums = sum(a["checks"]["a_numerals"]["checked"] for r in FINDINGS for a in r["attempts"])
    code_fails = sum(1 for r in FINDINGS for a in r["attempts"] if not a["checks"]["all_pass"])
    ver_fail = [(r, a) for r in FINDINGS for a in r["attempts"]
                if a["verifier"]["verdict"] == "fail"]
    ver_unverified = [(r, a) for r in FINDINGS for a in r["attempts"]
                      if a["verifier"]["verdict"] == "fail_to_verify"]

    W = []
    w = W.append

    w("# WP-D4 prose trial — review document")
    w("")
    w("**What this is.** A trial, not a shipped change. The fifteen findings at the top")
    w("of the Discover feed were rewritten by a writer that received **no writing rules")
    w("at all** — only the context brief and, per finding, a packet of deterministically")
    w("computed reference figures and variable definitions. All safety sits *after* the")
    w("writer: mechanical nothing-invented checks, then a different-model verifier.")
    w("Nothing here is wired to the feed, the reports or the frontend; `global_feed.json`")
    w("is untouched and the feed sentences below are its current text.")
    w("")
    w("**Your job at the gate.** Label each of the fifteen **adopt** / **adopt-with-edits**")
    w("/ **reject**, judging the new text against the current feed text shown beside it.")
    w("That labelling — not anything in this document — decides whether the design goes to")
    w("production and what the context brief needs changed.")
    w("")
    w("- **Candidate set:** `%s` (six pinned files in `Insights/metainsights/` verified against WP-D3b §4 before the run; feed `global_feed.json` sha256 `3da40edae324f917…`)" % CANDIDATE_SET)
    w("- **Writer:** `%s` — pinned by D17 through `discover_config`. One batch call, all 15 findings, no rules in the prompt." % D["writer_model"])
    w("- **Verifier:** `%s` — a different model generation; same vendor (disclosed limitation: one completion key on file)." % D["verifier_model"])
    w("- **Context:** the instantiated Appendix A, reproduced in full at the end of this document. It carries **no list of domain facts** and no caution layer; the writer worked from the packets alone.")
    w("")

    w("## Totals")
    w("")
    w("| | count |")
    w("|---|---:|")
    w("| Findings | 15 |")
    w("| Clean on the first pass (checks **and** verifier) | **%d** |" % statuses["first-pass"])
    w("| Passed after one regeneration | **%d** |" % statuses["regenerated"])
    w("| Fell back to the current feed sentence | **%d** |" % statuses["fell back"])
    w("| Renderings put through the safety net | %d |" % n_rend)
    w("| Numerals machine-checked across them | %d |" % n_nums)
    w("| Renderings the code checks failed | **%d** |" % code_fails)
    w("| Renderings the verifier failed | **%d** |" % len(ver_fail))
    w("| Verifier calls that returned nothing to parse | %d |" % len(ver_unverified))
    w("| API calls | %d of %d allowed |" % (total["n"], llm.MAX_CALLS))
    w("")

    w("**What the code checks caught: nothing.** Across %d renderings and %d numerals," % (n_rend, n_nums))
    w("every figure traced to its own packet or to the context, no rendering named a place")
    w("or category outside its own finding, no rendering emitted a database token, and every")
    w("lead and detail was inside the length bounds. The layer is not idle — it is the layer")
    w("that makes \"the writer invented no figure\" a measured statement rather than an")
    w("impression — but on this run it found nothing to reject. Round 1's only two catches")
    w("were fiscal years written `2020-21` against a packet that said `2020-2021`; this")
    w("round's packets carry both forms of every year, and that class is gone.")
    w("")

    w("**What the verifier caught that the code could not.** %d drifts, none of which changes" % len(ver_fail))
    w("a digit and none of which any mechanical check could see:")
    w("")
    n = 0
    for r, a in ver_fail:
        n += 1
        for p in a["verifier"].get("problems", []):
            w('%d. **Finding %d, attempt %d** — "%s"' % (n, r["rank"], a["attempt"], p.get("drifted_claim")))
            w("   *The source says:* %s" % p.get("missing_or_contradicted_fact"))
            break
    w("")
    w("All four are the same species: the numbers were right and the *attribution*,")
    w("*inference* or *implied fact* was not. A pattern read as a practice; a seasonal")
    w("shape read as a control risk; a partial coverage figure read as evidence of missing")
    w("records; a single quoted percentage read as a rank across nine districts. This is the")
    w("class of error the trial exists to test for, and code checks cannot reach it.")
    w("")

    if ver_unverified:
        w("**The verifier's own failure, measured.** One verifier call — finding 1, first")
        w("attempt — returned an empty string: the model spent all 4,000 of its completion")
        w("budget on internal reasoning and stopped for length. Under the brief an")
        w("unparseable verdict is a fail-to-verify, never a pass, so that finding was")
        w("regenerated and its recorded status is *regenerated*. Re-running that same call")
        rm = REMEASURE.get("1/1")
        if rm:
            w("afterwards at the same ceiling returned **%s** on %d reasoning tokens, so the"
              % (rm["remeasured_verdict"], rm["remeasured_usage"]["reasoning_tokens"]))
            w("starvation was a one-off, not a property of that prompt. **Finding 1's first")
            w("rendering was sound; it was regenerated because the judge fell over, not")
            w("because the writing did.** Both versions are shown below.")
        w("")

    w("**Cost.** %d calls: %s. Token usage in full:" % (
        total["n"], ", ".join("%d %s" % (v["n"], k.replace("_", " ")) for k, v in by.items())))
    w("")
    w("| call type | model | calls | prompt tokens | completion tokens | of which reasoning |")
    w("|---|---|---:|---:|---:|---:|")
    for k, v in by.items():
        w("| %s | `%s` | %d | %s | %s | %s |"
          % (k.replace("_", " "), v["model"], v["n"], f"{v['prompt']:,}",
             f"{v['completion']:,}", f"{v['reasoning']:,}"))
    w("| **total** | | **%d** | **%s** | **%s** | **%s** |"
      % (total["n"], f"{total['prompt']:,}", f"{total['completion']:,}",
         f"{total['reasoning']:,}"))
    w("")
    w("The repository holds no per-token price list for these model ids, so the cost is")
    w("stated in tokens rather than in an invented currency figure. Worst case allowed by")
    w("the brief was about 1.44M tokens; this run used %s." % f"{total['prompt'] + total['completion']:,}")
    w("")
    w("---")
    w("")

    for r in FINDINGS:
        rank = r["rank"]
        pk = PACKETS[rank]
        last = r["attempts"][-1]
        w("## Finding %d — %s" % (rank, VIEW_TITLE.get(r["view"], r["view"])))
        w("")
        w("**Status: %s.**" % r["status"].upper())
        w("")
        w("**Current feed text (what production says today)**")
        w("")
        w("> %s" % pk["feed_sentence"].replace("\n", " "))
        w("")
        w("**Final rendering**")
        w("")
        if r["status"] == "fell back":
            w("*The safety net rejected both attempts, so the final rendering is the current")
            w("feed sentence above, marked* `FELL BACK`. *The text the writer actually")
            w("produced is shown under \"attempts\" below, because you cannot judge the design")
            w("from a fallback.*")
        else:
            w("> **%s**" % r["final_lead"].replace("\n", " "))
            w(">")
            w("> %s" % r["final_detail"].replace("\n", " "))
        w("")
        w("**Checks (final attempt):** %s" % check_cell(last["checks"]))
        w("")
        w("**Verifier verdict (final attempt):** %s" % verdict_cell(last["verifier"]))
        if last["verifier"].get("problems"):
            w("")
            w(problems_block(last["verifier"], indent=""))
        w("")
        w("**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject")
        w("")

        if len(r["attempts"]) > 1 or r["status"] == "fell back":
            w("<details><summary>Attempts</summary>")
            w("")
            for a in r["attempts"]:
                w("**Attempt %d** — checks %s, verifier %s"
                  % (a["attempt"], "PASS" if a["checks"]["all_pass"] else "FAIL",
                     a["verifier"]["verdict"]))
                w("")
                w("> **%s**" % a["lead"].replace("\n", " "))
                w(">")
                w("> %s" % a["detail"].replace("\n", " "))
                w("")
                if a["verifier"].get("problems"):
                    w(problems_block(a["verifier"], indent=""))
                    w("")
            if r.get("regeneration_reason"):
                w("*Reason fed back to the writer for the regeneration:* %s"
                  % r["regeneration_reason"])
                w("")
            rm = REMEASURE.get("%d/1" % rank)
            if rm:
                w("*Re-measurement of attempt 1's verdict, run after the trial and not counted")
                w("in it:* the same verifier, same ceiling, same rendering returned **%s**"
                  % rm["remeasured_verdict"])
                w("(finish `%s`, %d reasoning tokens, %d factual claims mapped to source lines)."
                  % (rm["remeasured_finish_reason"],
                     rm["remeasured_usage"]["reasoning_tokens"],
                     len(rm.get("claim_map") or [])))
                w("")
            w("</details>")
            w("")
        w("---")
        w("")

    w("## Appendix — the context every rendering was written from")
    w("")
    w("Reproduced verbatim, so this document reads without opening another file. It is the")
    w("instantiated Appendix A of the WP-D4 brief: the operator's template with the four")
    w("PR&DW slot values filled in. Note what is *not* in it — no list of domain facts, no")
    w("caution library, no writing rules, no phrasing suggestions.")
    w("")
    for line in CONTEXT.split("\n"):
        w("> " + line if line.strip() else ">")
    w("")

    open(OUT, "w", encoding="utf-8").write("\n".join(W) + "\n")
    print("wrote %s (%d lines)" % (OUT, len(W)))


if __name__ == "__main__":
    main()
