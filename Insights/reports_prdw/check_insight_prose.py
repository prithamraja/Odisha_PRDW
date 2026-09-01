#!/usr/bin/env python
# -*- coding: utf-8 -*-
# =============================================================================
# WP-D4b T3 -- replayable checker for metainsights/insight_prose.json
# =============================================================================
# Re-runs the nothing-invented checks over the SHIPPED sidecar, from the SHIPPED
# packets. It re-derives nothing from the model and calls no API: if the sidecar
# says a rendering was check-green, this asserts that from the same inputs the
# build used, so a reviewer can replay the claim without trusting the run.
#
#   python Insights/reports_prdw/check_insight_prose.py --base Insights
#
# WHAT REPLAYS WHERE
#   Everything below replays on the Drive copy, with no parquet views and no
#   API key, because the packets, the instantiated context and the 217-name
#   roster all travel INSIDE the sidecar.
#   The one thing that needs a mirror with views_prdw/*.parquet is --rebuild-roster,
#   which rebuilds the name roster from the three views and asserts it matches
#   the one the sidecar shipped. Without that flag the roster is taken as
#   shipped and the check is stated as such in the output.
#
# There is also a --determinism mode, for the T2 gate: given two sidecars it
# asserts that every deterministic field is byte-identical and reports the run
# stamp and the LLM wording as the only differences.
# =============================================================================
"""WP-D4b -- replay the insight-prose checks over the shipped sidecar."""
import os
import sys
import re
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import phase5e_insight_prose as p5e
import insight_prose_config as CFG


# The run-level fields that must be byte-identical between two runs of the same
# build. Everything else in `run` is a measurement of the calls themselves.
DETERMINISTIC_RUN_FIELDS = [
    "candidate_set_id", "feed_sha256", "source_set_sha256", "context",
    "context_sha256", "context_slot_values", "ceilings", "writer_model",
    "verifier_model", "batch_plan", "name_roster", "packets",
]


def banned_tokens(text):
    """The T3 check-(c) scan, reusable: raw column identifiers, "(varies)",
    PERIOD_<n>, and the engine's pattern-type enums.

    Shared so the WP-D4c offline self-test scans cleaned fallback text with
    exactly the check the build applies to model-written text.
    """
    hits = list(p5e._SNAKE.findall(text)) + p5e._PERIOD_ANY.findall(text)
    if p5e._VARIES in text.lower():
        hits.append(p5e._VARIES)
    for enum in CFG.ENGINE_ENUMS:
        if re.search(r"\b" + enum + r"\b", text):
            hits.append(enum)
    return sorted(set(hits))


class Report(object):
    def __init__(self):
        self.rows = []

    def add(self, ok, name, detail=""):
        self.rows.append((bool(ok), name, detail))
        print("  %-5s %-52s %s" % ("PASS" if ok else "FAIL", name, detail))
        return ok

    @property
    def failures(self):
        return [r for r in self.rows if not r[0]]

    def done(self, title):
        n = len(self.rows)
        bad = len(self.failures)
        print("\n%s: %d checks, %d failed" % (title, n, bad))
        if bad:
            for _ok, name, detail in self.failures:
                print("  FAILED: %s %s" % (name, detail))
        return 1 if bad else 0


# =============================================================================
# The replay
# =============================================================================

def check_sidecar(sidecar_path, feed_path, source_set_path, rebuild_roster_base=None):
    doc = json.load(open(sidecar_path, encoding="utf-8"))
    run = doc["run"]
    records = doc["records"]
    R = Report()

    print("sidecar: %s" % sidecar_path)
    print("run stamp %s, candidate set %s, writer %s, verifier %s\n"
          % (run.get("stamp"), run.get("candidate_set_id"),
             run.get("writer_model"), run.get("verifier_model")))

    # ---- structural: one stamp, the right set, every rank exactly once -------
    print("Structure")
    stamps = {r.get("run_stamp") for r in records}
    R.add(len(stamps) == 1 and run.get("stamp") in stamps,
          "one run stamp across all records", "stamps=%s" % sorted(stamps))

    source_set = json.load(open(source_set_path, encoding="utf-8"))
    expected_set = source_set["candidate_set_id"]
    R.add(run.get("candidate_set_id") == expected_set,
          "run candidate_set_id matches the feed's source set",
          "%s vs %s" % (run.get("candidate_set_id"), expected_set))
    R.add(all(r.get("candidate_set_id") == expected_set for r in records),
          "every record carries that candidate_set_id")

    feed = json.load(open(feed_path, encoding="utf-8"))["feed"]
    want = [row["rank"] for row in feed]
    got = [r["rank"] for r in records]
    R.add(sorted(got) == sorted(want) and len(set(got)) == len(got),
          "all %d feed ranks present exactly once" % len(want),
          "%d records" % len(got))
    R.add(got == want, "records are in feed order")
    R.add(p5e._sha256_file(feed_path) == run.get("feed_sha256"),
          "the feed on disk is the feed the run read")

    # The context the checks match numerals against must be the one the writer
    # was given, and it must be the accepted Appendix A -- not a later edit.
    R.add(run.get("context") == CFG.CONTEXT,
          "shipped context is the instantiated Appendix A in the code")
    R.add(p5e._sha256_text(run.get("context", "")) == run.get("context_sha256"),
          "shipped context matches its own sha256")

    # ---- the nothing-invented checks, replayed from the shipped packets ------
    print("\nNothing-invented checks, replayed from the shipped packets")
    roster = run["name_roster"]
    roster_note = "roster as shipped (%d names)" % len(roster)
    if rebuild_roster_base:
        sys.path.insert(0, os.path.join(rebuild_roster_base, "src"))
        import phase5b_report as p5b
        rebuilt = p5e.build_name_roster(p5b)
        R.add(rebuilt == roster,
              "name roster rebuilds identically from views_prdw/*.parquet",
              "%d names" % len(rebuilt))
        roster_note = "roster rebuilt from the views (%d names)" % len(rebuilt)
    else:
        print("  ..... %-52s %s" % ("roster NOT rebuilt (no --rebuild-roster)",
                                    "needs a mirror with views_prdw/*.parquet"))

    replayed = failed = 0
    numerals_checked = 0
    for rec in records:
        packet = rec["packet"]
        if rec["status"] == "fell-back":
            continue                     # a fallback is template text, not prose
        chk = p5e.check_finding(packet, rec["lead"], rec["detail"], roster)
        replayed += 1
        numerals_checked += chk["a_numerals"]["checked"]
        if not chk["all_pass"]:
            failed += 1
            print("    rank %d: %s" % (rec["rank"], json.dumps(
                {k: v for k, v in chk.items()
                 if k != "all_pass" and not v["pass"]}, ensure_ascii=False)))
        # and the sidecar must not claim something the replay contradicts
        claimed = rec["attempts"][-1]["checks"]["all_pass"]
        if claimed != chk["all_pass"]:
            print("    rank %d: sidecar claims all_pass=%s, replay says %s"
                  % (rec["rank"], claimed, chk["all_pass"]))
            failed += 1
    R.add(failed == 0,
          "every shipped rendering is check-green on replay",
          "%d replayed, %d numerals, %s" % (replayed, numerals_checked, roster_note))

    # ---- the failure path is honest -----------------------------------------
    print("\nFailure path")
    fell = [r for r in records if r["status"] == "fell-back"]
    feed_by_rank = {row["rank"]: row for row in feed}

    # WP-D4c (D45). The fallback is no longer the raw feed sentence but a
    # deterministic CLEANED rendering of it. The renderer travels in the step,
    # so replay RECOMPUTES the text and asserts it byte-exact -- a stronger
    # assertion than the verbatim one it replaces, because it re-derives rather
    # than compares two copies of the same string.
    bad_fallback = []
    for r in fell:
        recomputed = p5e.cleaned_sentence(feed_by_rank[r["rank"]])
        if (r["lead"] != recomputed or r["detail"] != ""
                or not r.get("fallback_text_is_cleaned_sentence")
                or r["packet"].get("cleaned_sentence") != recomputed):
            bad_fallback.append(r["rank"])
    R.add(not bad_fallback,
          "every fell-back lead == the recomputed cleaned rendering (byte-exact)",
          "%d fell back%s" % (len(fell),
                              "" if not bad_fallback else " -- bad: %s" % bad_fallback))

    # Cleaned fallbacks must also survive the banned-token scan -- the whole
    # point of D45 is that the last resort is readable, not database language.
    dirty = []
    for r in fell:
        hits = banned_tokens(r["lead"])
        if hits:
            dirty.append((r["rank"], hits))
    R.add(not dirty, "cleaned fallbacks carry no raw database token",
          "" if not dirty else str(dirty))

    # A regenerated or fallen-back record must carry the verdict that caused it:
    # attempt 1 must be on the record, and it must actually be a failure.
    needs_cause = [r for r in records if r["status"] in ("regenerated", "fell-back")]
    missing_cause = []
    for r in needs_cause:
        a1 = r["attempts"][0] if r["attempts"] else None
        caused = (a1 is not None and a1["ok"] is False
                  and (a1["verifier"].get("verdict") in ("fail", "fail_to_verify")
                       or not a1["checks"]["all_pass"])
                  and bool(r.get("regeneration_reason", "").strip()))
        if r["status"] == "fell-back":
            a2 = r["attempts"][1] if len(r["attempts"]) > 1 else None
            caused = caused and a2 is not None and a2["ok"] is False
        if not caused:
            missing_cause.append(r["rank"])
    R.add(not missing_cause,
          "every regenerated / fell-back record carries the causing verdict",
          "%d records%s" % (len(needs_cause),
                            "" if not missing_cause else " -- missing: %s" % missing_cause))

    # A pass must never be a rubber stamp, and a fail must always quote.
    vague = []
    for r in records:
        for a in r["attempts"]:
            v = a["verifier"]
            if v["verdict"] == "pass" and not v.get("claim_map"):
                vague.append((r["rank"], "pass with no claim map"))
            if v["verdict"] == "fail" and not all(
                    p.get("drifted_claim") for p in v.get("problems", [])):
                vague.append((r["rank"], "fail with no quoted claim"))
    R.add(not vague, "no vague verdicts: passes map claims, fails quote them",
          "" if not vague else str(vague))

    # ---- the ceilings and the guard actually held ---------------------------
    print("\nGuards")
    ceil = run.get("ceilings", {})
    over_in = [b["batch"] for b in run.get("batch_structure", [])
               if b["usage"]["prompt_tokens"] > ceil.get("max_input_tokens", 0)]
    R.add(not over_in, "no writer batch exceeded the input ceiling",
          "largest %d of %d" % (max([b["usage"]["prompt_tokens"]
                                     for b in run.get("batch_structure", [])] or [0]),
                                ceil.get("max_input_tokens", 0)))
    calls = run.get("usage_totals", {}).get("calls", 0)
    R.add(calls <= ceil.get("max_calls_total", CFG.MAX_CALLS_TOTAL),
          "call count within the spend cap",
          "%d of %d" % (calls, ceil.get("max_calls_total", CFG.MAX_CALLS_TOTAL)))
    missing_usage = [r["rank"] for r in records for a in r["attempts"]
                     for t in a["verifier"].get("tries", [])
                     if not t.get("usage")]
    R.add(not missing_usage, "usage recorded on every verifier call")

    # ---- what the sidecar is for -------------------------------------------
    print("\nProfile (reported, not asserted)")
    counts = {}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    top = [r for r in records if r["rank"] <= 15]
    rest = [r for r in records if r["rank"] > 15]

    def tally(rows):
        c = {}
        for r in rows:
            c[r["status"]] = c.get(r["status"], 0) + 1
        return " / ".join("%s %d" % (k, c.get(k, 0))
                          for k in ("first-pass", "regenerated", "fell-back"))

    print("  all 32      : %s" % tally(records))
    print("  ranks 1-15  : %s" % tally(top))
    print("  ranks 16-32 : %s" % tally(rest))
    print("  thin packets: %s" % ([r["rank"] for r in records if r["thin_packet"]]
                                  or "none"))
    retried = [r["rank"] for r in records for a in r["attempts"]
               if a["verifier"].get("retried_on_empty")]
    print("  verifier retry-on-empty fired on ranks: %s" % (retried or "none"))
    assert counts  # keep the profile block honest about having read something

    return R.done("check_insight_prose")


# =============================================================================
# T2 determinism: two runs differ only in stamp and LLM wording
# =============================================================================

def check_determinism(path_a, path_b):
    a = json.load(open(path_a, encoding="utf-8"))
    b = json.load(open(path_b, encoding="utf-8"))
    R = Report()
    print("determinism: %s  vs  %s\n" % (path_a, path_b))

    print("Run-level deterministic fields")
    for field in DETERMINISTIC_RUN_FIELDS:
        ja = json.dumps(a["run"].get(field), sort_keys=True, ensure_ascii=False)
        jb = json.dumps(b["run"].get(field), sort_keys=True, ensure_ascii=False)
        R.add(ja == jb, "run.%s byte-identical" % field,
              "" if ja == jb else "%d vs %d chars" % (len(ja), len(jb)))

    print("\nRecord-level deterministic fields")
    ra = {r["rank"]: r for r in a["records"]}
    rb = {r["rank"]: r for r in b["records"]}
    R.add(sorted(ra) == sorted(rb), "same ranks in both runs")
    per_record = ["view", "view_title", "pattern_type", "measure", "breakdown",
                  "extending_dimension", "feed_sentence", "thin_packet",
                  "candidate_set_id", "packet"]
    diffs = []
    for rank in sorted(set(ra) & set(rb)):
        for field in per_record:
            ja = json.dumps(ra[rank].get(field), sort_keys=True, ensure_ascii=False)
            jb = json.dumps(rb[rank].get(field), sort_keys=True, ensure_ascii=False)
            if ja != jb:
                diffs.append("rank %d field %s" % (rank, field))
    R.add(not diffs, "every deterministic record field byte-identical",
          "%d fields x %d records%s" % (len(per_record), len(ra),
                                        "" if not diffs else " -- " + "; ".join(diffs[:5])))

    print("\nExpected differences (reported, not asserted)")
    print("  run stamp   : %s  vs  %s" % (a["run"]["stamp"], b["run"]["stamp"]))
    same_text = sum(1 for k in set(ra) & set(rb)
                    if ra[k]["lead"] == rb[k]["lead"]
                    and ra[k]["detail"] == rb[k]["detail"])
    print("  identical prose on %d of %d records (LLM wording is free to differ)"
          % (same_text, len(set(ra) & set(rb))))
    for label, doc in (("A", a), ("B", b)):
        c = {}
        for r in doc["records"]:
            c[r["status"]] = c.get(r["status"], 0) + 1
        print("  %s statuses  : %s" % (label, dict(sorted(c.items()))))
    return R.done("determinism")


# =============================================================================
# WP-D4c self-test: the cleaned renderer and the three ratified fixes, offline
# =============================================================================
# No API call, no sidecar needed -- it runs against the feed alone, so it can be
# run before a build rather than after one.

def self_test(feed_path):
    feed = json.load(open(feed_path, encoding="utf-8"))["feed"]
    R = Report()
    print("self-test: %d feed sentences, no API call\n" % len(feed))

    # ---- T1: every one of the 32 renders clean ------------------------------
    print("T1 -- the cleaned renderer, over all %d feed sentences" % len(feed))
    empty, dirty, varies, bad_others = [], [], [], []
    for row in feed:
        text = p5e.cleaned_sentence(row)
        if not text.strip():
            empty.append(row["rank"])
        hits = banned_tokens(text)
        if hits:
            dirty.append((row["rank"], hits))
        if "(varies)" in text:
            varies.append(row["rank"])
        # "and N others" must never survive as a bare digit: the remainder is
        # either named in full or written with a number word.
        if re.search(r"\band \d+ others\b", text):
            bad_others.append(row["rank"])

    R.add(not empty, "every finding renders a non-empty sentence",
          "%d rendered" % len(feed))
    R.add(not dirty, "no raw database token survives the cleaning",
          "" if not dirty else str(dirty[:4]))
    R.add(not varies, "no \"(varies)\" survives the cleaning",
          "" if not varies else str(varies))
    R.add(not bad_others, "no ungrammatical \"and N others\" survives",
          "" if not bad_others else str(bad_others))

    # The renderer must be deterministic -- the checker recomputes it on replay.
    twice = all(p5e.cleaned_sentence(r) == p5e.cleaned_sentence(r) for r in feed)
    R.add(twice, "the renderer is deterministic")

    # ---- T2: each fix, against the case WP-D4b measured ---------------------
    print("\nT2 -- the three ratified fixes, each against its measured case")

    # fix 2a: "Rs 14.00 lakh" vs "Rs 14 lakh" (WP-D4b rank 8)
    v = p5e._num_variants("14.00")
    R.add("14" in v and "14.00" in v,
          "numeral variant accepts a dropped trailing .00", "14.00 -> %s" % sorted(v))
    R.add("48" not in p5e._num_variants("48.3"),
          "...but still rejects rounding (48.3 is not 48)")
    R.add("5196" not in p5e._num_variants("5,196"),
          "...and never strips a comma (5,196 is not 5196)")

    # fix 2b: the "Tied" case (WP-D4b rank 18)
    packet = {"rank": 0, "view": "view1", "view_title": "t", "view_row": "r",
              "pattern_type": "TOP_TWO", "measure": "fund_tied_total",
              "breakdown": "focus_area_name", "compared_across": "x",
              "scope": "all records in this view", "feed_sentence": "s",
              "members_following_the_pattern": [], "exceptions": [],
              "definitions": [{"variable": "fund_tied_total", "role": "the measure",
                               "definition": "rupees, totalled, PLANNED basis -- the "
                                             "tied, earmarked part of the planned funding."}],
              "reference_figures": [], "grain_figures": [], "year_forms": {}}
    chk = p5e.check_finding(packet, "Tied funding is concentrated.", "Detail here.",
                            ["Tied"])
    R.add(chk["b_names"]["pass"],
          "name check accepts a name the packet carries in another case",
          "flagged: %s" % chk["b_names"]["not_in_packet"])
    chk2 = p5e.check_finding(packet, "Koraput leads.", "Detail here.", ["Koraput"])
    R.add(not chk2["b_names"]["pass"],
          "...but still rejects a name the packet does not carry at all")

    # fix 3: the top/bottom overlap guard (WP-D4b rank 21, 3 groups)
    small = {"count_breakdown_values": 3, "top_values": {"a": 1},
             "bottom_values": {"a": 1}, "note": "n"}
    big = {"count_breakdown_values": 9, "top_values": {"a": 1},
           "bottom_values": {"z": 1}}
    R.add("bottom_values" not in p5e._drop_degenerate_bottom(small),
          "bottom_values dropped when the breakdown has < 8 groups")
    R.add("bottom_values" in p5e._drop_degenerate_bottom(big),
          "...and kept when the breakdown is large enough to have a real bottom")
    R.add("note" not in p5e._drop_degenerate_bottom(small),
          "...and the engine's `note` never reaches a packet as a figure")

    # fix 4: the verifier probe exists and refuses a starved judge
    R.add(callable(getattr(p5e, "verifier_budget_check", None)),
          "the verifier path has a budget probe (D17 discipline on the judge)")

    print("\nSamples -- one per finding class")
    by_rank = {r["rank"]: r for r in feed}
    for rank, label in ((25, "(varies) measure"), (2, "(varies) breakdown"),
                        (3, "\"and 1 others\" fixed"), (14, "code-named"),
                        (11, "plain")):
        print("  rank %-2d %-22s %s" % (rank, label,
                                        p5e.cleaned_sentence(by_rank[rank])))
    return R.done("self-test")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None,
                    help="the Insights directory (default: the one holding this script)")
    ap.add_argument("--sidecar", default=None,
                    help="sidecar to check (default: <base>/metainsights/insight_prose.json)")
    ap.add_argument("--rebuild-roster", action="store_true",
                    help="rebuild the name roster from views_prdw/*.parquet and "
                         "assert it matches the shipped one (needs a mirror)")
    ap.add_argument("--determinism", nargs=2, metavar=("A", "B"),
                    help="compare two sidecars: assert every deterministic field "
                         "is byte-identical (the T2 gate)")
    ap.add_argument("--self-test", action="store_true",
                    help="WP-D4c: run the cleaned renderer over all 32 feed "
                         "sentences and unit-test the three ratified fixes. "
                         "No API call, no sidecar required")
    args = ap.parse_args(argv)

    base = os.path.abspath(args.base) if args.base else os.path.dirname(_HERE)
    P = CFG.paths(base)

    if args.self_test:
        return self_test(P["feed"])

    if args.determinism:
        return check_determinism(*args.determinism)

    sidecar = args.sidecar or P["sidecar"]
    if not os.path.exists(sidecar):
        print("FAIL: no sidecar at %s" % sidecar)
        return 1
    return check_sidecar(sidecar, P["feed"], P["source_set"],
                         rebuild_roster_base=base if args.rebuild_roster else None)


if __name__ == "__main__":
    sys.exit(main())
