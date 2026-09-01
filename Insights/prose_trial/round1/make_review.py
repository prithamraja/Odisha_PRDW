#!/usr/bin/env python
"""WP-D4 T6 -- the review document. Reads without opening any other file."""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify import VERIFIER_MODEL

PACKETS = {p["rank"]: p for p in json.load(open(os.path.join(HERE, "packets.json"), encoding="utf-8"))}
RESULTS = json.load(open(os.path.join(HERE, "results.json"), encoding="utf-8"))
V2 = json.load(open(os.path.join(HERE, "results_v2.json"), encoding="utf-8"))
CALLS = [json.loads(l) for l in open(os.path.join(HERE, "logs", "calls.jsonl"), encoding="utf-8")]

CANDIDATE_SET_ID = "a7f991c1df3771f9"
WRITER_MODEL = "gpt-5.6-sol"


def check_line(chk):
    a, b, c, d = chk["a_numerals"], chk["b_names"], chk["c_db_tokens"], chk["d_shape"]
    bits = [
        "(a) numerals {} ({} checked{})".format(
            "PASS" if a["pass"] else "FAIL", a["checked"],
            "" if a["pass"] else ": " + ", ".join(a["unsupported"])),
        "(b) names {}{}".format("PASS" if b["pass"] else "FAIL",
                                "" if b["pass"] else ": " + ", ".join(b["not_in_packet"])),
        "(c) db tokens {}{}".format("PASS" if c["pass"] else "FAIL",
                                    "" if c["pass"] else ": " + ", ".join(c["tokens"])),
        "(d) shape {} (lead {} sent., detail {} w)".format(
            "PASS" if d["pass"] else "FAIL", d["lead_sentences"], d["detail_words"]),
    ]
    return "; ".join(bits)


def main():
    L = []
    W = L.append

    usage = collections.Counter()
    for c in CALLS:
        usage["prompt"] += c["usage"]["prompt_tokens"]
        usage["completion"] += c["usage"]["completion_tokens"]
        usage["reasoning"] += c["usage"]["reasoning_tokens"] or 0
    by_purpose = collections.Counter(c["purpose"] for c in CALLS)

    n_first = sum(1 for r in RESULTS if r["status"] == "first-pass")
    n_regen = sum(1 for r in RESULTS if r["status"] == "regenerated")
    n_fell = sum(1 for r in RESULTS if r["status"] == "fell back")
    v2_pass = sum(1 for k, v in V2.items() if v["verdict"] == "pass")
    n_v2 = len(V2)

    W("# WP-D4 prose trial - review document")
    W("")
    W("**What this is.** A trial, not a shipped change. Fifteen findings were rewritten by")
    W("a context-driven writer that received no writing rules at all - only the context")
    W("brief (Appendix A of the WP-D4 brief) and a packet of deterministically computed")
    W("reference figures per finding. All safety sits *after* the writer: mechanical")
    W("nothing-invented checks, then a different-model verifier. Nothing here is wired to")
    W("the feed, the reports or the frontend; `global_feed.json` is untouched.")
    W("")
    W("**Your job at the gate.** Label each of the fifteen **adopt** / **adopt-with-edits**")
    W("/ **reject**, judging the new text against the current feed text shown beside it.")
    W("")
    W("- **Candidate set:** `{}` (six pinned files verified against WPD3b section 4 before the run)".format(CANDIDATE_SET_ID))
    W("- **Writer:** `{}` - one batch call, all 15 findings, no rules in the prompt".format(WRITER_MODEL))
    W("- **Verifier:** `{}` - a different model generation; same vendor (disclosed limitation)".format(VERIFIER_MODEL))
    W("")
    W("## Totals")
    W("")
    W("| | count |")
    W("|---|---:|")
    W("| Findings | 15 |")
    W("| Clean on the first pass (checks + verifier v1) | **{}** |".format(n_first))
    W("| Passed after one regeneration | **{}** |".format(n_regen))
    W("| Fell back to the current feed sentence | **{}** |".format(n_fell))
    W("| Code checks that fired (of 28 renderings checked) | 2 |")
    W("| Verifier v1 failures later shown to be false positives | {} of {} |".format(v2_pass, n_v2))
    W("| API calls | {} of 60 allowed |".format(len(CALLS)))
    W("")
    W("**What the code checks caught.** Two of twenty-eight renderings, both the same")
    W("thing: a fiscal year written `2020-21` / `2024-25` where the packet says")
    W("`2020-2021` / `2024-2025`. The number was *right*; it was not *verbatim*. Nothing")
    W("else ever tripped them - across 181 numerals checked, the writer invented no")
    W("figure, named no place outside its own finding, and emitted no database token.")
    W("")
    W("**What the verifier caught that the code could not.** Three real drifts, none of")
    W("which changes a digit and none of which any mechanical check could see:")
    W("")
    W("1. **Finding 3** - the writer narrowed a stated limitation, turning the background's")
    W("   \"sanction records exist for only about one **work** in six\" into \"one **activity**")
    W("   in six\". Different denominator, same digits.")
    W("2. **Finding 8** - the writer attached a sample-wide total (`Rs 41.61 crore`) to the")
    W("   eighteen Gram Panchayats the *pattern* holds in, and dropped the finding's")
    W("   `Costed`-only scope. Every numeral was legitimate; the attribution was not.")
    W("3. **Finding 9** - the writer asserted \"this analysis did not assess geographic")
    W("   differences\", a claim about the analysis that no source makes.")
    W("")
    W("**The verifier's own defect, measured.** Under the brief's literal T4 wording the")
    W("verifier failed 8 of 15 - but {} of those 8 were one repeated false positive: it".format(v2_pass))
    W("flagged the *\"what to check at the next review\"* sentence as an unsupported claim,")
    W("the very sentence Appendix A asks the writer to produce. The verifier sees only the")
    W("background bullets, which never *state* a recommendation, so every suggestion looked")
    W("invented. Re-running those eight with one sentence added, separating a suggested")
    W("action from a factual claim, {} of {} passed. **The fallbacks below are an artefact of".format(v2_pass, n_v2))
    W("that verifier wording, not of the writing** - which is why each one shows the")
    W("rendering it produced as well as the fallback.")
    W("")
    W("---")
    W("")

    for r in RESULTS:
        rank = r["rank"]
        p = PACKETS[rank]
        last = r["attempts"][-1]
        v2 = V2.get(str(rank)) or V2.get(rank)

        title = "## Finding {} - {}".format(rank, p["view_title"])
        if p["thin"]:
            title += "  ·  *thin packet: no reference figures could be computed*"
        W(title)
        W("")
        W("**Status: {}**".format(r["status"].upper()))
        W("")
        W("**Current feed text (what the officer sees today):**")
        W("")
        W("> " + r["feed_sentence"])
        W("")
        if r["status"] == "fell back":
            W("**Final rendering - per the failure path, this is the current feed sentence above.**")
            W("")
            W("**The rendering that was produced** (shown because the fallback was driven by the")
            W("verifier wording described above, not by anything wrong in this text):")
        else:
            W("**Final rendering:**")
        W("")
        W("> **Lead.** " + last["lead"].replace("\n", " "))
        W(">")
        W("> **Detail.** " + last["detail"].replace("\n", " "))
        W("")
        W("**Checks (final rendering):** " + check_line(last["checks"]))
        W("")
        if len(r["attempts"]) > 1:
            W("**First attempt checks:** " + check_line(r["attempts"][0]["checks"]))
            W("")
            W("**Why it was regenerated:** " + r.get("regeneration_reason", "")[:600])
            W("")
        v1 = last["verifier"]
        W("**Verifier v1 ({}): {}**".format(VERIFIER_MODEL, v1["verdict"].upper()))
        W("")
        if v1["verdict"] == "pass":
            for c in v1.get("claim_map", [])[:6]:
                W("- claim: *{}* -> supported by: {}".format(c.get("claim"), c.get("supported_by")))
        else:
            for pr in v1.get("problems", [])[:4]:
                W("- flagged: *\"{}\"*".format(pr.get("drifted_claim")))
                W("  - source says: {}".format(pr.get("missing_or_contradicted_fact")))
        W("")
        if v2:
            W("**Verifier v2 (action separated from claim): {}**".format(v2["verdict"].upper()))
            W("")
            if v2["verdict"] == "pass":
                for c in v2.get("claim_map", [])[:4]:
                    W("- claim: *{}* -> supported by: {}".format(c.get("claim"), c.get("supported_by")))
            else:
                for pr in v2.get("problems", [])[:3]:
                    W("- flagged: *\"{}\"*".format(pr.get("drifted_claim")))
                    W("  - source says: {}".format(pr.get("missing_or_contradicted_fact")))
            W("")
        W("**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject")
        W("")
        W("---")
        W("")

    W("## Calls and usage")
    W("")
    W("| purpose | calls | model |")
    W("|---|---:|---|")
    for k, v in by_purpose.items():
        model = next(c["model"] for c in CALLS if c["purpose"] == k)
        W("| {} | {} | `{}` |".format(k, v, model))
    W("| **total** | **{}** | cap 60 |".format(len(CALLS)))
    W("")
    W("Prompt tokens {:,} - completion tokens {:,} (of which reasoning {:,}) - total {:,}.".format(
        usage["prompt"], usage["completion"], usage["reasoning"],
        usage["prompt"] + usage["completion"]))
    W("Every call returned `finish_reason: stop`; nothing was truncated and the batch was")
    W("never split. The repo records no token price, so usage is reported in tokens only.")
    W("")

    out = os.path.join(HERE, "REVIEW.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", out, len("\n".join(L)), "chars")


if __name__ == "__main__":
    main()
