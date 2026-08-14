# Calibration package v2 — Odisha PR&DW Discover

Everything the operator needs for the calibration session, and nothing that
requires touching code to use. Built 2026-08-14 from the WP-D1 domain pack
(`Insights/domain_pack_prdw/`, gate-green) and the WP-D2 view configs as amended
by **D25 (WP-D2b)**.

**v2 is the complete package: 33 findings across all three views.** v1 covered
two views and 18 findings, because view1's queue would not drain at subspace
depth 2. D25 runs view1's sample at **depth 1** — all 17 dimensions and all 24
measures kept — and it now drains in **262.5 s**. view2 and view3 are unchanged
from v1: their configs did not move, they were not re-mined, and re-ranking them
from the same candidate files reproduced their v1 rankings byte for byte.

**The session's job (D20):** label each ranked finding **real**, **already-known**
or **spurious**. The workstream gate — "no nonsense findings in top ranks" —
closes on those labels, not on anything in this package.

---

## What to open

| File | What it is |
|---|---|
| `labeling_sheet.csv` | **The sheet to fill in.** One row per ranked finding (33 of them), with its plain-English summary, its figures, its exceptions and its score. The `label` column is empty and is the only one you have to touch. Opens in Excel (UTF-8 BOM, so the rupee and Odia text render). |
| `findings_view1.md`, `findings_view2.md`, `findings_view3.md` | The same findings, one page per view, laid out to read rather than to sort. Use these to judge; use the CSV to record. |
| `../../Insights/reports_prdw/executive_metainsight_report.md` | The generated executive report — the prose an officer would actually receive, now carrying all three view sections. A `.pdf` sits beside it. |
| `layer3p_ranked_dashboard.txt` | The engine's own ranked dashboard: full pattern detail, commonness sets, member lists, exception categories. The audit trail behind every row of the sheet. |
| `layer2p_raw_explorer.txt` | The pre-ranking candidate pool, for anyone who wants to see what the ranker rejected. |
| `mining_log.txt` | The mining transcripts: subspaces enumerated and pruned, scopes evaluated, patterns found, HDPs deduplicated, cache hit rates and drain time, per view — plus the candidate-file hashes this package was ranked from. |
| `ranking_log.txt` | The phase 5 run: candidates in, top-15 out, per view. |
| `verify_configs_output.txt` | The 99-check config gate, as run. `verify_configs_prdw.py` re-runs it. |
| `check_report_output.txt` | The four report checks, as run. `check_report_prdw.py` re-runs them. |
| `model_probe_results.json` | The GPT-5.6 budget probe that pinned `gpt-5.6-sol`. |

## Where the 33 findings come from

| view | mined | candidates | ranked |
|---|---|---|---|
| view1 Activity Lifecycle | depth 1, drained 262.5 s of a 3,600 s budget | 3,139 | **15** |
| view2 Geo-Month Cash Cube | WP-D2 run, drained 21.6 s | 110 | **15** |
| view3 GP Performance | WP-D2 run, drained 6.2 s | 5 | **3** |

**What depth 1 costs view1.** Every two-filter slice — "within Bargarh district,
among costless activities…". Its findings are whole-view patterns varied along
one dimension, which is what the 20-GP sample can actually support: at depth 2
the average two-filter slice held ~37 rows. The statewide config keeps depth 2
and is compute-gated behind the engine-scaling WP.

## What to expect while labelling

Three things are **known properties of the data** and should be labelled
`already-known` rather than `real` if they surface:

1. **The March year-end concentration.** 2,040 of the 8,529 payment vouchers
   fall in a March. Real, and long known to anyone who has run a government
   cashbook.
2. **Completion is near-degenerate.** Only 17 of 12,704 activities are marked
   WORK COMPLETED. Any finding that ranks places by completions is measuring
   recording practice.
3. **The FY 2023-24 reporting change.** Activity counts jump about eightfold at
   that boundary because costless activities begin being recorded. Findings that
   compare activity counts across it carry a deterministic caveat
   (`fy_2023_24_caveat` = yes in the sheet); the caveat text is appended to the
   report section automatically and is never written by the model.

A fourth is worth watching for as a **spurious** class: a total broken down by
Gram Panchayat, block or district ranks places by their own size. The report
prompt carries a rule against writing those as delivery gaps, and the enrichment
sends each place's share of the volume alongside the total so the distinction can
be made — but the *finding* is still there in the sheet, and it is the operator's
call whether it earns a slot.

**Two view1-specific things to watch.** Its top two findings are EVENNESS
patterns over `asset_category_label` with the same 27-of-28 commonness set and
the same single exception (Banking Facilities); they differ only in measure and
breakdown, and whether both earn a slot is a judgement about redundancy the
greedy ranker did not make for you. And ranks 3–11 are largely the same 20-GP
HDP seen through different measures — a property of a view whose only depth-1
geography subspaces are single GPs.

## Re-running any of it

From a **local** copy of the repo (DuckDB and the engine must not write to the
Drive mount), with an OpenAI key in `Insights/.env`:

```
# 1. build the three Parquet views from Data/ + the pack
python Insights/src/build_views.py --pack Insights/domain_pack_prdw \
       --data-dir Data --views-dir Insights/views_prdw \
       --reports-dir Insights/reports_prdw --strict

# 2. mine  (all three views; view1 drains in ~4.5 min at depth 1)
python Insights/src/phase4b_engine.py

# 3. rank  (all three views; the nine-view list is gone — D-12/D25)
python Insights/src/phase5_ranking.py

# 4. write the executive report  (the only step that calls an API)
python Insights/src/phase5b_report.py

# 5. check the report
python handoffs/WPD2_calibration/check_report_prdw.py --base Insights

# 6. rebuild this package
python handoffs/WPD2_calibration/build_labeling_sheet.py \
       --base Insights --out handoffs/WPD2_calibration

# and the config gate, any time
python handoffs/WPD2_calibration/verify_configs_prdw.py --base Insights
```

Steps 1–3 make no API call. Only step 4 does.

`run_phase5_prdw.py` is **gone**: it existed only to work around the nine-view
list in `phase5_ranking.py`'s `__main__`, and D25 authorised deleting the six
stale entries instead. Step 3 above is now the ranking command.

**Statewide:** set `DISCOVER_SCALE=statewide` before step 2. It changes dimension
lists and subspace depths only — including view1 back to depth 2 — and it is
untested: no statewide drop exists yet, and the depth-2 walls WP-D2 measured are
scale walls. Do not run it before the statewide checklist is cleared.

See `handoffs/WPD2b_REPORT.md` for this run, and `handoffs/WPD2_REPORT.md` for
the configs, the model pin and the depth-2 measurements that produced D25.
