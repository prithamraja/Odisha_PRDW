#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) T1 -- deterministic finding packets.

One packet per feed rank 1-15. A packet is STRUCTURE, FIGURES and DEFINITIONS,
and nothing else. Per the operator ruling of 2026-08-31 there is no caution
layer, no scope note and no interpretive text of any kind.

  structure   the current feed sentence verbatim; what the finding is measured
              over; which members follow the pattern; which are exceptions and
              in what way, in words
  figures     computed by REUSING phase5b_report.enrich_candidates_with_stats,
              never reinvented, and carried as DISPLAY STRINGS because the T3
              checks match text (brief T1 trap: no raw floats)
  definitions one line per variable the finding uses -- measure, breakdown,
              extending dimension, filter dimensions -- from the signed
              glossary; unit, money basis, sign convention, what the values are

Deliberately excluded: every *_framing / *_caveat key the enrichment attaches.
Those are imperative writing rules for the production prompt ("LEAD WITH THE
PERCENTAGE", "Copy both figures verbatim"), and WP-D4's whole design is that no
rule constrains the writer.
"""
import os, sys, json, ast, copy

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(BASE, "Insights", "src"))
sys.path.insert(0, HERE)

import phase5b_report as p5b
import glossary

FEED_PATH = os.path.join(BASE, "Insights", "metainsights", "global_feed.json")

# Provenance strings. Every figure carries one (T1 done-when).
PROV_FEED = "global_feed.json feed[rank] (pinned candidate set, WPD3b section 4 hashes)"
PROV_STATS = ("computed by phase5b_report.enrich_candidates_with_stats over "
              "Insights/views_prdw/*.parquet, rebuilt from Data/ via "
              "domain_pack_prdw (calibration README step 1)")
PROV_GRAIN = ("computed by phase5b_report.enrich_candidates_with_stats on the "
              "same view, measure and filter, with the breakdown set to the "
              "fiscal-year grain this finding covers")

# Keys the enrichment adds that are RULE TEXT, not figures. Never in a packet.
RULE_KEYS = {"evenness_framing", "linkage_framing", "earmark_framing",
             "reporting_caveat", "count_caveat", "linkage_note"}


def words_for_exception(exc, common_highlight):
    """The engine's exception category, in words. Three kinds per the brief:
    opposite-direction, different-pattern, no-clear-pattern."""
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


def flatten_figures(obj, path, out, provenance):
    """Every display string in the stats tree becomes one labelled figure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in RULE_KEYS:
                continue
            flatten_figures(v, path + [str(k)], out, provenance)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_figures(v, path + [str(i)], out, provenance)
    else:
        out.append({"label": " / ".join(path), "display": str(obj),
                    "provenance": provenance})


def scope_in_words(base_subspace):
    if not base_subspace:
        return "all records in this view"
    return "; ".join(f"{d} = {v}" for d, v in base_subspace)


def year_forms(text):
    """T1: give every fiscal year in BOTH display forms, so a rendering that
    writes 2020-21 for the packet's 2020-2021 is not failed on formatting."""
    import re
    out = {}
    for y in re.findall(r"\b(\d{4})-(\d{4})\b", text):
        full = f"{y[0]}-{y[1]}"
        out[full] = f"{y[0]}-{y[1][2:]}"
    return dict(sorted(out.items()))


def definitions_for(row):
    """One line per variable the finding uses. Order: measure, breakdown,
    extending dimension, then each filter dimension."""
    view = row["view"]
    defs = []
    seen = set()

    def add(name, kind, text):
        if name in seen or not text:
            return
        seen.add(name)
        defs.append({"variable": name, "role": kind, "definition": text,
                     "provenance": glossary.PROVENANCE})

    add(row["measure"], "the measure", glossary.measure_definition(view, row["measure"]))
    add(row["breakdown"], "the breakdown", glossary.dimension_definition(row["breakdown"]))
    add(row["extending_dimension"], "compared across",
        glossary.dimension_definition(row["extending_dimension"]))
    for dim, _val in (row.get("base_subspace") or []):
        add(dim, "filter", glossary.dimension_definition(dim))
    return defs


def missing_definitions(row, defs):
    """Variables the finding uses that the signed glossary has no line for."""
    used = [row["measure"], row["breakdown"], row["extending_dimension"]]
    used += [d for d, _ in (row.get("base_subspace") or [])]
    have = {d["variable"] for d in defs}
    return sorted({u for u in used if u and u not in have})


def grain_figures(row, config):
    """For the two temporal_grain findings (breakdown '(varies)'), the enrichment
    returns figures for no grain at all, because the aggregation across three
    different time units is ambiguous. Rather than ship an empty packet, run the
    SAME enrichment function on the SAME view, measure and filter with the
    breakdown set to fiscal_year -- which is one of the three grains the finding
    itself covers. Nothing is computed here that the enrichment does not compute;
    only the breakdown argument changes, and the figures are labelled in the
    packet as the fiscal-year grain's own. (Decide-and-document, T1.)"""
    probe = copy.deepcopy(row)
    probe["breakdown"] = "fiscal_year"
    probe.pop("commonness_sets", None)
    out = p5b.enrich_candidates_with_stats(row["view"], [probe], config)[0]
    stats = {k: v for k, v in (out.get("stats") or {}).items() if k != "note"}
    figures = []
    flatten_figures(stats, [], figures, PROV_GRAIN)
    return figures


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
        note = stats.get("note")

        figures = []
        flatten_figures({k: v for k, v in stats.items() if k != "note"}, [],
                        figures, PROV_STATS)

        grain = []
        if not figures and row["breakdown"] == "(varies)":
            grain = grain_figures(row, p5b.VIEW_CONFIGS[row["view"]])

        thin = not figures and not grain

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

        defs = definitions_for(row)

        packet = {
            "rank": row["rank"],
            "view": row["view"],
            "view_title": row["view_title"],
            "view_row": glossary.VIEW_ROW.get(row["view"]),
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
            "definitions": defs,
            "definitions_missing": missing_definitions(row, defs),
            "reference_figures": figures,
            "grain_figures": grain,
            "thin": thin,
            "thin_reason": (note if thin else None),
        }
        blob = json.dumps(packet, ensure_ascii=False)
        packet["year_forms"] = year_forms(blob)
        packets.append(packet)

    out_path = os.path.join(HERE, "packets.json")
    json.dump(packets, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print("wrote %s: %d packets" % (out_path, len(packets)))
    for p in packets:
        flag = "THIN" if p["thin"] else "    "
        print("  rank %2d %s figures=%3d grain=%2d defs=%d missing=%s exceptions=%d members=%d"
              % (p["rank"], flag, len(p["reference_figures"]), len(p["grain_figures"]),
                 len(p["definitions"]), p["definitions_missing"] or "-",
                 len(p["exceptions"]), len(p["members_following_the_pattern"])))


if __name__ == "__main__":
    main()
