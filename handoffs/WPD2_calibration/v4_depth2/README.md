# Calibration package v4 — the depth-2 sample run

Built 2026-08-15 by WP-D2c T4. This is the **same pipeline as v3 in the parent
directory**, with one difference: view1 was mined at **subspace depth 2** rather
than depth 1, so its findings can be conditional — a slice, a dimension varied
inside it, and a breakdown. That is the "three-way structure" D25 said the 2,438
surviving depth-2 subspaces carry, and it is what the operator asked to see.

view2 and view3 are byte-identical to v3. Their configs are depth 1 at both
scales (mapping doc §6) and they were not re-mined.

**Read the parent directory first.** `../README.md` explains the seven
calibration actions and what changed since v2; `../CALIBRATION_SESSION_1.md` and
`../CALIBRATION_SESSION_1_labels.csv` are the session-1 record and its labels.
Everything said there about how to label applies here unchanged.

---

## The run

| | v3 (depth 1) | **v4 (depth 2)** |
|---|---|---|
| subspaces enumerated | 173 | **13,495** |
| retained after the 1% impact prune | 127 | **2,438** |
| data scopes | 44,846 | **809,554** |
| workers | 1 | **5**, caches bounded to 60,000 entries each |
| elapsed | 212.1 s | **5,544.0 s — the queue emptied** |
| throughput | 212.7 scopes/s | **146.0 scopes/s** |
| peak memory | 0.62 GB | **0.57 GB per worker** (~2.85 GB across five) |
| view1 candidates | 2,969 | **5,000 kept** of 65,488 scored |
| view1 findings | 15 | **15**, of which **9 are new** |

The candidate store is at its bound here, and the bound is the ranker's own
prefilter, so it is lossless: everything the store dropped, `prefilter_candidates`
would have dropped a step later, and the ranked top-15 is the same list it would
have produced from the whole pool.

## What to open

| File | What it is |
|---|---|
| `labeling_sheet.csv` | The sheet. **The `new_in_this_run` column is the point**: `yes` marks a finding the depth-1 run could not produce. Nine of view1's fifteen carry it. |
| `findings_view1.md` | The readable version. New findings carry a **NEW IN THIS RUN** line. |
| `findings_view2.md`, `findings_view3.md` | Unchanged from v3; included so the package is complete. |
| `executive_metainsight_report.md` / `.pdf` | The report regenerated from the depth-2 findings. |
| `mining_log.txt` | The depth-2 mining transcript, including the per-worker progress and the final diagnostics. |
| `ranking_log.txt` | 5,000 candidates in, 884 twins merged, 15 out. |
| `regression_output.txt` | The calibration regression gate, run against the depth-2 ranked output. Green on all four classes. |
| `check_report_output.txt` | The four report checks over the regenerated report: 680 / 633 / 571 words, prose gate clean, 85/85 figures traced. |
| `layer2p_raw_explorer.txt`, `layer3p_ranked_dashboard.txt` | The engine's own pre-ranking and ranked dashboards. |

## The nine new findings, and the one honest caveat about them

Six of the nine restrict to `is_costless = Costed` or `activity_type_label =
Public Works` — the two slices where the money is. Conditioning on them sharpens
a finding (19 of 20 Gram Panchayats rather than 18) without changing its
subject, and the operator should feel free to say so when labelling.

**Two are genuinely new subjects**, both restricted to New/Fresh works and both
about output Code 101: it has the lowest overspend against sanction in 19 of 20
Gram Panchayats (rank 9), and it takes the majority of geotagged photo uploads
in 19 of 20 (rank 10). Code 101 still has no description on file — it is one of
the eight undecoded `output_type` codes in the standing team ask — so both
findings are held from publication for the same reason v2's rank 8 was.

## Which package is the working one

`../` (v3, depth 1) is what the committed configuration reproduces: D25 sets the
sample to depth 1 and nothing in WP-D2c changes that. This directory is a
**deliberate one-off deep run**, made with a `--depth2` command-line flag rather
than a config edit, to answer the question D25 deferred rather than rejected.

If the operator wants depth 2 to become the sample default, that is a config
change and a decision — the numbers it should be made on are in
`handoffs/WPD2c_REPORT.md` §4.
