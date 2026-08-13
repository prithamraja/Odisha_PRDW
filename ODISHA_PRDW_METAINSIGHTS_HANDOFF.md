# Odisha PR&DW — Metainsights (Discover) workstream handoff

You are building the **Discover** mode for the Odisha PR&DW instance. This is
the second workstream; the Ask chatbot (`Chatbot/`) is largely built. Read
`ODISHA_PRDW_BOOTSTRAP.md` in this directory first — it covers the product,
the lineage (UP health → AP agriculture → this instance), the design
principles, and the operating lessons. This document covers only what Discover
adds.

---

## 1. What Discover is

An automated insight-mining pipeline (MetaInsight framework, Ma et al. SIGMOD
2021). It exhaustively searches flat analytical views for statistical patterns
(11 pattern types) and emits ranked "this holds broadly, except here" findings,
an LLM-written executive report, and a JSON feed consumed by the frontend's
Discover tab.

**The load-bearing principle:** the mining engine does all analysis; the LLM
only turns pre-validated structured findings into prose. Every claim in a
report is grounded in engine output. The prose layer additionally passes a
deterministic **prose gate** (`src/prose_gate.py`) and uses deterministic
reading notes/caveats — do not replace either with free LLM generation.

### Pipeline

```
ministry raw tables
  → staging (domain-specific script: cast/flatten to CSVs the pack expects)
  → domain_pack_prdw/  (sources.yaml, derived_columns.sql, views/*.sql,
                        validation.yaml — declarative, no Python)
  → src/build_views.py  (generic runner, DuckDB → Parquet views + validation
                        report + profiles)
  → src/phase4b_engine.py  (mining over all views)
  → src/phase5_ranking.py  (scoring + greedy diversity ranking)
  → src/phase5b_report.py / phase5b_dual_reports.py  (executive report)
  → src/phase5c_gamma_reports.py / phase5c_global_feed.py  (gamma editions +
                        the frontend feed)
```

A **view** = one denormalized table tuned for a question family. Views are the
single source of truth for numbers: the Ask catalogue's SQL templates target
these same views wherever possible, so Ask answers and Discover findings can
never disagree. **Before designing views, read the Chatbot's template catalogue
and reuse/extend whatever flat views it already targets — do not create a
parallel set.**

---

## 2. What was copied, and what each piece is

| Path | Status | Notes |
|---|---|---|
| `src/build_views.py` | KEEP | Generic pack runner. CLI: `--pack domain_pack_prdw --data-dir <staged csvs> --views-dir views_prdw --reports-dir reports_prdw` (add `--strict` in gates). Contains no domain strings. |
| `src/parity_check.py` | KEEP | View-comparison harness; useful while iterating on view SQL. |
| `src/discover_config.py` | KEEP — do not fork | Central prose-model choice + completion-token budget. Encodes a hard lesson: a reasoning model once spent the entire 2,000-token budget on reasoning and returned empty strings, producing a report with every section silently blank. The single shared constant exists so a model swap cannot under-budget one path while others work. |
| `src/prose_gate.py` | KEEP | Deterministic gate on report prose; part of what makes reports auditable. |
| `src/phase2_engine.py` | EDIT | Engine generic; the `VIEW*_CONFIG` declarations near the top (dimensions / temporal_dimensions / measures / impact_measures per view) are domain config — write them for the PR&DW views. |
| `src/phase4a_engine.py`, `src/phase4b_engine.py` | EDIT | Same: engine generic, imports the `VIEW*_CONFIG`s. View count is flexible — adjust the run list in phase4b. |
| `src/phase5_ranking.py` | KEEP | Generic greedy diversity ranking. |
| `src/phase5b_report.py`, `src/phase5b_dual_reports.py` | EDIT | Generator generic; the per-view `column_glossary` dicts and the audience/tone framing in the prompt builder are domain content. Set report language/audience here (PR&DW review-meeting officers; English unless the operator says otherwise). |
| `src/phase5c_gamma_reports.py`, `src/phase5c_global_feed.py` | KEEP (check output paths) | Gamma-weighted report editions and the frontend feed. The feed's JSON shape is the contract with the frontend Discover tab — read the file header and do not change the shape without an operator decision. |
| `src/gamma_sensitivity.py`, `src/generate_4a_report.py`, `src/generate_candidate_report.py` | KEEP | Calibration/diagnostic report helpers used during iteration. |
| `src/md_to_pdf.py` | KEEP | |
| `domain_pack/` (UP) | REFERENCE ONLY | Its `README.md` documents the pack format and runner contract — **read it before authoring anything**. Delete the pack once `domain_pack_prdw/` is done. |
| `domain_pack_rtgs/` (AP) | REFERENCE ONLY | The more evolved worked example: 9 views, a column crosswalk gating what may be staged (`demo_crosswalk.csv`), Aadhaar used as join spine but excluded from every view. Imitate those privacy/scope mechanics. Delete when done. |
| `domain_pack_prdw/` | **YOU AUTHOR THIS** | sources.yaml, derived_columns.sql, views/*.sql, validation.yaml. This IS the domain. No Python. |

Not copied (don't look for them): `data_fix.py` (UP synthetic-data repairs —
never migrates), `phase1_pipeline.py` (legacy pre-pack pipeline superseded by
build_views.py), all build outputs (`views/`, `metainsights/`, `reports*/`),
UP-era phase specs. The AP staging scripts weren't copied either — you write a
PR&DW staging script for step one of the pipeline.

---

## 3. Build order and gates

**Stage D0 — view mapping (no code).** From the PR&DW data dictionary, the
question material, and the *existing Chatbot catalogue*, produce a short
mapping doc: the flat views (grain, dimensions, measures, impact measures per
view), which existing Ask views are reused vs. extended vs. new, and metric
definitions with SME sign-off. The archetypes that transferred across both
prior domains, renamed for PR&DW:

1. *Lifecycle view* — one row per fund-release / work / grant instalment (the
   richest view; AP: one row per benefit payment).
2. *Geography × month cube* — GP × month grain for temporal trends.
3. *Institution performance* — one row per GP (× scheme/service where
   applicable). **Keep zero-activity rows** (LEFT JOIN from the GP master):
   a GP that filed or spent nothing is the finding, and an inner join
   silently deletes it.
4. *Journey/equity view* — per-beneficiary or per-work equity cube if the data
   supports it.

*Gate: operator + SME approve the mapping doc.*

**Stage D1 — domain pack + views.** Write the staging script and
`domain_pack_prdw/`; run `build_views.py --strict`. Scope discipline as in the
AP pack: an explicit crosswalk of every staged column to its analytical role;
no personal identifiers or bank/DBT-type fields reach any view; join keys
(LGD codes, any person ID) are consumed in `derived_columns.sql` and appear in
no view. Data-quality defects are **logged, never fixed** — the validation
report goes to the ministry; defects are analytically meaningful.
*Gate: views build clean under `--strict`; row counts and spot-check
aggregates confirmed by SME; validation report delivered.*

**Stage D2 — mining + calibration.** Write the `VIEW*_CONFIG`s and column
glossaries; run phase4b → phase5 → phase5b. Hold a calibration session with
the SME on the top-15 findings per view: real / already-known / spurious?
Iterate dimensions, measures, and engine params accordingly.
*Gate: SME rates the executive report useful; no nonsense findings in the top
ranks.*

**Stage D3 — feed + editions.** Generate the global feed and gamma report
editions; verify the frontend contract.
*Gate: feed validates against what the frontend expects; if multiple gamma
editions are published, ALL are regenerated from the same candidate set —
never ship a mix of fresh and stale editions.*

---

## 4. Discover-specific lessons from the AP campaign (do not relearn)

- **DuckDB cannot spill temp files on a Google Drive mount.** build_views.py
  already points DuckDB's temp at local system temp; still, run the whole
  pipeline from a local mirror and sync artifacts back (see the bootstrap
  doc's Drive/mirror protocol).
- **On any prose-model swap, check the completion-token budget first**, in
  `discover_config.py`, and diff the output for silently empty sections. The
  failure mode is a structurally complete report with hollow prose — nothing
  errors.
- **Define calibration gates as measurable, reachable metrics before
  iterating.** AP burned two full iterations on a gate whose measure spec was
  wrong (too sparse, then structurally unreachable given the data). When a
  gate keeps failing, first ask whether the *measure* is wrong or the target
  is structurally impossible for this dataset — escalate that to the operator
  as a decision, don't keep tuning toward it.
- **Prose determinism is a feature.** Reading notes/caveats are generated
  deterministically and the prose gate enforces report properties. Keep both
  wired in for PR&DW reports from the first run, not retrofitted.
- **Regenerate all published report editions together.** AP once regenerated
  only one gamma edition, leaving four stale files next to a fresh one on the
  shared Drive. Stale-but-plausible reports are worse than missing ones.
- **The engine's empty-subspace handling had a real defect once**
  (pair-overlap measure returning empty subspaces in AP iteration 4). It was
  diagnosed and fixed — but if a Discover measure produces suspiciously empty
  or sparse results on PR&DW data, check the measure implementation against a
  hand computation before trusting it.

---

## 5. Working practices (same as chatbot workstream)

- Drive repo is ground truth for code, packs, and reports; execute from a
  local mirror. One agent run per working tree; commit before trusting any
  prior report. End your run with a REPORT.md: what changed, gate results,
  open operator decisions. Flag missing inputs (data dictionary, SME access,
  frontend feed contract) to the operator before building around them.
