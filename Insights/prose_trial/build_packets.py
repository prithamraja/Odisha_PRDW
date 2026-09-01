#!/usr/bin/env python
"""WP-D4 T1 -- deterministic finding packets.

One packet per feed rank 1-15: the current feed sentence verbatim, plus
reference figures computed by REUSING phase5b_report's enrichment (never
reinvented), rendered as display strings because the T3 checks substring-match.

Excluded on purpose: every *_framing / *_caveat key the enrichment attaches.
Those are imperative writing rules for the old prompt ("Lead with the magnitude
from stats.total"), and WP-D4's design is that no rule constrains the writer.
"""
import os, sys, json, ast

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(BASE, "Insights", "src"))

import phase5b_report as p5b

FEED_PATH = os.path.join(BASE, "Insights", "metainsights", "global_feed.json")

# Provenance strings. Every figure must carry one (T1 done-when).
PROV_FEED = "global_feed.json feed[rank] (pinned candidate set, WPD3b §4 hashes)"
PROV_STATS = ("computed by phase5b_report.enrich_candidates_with_stats over "
              "Insights/views_prdw/*.parquet, rebuilt from Data/ via "
              "domain_pack_prdw (calibration README step 1)")

# Keys the enrichment adds that are RULE TEXT, not figures. Never in a packet.
RULE_KEYS = {"evenness_framing", "linkage_framing", "earmark_framing",
             "reporting_caveat", "count_caveat", "linkage_note"}
# Keys that describe what a figure means (kept -- factual, not stylistic).
DESC_KEYS = {"what_this_is", "how_computed", "scope", "basis",
             "how_aggregated", "measure_unit"}


def words_for_exception(exc, common_highlight):
    """The engine's exception category, in words. Three kinds per the brief."""
    cat = exc.get("category")
    hl = exc.get("highlight")
    try:
        hl_t = ast.literal_eval(hl) if isinstance(hl, str) else hl
    except (ValueError, SyntaxError):
        hl_t = None
    hl_vals = [str(x) for x in hl_t] if isinstance(hl_t, tuple) else ([str(hl_t)] if hl_t else [])

    if cat == "NO_PATTERN":
        return "no clear pattern", "the engine found no clear pattern here"
    if cat == "TYPE_CHANGE":
        return "different pattern", "the engine found a different kind of pattern here"
    if cat == "HIGHLIGHT_CHANGE":
        directional = {"INCREASING", "DECREASING"}
        if hl_vals and set(hl_vals) & directional:
            common = set(common_highlight or [])
            if common & directional and not (set(hl_vals) & common):
                other = "increasing" if "INCREASING" in hl_vals else "decreasing"
                theirs = "decreasing" if "INCREASING" in hl_vals else "increasing"
                return ("opposite direction",
                        f"moves in the opposite direction: {other}, where most are {theirs}")
            return "different pattern", f"direction here is {hl_vals[0].lower()}"
        if hl_vals:
            return ("different pattern",
                    "a different one leads here: " + ", ".join(hl_vals))
        return "different pattern", "the engine recorded a different highlight here"
    return "different pattern", f"engine category {cat}"


def flatten_figures(obj, path, out):
    """Every display string in the stats tree becomes one labelled figure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in RULE_KEYS:
                continue
            flatten_figures(v, path + [str(k)], out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_figures(v, path + [str(i)], out)
    else:
        label = " / ".join(path)
        out.append({"label": label, "display": str(obj), "provenance": PROV_STATS})


def scope_in_words(base_subspace):
    if not base_subspace:
        return "all records in this view"
    return "; ".join(f"{d} = {v}" for d, v in base_subspace)


def main():
    feed = json.load(open(FEED_PATH, encoding="utf-8"))["feed"][:15]
    by_view = {}
    for row in feed:
        by_view.setdefault(row["view"], []).append(row)

    enriched = {}
    for view, rows in by_view.items():
        for e in p5b.enrich_candidates_with_stats(view, rows, p5b.VIEW_CONFIGS[view]):
            enriched[e["rank"]] = e

    packets = []
    for row in feed:
        e = enriched[row["rank"]]
        stats = e.get("stats", {}) or {}
        thin = "note" in stats and "top_values" not in stats

        figures = []
        flatten_figures({k: v for k, v in stats.items() if k != "note"}, [], figures)

        cs = (row.get("commonness_sets") or [{}])[0]
        try:
            common_hl = ast.literal_eval(cs.get("highlight") or "()")
        except (ValueError, SyntaxError):
            common_hl = ()
        common_hl = [str(x) for x in common_hl] if isinstance(common_hl, tuple) else []

        exceptions = []
        for exc in row.get("exceptions", []):
            kind, detail = words_for_exception(exc, common_hl)
            exceptions.append({"name": exc["member_label"], "kind": kind,
                               "in_words": detail, "provenance": PROV_FEED})

        packets.append({
            "rank": row["rank"],
            "view": row["view"],
            "view_title": row["view_title"],
            "pattern_type": row["pattern_type"],
            "measure": row["measure"],
            "breakdown": row["breakdown"],
            "compared_across": row["extending_dimension"],
            "scope": scope_in_words(row["base_subspace"]),
            "feed_sentence": row["summary"],
            "feed_sentence_provenance": PROV_FEED,
            "members_following_the_pattern": cs.get("members", []),
            "members_count": cs.get("count"),
            "members_out_of": row.get("hdp_size"),
            "exceptions": exceptions,
            "reference_figures": figures,
            "thin": thin,
            "thin_reason": (stats.get("note") if thin else None),
        })

    out_path = os.path.join(HERE, "packets.json")
    json.dump(packets, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"wrote {out_path}: {len(packets)} packets")
    for p in packets:
        flag = "THIN" if p["thin"] else "    "
        print(f"  rank {p['rank']:2d} {flag} figures={len(p['reference_figures']):3d} "
              f"exceptions={len(p['exceptions'])} members={len(p['members_following_the_pattern'])}")


if __name__ == "__main__":
    main()
