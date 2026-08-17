"""WP-D2 T1/T2 gate checks — re-runnable evidence, not a one-off transcript.

Verifies, mechanically:
  1. every module in the Discover pipeline still imports
  2. every view registry holds exactly the three PR&DW views, and no AP config
     survives anywhere
  3. every config dimension and measure has a glossary entry and a unit, every
     measure is SUM, extremum_ratio is at its default, and no LGD code column
     reached a dimension list
  4. the prose gate's expectations are satisfiable: a reading note and a
     vocabulary entry per view, deny-lists and prose phrases in step
  5. DISCOVER_SCALE flips the dimension lists and the depths and NOTHING else
  6. no AP/UP vocabulary survives in phase5b_report.py or in a built prompt
  7. the FY 2023-24 caveat predicate fires on exactly the findings §5.2 names

Usage:
    python verify_configs_prdw.py --base <Insights dir>

Exits non-zero on any failure, so it can gate a run.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

fails = []


def check(ok, label, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")
    if not ok:
        fails.append(label)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the Insights directory")
    args = ap.parse_args()
    base = os.path.abspath(args.base)
    src = os.path.join(base, "src")
    sys.path.insert(0, src)

    print("\n=== 1. imports ===")
    import phase2_engine, phase4a_engine, phase4b_engine            # noqa: F401
    import phase5_ranking, phase5b_report, phase5b_dual_reports     # noqa: F401
    import phase5c_gamma_reports, phase5c_global_feed, prose_gate   # noqa: F401
    import discover_config                                          # noqa: F401
    check(True, "all nine pipeline modules import")

    print("\n=== 2. registries hold exactly the three PR&DW views ===")
    check(list(phase5b_report.VIEW_CONFIGS) == ["view1", "view2", "view3"],
          "phase5b_report.VIEW_CONFIGS", str(list(phase5b_report.VIEW_CONFIGS)))
    check(list(phase5b_report.VIEW_DESCRIPTIONS) == ["view1", "view2", "view3"],
          "phase5b_report.VIEW_DESCRIPTIONS")
    check(list(phase5b_dual_reports.ALL_CONFIGS) == ["view1", "view2", "view3"],
          "phase5b_dual_reports.ALL_CONFIGS")
    check(phase5c_global_feed.VIEWS == ["view1", "view2", "view3"],
          "phase5c_global_feed.VIEWS")
    check(not any(re.match(r"^VIEW[4-9]_CONFIG$", a) for a in dir(phase4a_engine)),
          "no VIEW4..9_CONFIG survives on phase4a_engine")
    views, skipped = phase5c_gamma_reports.discover_views()
    check(sorted([v[0] for v in views] + [s[0] for s in skipped])
          == ["view1", "view2", "view3"],
          "phase5c_gamma_reports.discover_views sees exactly three")

    print("\n=== 3. every config column is glossed, united and SUM ===")
    CFG = {"view1": phase2_engine.VIEW1_CONFIG,
           "view2": phase4a_engine.VIEW2_CONFIG,
           "view3": phase4a_engine.VIEW3_CONFIG}
    for name, cfg in CFG.items():
        gloss = set(phase5b_report.VIEW_DESCRIPTIONS[name]["column_glossary"])
        cols = list(cfg.dimensions) + list(cfg.temporal_dimensions) + cfg.measure_names
        check(not set(cols) - gloss, f"{name}: all {len(set(cols))} config columns glossed",
              f"missing={sorted(set(cols) - gloss)}")
        check(not gloss - set(cols), f"{name}: no glossary entry without a config column",
              f"extra={sorted(gloss - set(cols))}")
        units = set(phase5b_report._UNITS[name])
        check(set(cfg.measure_names) == units, f"{name}: every measure has a unit")
        # WP-D2c A4 puts the first two AVG measures in this deployment. Every
        # other measure is still SUM, and an AVG one must be an ALIAS of a
        # column that is already in the view -- an intensity measure is the
        # same money seen per unit, never a new number.
        avg = [m for m in cfg.measures if m.agg == "avg"]
        check(all(m.agg in ("sum", "avg") for m in cfg.measures),
              f"{name}: every measure is SUM or AVG")
        check(all(m.name.endswith("_mean") and m.column for m in avg),
              f"{name}: every AVG measure is a named _mean alias",
              str([m.name for m in avg]))
        check(all(m.column in cfg.measure_names for m in avg),
              f"{name}: every AVG measure aliases a measure of this view")
        check(not [m for m in cfg.measures
                   if m.name in cfg.impact_measures and m.column],
              f"{name}: no impact measure is an alias (impact is always SUM)")
        check(cfg.extremum_ratio == 0.67, f"{name}: extremum_ratio at the 0.67 default")
        check(set(cfg.impact_measures) <= set(cfg.measure_names),
              f"{name}: impact measures are measures")
        check(not [d for d in cfg.dimensions if d.endswith("_code")],
              f"{name}: no LGD code column is a dimension")

    print("\n=== 3b. WP-D2c A1: the definitional-pair exclusions ===")
    for name, cfg in CFG.items():
        dims = set(cfg.dimensions) | set(cfg.temporal_dimensions)
        bad_measure = [p for p in cfg.excluded_pairs if p[0] not in cfg.measure_names]
        bad_dim     = [p for p in cfg.excluded_pairs if p[1] not in dims]
        check(not bad_measure, f"{name}: every excluded pair names a real measure",
              str(bad_measure))
        check(not bad_dim, f"{name}: every excluded pair names a real dimension",
              str(bad_dim))
        check(len(set(cfg.excluded_pairs)) == len(cfg.excluded_pairs),
              f"{name}: no duplicate excluded pair")
        # the exclusion must not remove a whole measure or a whole dimension
        # from the view: it removes a pairing, and both sides stay minable
        for m, d in cfg.excluded_pairs:
            others = [b for b in dims if not cfg.is_excluded(m, b)]
            check(bool(others), f"{name}: {m} is still minable by some breakdown")
    v1 = CFG["view1"]
    check(len(v1.excluded_pairs) >= 6, "view1: the session's six pairs are in",
          f"{len(v1.excluded_pairs)} pairs")
    for pair in [("trainees_total", "work_type_label"),
                 ("beneficiaries_expected", "work_type_label"),
                 ("fund_tied_total", "fund_component_name"),
                 ("fund_tied_total", "tied_untied"),
                 ("fund_untied_total", "fund_component_name"),
                 ("fund_untied_total", "tied_untied")]:
        check(v1.is_excluded(*pair), f"view1: session pair {pair[0]} x {pair[1]}")
    scopes = phase2_engine.generate_data_scopes(
        phase2_engine.Subspace(frozenset()), v1)
    check(not [s for s in scopes if v1.is_excluded(s.measure, s.breakdown)],
          "view1: scope generation emits no excluded pair")

    print("\n=== 3c. WP-D2c A7: the temporal support guard ===")
    import pandas as _pd
    for name, cfg in CFG.items():
        check(cfg.min_temporal_nonzero >= 4 and 0 < cfg.min_temporal_nonzero_frac <= 1,
              f"{name}: support thresholds are set",
              f"{cfg.min_temporal_nonzero} points / "
              f"{cfg.min_temporal_nonzero_frac:.0%}")
    v3 = CFG["view3"]
    df3 = _pd.read_parquet(v3.parquet_path)
    completions = df3.groupby("gp_name")["n_completed"].apply(
        lambda s: int((s != 0).sum()))
    check(int(df3["n_completed"].sum()) == 17,
          "view3: the sample still carries 17 recorded completions")
    fails_guard = sum(
        1 for gp in df3.gp_name.unique()
        if not phase2_engine.temporal_support_ok(
            df3[df3.gp_name == gp].groupby("fiscal_year")["n_completed"].sum(), v3))
    check(fails_guard >= 18,
          "view3: n_completed's per-GP series fail the guard",
          f"{fails_guard} of {df3.gp_name.nunique()} fail")
    healthy = df3.groupby("fiscal_year")["n_activities"].sum()
    check(phase2_engine.temporal_support_ok(healthy, v3),
          "view3: a real series still clears the guard (n_activities by FY)")

    print("\n=== 3d. WP-D2c A5: the known-events table ===")
    events = phase5b_report.known_events()
    check(len(events) >= 1, "known_events.csv loads at least one usable event",
          str([e["event"] for e in events]))
    check(not [e for e in events if e["event"].startswith("TODO(SME)")],
          "TODO(SME) template rows are skipped")
    covid = [e for e in events if "COVID" in e["event"]]
    check(len(covid) == 1, "the COVID first-wave window is present")
    if covid:
        ganjam = {"pattern_type": "CHANGE_POINT", "measure": "(varies)",
                  "breakdown": "month", "base_subspace": [],
                  "commonness_sets": [{"pattern_type": "CHANGE_POINT",
                                       "highlight": "('2020-08',)",
                                       "members": ["payment_amount"]}],
                  "exceptions": []}
        quiet = dict(ganjam, commonness_sets=[{"pattern_type": "CHANGE_POINT",
                                               "highlight": "('2023-05',)",
                                               "members": ["payment_amount"]}])
        fy = {"pattern_type": "TREND", "measure": "sanctioned_amount",
              "breakdown": "(varies)",
              "base_subspace": [["fiscal_year", "2020-2021"]],
              "commonness_sets": [], "exceptions": []}
        check(len(phase5b_report.event_citations([ganjam])) == 1,
              "a change point in the recovery window cites the event")
        check(phase5b_report.event_citations([quiet]) == [],
              "a change point three years later cites nothing")
        check(len(phase5b_report.event_citations([fy])) == 1,
              "a finding pinned to FY 2020-2021 cites the event")
        check("does not establish" in phase5b_report.event_citations([ganjam])[0],
              "the citation states coincidence, never causation")

    print("\n=== 4. the prose gate's expectations are satisfiable ===")
    check(set(phase5b_report.READING_NOTES) == set(CFG),
          "every view has a deterministic reading note")
    check(set(phase5b_report.VIEW_VOCABULARY) == set(CFG),
          "every view has a vocabulary entry")
    for v, rules in phase5b_report.VIEW_VOCABULARY.items():
        check(len(phase5b_report._DENIED_PHRASES[v]) == len(rules["deny"]),
              f"{v}: denied regexes and prose phrases are in step")

    print("\n=== 5. DISCOVER_SCALE flips the marked blocks and nothing else ===")
    probe = (
        "import sys, json\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import phase2_engine as p2, phase4a_engine as p4\n"
        "out = {}\n"
        "for n, c in (('view1', p2.VIEW1_CONFIG), ('view2', p4.VIEW2_CONFIG),"
        " ('view3', p4.VIEW3_CONFIG)):\n"
        "    out[n] = {'scale': p2.DISCOVER_SCALE, 'dims': c.dimensions,\n"
        "              'temporal': c.temporal_dimensions, 'measures': c.measure_names,\n"
        "              'impact': c.impact_measures, 'depth': c.max_subspace_depth,\n"
        "              'tau': c.tau, 'min_impact': c.min_impact,\n"
        "              'min_hdp': c.min_hdp_size, 'ratio': c.extremum_ratio,\n"
        "              'excluded': [list(p) for p in c.excluded_pairs],\n"
        "              'support': [c.min_temporal_nonzero,\n"
        "                          c.min_temporal_nonzero_frac]}\n"
        "print(json.dumps(out))\n"
    )

    def at(scale):
        env = dict(os.environ, DISCOVER_SCALE=scale)
        r = subprocess.run([sys.executable, "-c", probe, src],
                           capture_output=True, text=True, env=env)
        return json.loads(r.stdout)

    sample, state = at("sample"), at("statewide")
    check(sample["view1"]["scale"] == "sample"
          and state["view1"]["scale"] == "statewide",
          "the switch is read from the environment")
    for n in CFG:
        for key in ("temporal", "measures", "impact", "tau", "min_impact",
                    "min_hdp", "ratio", "excluded", "support"):
            check(sample[n][key] == state[n][key], f"{n}: {key} does not move with scale")
    check(state["view1"]["dims"] == ["district_name"] + sample["view1"]["dims"][3:],
          "view1 statewide drops gp_name and block_name only")
    check(state["view2"]["dims"] == ["district_name", "block_name", "fiscal_year"],
          "view2 statewide dims")
    check(state["view3"]["dims"] == ["district_name", "block_name"],
          "view3 statewide dims")
    check(sample["view3"]["depth"] == 1 and state["view3"]["depth"] == 2,
          "view3 depth 1 sample / 2 statewide")
    # D29 (calibration session 2) SUPERSEDES D25 here. D25 ratified depth 1 for
    # the sample because the depth-2 queue drained neither in time nor in memory
    # -- 880,752 data scopes behind 13,495 subspaces. WP-D2c's A1 exclusions and
    # the worker pool changed that arithmetic: the depth-2 sample now drains in
    # 5,208.9 s of a 36,000 s budget across five workers, and nine of view1's
    # fifteen findings at depth 2 are new. So depth 2 is the sample default too,
    # and the sample/statewide split no longer says anything about view1's depth.
    # This assertion was the last place D25 survived; WP-D3 §4.1 reported it as
    # the one stale check in an otherwise green gate.
    check(sample["view1"]["depth"] == state["view1"]["depth"] == 2,
          "view1 depth 2 both (D29)")
    check(sample["view2"]["depth"] == state["view2"]["depth"] == 1, "view2 depth 1 both")

    print("\n=== 6. no AP/UP vocabulary survives the prompt path ===")
    AP = ["Andhra", "PM-KISAN", "MARKFED", "APMIP", "RTGS", "Rythu", "Sericulture",
          "Horticulture", "quintal", "Kharif", "Rabi", "farmer", "PM-JAY", "Uttar",
          "Cardiology", "eKYC", "khata"]
    with io.open(os.path.join(src, "phase5b_report.py"), encoding="utf-8") as f:
        body = f.read()
    for token in AP:
        n = len(re.findall(token, body, re.IGNORECASE))
        check(n == 0, f"phase5b_report.py: {token!r} x{n}")
    fake = [{"rank": 1, "pattern_type": "OUTSTANDING_1", "extending_strategy": "subspace",
             "extending_dimension": "district_name", "breakdown": "theme",
             "measure": "total_cost", "base_subspace": [], "hdp_size": 5,
             "commonness_sets": [], "exceptions": [], "score": 0.1,
             "conciseness": 0.5, "impact": 0.2, "stats": {}}]
    for v in CFG:
        prompt = phase5b_report.build_view_prompt(v, fake)
        hits = [t for t in AP if re.search(t, prompt, re.IGNORECASE)]
        check(not hits, f"{v}: built prompt is free of AP vocabulary", str(hits))

    print("\n=== 7. the FY 2023-24 caveat predicate ===")
    ca = phase5b_report.count_caveat_applies

    def f(**kw):
        d = {"measure": "n_activities", "breakdown": "theme",
             "extending_strategy": "subspace", "extending_dimension": "district_name",
             "commonness_sets": [], "exceptions": []}
        d.update(kw)
        return d

    cases = [
        ("view1", f(breakdown="fiscal_year"), ["2022-2023", "2023-2024"], True,
         "activity count by FY, across the boundary"),
        ("view1", f(breakdown="fiscal_year"), ["2023-2024", "2024-2025"], False,
         "activity count by FY, all after the boundary"),
        ("view1", f(breakdown="fiscal_year"), ["2020-2021", "2021-2022"], False,
         "activity count by FY, all before it"),
        ("view1", f(measure="total_cost", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], False, "a RUPEE measure across the boundary"),
        ("view1", f(measure="evidence_uploads", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], False, "photo uploads are not an activity count"),
        ("view1", f(extending_dimension="fiscal_year",
                    commonness_sets=[{"members": ["2021-2022", "2022-2023", "2023-2024"]}]),
         None, True, "HDP whose members are years, straddling"),
        ("view1", f(extending_dimension="fiscal_year",
                    commonness_sets=[{"members": ["2023-2024", "2024-2025"]}],
                    exceptions=[{"member_label": "2025-2026"}]),
         None, False, "HDP over years, all after the boundary"),
        ("view1", f(base_subspace=[["fiscal_year", "2024-2025"]]), None, False,
         "fiscal_year as a FILTER makes no comparison"),
        ("view2", f(measure="payment_count", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], False, "view2 is artifact-free"),
        ("view3", f(measure="n_costless", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], True, "view3 costless count across the boundary"),
        ("view3", f(measure="n_admin_approvals", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], False, "approvals are steady across the boundary"),
        ("view3", f(measure="n_plans", breakdown="fiscal_year"),
         ["2022-2023", "2023-2024"], False, "plans are not activities"),
        ("view1", f(measure="(varies)", breakdown="fiscal_year",
                    commonness_sets=[{"members": ["n_activities", "total_cost"]}]),
         ["2022-2023", "2023-2024"], True, "measure-extending HDP including a count"),
        ("view1", f(measure="(varies)", breakdown="fiscal_year",
                    commonness_sets=[{"members": ["total_cost", "gen_amount"]}]),
         ["2022-2023", "2023-2024"], False, "measure-extending HDP, rupees only"),
    ]
    for view, finding, fys, expected, why in cases:
        check(ca(view, finding, fys) == expected, f"{view}: {why}")

    check(phase5b_report.activity_count_measures("view2") == set(),
          "view2 has no activity-count measure")
    plain = phase5b_report.reading_note_block("view1", [{"reporting_caveat": False}])
    caveat = phase5b_report.reading_note_block("view1", [{"reporting_caveat": True}])
    check(phase5b_report.COUNT_CAVEAT_SENTENCE not in plain,
          "no qualifying finding -> no caveat sentence")
    check(phase5b_report.COUNT_CAVEAT_SENTENCE in caveat,
          "a qualifying finding -> the caveat sentence, verbatim")
    check(caveat.count(phase5b_report.READING_NOTE_MARKER) == 1,
          "still exactly one reading-note marker")

    print(f"\n{'=' * 60}")
    print(f"{len(fails)} failure(s)" + (": " + "; ".join(fails) if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
