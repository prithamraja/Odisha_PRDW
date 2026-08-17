# Calibration package v3 — Odisha PR&DW Discover

Everything the operator needs for calibration session 2, and nothing that
requires touching code to use. Built 2026-08-15 from the WP-D1 domain pack
(`Insights/domain_pack_prdw/`, gate-green) and the view configs as amended by
**D25** and by **WP-D2c's seven calibration actions**.

**v3 is the post-calibration re-mine.** v2 carried 33 findings, of which the
operator labelled 11 spurious. Those 11 were four repeatable classes, each with
an engine or prose fix in WP-D2c (`handoffs/WPD2c_REPORT.md` §1), and this
package is the same pipeline re-run with the fixes in. The labelled sheet from
session 1 is now a **regression baseline**: `check_calibration_regression.py`
re-runs the four class checks against whatever is currently ranked, and it is
part of the WP-D2 gate rather than a one-off.

**The session's job (D20):** label each ranked finding **real**,
**already-known** or **spurious**, as before. Two things are new on the sheet:
`framing_applied` says which deterministic rule touched a finding, and
`merged_twin` says when a finding absorbed its OUTSTANDING_1/ATTRIBUTION twin.

---

## What changed since v2, in one table

| | v2 (WP-D2b) | **v3 (WP-D2c)** |
|---|---|---|
| findings | 33 (15 / 15 / 3) | **32 (15 / 15 / 2)** |
| view1 candidates mined | 3,139 | **2,969** (30 → 32 definitional pairs excluded) |
| view2 candidates mined | 110 | **122** (two intensity measures added) |
| view3 candidates mined | 5 | **2** (three all-zero completion trends no longer found) |
| twins merged before ranking | — | **489** view1, **1** view2 |
| view2 candidate-file hash | different on every run | **stable** (D26c fixed) |
| data-quality annex | — | **in the report**, from the mining run's own record |
| known-events context | — | `domain_pack_prdw/known_events.csv` |

## What to open

| File | What it is |
|---|---|
| `labeling_sheet.csv` | **The sheet to fill in.** One row per ranked finding, with its plain-English summary, its figures, its exceptions and its score. The `label` column is empty and is the only one you have to touch. Opens in Excel (UTF-8 BOM). |
| `findings_view1.md`, `findings_view2.md`, `findings_view3.md` | The same findings, one page per view, laid out to read rather than to sort. Use these to judge; use the CSV to record. |
| `../../Insights/reports_prdw/executive_metainsight_report.md` | The generated executive report — the prose an officer would actually receive. A `.pdf` sits beside it. It now ends with a **data-quality annex**. |
| `layer3p_ranked_dashboard.txt` | The engine's own ranked dashboard: full pattern detail, commonness sets, member lists, exception categories. The audit trail behind every row of the sheet. |
| `layer2p_raw_explorer.txt` | The pre-ranking candidate pool, for anyone who wants to see what the ranker rejected. |
| `mining_log.txt` | The mining transcripts: subspaces enumerated and pruned, scopes evaluated, patterns found, HDPs deduplicated, cache hit rates, drain time and candidate hashes, per view. |
| `ranking_log.txt` | The phase 5 run: candidates in, twins merged, top-15 out, per view. |
| `verify_configs_output.txt` | The config gate, as run. `verify_configs_prdw.py` re-runs it. |
| `check_report_output.txt` | The four report checks, as run. `check_report_prdw.py` re-runs them. |
| `regression_output.txt` | The calibration regression gate, as run. `check_calibration_regression.py` re-runs it. |
| `determinism_output.txt` | The determinism gate: two runs agree, and four workers agree with one. `check_determinism.py` re-runs it. |
| `CALIBRATION_SESSION_1.md` | The session-1 record — the tally, the seven rulings and the gate status. |
| `CALIBRATION_SESSION_1_labels.csv` | **The labelled baseline, frozen.** Session 1's sheet with its labels, kept under its own name because `build_labeling_sheet.py` rewrites `labeling_sheet.csv` with an empty label column every time the package is rebuilt — which is how this WP briefly lost them. `check_calibration_regression.py` reads this file; nothing writes it. |
| `v4_depth2/` | **The depth-2 run.** Same pipeline, view1 mined at subspace depth 2, nine of its fifteen findings new. Its own README, sheet, report and gate outputs. |
| `model_probe_results.json` | The GPT-5.6 budget probe that pinned `gpt-5.6-sol`. |

## Where the 32 findings come from

| view | mined | candidates | after twin merge | ranked |
|---|---|---|---|---|
| view1 Activity Lifecycle | depth 1, drained 212.1 s of a 3,600 s budget | 2,969 | 2,480 | **15** |
| view2 Geo-Month Cash Cube | drained 32.0 s of a 300 s budget | 122 | 121 | **15** |
| view3 GP Performance | drained 7.2 s of a 120 s budget | 2 | 2 | **2** |

## What to expect while labelling

The three known properties of the data from v2 still hold and should still be
labelled `already-known` if they surface: the **March year-end concentration**,
the **near-degenerate completion column**, and the **FY 2023-24 reporting
change** (which still carries its deterministic caveat, flagged in the sheet).

Four things are new, and each is one of the session's own rulings made
mechanical:

1. **Definitional pairs are gone from the search space.** 32 (measure,
   dimension) pairs are excluded at scope generation — the six the session
   named plus 26 the audit found in the same class. `trainees_total` broken
   down by `work_type_label` cannot be mined at all now. Both sides stay
   minable separately: the exclusion removes a pairing, not a column.
2. **Size context travels with every total.** A total broken down by any group
   — a place, a work type, a status — now arrives with each group's share of
   the volume behind it, so "the biggest category has the biggest total" is
   visible as arithmetic. Watch for it in the prose: the report should say "in
   proportion to" where the shares match.
3. **view2 has two intensity measures.** `payment_amount_mean` and
   `receipt_amount_mean` are the same rupees per Gram Panchayat per month.
   They are already earning their place: the "Ganjam has the highest ..."
   finding now carries both of them as EXCEPTIONS — Ganjam leads on the totals
   and does not lead per Gram Panchayat.
4. **view3 has two findings, not three.** Its two completion trends are gone,
   because a series of six zeros can no longer be read as a decline. The
   completion story is not lost: it is in view3's reading note and in the
   report's data-quality annex, which is where the session said it belonged.

**Still open for this session** (WPD2c_REPORT §2 has the detail): four of the
eleven findings labelled spurious in session 1 still say the same thing. Three
of them are size artifacts that now arrive framed rather than removed, and one
— view3's abstract "evenness across measures" — survives because view3 has only
two candidates at sample scale. Whether framing is enough, or whether those
findings should be suppressed outright, is a calibration decision and not an
implementation one.

## Re-running any of it

From a **local** copy of the repo (DuckDB and the engine must not write to the
Drive mount), with an OpenAI key in `Insights/.env`:

```
# 1. build the three Parquet views from Data/ + the pack
python Insights/src/build_views.py --pack Insights/domain_pack_prdw \
       --data-dir Data --views-dir Insights/views_prdw \
       --reports-dir Insights/reports_prdw --strict

# 2. mine  (all three views; view1 drains in ~3.5 min at depth 1)
python Insights/src/phase4b_engine.py
#    ... across 4 worker processes instead of one:
python Insights/src/phase4b_engine.py --workers 4
#    ... view1 at subspace depth 2 (the WP-D2c T4 run):
python Insights/src/phase4b_engine.py --views view1 --depth2 --workers 6 \
       --cache-max-entries 150000

# 3. rank  (all three views; twins are merged here)
python Insights/src/phase5_ranking.py

# 4. write the executive report  (the only step that calls an API)
python Insights/src/phase5b_report.py

# 5. check the report
python handoffs/WPD2_calibration/check_report_prdw.py --base Insights

# 6. the calibration regression gate
python handoffs/WPD2_calibration/check_calibration_regression.py --base Insights

# 7. rebuild this package
python handoffs/WPD2_calibration/build_labeling_sheet.py \
       --base Insights --out handoffs/WPD2_calibration

# and the two engine gates, any time
python handoffs/WPD2_calibration/verify_configs_prdw.py --base Insights
python handoffs/WPD2_calibration/check_determinism.py --base Insights --workers 4
```

Steps 1–3 and 5–7 make no API call. Only step 4 does.

**Statewide:** set `DISCOVER_SCALE=statewide` before step 2. It changes
dimension lists and subspace depths only — including view1 back to depth 2 —
and it is untested: no statewide drop exists yet. Do not run it before the
statewide checklist is cleared.

See `handoffs/WPD2c_REPORT.md` for this run, `handoffs/WPD2b_REPORT.md` for the
depth-1 baseline it is measured against, and
`handoffs/WPD2_calibration/CALIBRATION_SESSION_1.md` for the rulings the seven
actions implement.
