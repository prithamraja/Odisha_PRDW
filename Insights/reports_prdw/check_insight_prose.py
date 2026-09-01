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
#
# WP-D4d adds the Discover rendering to the default run: metainsights/
# insight_feed.md must regenerate byte-identical from the shipped sidecar, and
# must parse back through a transcription of the frontend parser into one
# insight per record with every lead and every detail verbatim. Both replay on
# the Drive copy while the shipped rendering carries no reading notes; with
# notes ON the regeneration half needs the parquet views and says so instead of
# asserting.
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

def check_sidecar(sidecar_path, feed_path, source_set_path, rebuild_roster_base=None,
                  feed_md_path=None, base=None):
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

    # WP-D4d. The rendering the Discover page actually serves.
    if feed_md_path:
        check_feed_md(R, sidecar_path, feed_md_path, feed_path, base)

    return R.done("check_insight_prose")


# =============================================================================
# WP-D4d T3 -- the feed markdown: regeneration, and a parse-level round trip
# =============================================================================
# Two claims are worth asserting about metainsights/insight_feed.md, because
# between them they are the whole reason it exists.
#
#   (a) It is a RENDERING. Regenerated from the shipped sidecar it comes back
#       byte-identical, so the published Discover page cannot have drifted from
#       the checked prose -- not by a hand-edit, not by a stale copy.
#   (b) It ROUND-TRIPS. Run back through the frontend's recognition it yields
#       one insight per record, each leadline exactly the record's lead and each
#       detail present verbatim, with reading notes (when on) attached to their
#       section and to no finding row.
#
# `parse_report_min` below is a deliberately literal transcription of
# `frontend/ab-dashboard-main/src/lib/insights-report.ts` -- both insight shapes
# and the reading-note blockquote, in the same order, with the same `tidy` and
# `stripOuterBold`. A transcription can only ever prove the emitter agrees with
# THIS reading of the parser, which is why it is not the only round-trip
# evidence: the frontend's own vitest suite parses the same file with the real
# parser in the mirror (WP-D4d report sec.3). This one replays anywhere,
# including on the Drive copy with no node and no parquet.

_MD_TIDY = " -- "
_MD_TIDY_TO = " — "


def _md_tidy(text):
    return text.replace(_MD_TIDY, _MD_TIDY_TO)


def _md_strip_outer_bold(line):
    trimmed = line.strip()
    inner = trimmed[2:-2].strip()
    return trimmed if "**" in inner else inner


def parse_report_min(md):
    """insights-report.ts's `parseReport`, transcribed. Returns the same shape:
    {"insights": [...], "sections": [{"name", "insights", "readingNote"}]}.
    """
    marker = "> **Reading note:**"
    insights = []
    sections = []
    by_name = {}

    def section_for(name):
        if name not in by_name:
            by_name[name] = {"name": name, "insights": [], "readingNote": None}
            sections.append(by_name[name])
        return by_name[name]

    current = "General"
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("## ") and not line.startswith("### "):
            current = line[3:].strip() or "General"
            section_for(current)
            i += 1
            continue

        if line.startswith(marker):
            parts = [line[len(marker):].strip()]
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                parts.append(re.sub(r"^>\s?", "", lines[i]).strip())
                i += 1
            note = _md_tidy(" ".join(parts).strip())
            if note:
                section_for(current)["readingNote"] = note
            continue

        if line.startswith("**") and line.rstrip().endswith("**"):
            leadline = _md_strip_outer_bold(line)
            bullets = []
            i += 1
            while i < len(lines):
                b = lines[i].strip()
                if re.match(r"^\d+\.\s", b):
                    bullets.append(_md_tidy(re.sub(r"^\d+\.\s*", "", b)))
                    i += 1
                elif b == "":
                    i += 1
                    if i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                        continue
                    break
                else:
                    break
            if leadline:
                ins = {"leadline": _md_tidy(leadline), "bullets": bullets,
                       "section": current}
                insights.append(ins)
                section_for(current)["insights"].append(ins)
            continue

        if line.startswith("### "):
            heading = line[4:].strip()
            i += 1
            nxt = next((l for l in lines[i:] if l.strip() != ""), None)
            if nxt is not None and nxt.startswith("**"):
                continue
            bullets = []
            paragraph = ""
            while i < len(lines):
                b = lines[i].strip()
                if b.startswith("## ") or b.startswith("### ") or b.startswith("---"):
                    break
                if b.startswith("- "):
                    bullets.append(_md_tidy(b[2:]))
                    i += 1
                elif re.match(r"^\d+\.\s", b):
                    bullets.append(_md_tidy(re.sub(r"^\d+\.\s*", "", b)))
                    i += 1
                elif b != "" and not paragraph:
                    paragraph = _md_tidy(b)
                    i += 1
                else:
                    i += 1
            all_bullets = ([paragraph] if paragraph else []) + bullets
            if heading:
                ins = {"leadline": _md_tidy(heading), "bullets": all_bullets,
                       "section": current}
                insights.append(ins)
                section_for(current)["insights"].append(ins)
            continue

        i += 1

    populated = [s for s in sections
                 if s["insights"] or s["readingNote"] is not None]
    return {"insights": insights, "sections": populated}


def check_feed_md(R, sidecar_path, feed_md_path, feed_path, base):
    """(a) the rendering regenerates byte-identical; (b) it round-trips."""
    print("\nThe Discover rendering -- %s" % os.path.basename(feed_md_path))
    if not os.path.exists(feed_md_path):
        R.add(False, "insight_feed.md exists", feed_md_path)
        return

    with open(feed_md_path, "rb") as fh:
        on_disk = fh.read()
    md = on_disk.decode("utf-8")

    # The header states the mode it was emitted in, so the regeneration cannot
    # silently use the other one and call the difference a drift.
    modes = [m for m, line in p5e.FEED_MD_NOTES_LINE.items() if line in md]
    if not R.add(len(modes) == 1,
                 "header names exactly one reading-notes mode",
                 "matched %d of the 2 mode lines" % len(modes)):
        return
    reading_notes = modes[0]

    R.add("do not hand-edit" in md and "phase5e_insight_prose.py" in md,
          "provenance header present (generated, do not hand-edit)")
    sidecar = json.load(open(sidecar_path, encoding="utf-8"))
    stamp = sidecar["run"]["stamp"]
    R.add(stamp in md and sidecar["run"]["candidate_set_id"] in md,
          "header carries the run stamp and candidate set id",
          "%s / %s" % (stamp, sidecar["run"]["candidate_set_id"]))

    # ---- (a) regeneration ---------------------------------------------------
    notes_by_view = None
    can_regen = True
    if reading_notes:
        views = os.path.join(base, "views_prdw")
        can_regen = os.path.isdir(views)
        if can_regen:
            sys.path.insert(0, os.path.join(base, "src"))
            import phase5b_report as p5b
            feed = json.load(open(feed_path, encoding="utf-8"))["feed"]
            notes_by_view = p5e.build_reading_notes(p5b, feed)
        else:
            print("  ..... %-52s %s"
                  % ("regeneration NOT replayed (notes are ON)",
                     "needs a mirror with views_prdw/*.parquet"))
    if can_regen:
        regenerated = p5e.render_feed_markdown(sidecar, notes_by_view).encode("utf-8")
        R.add(regenerated == on_disk,
              "regenerates byte-identical from the shipped sidecar",
              "%d bytes, sha256 %s" % (len(on_disk),
                                       p5e._sha256_text(md)[:16]))

    # ---- (b) the parse-level round trip ------------------------------------
    parsed = parse_report_min(md)
    records = sidecar["records"]

    # The parser returns insights in DOCUMENT order, and the document groups the
    # feed by view. So the records are grouped the same way before they are
    # paired off -- comparing feed order against document order would fail every
    # record after the first for no reason but the grouping. (Feed order itself
    # is asserted inside each section by the pairing, and the page interleaves
    # the sections again at render time.)
    order, by_view = [], {}
    for r in records:
        if r["view"] not in by_view:
            by_view[r["view"]] = []
            order.append(r["view"])
        by_view[r["view"]].append(r)
    want = [r for v in order for r in by_view[v]]
    got = parsed["insights"]

    R.add(len(got) == len(want),
          "one insight parses back per sidecar record",
          "%d parsed, %d records" % (len(got), len(want)))
    if len(got) != len(want):
        return

    bad_lead = [r["rank"] for r, g in zip(want, got) if g["leadline"] != r["lead"]]
    R.add(not bad_lead, "every leadline is its record's lead, verbatim",
          "%d compared%s" % (len(want),
                             "" if not bad_lead else " -- differs: %s" % bad_lead))

    bad_detail = []
    for r, g in zip(want, got):
        expected = [r["detail"]] if r["detail"].strip() else []
        if g["bullets"] != expected:
            bad_detail.append(r["rank"])
    R.add(not bad_detail,
          "every detail comes back whole, and nothing else does",
          "%d with detail, %d fallbacks%s"
          % (sum(1 for r in want if r["detail"].strip()),
             sum(1 for r in want if not r["detail"].strip()),
             "" if not bad_detail else " -- differs: %s" % bad_detail))

    # Order and section membership: the page interleaves by section, so a
    # finding in the wrong one is filed under the wrong chip.
    bad_section = [r["rank"] for r, g in zip(want, got)
                   if g["section"] != r["view_title"]]
    R.add(not bad_section, "every finding lands in its own view's section",
          "" if not bad_section else "misfiled: %s" % bad_section)

    titles = []
    for r in records:
        if r["view_title"] not in titles:
            titles.append(r["view_title"])
    R.add([s["name"] for s in parsed["sections"]] == titles,
          "sections are the feed's view titles, in feed order",
          " / ".join(titles))
    R.add(not [i for i in got if i["section"] == "General"],
          "no finding is stranded outside a section")

    counted = sum(len(s["insights"]) for s in parsed["sections"])
    R.add(counted == len(got),
          "the chip counts sum to the row count", "%d" % counted)

    # ---- reading notes: in the right place, and never a finding -------------
    noted = [s for s in parsed["sections"] if s["readingNote"] is not None]
    if reading_notes:
        expected_views = [r["view"] for r in records]
        seen = []
        for v in expected_views:
            if v not in seen:
                seen.append(v)
        if notes_by_view is not None:
            want_sections = [records[[r["view"] for r in records].index(v)]["view_title"]
                             for v in seen if notes_by_view.get(v)]
            R.add([s["name"] for s in noted] == want_sections,
                  "each note is attached to the section that earned it",
                  " / ".join(want_sections))
        R.add(len(noted) == md.count("\n> **Reading note:**"),
              "one parsed note per marker in the file", "%d" % len(noted))
    else:
        R.add(not noted and "> **Reading note:**" not in md,
              "no reading notes, as emitted (--no-reading-notes)",
              "the operator's dispatch decision, 2026-09-01")

    R.add(not [i for i in got if "Reading note" in i["leadline"]],
          "no reading note is parsed as a finding")


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
    ap.add_argument("--feed-md", default=None,
                    help="the emitted Discover rendering to check (default: "
                         "<base>/metainsights/insight_feed.md)")
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
                         rebuild_roster_base=base if args.rebuild_roster else None,
                         feed_md_path=args.feed_md or P["feed_md"], base=base)


if __name__ == "__main__":
    sys.exit(main())
