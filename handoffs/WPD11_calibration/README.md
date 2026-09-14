# WP-D11 calibration package

Evidence and re-runnable gates for `handoffs/WPD11_REPORT.md`. Everything here
was produced from the local mirror `C:\dev\odisha-d11`, never from the Drive
mount — DuckDB spills temp files Drive cannot take, and the engine loads a
1.8-million-scope queue that has no business on a network filesystem.

## THE MINING COMMAND — PASS THE CACHE BOUNDS

```bash
python Insights/src/phase4b_engine.py \
    --views view2,view3,view4,view1 \
    --workers 6 \
    --cache-max-entries 60000 \
    --dedup-max-entries 600000
```

**The two cache flags are not optional and their absence is silent.** The CLI
defaults are `None`, which means *never evict*, and that is the configuration
WP-D2 measured at 25.6 scopes/s and 3.94 GB in one process before WP-D2c
introduced the bounds and reached 146.0 scopes/s at 0.57 GB per worker.
`QueryCache`'s own docstring names never-evict as "the wall that stopped that
run".

WP-D11 walked back into it. The first view1 attempt was launched without the
flags, ran at 36–38 scopes/s, and was projected to miss its 36,000 s budget —
which was very nearly escalated to the operator as the cost of Amendment B's six
new dimensions. It was not: it was the cache policy. Re-run with the bounds, the
same view on the same machine reached 74–81 scopes/s and drained inside budget.

The bounds change **speed and memory only, never results**. Both caches are
memoisation with LRU eviction, and the run above reproduced views 2, 3 and 4
candidate-for-candidate against the unbounded run (322 / 45 / 32).

So: whoever re-mines this deployment should copy the command above verbatim.
The reason WP-D2c's report records the flags in its §4 command block is the same
reason they are repeated here.

## What is in this directory

| File | What it is |
|---|---|
| `t5_reconcile.py`, `t5_reconciliation_output.txt` | the T5 gate: the amended pack against the pre-change baseline — row counts, every pre-existing column of views 1–3 byte-identical, the seven dimension splits, view4 ↔ view3 SUM equality, the profile totals, the Chikilli guard, the `X-pii` sweep |
| `crosswalk_gate_output.txt` | `build_crosswalk.py`'s five gate checks over the four built Parquets, 281/281 columns |
| `verify_configs_prdw_d11.py`, `verify_configs_d11_output.txt` | the WP-D2 config gate with its view count corrected to four; 219 checks, 0 failures. See the file's own header for the exact diff from the WP-D2 copy, which is left untouched and now fails by design |
| `determinism_view2_output.txt` | five workers vs one process on view2, identical content hash |
| `cost_probe.py` | mines a fixed subspace count under 17 dimensions and again under 23, to separate what the profile dimensions cost from what the machine costs. Written for the B4 escalation that turned out not to be needed; kept because the same question will be asked at statewide scale |
| `profile_diff.py` | the top-15 diff: which findings dropped, which entered, and how many of the new ones use a profile band |
| `new_candidates_views234/` | the views 2/3/4 candidates and engine diagnostics from the first (unbounded-cache) run, kept as the evidence that the cache bounds changed no result |
| `view1_mine_partial.log` | the abandoned unbounded-cache run, 5.9% drained — the measurement behind the cache finding above |
| `run_t7_editions.sh` | regenerates every published artefact from one candidate set, under one `DISCOVER_RUN_STAMP` |
| `sync_back.sh` | copies the deliverables to the Drive repo. Performs no git operation |

## The labelling sheets

Built with the WP-D2 tool, which is view-generic and reads
`phase5b_report.VIEW_CONFIGS`, so it picks up view4 without modification:

```bash
python handoffs/WPD2_calibration/build_labeling_sheet.py \
    --base Insights --out handoffs/WPD11_calibration \
    --compare-ranked Insights/metainsights_baseline_a7f991c1
```

`--compare-ranked` marks the findings that are new since the pre-amendment
candidate set `a7f991c1df3771f9`, which is the column the calibration session
should read first.
