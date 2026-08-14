# WP-D2b — view1 re-run at depth 1 + ranking-list fix (addendum brief)

**Workstream:** Discover. **For:** the operator-controlled implementation agent
(continuation of WP-D2; read `handoffs/WPD2_REPORT.md` first — this addendum
executes the PM/operator decisions taken on its §2 escalation and §6 journal).
**Precondition:** D25 ratified by the operator; `Insights/.env` exists with the
OpenAI key (WPD2 report D-2 — operator-created); tree committed; local mirror.

**Files in scope:** `Insights/src/phase2_engine.py` (the `VIEW1_CONFIG` depth
line + comment), `Insights/src/phase5_ranking.py` (**`__main__` list only** —
authorized by D23/D25 rulings: delete the six stale AP view entries),
`Insights/src/phase5b_report.py` (two glossary wording edits below),
`Insights/reports_prdw/**`, `handoffs/WPD2_calibration/**` (regenerate; retire
`run_phase5_prdw.py`), `handoffs/WPD2b_REPORT.md`.
**DO NOT TOUCH:** everything else, same list as WP-D2.

## The decisions this implements

1. **D25:** view1 sample mining runs at **`max_subspace_depth = 1`**, all 17
   dimensions and 24 measures kept. Comment the config with the rationale:
   13,322 of 13,495 enumerated subspaces were depth-2; at 20 GPs those slices
   average ~37 rows (statistically fragile) and the full queue (880,752 scopes)
   breaks both the never-evict caches (3.94 GB at 1.7%) and the ranker
   (~800k projected candidates). The **statewide branch keeps depth 2**,
   with a comment that it is compute-gated (statewide checklist: engine-scaling
   WP + provisioning before the wide-view statewide run).
2. **D-12 authorized:** `phase5_ranking.py.__main__` shrinks to the three PR&DW
   views; delete `WPD2_calibration/run_phase5_prdw.py` in the same change.
3. **Glossary wording (D-4 correction):** `sc_amount`/`st_amount` entries say
   **suspected** swap ("the two source tables carry these values swapped
   relative to each other; whether the labels or the data are wrong is
   unconfirmed with the data team") — the ban on SC-vs-ST comparisons stays.
4. **D-15 stands as implemented** (wider caveat reading). No change.

## Tasks

- **T1 — Config + list edits** per above. Re-run `verify_configs_prdw.py`;
  update its depth assertion. *Done when:* 99+ checks pass.
- **T2 — Mine view1** (budget 3,600 s; expected ≈0.9 h at the conservative
  measured rate). **Drain required** — if it does not drain, STOP and report
  throughput; do not trim further. view2/view3 candidates from the WP-D2 run
  are current (configs unchanged) — do not re-mine them; record their file
  hashes as the set you rank against.
- **T3 — Rank + report.** phase5 over all three views via the fixed
  `__main__`; regenerate the executive report (all three sections expected).
  Re-run the four T5 checks (prose gate / hollow / caveat both-directions /
  full figure trace) over the **whole** report.
- **T4 — Calibration package v2.** Rebuild the labelling sheet (expect
  15 + 15 + 3 ≈ 33 findings), refresh the per-view read-ups and README.
- **T5 — Report** `handoffs/WPD2b_REPORT.md`: drain diagnostics, check
  evidence, deltas from the WP-D2 package, decision journal, self-audit.

## Gate

1. view1 drains at depth 1; diagnostics prove it. 2. Ranking list fixed;
driver retired. 3. Executive report carries all three sections; all four T5
checks green across it. 4. Calibration package v2 delivered. 5. No file
outside scope touched; no git operations.
