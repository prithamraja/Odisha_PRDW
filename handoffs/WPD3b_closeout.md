# WP-D3b — closeout fixes + edition regeneration (micro-brief)

**Workstream:** Discover. **For:** the operator-controlled implementation agent.
**Purpose:** apply the four PM-authorized fixes from the WP-D3 report (D30) and
regenerate the publication suite so the operator reviews what would actually
ship. Small package; everything is specified.
**Precondition:** tree committed (fourth consecutive run on a dirty tree is not
acceptable — STOP if not committed); local mirror; `Insights/.env` present.
**Read first:** `handoffs/WPD3_REPORT.md` §4 (the defects, incl. the exact fix
lines) and §1.2 (the pinned candidate set).

**Files in scope:** `Insights/src/phase4b_engine.py` (**one number**: view1
budget 3600 → 36000, + comment — WPD3 §4.2), `Insights/src/phase5_ranking.py`
(relocate the A2 twin merge into the shared ranking path so BOTH prose paths
rank merged candidates — WPD3 §4.3), `Insights/src/phase5c_gamma_reports.py`
(only if the relocation requires a call-site change),
`handoffs/WPD2_calibration/verify_configs_prdw.py` (**one line**: the depth
assertion becomes `sample == statewide == 2`, labeled D29 — WPD3 §4.1),
`Insights/reports_prdw/**` + `Insights/metainsights/**` (regenerated artefacts;
`check_editions_prdw.py` check (f) tightened to require **every** earmark
carrier — the WPD3 report's own suggestion), `handoffs/WPD3b_REPORT.md`.
**DO NOT TOUCH:** everything else. **No re-mine**: the candidate set is pinned.

## Tasks

- **T1 — the four fixes**, exactly as specified in WPD3 §4 / D30. For the twin
  merge relocation: the executive path already merges, so after relocation its
  ranked output must be **byte-identical** to the current committed
  `*_ranked.json` — that is the done-check; and the gamma path must now rank
  merged candidates (expected: 0 twin pairs in every edition's top-30,
  measured, vs the 2–3 reported).
- **T2 — verify the candidate set then regenerate.** SHA-256 the six files in
  `Insights/metainsights/` against WPD3 §1.2 (STOP on any mismatch — that
  means someone re-mined). Then regenerate, one shared run stamp: feed →
  executive report → all five gamma editions (the WPD3 §5.3 order). Set id
  stays `a7f991c1df3771f9`; only the stamp changes.
- **T3 — gates.** Config gate (expect **176/176** now), regression, report
  checks, feed contract, editions gate (with tightened (f)) — all green, all
  archived. Report: `handoffs/WPD3b_REPORT.md`, short — gate table, twin-pair
  measurements before/after, hashes, deltas.

## Gate

(1) Four fixes in with evidence; executive ranked output byte-identical;
0 twin pairs in all editions. (2) Suite + feed + report regenerated from the
pinned set under one stamp; no stale file (the in-code deletion rule runs).
(3) All gates green including config 176/176. (4) No out-of-scope file, no git.
