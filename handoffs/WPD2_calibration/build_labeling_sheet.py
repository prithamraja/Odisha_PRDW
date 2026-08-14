"""WP-D2 T6: build the operator's calibration labeling sheet.

One row per ranked finding across the three views, carrying everything the
operator needs to judge it -- the plain-English summary the engine itself
generates, the figures, the exceptions, the score components -- and one EMPTY
column for their verdict. The point of the sheet is that labelling requires no
code, no notebook and no re-run: open it, read the summary, type a word.

Usage:
    python build_labeling_sheet.py --base <Insights dir> --out <dir>

Writes  <out>/labeling_sheet.csv        one row per finding, blank `label`
        <out>/findings_view{1,2,3}.md   the same findings, readable, per view
"""
import argparse
import csv
import io
import json
import os
import sys

LABELS = "real | already-known | spurious"


def fmt_subspace(base_subspace) -> str:
    if not base_subspace:
        return "(whole view)"
    return "; ".join(f"{d}={v}" for d, v in base_subspace)


def fmt_commonness(c: dict) -> str:
    out = []
    for cs in c.get("commonness_sets") or []:
        members = ", ".join(str(m) for m in cs["members"])
        out.append(f"{cs['highlight']} in {cs['count']}/{c['hdp_size']} "
                   f"({cs['proportion']:.0%}): {members}")
    return " | ".join(out)


def fmt_exceptions(c: dict) -> str:
    out = []
    for exc in c.get("exceptions") or []:
        bits = f"{exc['member_label']} [{exc['category']}]"
        if exc.get("highlight"):
            bits += f" {exc['highlight']}"
        out.append(bits)
    return " | ".join(out)


def fmt_stats(c: dict) -> str:
    stats = c.get("stats") or {}
    if "note" in stats:
        return stats["note"]
    bits = []
    if "total" in stats:
        bits.append(f"total {stats['total']}")
    for label, entry in list((stats.get("highlight_values") or {}).items())[:3]:
        share = f" ({entry['share_of_total']})" if "share_of_total" in entry else ""
        bits.append(f"{label} = {entry['value']}{share}")
    for label, entry in list((stats.get("top_values") or {}).items())[:3]:
        share = f" ({entry['share_of_total']})" if "share_of_total" in entry else ""
        bits.append(f"top: {label} = {entry['value']}{share}")
    return "; ".join(bits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    sys.path.insert(0, os.path.join(base, "src"))
    os.makedirs(args.out, exist_ok=True)

    from phase2_engine import load_candidates
    from phase5_ranking import generate_nl_summary
    import phase5b_report as p5b

    rows = []
    for view_name, cfg in p5b.VIEW_CONFIGS.items():
        ranked_path = os.path.join(base, "metainsights", f"{view_name}_ranked.json")
        if not os.path.exists(ranked_path):
            print(f"MISSING {ranked_path} -- skipping {view_name}")
            continue
        with io.open(ranked_path, encoding="utf-8") as f:
            ranked = json.load(f)
        enriched = p5b.enrich_candidates_with_stats(view_name, ranked, cfg)
        summaries = [generate_nl_summary(c) for c in load_candidates(ranked_path)]
        title = p5b.VIEW_DESCRIPTIONS[view_name]["title"]

        md = [f"# {title} -- top {len(enriched)} findings\n",
              f"*View `{view_name}`, {cfg.name}. Ranked by the phase 5 greedy "
              f"selector (score = conciseness x impact), redundancy-penalised.*\n"]

        for i, c in enumerate(enriched):
            rank = i + 1
            rows.append({
                "view": view_name,
                "view_title": title,
                "rank": rank,
                "label  (" + LABELS + ")": "",
                "operator_notes": "",
                "summary": summaries[i],
                "figures": fmt_stats(c),
                "pattern_type": c["pattern_type"],
                "measure": c["measure"],
                "breakdown": c["breakdown"],
                "subspace": fmt_subspace(c["base_subspace"]),
                "varied_along": f"{c['extending_strategy']} on {c['extending_dimension']}",
                "hdp_size": c["hdp_size"],
                "commonness": fmt_commonness(c),
                "exceptions": fmt_exceptions(c),
                "n_exceptions": len(c.get("exceptions") or []),
                "score": round(c["score"], 4),
                "conciseness": round(c["conciseness"], 4),
                "impact": round(c["impact"], 4),
                "fy_2023_24_caveat": "yes" if c.get("reporting_caveat") else "",
            })

            md += [
                f"\n## #{rank}  score {c['score']:.4f}"
                f"  (conciseness {c['conciseness']:.4f} x impact {c['impact']:.4f})\n",
                f"**{summaries[i]}**\n",
                f"- pattern: `{c['pattern_type']}`, measure `{c['measure']}`, "
                f"broken down by `{c['breakdown']}`",
                f"- slice: {fmt_subspace(c['base_subspace'])}, "
                f"varied along `{c['extending_dimension']}` "
                f"({c['extending_strategy']}), {c['hdp_size']} members",
                f"- commonness: {fmt_commonness(c) or '(none)'}",
                f"- exceptions: {fmt_exceptions(c) or '(none)'}",
                f"- figures: {fmt_stats(c) or '(none)'}",
            ]
            if c.get("reporting_caveat"):
                md.append("- **FY 2023-24 reporting caveat applies** "
                          "(activity counts compared across the boundary)")
            md.append("\n**label:** `real` / `already-known` / `spurious`  ->  "
                      "________________\n")

        out_md = os.path.join(args.out, f"findings_{view_name}.md")
        with io.open(out_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        print(f"{view_name}: {len(enriched)} findings -> {out_md}")

    if not rows:
        print("no findings")
        return 1

    out_csv = os.path.join(args.out, "labeling_sheet.csv")
    with io.open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} findings -> {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
