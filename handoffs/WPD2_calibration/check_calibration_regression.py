"""WP-D2c T2: the Discover regression gate.

Calibration session 1 labelled 33 ranked findings real / already-known /
spurious. Eleven were spurious, and the eleven were not eleven separate
mistakes -- they were four repeatable CLASSES of mistake, each with an engine
or prose fix in WP-D2c. The labelled sheet is therefore a baseline, and this
script is the gate that keeps the fixes fixed:

  1. DEFINITIONAL PAIRS (A1)      no ranked finding breaks a measure down by a
                                  dimension that measure is tied to by
                                  construction -- as a breakdown, as an HDP
                                  member measure, or as an HDP member breakdown
  2. TWINS (A2)                   no top-15 carries an OUTSTANDING_1 and an
                                  ATTRIBUTION that are the same sentence
  3. SUB-SUPPORT TEMPORAL (A7)    no ranked finding rests on time series with
                                  too few non-zero points to read; re-measured
                                  here from the Parquet, not trusted from a flag
  4. SIZE-TOTAL RANKINGS (A4/2b)  every ranked TOTAL broken down by a group
                                  carries either the volume shares behind it or
                                  a per-unit companion, so it cannot be read as
                                  performance

Each check is run against the CURRENT ranked output, so it fails on a
regression rather than on a copy of what was true when it was written.

It also reports, without gating, how the eleven labelled-spurious findings and
the fifteen labelled-real ones fared -- the class checks above are the gate,
but a human reading the report wants the row-level answer too.

Usage:
    python check_calibration_regression.py --base <Insights dir> \
        [--sheet <labeling_sheet.csv>] [--views view1,view2,view3]

Exits non-zero on any failure, so it can gate a run.
"""
import argparse
import csv
import io
import json
import os
import sys

fails = []


def check(ok, label, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)


def _member_labels(finding: dict) -> set:
    labels = set()
    for cs in finding.get("commonness_sets") or []:
        labels.update(str(m) for m in cs.get("members", []))
    for exc in finding.get("exceptions") or []:
        labels.add(str(exc.get("member_label")))
    return labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the Insights directory")
    ap.add_argument("--sheet", default=None,
                    help="the labelled baseline; defaults to "
                         "CALIBRATION_SESSION_1_labels.csv beside this file")
    ap.add_argument("--views", default="view1,view2,view3")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    src = os.path.join(base, "src")
    sys.path.insert(0, src)
    # The BASELINE is a different file from the working sheet, deliberately.
    # `build_labeling_sheet.py` rewrites `labeling_sheet.csv` with an empty
    # label column on every package rebuild, and the first time this WP rebuilt
    # the package it did exactly that to the operator's session-1 labels. The
    # labelled copy is frozen beside the session record and nothing writes it.
    sheet_path = args.sheet or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "CALIBRATION_SESSION_1_labels.csv")

    import pandas as pd
    import phase5b_report as p5b
    from phase2_engine import load_candidates, temporal_support, temporal_support_ok
    from phase5_ranking import _twin_key, _TWIN_TYPES

    views = args.views.split(",")
    configs = {v: p5b.VIEW_CONFIGS[v] for v in views}
    ranked_raw, ranked_obj = {}, {}
    for v in views:
        path = os.path.join(base, "metainsights", f"{v}_ranked.json")
        if not os.path.exists(path):
            check(False, f"{v}: ranked findings exist", path)
            continue
        with io.open(path, encoding="utf-8") as f:
            ranked_raw[v] = json.load(f)
        ranked_obj[v] = load_candidates(path)

    # ------------------------------------------------------------------ 1
    # A1. The pair is excluded at scope generation, so a ranked finding can
    # only carry one if the exclusion list and the mining run have gone out of
    # step -- which is exactly the regression this is here to catch. Member
    # measures and member breakdowns are checked too: a measure-extending HDP
    # whose members include the excluded measure would put the definitional
    # pattern back in the report through the side door.
    print("\n=== 1. definitional (measure, breakdown) pairs are absent (A1) ===")
    for v in views:
        cfg = configs[v]
        offenders = []
        for i, c in enumerate(ranked_raw.get(v, []), start=1):
            measure, breakdown = c["measure"], c["breakdown"]
            members = _member_labels(c)
            pairs = set()
            if measure != "(varies)" and breakdown != "(varies)":
                pairs.add((measure, breakdown))
            elif measure == "(varies)":
                pairs |= {(m, breakdown) for m in members}
            elif breakdown == "(varies)":
                pairs |= {(measure, b) for b in members}
            hit = [p for p in sorted(pairs) if cfg.is_excluded(*p)]
            if hit:
                offenders.append(f"#{i} {hit}")
        check(not offenders,
              f"{v}: no top-{len(ranked_raw.get(v, []))} finding uses an excluded pair",
              "; ".join(offenders))
        check(bool(cfg.excluded_pairs) or v != "view1",
              f"{v}: the exclusion list is populated",
              f"{len(cfg.excluded_pairs)} pairs")

    # ------------------------------------------------------------------ 2
    print("\n=== 2. OUTSTANDING_1 / ATTRIBUTION twins are merged (A2) ===")
    for v in views:
        seen: dict = {}
        twins = []
        for i, c in enumerate(ranked_obj.get(v, []), start=1):
            if c.pattern_type not in _TWIN_TYPES:
                continue
            key = _twin_key(c)
            if key in seen:
                twins.append(f"#{seen[key]} and #{i}")
            seen[key] = i
        check(not twins, f"{v}: no twin pair survives into the ranked list",
              "; ".join(twins))

    # ------------------------------------------------------------------ 3
    # A7, re-measured. The candidate carries a flag, but a gate that reads the
    # flag it is checking proves nothing: the series are rebuilt from the view
    # here and the guard is applied to them again.
    print("\n=== 3. no temporal finding rests on sub-support series (A7) ===")
    TEMPORAL = {"TREND", "OUTLIER", "SEASONALITY", "CHANGE_POINT", "UNIMODALITY"}
    for v in views:
        cfg = configs[v]
        df = pd.read_parquet(cfg.parquet_path)
        offenders = []
        for i, c in enumerate(ranked_raw.get(v, []), start=1):
            if c.get("low_temporal_support"):
                offenders.append(f"#{i} carries the A7 flag")
                continue
            if c["pattern_type"] not in TEMPORAL:
                continue
            breakdowns = ([c["breakdown"]] if c["breakdown"] != "(varies)"
                          else [b for b in _member_labels(c)
                                if b in cfg.temporal_dimensions])
            measures = ([c["measure"]] if c["measure"] != "(varies)"
                        else [m for m in _member_labels(c)
                              if m in cfg.measure_names])
            # the slices the HDP members describe
            slices = [[]]
            if c["extending_strategy"] == "subspace":
                dim = c["extending_dimension"]
                slices = [[(dim, val)] for val in _member_labels(c)
                          if dim in df.columns and val in set(df[dim].dropna())]
            base = [tuple(f) for f in (c.get("base_subspace") or [])]
            ok_series, bad_series = 0, 0
            for extra in slices:
                sub = df
                for dim, val in base + extra:
                    if dim in sub.columns:
                        sub = sub[sub[dim] == val]
                for b in breakdowns:
                    for m in measures:
                        if b not in sub.columns or len(sub) == 0:
                            continue
                        col = cfg.get_column(m)
                        series = sub.groupby(b)[col].sum().sort_index()
                        if temporal_support_ok(series, cfg):
                            ok_series += 1
                        else:
                            bad_series += 1
            total = ok_series + bad_series
            if total and ok_series <= cfg.tau * total:
                offenders.append(
                    f"#{i} {c['pattern_type']} {c['measure']}: only "
                    f"{ok_series}/{total} member series clear the guard")
        check(not offenders,
              f"{v}: every ranked temporal finding has non-zero support",
              "; ".join(offenders))

    # ------------------------------------------------------------------ 4
    print("\n=== 4. size-total rankings carry size shares or a per-unit companion "
          "(A4 / rule 2b) ===")
    enriched_by_view = {}
    for v in views:
        cfg = configs[v]
        enriched = p5b.enrich_candidates_with_stats(v, ranked_raw.get(v, []), cfg)
        enriched_by_view[v] = enriched
        offenders = []
        for i, c in enumerate(enriched, start=1):
            measure, breakdown = c["measure"], c["breakdown"]
            if measure == "(varies)" or breakdown == "(varies)":
                continue
            if cfg.get_agg(measure) != "sum":
                continue
            if breakdown in cfg.temporal_dimensions:
                continue
            if measure == p5b._VOLUME_MEASURE.get(v):
                continue      # the finding IS the volume; a share would restate it
            stats = c.get("stats") or {}
            if not (stats.get("size_share") or stats.get("intensity_companion")):
                offenders.append(f"#{i} {measure} by {breakdown}")
        check(not offenders,
              f"{v}: every size-total ranking carries its volume context",
              "; ".join(offenders))

    # ---------------------------------------------------------- the sheet
    # Reported, not gated. The gate above is about classes, because a class is
    # what a fix can remove; whether one particular labelled row reappears is a
    # question for the next calibration session, and this is the evidence for it.
    print("\n=== the labelled baseline, row by row (reported, not gated) ===")
    if not os.path.exists(sheet_path):
        print(f"  [skip] no labelled sheet at {sheet_path}")
    else:
        with io.open(sheet_path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        label_col = next(k for k in rows[0] if k.startswith("label"))

        # Two levels of match, because they answer different questions. The
        # SLOT is the shape of the finding -- same pattern type, measure,
        # breakdown and extending axis -- and tells you whether the engine is
        # still looking in the same place. The HIGHLIGHT is what the finding
        # actually says. view2's "Bhubaneswar has the highest (varies) among
        # block_name values" still occupies its slot after A4, but it now says
        # Bheden, because the two intensity measures joined the HDP and changed
        # which value the majority of members point at. That is a different
        # sentence and it is not the labelled row surviving.
        def slot(view, pattern_type, measure, breakdown, varied):
            return (view, pattern_type, measure, breakdown, varied)

        current: dict = {}
        for v in views:
            for c in ranked_raw.get(v, []):
                key = slot(v, c["pattern_type"], c["measure"], c["breakdown"],
                           f"{c['extending_strategy']} on {c['extending_dimension']}")
                highlights = {cs.get("highlight", "")
                              for cs in c.get("commonness_sets") or []}
                current.setdefault(key, set()).update(highlights)

        def sheet_highlight(row: str) -> str:
            # the sheet's `commonness` column reads "('EVEN',) in 27/28 (96%): ..."
            return row.split(" in ", 1)[0].strip() if row else ""

        for want in ("spurious", "real", "already-known"):
            group = [r for r in rows if r[label_col].strip() == want]
            same_slot, same_finding = [], []
            for r in group:
                key = slot(r["view"], r["pattern_type"], r["measure"],
                           r["breakdown"], r["varied_along"])
                if key not in current:
                    continue
                same_slot.append(r)
                if sheet_highlight(r["commonness"]) in current[key]:
                    same_finding.append(r)
            print(f"\n  {want}: {len(same_finding)} of {len(group)} still say the "
                  f"same thing; {len(same_slot)} still occupy the same slot")
            for r in same_slot:
                verdict = ("same finding" if r in same_finding
                           else "SLOT ONLY -- the highlight changed")
                print(f"    [{verdict}] {r['view']} #{r['rank']}: "
                      f"{r['pattern_type']} {r['measure']} by {r['breakdown']}")
                print(f"        {r['summary'][:100]}")

    print(f"\n{'=' * 60}")
    print(f"{len(fails)} failure(s)" + (": " + "; ".join(fails) if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
