# WP-D0 — Discover view mapping (handoff brief)

**Workstream:** Discover (runs parallel to Ask — D14).
**Files in scope (you may write ONLY these):** `Insights/DISCOVER_VIEW_MAPPING.md` (the deliverable), `handoffs/WPD0_REPORT.md` (your report). Scratch work goes in local system temp, never the repo.
**DO NOT TOUCH:** `Chatbot/`, `eval/`, `Data/`, `Insights/src/`, `Insights/domain_pack*/`, `PROJECT_PLAN.md`, `.env`, any `.xlsx`/`.docx`/`.duckdb`. This WP produces documentation only — no code, no pack files, no data changes.

**Preconditions — verify all before starting; if any fail, STOP and flag in your report:**

- [ ] Working tree clean; `Insights/` and `ODISHA_PRDW_METAINSIGHTS_HANDOFF.md` are committed (the operator commits the Discover baseline before this run).
- [ ] `Data/` holds 19 per-table CSVs; `gram_panchayat.csv` has exactly 20 rows.
- [ ] `Data/create_views.sql` exists and defines seven `v_*` views.
- [ ] No `~$AI_Chatbot_Questions.xlsx` lock file (workbook closed; it is read-only input here).
- [ ] No other agent is live on this working tree (ask the operator if unsure).

**Read first — each earns its place:**

| Document | Why |
|---|---|
| `ODISHA_PRDW_BOOTSTRAP.md` | Product, lineage, operating rules (Drive/mirror discipline, log-never-fix). |
| `ODISHA_PRDW_METAINSIGHTS_HANDOFF.md` | The Discover pipeline; this WP is its Stage D0. §3 defines your task's contract, §4 the inherited lessons. |
| `PROJECT_PLAN.md` — §2, §5.1, §5.5, decisions D14–D17, D19–D20 | The verified repo state and the decisions this brief implements. |
| `Insights/domain_pack/README.md` | The pack format; everything you specify must be expressible in it. |
| `Insights/domain_pack_rtgs/` (esp. `demo_crosswalk.csv`, `derived_columns.sql`) | The worked example: crosswalk mechanics, scope discipline, join-key consumption. |
| `panchayat_database_description_v2 (1).docx` | Data dictionary — the authoritative traps list. |
| `Data/table_sources_and_changes.docx` | Build provenance for the CSVs. |
| `Insights/README_MetaInsight_System.md` | What the engine consumes: dimensions / temporal_dimensions / measures / impact_measures per view; subspace depth; pattern types. |

---

## Objective

One document — `Insights/DISCOVER_VIEW_MAPPING.md` — that fully specifies the PR&DW analytical views and their mining configuration, precise enough that WP-D1 can author `domain_pack_prdw/` and WP-D2 can write the `VIEW*_CONFIG`s from it **without reopening any design question**. The operator (who is the SME for Discover — D20) signs it off; that sign-off is Stage D0's gate.

## Non-goals

- No SQL authoring beyond illustrative fragments (pack authoring is WP-D1).
- No engine or config edits (WP-D2).
- No re-validation of `Data/` against `panchayat_1.duckdb` — already PM-verified identical (plan §5.5).
- No data-quality fixes, ever. Oddities are logged in your report (bootstrap: log, never fix).

## Facts you need (provenance in parens — restated here so you don't have to trust your skim)

1. **Views are the single source of truth for numbers.** Discover views must reuse/extend the seven `v_*` definitions in `Data/create_views.sql` that the Ask catalogue's 346 queries target (handoff §1). An Ask answer and a Discover finding disagreeing on the same number is a defect, full stop.
2. `v_activity` grain = one row per planned activity (12,704 sample); `search_text = LOWER(activity_name || ' ' || COALESCE(activity_desc,''))`; `status_label` is TRIM/tab-cleaned **in the views** while raw `dim_code` still carries `'\tWORK COMPLETED'`; `theme` keeps its trailing space (plan §5.1, §3a).
3. `gram_panchayat` carries block and district **codes** (merged from the voucher source) — it is the geography-hierarchy source and the LEFT-JOIN master for zero-activity rows (plan §5.5b).
4. Statewide data arrives later **in the same one-CSV-per-table format**: 30 districts / 314 blocks / ~6,800 GPs (D15, D4). Design for that scale; build for the sample.
5. **Two expenditure conventions**: cash basis (vouchers) vs plan basis (activity_expenditure). Every money measure you define must declare its basis (data dictionary; this is the marquee metric-definition risk).
6. The **2023-24 reporting-completeness step-change** poisons cross-year temporal comparisons (data dictionary). T4 exists because of it.
7. Approval tables cover only ~17% of activities — absence of an approval row ≠ unapproved (data dictionary).
8. `scheme_name` is 82% null (unusable as a dimension without explicit justification); NSAP beneficiary columns are empty — 13 beneficiary questions were dropped from the Ask catalogue for it (plan §2).
9. `dim_code` decode requires both the `variable` predicate and a VARCHAR cast (WP-2 report §6).
10. Fiscal year is the literal string `'2024-2025'` (D9).
11. The engine consumes, per view: `dimensions`, `temporal_dimensions`, `measures` (each SUM or AVG), `impact_measures`, and a max subspace depth (README + `phase4b_engine.py` `VIEW*_CONFIG`s).
12. Rate/average quantities must be carried as **numerator + denominator at base grain**, never pre-computed ratios — block/district roll-ups must not become averages-of-averages (D15).
13. Known oddities running list (plan §3a): 'Buildings' mis-decode (code 173), 'Poverty allevation' misspelling, `Kalyansinghpur`/`Kalyansingpur` GP-vs-block spelling, SARPANCH/SARAPANCH split. Expect them in profiles; log, don't fix.

## Tasks

### T1 — Input inventory & geography audit

- **Do:** Load the 19 CSVs read-only into a scratch DuckDB **in local system temp** (D6 — never on Drive). Profile every candidate dimension: sample cardinality, null rate, decode requirement. Audit the geography hierarchy from `gram_panchayat`: how many districts/blocks does the 20-GP sample span; are `block`/`district` code columns fully populated? Parse `create_views.sql` and list each `v_*` view's columns.
- **Done when:** your report carries a table of every candidate dimension (district, block, gp, fiscal_year, theme, focus_area, work_type, activity_status, sanction_authority, tied/untied, fund/scheme component, …) with cardinality + null rate + source, and a geography-coverage statement.
- **Traps:** fact 9 (dim_code decode); facts 2, 13.
- **Escalate if:** any CSV fails to load, or block/district codes are null for >5% of GPs — that undermines D15's geography-complete requirement.

### T2 — Measure census, with basis declared

- **Do:** Enumerate every candidate measure across the tables/views: amounts (sanctioned funds, proposed/approved cost, expenditure gen/SC/ST components, voucher amounts by direction), counts (activities, plans, vouchers, assets, approvals, progress uploads), durations, flags-as-rates (completion, approval, evidence-upload). For each: source column(s), aggregation (SUM/AVG), **cash-vs-plan basis for every money measure** (fact 5), and for anything rate-like the explicit numerator + denominator pair (fact 12).
- **Done when:** the measure table has no empty basis cell and no ratio without its num/denom decomposition.
- **Escalate if:** a measure's basis is genuinely ambiguous — list it as an open decision with your recommendation; do not pick silently.

### T3 — View designs *(the core of this WP)*

- **Do:** Specify each proposed view: name, grain, sample + statewide row estimates, dimensions, temporal_dimensions, measures, impact_measures, which `v_*` definitions it reuses/extends (with any delta justified), join/derivation notes in prose, zero-activity handling. Start from the handoff's archetypes, deviating only with written justification:
  1. `view1_activity_lifecycle` — one row per planned activity (the richest view; extends `v_activity`).
  2. `view2_geo_month_cube` — **GP × month grain with block/district as roll-up dimension columns** (D15); SUM-able measures and num/denom pairs only.
  3. `view3_gp_performance` — one row per GP (decide: × fiscal year?), **LEFT JOIN from `gram_panchayat` so zero-activity GPs survive** — the silent GP is the finding (bootstrap lesson).
  4. Equity/journey — assess feasibility honestly. Expected verdict given fact 8: not supportable in v1. Document the evidence and what data would change the verdict.
  - Also assess whether an **asset-grain** or **plan-grain** view earns a slot (`v_asset` serves 14 Ask queries, `v_plan` 18) — propose, don't assume.
  - Every view geography-complete: district/block/GP names **and** LGD codes (D15). No person-name column reaches any view (sanction authority is a role/designation — verify; vendor/payee names excluded).
- **Done when:** every view has every engine-config field filled (fact 11), and every column traces to a source column or a prose derivation.
- **Traps:** averages-of-averages (fact 12); inner joins deleting zero-activity rows; `scheme_name` as a dimension (fact 8); fact 7 (approval flags must encode three states, not two).
- **Escalate if:** reusing a `v_*` definition would require *changing its semantics* rather than extending it — that risks Ask/Discover divergence (fact 1) and is an operator decision.

### T4 — Temporal scope proposal (the step-change decision)

- **Do:** Quantify rows and measure-mass per fiscal year per table. Propose the mining window — e.g. temporal pattern types restricted to post-step-change months; categorical patterns over the full range or current FY — and draft the deterministic caveat text for any finding whose window crosses the boundary (fact 6).
- **Done when:** a data-backed recommendation with a stated default, framed as an open decision for the operator's sign-off.

### T5 — Sample-vs-statewide switch plan

- **Do:** Per view: which dimensions are breakdown-eligible at sample vs statewide (GP breakdown is fine at 20 values, not at ~6,800; district is degenerate in the sample, headline statewide), proposed subspace depths for each regime, and where the switch lives — one clearly marked block per `VIEW*_CONFIG` (the `_DB_SOURCES` pattern, D15).
- **Done when:** a two-column (sample | statewide) config sketch exists per view.

### T6 — Column crosswalk draft

- **Do:** Every column of every staged CSV gets an analytical role: `dimension` / `temporal` / `measure` / `join_key_consumed` (used in derivations, appears in no view) / `excluded_personal` / `excluded_other` (+reason). Table lives in the mapping doc; WP-D1 materializes it as the pack's crosswalk CSV (AP `demo_crosswalk.csv` mechanics).
- **Done when:** 100% of columns across all 19 tables have exactly one role, and nothing personal carries an included role.

### T7 — Report

- **Do:** Write `handoffs/WPD0_REPORT.md` per the report spec below.

## Cut-line

T1–T3 and T6 are core — WP-D1 cannot start without them. T4–T5 may be deferred to a flagged follow-up **only** if the run degrades, stated loudly in the report (WP-D2 needs them before mining).

## Escalation protocol

- **STOP and end the run** (report what you have): a precondition fails; `Data/` contradicts the PM-verified state; a `v_*` reuse needs a semantic change (T3).
- **Decide-and-document** (proceed; journal in report §9): ambiguous measure basis, archetype deviations, the equity verdict, the temporal default, the GP-performance grain question. Journal format per entry: *decision / options considered / choice / cost to reverse*.
- **Never:** fix data, write code, touch out-of-scope files, call any LLM API (nothing in this WP needs one).

## Gate (definition of done)

1. `Insights/DISCOVER_VIEW_MAPPING.md` exists; every proposed view fully specified (grain, dimensions, temporal, measures with basis, impact measures, provenance, zero-activity handling).
2. Crosswalk covers 100% of staged columns; zero personal identifiers in included roles.
3. Every rate is a num+denom pair; every money measure declares cash or plan basis.
4. Every view is geography-complete per D15.
5. Open-decisions list is explicit and self-contained (temporal scope, equity verdict, view-slate additions, any basis calls).

Gate holder: **operator as SME** approves the mapping doc (D20); PM reviews first.

## Report spec — `handoffs/WPD0_REPORT.md`

- **§0 Status** — gate self-assessment: the five gate items, each PASS/FAIL/PARTIAL with one line of evidence.
- **§1 Inputs verified** — precondition results, what was read.
- **§2 Dimension & geography audit** (T1 tables).
- **§3 Measure census** (T2 table).
- **§4 View designs** — summary + deltas from the archetypes and why.
- **§5 Temporal scope recommendation** (T4).
- **§6 Sample/statewide switch plan** (T5).
- **§7 Crosswalk summary** — role counts, full exclusion list with reasons.
- **§8 Data oddities observed** — additions to the running log (log-never-fix).
- **§9 Open decisions** — the journal, each entry decision-ready for the operator.
- **§10 Self-audit** — what you checked, what you did NOT verify, and anything a reviewer should replay.
