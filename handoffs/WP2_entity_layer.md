# WP-2 — Entity layer (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `ODISHA_PRDW_BOOTSTRAP.md`; `PROJECT_PLAN.md` (decisions D2, D4, D5, D9, D10 and §3a disciplines); `handoffs/REPORT.md` (the WP-1 report — especially §5 optional-slot semantics, §2 the stale-bytecode warning, §7 finding 3).
**Scope:** the system's vocabulary — entity registry, name→LGD-code resolution, extraction enums, fiscal-year phrases, amount normalization, collision guard. **No catalogue content** (templates, rerank descriptions, dashboards are WP-3).

## Context you need

- WP-1 is merged and gate-green (commits `55c5a76`..`8af162e`): `DB_ENGINE=duckdb_file` + `DB_PATH` opens `Chatbot/data/panchayat_1.duckdb` read-only; catalogue entries may use named `$name` SQL; slots support `{"optional": True}` (absent optional → binds NULL; a *supplied but invalid* optional value still clarifies — preserve that); entries carry an optional `caveat`.
- The spec for this package is the **Parameter Registry sheet** of `AI_Chatbot_Questions.xlsx` (root): 20 bind names, each with source column, allowed-values query, and NULL-skips-filter semantics. Parse it directly (openpyxl is available). The workbook is signed off — implement what it says; log oddities, don't "fix" them.
- The seven `v_*` views are still absent. Some allowed-values queries in the sheet reference them (`$status` → `v_activity.status_label`, `$asset_*` → `v_asset`). Substitute base-table equivalents for now (`activity_status` decoded via `dim_code` with the two-part join — `variable` predicate + VARCHAR cast, see the data dictionary §4; assets via `activity_asset` + `dim_code`) and leave a `# TODO(create_views)` marker at each substitution.

## Hard constraints

- Same as WP-1: work only in the repo root (+ scratchpad); never open the Drive `.duckdb` writable (registry loads use the read-only adapter); never print or commit `.env`; don't touch `frontend/`; **no LLM API calls** — extractor changes are prompt/enum content, tested with mocks.
- **Before T0: delete `Chatbot/**/__pycache__` and `Chatbot/.pytest_cache`** (§3a stale-bytecode discipline), and confirm `git status` is clean — stop and report if not.

## Tasks

**T0 — Baseline.** Fresh-cache full suite run; record exact counts. Expected from WP-1 close: 293 passed / 32 skipped / 17 errors (the errors are all `test_name_collisions.py`, retired in T4).

**T1 — Registry (`entity_validator.py`).** Replace `REGISTRY_CONFIG` and `_load()` with PR&DW entity types, values loaded from the DB read-only at startup:

- `district` (from `gram_panchayat.zp_name` — note the sheet's warning: the concept is "district" but the column is `zp_name`; 9 values in sample, 30 statewide), `block` (16 sample / 314 statewide), `gp` — **resolved to `gp_lgd_code`, roster-style**: the validated result carries the LGD code plus display name; a name matching multiple GPs raises the clarification path with block/district qualifiers as chip labels. Never a silent pick (bootstrap name-collision lesson). The sample's 20 names are unique — the machinery must not depend on that (see T4).
- `fiscal_year`: the 6 exact strings `'2020-2021'`…`'2025-2026'` loaded from `planned_activity`. Full-form only — `'2024-25'` must never reach SQL.
- `focus_area` (30 labels via `dim_code`), `theme` (from `dim_lsdg_theme` — **normalize trailing whitespace on load and when matching user input; log that the source values carry it; do not modify the DB**), `scheme` (5 non-null values from `activity_expenditure` + aliases: "CFC"/"central finance commission"→`XV Finance Commission`, "SFC"→`5TH STATE FINANCE COMMISSION`, "own funds"→`Own Funds`; grow from there), `status` (5 valid labels; if the suspected-bad decode `'Buildings'` appears in loaded values, keep it out of the enum and log it — validation logs, never fixes), `asset_category` / `asset_subcategory` (decoded labels; sparse-coverage reality is a WP-3 caveat, not your problem).
- Numerics as passthrough with range checks: `top_n` (positive int), `threshold`, `amount_threshold`; `deadline` (ISO date string, format-validated).
- Alias scaffolding: aliases live in per-entity dicts with a documented growth path (query logs, the operator's forthcoming dictionary file — D5). Seed English colloquials now; structure must accept Odia/transliterations later without code change.

**T2 — Fiscal-year phrases (`date_phrase.py`).** Replace agricultural-calendar logic with fiscal-year mapping per D9: "FY 24-25", "2024-25", "24-25", "this year", "last year", "last two years" (→ list/range) resolve to exact full-form strings, relative to the latest fiscal year present in the DB (not the wall clock — the sample ends at 2025-2026). Absent year = required-slot clarification, per D9. Swap `test_date_phrase*.py` fixtures to PR&DW expectations (bucket-2: keep test logic, swap fixtures).

**T3 — Extraction (`entity_extractor.py`).** PR&DW few-shot examples (use realistic officer phrasings: "GPDP status of Andhrua", "khordha me kitne GP…" code-mix is fine); **enum lists in the prompt generated from the registry at import time, never hand-written** — `test_extraction_enums.py` is the agreement gate and its fixture swap is part of this task. Extraction must emit the raw user surface form; validation (T1) owns resolution.

**T4 — Collision guard.** Retire `test_name_collisions.py` (AP roster; source of the 17 baseline errors) and write `test_gp_collisions.py` around PR&DW's unique keys, per the bootstrap's "port the concept, not the file": build a **synthetic fixture DB in the scratchpad** with duplicate GP names (e.g. two "Naugaon" in different blocks, one name duplicated within a district, plus unique names) and assert: ambiguous name → clarification listing each candidate with block/district qualifier; each candidate separately selectable and binding its distinct `gp_lgd_code`; unique names resolve silently; no template ever receives an unresolved ambiguous name. Include the guarded-connect pattern (skip cleanly when the fixture can't build, don't error — WP-1 report §7.3).

**T5 — Amount normalization.** Port the concept from `test_land_units.py` (then retire it): Indian-notation amounts in user text — "1 lakh" → `100000`, "2.5 crore" → `25000000`, "₹50,000"/"50,000" → `50000` — normalized before numeric slots (`amount_threshold`, `threshold`) validate. Tests for the conversions and for passthrough of plain numbers.

**T6 — Full suite + report.** Fresh run; then write `handoffs/WP2_REPORT.md` (leave WP-1's `REPORT.md` alone): what changed, baseline vs final counts, **an explicit list of every test whose fixtures you swapped or which you retired/replaced, with one line of justification each**, oddities logged (trailing spaces, 'Buildings', anything new), open decisions. Logical commits throughout.

## Gate (definition of done)

1. `test_extraction_enums.py` green against the PR&DW registry.
2. `test_gp_collisions.py` green (with synthetic duplicates exercised).
3. Everything green at T0 stays green, except tests explicitly listed in the report as fixture-swapped (green in new form) or retired-with-replacement. Net error count must drop by the 17 retired ones.
4. No live API calls anywhere in the run.

## Explicitly out of scope

Template/dashboard/rerank content; SQL predicate rewrite names→codes (D10 — WP-3 decides once `create_views.sql` arrives; your T1 resolution machinery is what makes that a small edit); `preprocessor.py`/`suggestions.py`/`fallback.py` domain copy (WP-3); the four retrieval-layer optional-slot consumers (WP-3, report §8.2).
