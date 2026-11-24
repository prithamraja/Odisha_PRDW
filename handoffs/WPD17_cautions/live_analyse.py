#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D17 T5: the live check against WP-D15c's rule_off arm. No model call.

    python handoffs/WPD17_cautions/live_analyse.py

Reads live/after.json and handoffs/WPD15c_trial/rule_off.json; writes
live/tables.md and live/answers_before_after.md (GEO-29, L01, L06 in full).
Pass mark 3: every shown answer is searched for the removed cautions' figures
("2.7%" beside "53.2%", "about one in six", "17 completions"); each hit is
listed with the record its sentence cites and whether that record states the
figure for its own subject.
"""
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
import logging                                                     # noqa: E402
logging.basicConfig(level=logging.ERROR)
from DiscoverChat import checks, corpus as corpus_mod, profile_store  # noqa: E402

PATTERNS = [("2.7% / 53.2%", re.compile(r"2\.7%.*53\.2%|53\.2%.*2\.7%")),
            ("about one in six", re.compile(r"one in six", re.I)),
            ("17 completions", re.compile(r"\b17\b[^.]*complet", re.I))]


def mid(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else "-"


def table(res):
    kept = [r for r in res if not r["lost"]]
    m = [r["measures"] for r in kept if r.get("measures")]
    return {
        "Answers": len(res), "Kept": len(kept), "Lost": len(res) - len(kept),
        "Lost on": ", ".join(f"{k} {v}" for k, v in Counter(
            k for r in res if r["lost"] for k in r["lost_on"]).items()) or "-",
        "Passed on the first try": sum(1 for r in kept if r["attempts"] == 1),
        "Wrong numbers shown": sum(len(r["wrong_numbers_shown"]) for r in res),
        "Seconds per answer, middle": mid(r["seconds"] for r in res),
        "Words, middle (kept)": mid(x["words"] for x in m),
        "Insights cited, middle (kept)": mid(r["insights_cited"] for r in kept),
        "Place facts used, middle (kept place answers)": mid(
            len(r["place"].get("lines_used", [])) for r in kept if r.get("place")),
    }


def stated_by(record_id, corpus, figure_re):
    f = corpus.get(record_id)
    text = f.sentence if f is not None else ((profile_store.sentence(record_id) or {}).get("sentence", ""))
    return bool(figure_re.search(text))


def main():
    after = json.loads((HERE / "live" / "after.json").read_text(encoding="utf-8"))
    before = json.loads((REPO / "handoffs" / "WPD15c_trial" / "rule_off.json").read_text(encoding="utf-8"))
    corpus = corpus_mod.load()
    ta, tb = table(after["results"]), table(before["results"])   # a = after, b = before
    out = ["# WP-D17 live check", "",
           "50 held questions, `gpt-6.2-sol`, through `Assembler.answer`, shipped "
           "defaults. Before = WP-D15c `rule_off` (old breakdown store); after = "
           "the rebuilt store.", "", "| | before (WP-D15c rule_off) | after |", "|---|---|---|"]
    out += [f"| {k} | {tb[k]} | {ta[k]} |" for k in ta]
    lost_ok = ta["Lost"] <= tb["Lost"] + 1
    out += ["", f"**Pass mark 1:** wrong numbers shown {ta['Wrong numbers shown']}. "
            f"**Pass mark 2:** lost {ta['Lost']} against {tb['Lost']} + 1 — "
            f"{'HOLDS' if lost_ok else 'FAILS'}.", ""]
    hits = []
    for name, rx in PATTERNS:
        for side, run in (("before", before), ("after", after)):
            for r in run["results"]:
                if r["lost"]:
                    text = r.get("shown_text") or ""
                    sents = [(s, []) for s in text.split("\n") if rx.search(s)]
                else:
                    sents = [(checks.strip_tags(s), checks.cited_ids(s))
                             for s in checks._tagged_sentences(r["tagged"])
                             if rx.search(checks.strip_tags(s))]
                for s, cited in sents:
                    own = [c for c in cited if stated_by(c, corpus, rx)]
                    hits.append({"side": side, "id": r["id"], "figure": name,
                                 "sentence": s, "cited": cited,
                                 "cited_record_states_it": own})
    after_hits = [h for h in hits if h["side"] == "after"]
    out += [f"**Pass mark 3:** answers after the rebuild that state a removed "
            f"caution's figure: {len(after_hits)}"
            + (" — every one listed below with its cited record." if after_hits else "."),
            f"(Before the rebuild, in WP-D15c rule_off: "
            f"{sum(1 for h in hits if h['side'] == 'before')} such sentences.)", ""]
    for h in hits:
        out.append(f"- {h['side']} {h['id']} [{h['figure']}]: {h['sentence'][:220]} — cites "
                   f"{h['cited']}; record states it for its own subject: "
                   f"{h['cited_record_states_it'] or 'no'}")
    (HERE / "live" / "tables.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))

    by_b = {r["id"]: r for r in before["results"]}
    by_a = {r["id"]: r for r in after["results"]}
    ans = ["# GEO-29, L01, L06 — before and after", ""]
    for qid in ("GEO-29", "L01", "L06"):
        ans += [f"## {qid} — {by_a[qid]['question']}", ""]
        for side, r in (("Before (WP-D15c rule_off, old store)", by_b[qid]),
                        ("After (rebuilt store)", by_a[qid])):
            m = r["measures"] or {}
            ans += [f"**{side}** — {'LOST' if r['lost'] else 'kept'}, {r['attempts']} tries, "
                    f"{m.get('words')} words, insights cited {r['insights_cited']} of "
                    f"{r['findings']}, place facts used "
                    f"{', '.join(r.get('lines_used_rows', [])) or '-'}", ""]
            ans += ["> " + l if l else ">" for l in (r["shown_text"] or "").splitlines()]
            ans.append("")
    (HERE / "live" / "answers_before_after.md").write_text("\n".join(ans), encoding="utf-8")


if __name__ == "__main__":
    main()
