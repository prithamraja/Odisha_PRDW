# WP-D2 — Mining configs, prose model, first Discover run (handoff brief)

**Workstream:** Discover. **For:** the operator-controlled implementation agent.
**Status note:** drafted while WP-D1 was in progress. Slots marked `⟦PENDING-WPD1⟧`
are filled by the PM from the WP-D1 report before dispatch — if you receive this
brief with any such slot unfilled, STOP and flag.

**Files in scope (you may write ONLY these):**
`Insights/src/phase2_engine.py` (the `VIEW1_CONFIG` block only),
`Insights/src/phase4a_engine.py` (`VIEW2_CONFIG`/`VIEW3_CONFIG` blocks; retire `VIEW4..9`),
`Insights/src/phase4b_engine.py` (the `ALL_CONFIGS` run list only),
`Insights/src/phase5b_report.py` (`VIEW_DESCRIPTIONS` + `VIEW_CONFIGS` registry),
`Insights/src/phase5b_dual_reports.py`, `Insights/src/phase5c_gamma_reports.py`,
`Insights/src/phase5c_global_feed.py` (**import lists / view registries only — no
logic, no feed-shape change: D16**),
`Insights/src/discover_config.py` (model pin per D17),
`handoffs/WPD2_REPORT.md`.
**DO NOT TOUCH:** engine algorithm code (Modules B–E in phase2, evaluators in 4a,
ranking in phase5), `Insights/src/prose_gate.py`, `domain_pack_prdw/` (frozen at
WP-D1 gate), `Data/`, `Chatbot/`, `eval/`, `.env`, `Insights/DISCOVER_VIEW_MAPPING.md`,
`PROJECT_PLAN.md`.

**Preconditions — verify all; if any fail, STOP and flag:**

- [ ] WP-D1 is gate-green and committed; `views_prdw/` builds locally from the pack (`--strict`).
- [ ] Every `⟦PENDING-WPD1⟧` slot in this brief is filled.
- [ ] Local mirror execution (Drive temp-file rule); Python env has the packages `phase5b_report.py` imports.
- [ ] `.env` OpenAI key present but **no LLM call happens before T4's budget verification**.
- [ ] No other agent live on this tree.

**Read first:**

| Document | Why |
|---|---|
| `Insights/DISCOVER_VIEW_MAPPING.md` | The signed spec: §4 per-view dims/measures, §5 temporal rules, §6 the sample↔statewide switch you implement. |
| `Insights/src/phase2_engine.py` lines 42–120 | The `ViewConfig`/`MeasureConfig` contract you fill, incl. `extremum_ratio` semantics. |
| `Insights/src/phase4b_engine.py` `__main__` block | The run list + the **truncated-queue lesson** in its comments — read the iteration notes. |
| `Insights/src/phase5b_report.py` `VIEW_DESCRIPTIONS` | The glossary structure (title / description / audience_context / column_glossary) and its UNIT/TOTALLED-vs-AVERAGED conventions. |
| `Insights/src/discover_config.py` | The gpt-5.5 empty-prose incident, documented in place. This is why T4 exists. |
| `handoffs/WPD1_REPORT.md` | Actual view columns, reconciliation deltas, any renames. |
| `PROJECT_PLAN.md` D15–D17, D20–D22 | The decisions this brief implements. |

---

## Objective

The three PR&DW views mine end-to-end: phase4b drains all three queues, phase5
ranks, phase5b writes an executive report with **zero hollow sections** under
the pinned GPT-5.6 model, and the top-15 findings per view are packaged for the
operator calibration session (which the PM runs — not you).

## Non-goals

- No engine algorithm changes, no ranking changes, no prose-gate changes.
- No feed generation or gamma editions (WP-D3) — you only keep those files importable.
- No calibration judgments: you produce the materials; labeling is the operator's (D20).
- No pack edits: if a view column is wrong, that is a WP-D1 defect — STOP and flag.

## Facts you need

1. **Engine config contract** (`phase2_engine.ViewConfig`): dimensions,
   temporal_dimensions, measures (`MeasureConfig(name, agg)`), impact_measures,
   max_subspace_depth, tau, min_impact, min_hdp_size, extremum_ratio.
2. **Dimensions are NAME columns only.** The views carry LGD codes for the
   frontend contract; putting both a name and its code in `dimensions` would
   mine every finding twice. Codes stay out of the configs.
3. **All PR&DW measures are SUM** (mapping doc §3): volumes, amounts, flags,
   and the two signed overspend differences. No AVG measures in v1;
   `extremum_ratio` stays at the 0.67 default (the 0.80 override was for AP's
   proportional-share measures — we have none yet).
4. **Truncated queue = the one unscoreable failure** (phase4b iteration
   comments): a budget that cuts the queue silently changes what a view can
   find. Budgets start generous; the report states each view's actual drain
   time; a truncated view is a FAIL, not a smaller result.
5. **The sample↔statewide switch** (D15/§6): implement as one module-level
   switch (`DISCOVER_SCALE = os.getenv("DISCOVER_SCALE", "sample")`) selecting
   the dimension lists and depths below — the `_DB_SOURCES` pattern. Statewide
   values ship now, commented with their §6 rationale, untested until the data
   lands.
6. **D17 model pin:** `DISCOVER_PROSE_MODEL` default becomes GPT-5.6's exact
   API model ID — **verified against the live OpenAI model list, not guessed**
   (the current file pins `gpt-5.5`; its comment block documents why the budget
   constant exists). `DISCOVER_MAX_COMPLETION_TOKENS` (9000) must be
   re-verified for 5.6 in T4 before any report generation.
7. **Prose determinism stays wired:** deterministic reading notes/caveats and
   the prose gate run on the first report, not retrofitted (handoff §4). The
   §5.2 count-caveat (activity counts across FY 2023-24) must appear on any
   qualifying finding — T5 checks this explicitly.
8. **LLM spend discipline:** mining (T3) makes zero API calls; only phase5b
   report generation calls the model, and only after T4 passes. Nothing in
   this WP runs unattended LLM loops.
9. Actual view shapes (WPD1 report §8, PM-replayed 2026-08-14): view1
   **12,704 × 70**, view2 **1,440 × 17**, view3 **120 × 26**. **There are no
   renames** — every column named in T1's config table exists verbatim in the
   built Parquets. Columns present in the views but absent from the configs are
   intentional and stay out (LGD codes per fact 2; non-mining `meas` columns;
   the five statewide-staged sparse dimensions; `work_proposed_amount`/
   `work_proposed_cost`). Appendix A transcribes verbatim — its five
   measured-content patches from the WPD1 report are already applied below.

## Tasks

### T1 — The three `VIEW*_CONFIG`s

- **Do:** Replace the AP configs. `VIEW1_CONFIG` (phase2), `VIEW2_CONFIG`/`VIEW3_CONFIG`
  (phase4a); delete `VIEW4..9_CONFIG` and fix every import site (phase4a/4b/5b/5b_dual/5c×2 —
  registries and import lists shrink to three views).

| | view1 activity_lifecycle | view2 geo_month_cube | view3 gp_performance |
|---|---|---|---|
| dimensions (sample) | gp_name, block_name, district_name, theme, focus_area_name, work_type_label, activity_for_label, activity_type_label, output_type_label, status_label, is_costless, tied_untied, sanction_authority, sanctioned_scheme_name, fund_component_name, asset_category_label, fiscal_year | gp_name, block_name, district_name, fiscal_year | gp_name, block_name, district_name |
| dimensions (statewide) | as sample **minus gp_name, block_name** | district_name, block_name, fiscal_year | district_name, block_name |
| temporal_dimensions | **[] — none** (D22/§5: temporal mining is view2's job) | month, quarter, fiscal_year | fiscal_year |
| measures (all SUM) | n_activities, total_cost, fund_tied_total, fund_untied_total, fund_abandoned_total, work_proposed_cost, fund_sanctioned_total, total_expenditure, gen_amount, sc_amount, st_amount, overspend_vs_plan, overspend_vs_sanction, is_started, is_completed, is_ongoing, is_abandoned, is_under_approval, is_admin_approved, has_technical_approval, has_progress_evidence, evidence_uploads, trainees_total, beneficiaries_expected | payment_amount, receipt_amount, payment_count, receipt_count, activity_linked_expenditure, sanctions_count, sanctioned_amount | n_plans, n_activities, n_costed, n_costless, planned_cost, sanctioned_total, expenditure_total, overspend_vs_plan, overspend_vs_sanction, payment_amount, receipt_amount, n_admin_approvals, n_tech_approvals, n_completed, n_ongoing, n_abandoned, n_with_evidence, evidence_uploads |
| impact_measures | n_activities, total_cost | payment_amount, payment_count | n_activities, expenditure_total |
| max_subspace_depth | 2 (sample & statewide) | 1 | 1 sample / 2 statewide |

- **Done when:** configs import cleanly everywhere; `DISCOVER_SCALE` flips the
  marked blocks and nothing else; column names match the WP-D1 Parquets exactly.
- **Trap:** view1 is wide (17 dims × 24 measures). Do not pre-trim it to make
  the queue drain — that is a calibration decision (T6 escalation), not yours.

### T2 — Glossaries and audience framing (`phase5b_report.py`)

- **Do:** Replace `VIEW_DESCRIPTIONS` with the three PR&DW entries in
  **Appendix A — transcribe verbatim** (adjusting only column names WP-D1
  renamed). Audience: PR&DW review-meeting officers, English (D17 context /
  handoff). Update `VIEW_CONFIGS` and the dual-reports/gamma/global-feed
  registries to the three views.
- **Done when:** every config dimension and measure has a glossary entry; no AP
  string survives anywhere in the prompt path.

### T3 — Mining run (no LLM)

- **Do:** phase4b over the three views on the local mirror. Starting budgets:
  view1 900s, view2 300s, view3 120s. Then phase5 ranking.
- **Done when:** all three queues **drain** (diagnostics prove it; raise a
  budget and rerun if not), candidates + top-15 per view produced, drain
  times recorded.
- **Escalate if:** view1 cannot drain inside 1800s — report measured
  throughput and stop; trimming dims/measures is an operator decision at
  calibration (fact 4 / T1 trap).

### T4 — Model pin + budget verification (before any report)

- **Do:** In `discover_config.py`: set the verified GPT-5.6 model ID (fact 6),
  keep the shared budget constant. Then a **one-prompt live probe**: send one
  representative phase5b prompt; record `completion_tokens_details.reasoning_tokens`,
  visible-answer tokens, and `finish_reason`. If reasoning consumes the budget
  or `finish_reason='length'`, raise the constant (document the number) before
  T5.
- **Done when:** the probe returns non-empty prose with headroom, evidence in
  the report.

### T5 — Executive report + determinism checks

- **Do:** Run phase5b for all three views. Then verify: (a) prose gate passes;
  (b) **no hollow sections** — every per-view section has non-empty prose
  (diff against section headers; the gpt-5.5 incident is the reason);
  (c) the §5.2 reporting-artifact caveat appears on every qualifying finding
  (activity-count measure + fiscal_year involvement spanning 2023-24) and on
  none other; (d) every number in the prose traces to engine output (spot-check
  10 claims).
- **Done when:** all four checks pass with evidence in the report.

### T6 — Calibration package + report

- **Do:** Assemble for the PM/operator session: top-15 per view (Layer 3P) with
  template summaries, scores, and the executive report; a labeling sheet with
  one row per finding (blank label column: real / already-known / spurious).
  Expected-by-design entries the session will test: the March year-end spike
  (should surface → "already-known"), completion-measure degeneracy (17
  completed works), the FY 2023-24 caveat behavior. Write `handoffs/WPD2_REPORT.md`.
- **Done when:** the package lets the operator label without touching code.

## Cut-line

T1–T3 are the core (configs + a drained mining run). T4–T5 must not be split
from each other (a report without the budget probe is how the hollow-report
incident happened). If the run degrades, deliver T1–T3 + an honest T6 report
over a rushed T5.

## Escalation protocol

- **STOP:** preconditions fail; a view column contradicts the WP-D1 report (pack defect); view1 exceeds the T3 budget ceiling; the verified GPT-5.6 model ID cannot be confirmed via the API.
- **Decide-and-document:** budget raises (with drain evidence), glossary micro-edits forced by renames, probe-driven token-budget change.
- **Never:** trim configs to force a drain; edit engine logic, the prose gate, or the pack; run LLM calls before T4; commit.

## Gate (definition of done)

1. Three configs live; imports clean; `DISCOVER_SCALE` switch works; AP configs gone.
2. Mining drains on all three views; drain times reported.
3. Model pinned to the verified GPT-5.6 ID; budget probe evidence recorded.
4. Executive report: prose gate green, zero hollow sections, caveat check green, spot-checked claims trace.
5. Calibration package delivered.

The **workstream** gate ("no nonsense findings in top ranks") closes only after
the operator's calibration session — that part is not this brief's scope.

## Report spec — `handoffs/WPD2_REPORT.md`

§0 gate self-assessment · §1 config summary + switch design · §2 mining
diagnostics (per view: scopes, candidates, drain time, budget) · §3 model
probe evidence (tokens, finish_reason) · §4 report checks (gate/hollow/caveat/
trace) · §5 calibration package location + labeling sheet · §6 decision
journal · §7 self-audit.

---

## Appendix A — `VIEW_DESCRIPTIONS` content (PM-authored; transcribe verbatim)

Conventions follow the AP file: measures state UNIT and TOTALLED/COUNTED;
descriptions state known skews so the model contextualizes rather than
"discovers" them.

### view1 — Activity Lifecycle

- **title:** `"Activity Lifecycle — Every Planned Work and Its Money"`
- **description:** One row for each of the 12,704 activities the 20 Gram
  Panchayats planned between fiscal years 2020-2021 and 2025-2026, following
  each from plan (cost, funding source, LSDG theme, focus area) through
  administrative and technical sanction, voucher-linked spending, current
  status, and geotagged photo evidence. Three recorded skews are properties of
  the data, not findings: (1) costless activities (56% of rows) only began
  being reported from 2023-24, so activity counts jump ~8× at that boundary;
  (2) sanction records cover only ~17% of activities — an activity without one
  is not shown to be unapproved; (3) only 17 activities are marked WORK
  COMPLETED, so completion is near-degenerate in this sample. Money columns
  carry their basis: PLANNED (action-plan cost and funding splits), SANCTIONED
  (approval amounts), SPENT (voucher-linked expenditure).
- **audience_context:** Key questions for the review meeting: which themes and
  focus areas carry the money, and in which districts or blocks does that
  pattern break? Where do sanctioned funds and actual spending diverge? Which
  sanctioning authorities dominate, and where? Where does spending run ahead
  of the plan (positive overspend), and is it the same Gram Panchayats each
  time?
- **column_glossary:**
  - `gp_name` / `block_name` / `district_name`: The Gram Panchayat / Block /
    District, from the LGD-coded government roster. 20 GPs across 16 blocks
    and 9 districts in this sample.
  - `fiscal_year`: The plan year, as the full string form ('2024-2025').
    Counts across the 2023-24 boundary reflect the reporting change described
    above, not real workload change.
  - `theme`: The LSDG theme (6 themes; 'Unmapped theme' where the focus area
    has no mapping — 986 activities).
  - `focus_area_name`: The plan's focus area, 30 values (roads, drinking
    water, sanitation, education, …).
  - `work_type_label` / `activity_for_label` / `activity_type_label`: Decoded
    classification of the work (4 / 4 / 2 values). 'Unknown' means the code has
    no decode on file.
  - `output_type_label`: The activity's output-type code. **No output_type code
    has a description on file**, so every value reads 'Code 101' … 'Code 110' —
    eight opaque codes until the department supplies the decode.
  - `status_label`: Current recorded status. Heavily skewed: Activity Approved
    10,108; WORK ONGOING 2,110; WORK ABANDONED 420; UNDER APPROVAL 36; WORK
    COMPLETED 17; 'Buildings' is a known mis-coding affecting 13 rows.
  - `is_costless`: 'Costless' marks activities planned without a cost (training,
    campaigns, services); recorded only from 2023-24 onward.
  - `tied_untied`: Whether the sanctioned grant is Tied (earmarked, code 4249)
    or Untied (discretionary, codes 4211/4250); 'Other' is any other component.
  - `sanction_authority`: The sanctioning office, cleaned of spelling variants:
    Sarpanch, BDO, Engineer, Gram Panchayat, Panchayat Samiti — plus, in this
    sample, ten low-count free-text residues (15 records) the cleaning rule
    passes through, so 14 distinct values in all.
  - `sanctioned_scheme_name` / `fund_component_name`: The scheme and component
    behind the sanction; 'Code N' means the code has no description on file.
  - `asset_category_label`: The asset the work creates — 27 named categories
    reach this view (several codes share a description and 8 codes have none);
    'Uncategorised' covers 8,439 activities: the two-thirds without asset data
    plus 21 whose code has no description. It is not itself an asset category.
  - `n_activities`: UNIT: activities, COUNTED — one per planned activity.
  - `total_cost`: UNIT: rupees, TOTALLED. PLANNED basis — the action-plan cost.
    Null for costless activities.
  - `fund_tied_total` / `fund_untied_total`: UNIT: rupees, TOTALLED. PLANNED
    basis — the tied/untied split of the planned funding.
  - `fund_abandoned_total`: UNIT: rupees, TOTALLED. PLANNED basis — funding
    recorded against abandoned works (₹61.7M in this sample).
  - `work_proposed_cost` / `fund_sanctioned_total`: UNIT: rupees, TOTALLED.
    SANCTIONED basis — present only for the ~17% with sanction records.
  - `total_expenditure`: UNIT: rupees, TOTALLED. SPENT basis — voucher-linked
    actual spending; reconciles exactly with the cashbook links.
  - `gen_amount` / `sc_amount` / `st_amount`: UNIT: rupees, TOTALLED. SPENT
    basis, by social-category component. SC/ST components are near-empty in
    this sample — a near-zero here is data coverage, not a finding.
  - `overspend_vs_plan`: UNIT: rupees, TOTALLED, SIGNED (SPENT minus PLANNED).
    Positive = spending above plan; negative = unspent plan. The
    over/under-spend detector.
  - `overspend_vs_sanction`: UNIT: rupees, TOTALLED, SIGNED (SPENT minus
    SANCTIONED); meaningful only for the sanctioned ~17%.
  - `is_started` / `is_completed` / `is_ongoing` / `is_abandoned` /
    `is_under_approval` / `is_admin_approved` / `has_technical_approval` /
    `has_progress_evidence`: UNIT: activities, COUNTED — activities meeting the
    condition. Read against n_activities for a rate.
  - `evidence_uploads`: UNIT: geotagged photo uploads, TOTALLED (8,267 uploads
    across 1,675 activities).
  - `trainees_total` / `beneficiaries_expected`: UNIT: people, TOTALLED — for
    the small subsets recording training (1,034) and community-service (763)
    detail.

### view2 — Cash Cube

- **title:** `"Monthly Money Flows by Gram Panchayat"`
- **description:** One row per Gram Panchayat per calendar month across the
  full cashbook window (April 2020 – March 2026, 72 months — 1,440 rows
  including months with no transactions, which appear as zeros and are
  themselves meaningful). CASHBOOK basis: every voucher the GP recorded,
  including flows not tied to planned activities. This is the view for trends,
  seasonality, sudden shifts, and outlier months. One pattern is real and
  known: March, the fiscal year-end, concentrates payments every year.
- **audience_context:** Key questions: Is money moving steadily, or in
  year-end bursts? Which GPs' outflows have shifted sharply, and when? Where
  are receipts arriving but payments stalling — or payments running with no
  matching receipts? Which blocks or districts move money differently from
  the rest?
- **column_glossary:**
  - `gp_name` / `block_name` / `district_name`: as view1.
  - `month`: Calendar month ('YYYY-MM'). / `quarter`: calendar quarter. /
    `fiscal_year`: April–March year, full string form.
  - `payment_amount` / `receipt_amount`: UNIT: rupees, TOTALLED. CASHBOOK
    basis — all outflows / inflows in the month.
  - `payment_count` / `receipt_count`: UNIT: vouchers, COUNTED.
  - `activity_linked_expenditure`: UNIT: rupees, TOTALLED. SPENT basis — the
    subset of payments linked to planned activities.
  - `sanctions_count` / `sanctioned_amount`: UNIT: sanctions COUNTED / rupees
    TOTALLED. SANCTIONED basis, by sanction month. This view counts 2,040 of
    the 2,101 sanctions: 61 are dated outside the cashbook's 72-month window
    (14 before it, 47 after, including one future-dated sanction). The yearly
    report card (view3) counts by fiscal year and carries the full 2,101 —
    two time axes, two totals, both correct.

### view3 — GP Performance

- **title:** `"Gram Panchayat Report Card by Year"`
- **description:** One row per Gram Panchayat per fiscal year — all 20 GPs ×
  all 6 years, 120 rows, **including GP-years with nothing recorded** (zeros
  are the point: a GP with activities but no sanctions, or plans but no
  spending, is exactly what this view exists to surface — one sample GP has
  640 activities and zero administrative approvals on record). The
  institutional comparison table: who plans, who sanctions, who spends, who
  uploads evidence, year over year.
- **audience_context:** Key questions: Which GPs convert plans into sanctioned,
  executed, evidenced work — and which consistently do not? Is a GP's weak
  year a one-off or a trajectory? Do neighbouring GPs in the same block behave
  alike? Where is money spent with thin photo evidence?
- **column_glossary:**
  - `gp_name` / `block_name` / `district_name`: as view1. / `fiscal_year`: as view1
    (the activity-count reporting change applies here too).
  - `n_plans`: UNIT: GPDP plans, COUNTED (Main + Supplementary).
  - `n_activities` / `n_costed` / `n_costless`: UNIT: activities, COUNTED.
  - `planned_cost`: UNIT: rupees, TOTALLED, PLANNED basis.
  - `sanctioned_total`: UNIT: rupees, TOTALLED, SANCTIONED basis (~17%
    coverage caveat as in view1).
  - `expenditure_total`: UNIT: rupees, TOTALLED, SPENT basis.
  - `overspend_vs_plan` / `overspend_vs_sanction`: as view1, aggregated per
    GP-year.
  - `payment_amount` / `receipt_amount`: UNIT: rupees, TOTALLED, CASHBOOK basis.
  - `n_admin_approvals` / `n_tech_approvals`: UNIT: sanction records, COUNTED.
    Zero can mean nothing was sanctioned **or** nothing was recorded — the
    17%-coverage caveat applies. `n_tech_approvals` totals 2,095, not the
    2,134 technical-approval records: 39 sit on activities with no
    administrative approval and are invisible to this view — deliberately, so
    the Ask chatbot and Discover report the same number.
  - `n_completed` / `n_ongoing` / `n_abandoned` / `n_with_evidence`: UNIT:
    activities, COUNTED (completion near-degenerate in sample — see view1).
  - `evidence_uploads`: as view1.
