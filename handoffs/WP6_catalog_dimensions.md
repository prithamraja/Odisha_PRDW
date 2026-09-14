# WP-6 — Catalogue dimensions: filters, breakdowns, lists, and the Eval_1 gaps (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `Ask/tools/build_catalog.py` (its two halves are split in T0; `rewrite_geography` is the model for the migration scripts); `Ask/query_router/vector_retriever.py` (many-vectors-per-template, k counts distinct ids); `Ask/query_router/rerank_context.py` (why family descriptions are generated from SQL); `handoffs/WP5_REPORT.md` (current gate-green baseline); `Eval_1.xlsx` (the 28 questions that motivated this package).
**Scope:** options 1–4 from the 2026-09-12 catalogue review. **Not in scope:** option 5 (side-by-side composition) and option 6 (measure-first semantic layer). Those wait until this package shows whether the template count is still growing.

## 0. Why this package exists

`Eval_1.xlsx` holds 371 rows that collapse to 28 distinct officer questions. Against the 346-template catalogue: 13 match directly, 11 are near-misses, 2 are absent, 0 are in the refusal list. The misses are not 13 missing rows in the workbook. They are three structural gaps:

| Gap | Example from Eval_1 | Why the catalogue cannot serve it today |
|---|---|---|
| A. Missing filter dimensions | "road construction activities in progress" | STS-003 has `$status`, no `$focus_area`. Plan type (Main/Supplementary) is in `plan.plan_type` but no template and no view column carries it. |
| B. Missing aggregate shapes | "total planned cost of all activities" | Only exists as a per-theme breakdown (BUD-006). "GP with the most planned activities" requires a theme (PLN-031). |
| C. No combination or comparison | "tied spend, water vs sanitation" | One measure, one dimension, two values, side by side. No slot takes a list; no slot chooses the breakdown. |

Plus a vocabulary gap the validator cannot bridge: *sector* (= focus area), *Sankalp themes* (= LSDG themes; only 6 of 9 present in `dim_lsdg_theme`), *main GPDP* (= `plan_type = 'Main'`), *Swachh Bharat* (not a scheme in `activity_expenditure`; the eval uses it to mean the Sanitation focus area).

## 1. Hard constraints

1. **The catalogue file becomes the source of truth (operator decision, 2026-09-12).** `template_catalog.py` stops being regenerated from the workbook after T0. SQL changes in this package are made to the file: bulk changes by one-shot migration scripts whose diff is reviewed and committed, awkward templates by hand. The workbook is archived as the record of the 2026-08-13 sign-off and is not edited again.
2. **The Test Report row counts remain the regression contract.** Every statement, bound with any new slot absent, must return the count in `tests/data/workbook_test_report.json`. `tests/test_catalog_execution.py` and `validate_catalog.py` keep running unchanged. This check never depended on the workbook and is the net that lets the file be edited freely.
3. **Derived artefacts stay generated from the SQL.** Paraphrases and `rerank_context.py` family descriptions are built from the statements, not hand-written, or they drift at the first edit. T0 repoints those generators at the catalogue file.
4. **Bound values are never interpolated into SQL.** Filter values bind as parameters. Breakdown columns come from a whitelist in the migration script, never from user text.
5. **The `$p IS NULL OR col = $p` idiom is the only way a filter is optional** (D2).
6. **SBM templates are excluded from the universal-slot migration.** The 85 SBM entries define their subject by a keyword regex on activity text; adding a `$focus_area` predicate would silently narrow them.
7. Ask-side paths only (D14), Drive `.duckdb` read-only, `.env` untouched, §3a spend discipline. LLM spend only in T7's replay.

## 2. Tasks

### T0 — Make the catalogue file the source of truth

`tools/build_catalog.py` has two halves. The import half (`read_workbook`, `build_templates`, `build_unanswerable`, `build_oracle`) reads the spreadsheet. The derivation half (`rewrite_geography`, `build_paraphrases`, `build_rerank_context`, `describe_family`) reads SQL and slot lists and would work from any source. Split them:

1. Run the builder one last time and confirm `--check` is green, so the file and the workbook agree at the moment of the switch.
2. Move the derivation half into `tools/derive_catalog.py`, which imports `TEMPLATE_CATALOG` and `UNANSWERABLE_CATALOG` from the `.py` files, regenerates the `paraphrases` lists in place (a marked block per entry, so hand-written SQL and generated paraphrases coexist in one file), and regenerates `rerank_context.py`. Its `--check` asserts the committed paraphrases and descriptions match what the current SQL derives.
3. Retire the import half. Delete `read_workbook` and friends, or leave a `tools/import_workbook.py` that can only *create* a fresh file, never overwrite. Move `AI_Chatbot_Questions.xlsx` to `handoffs/archive/` with a README line naming it as the 2026-08-13 sign-off.
4. `prdw_gates.py` check 3 changes from `build_catalog.py --check` to `derive_catalog.py --check`. The Test Report check (check 2) is unchanged.
5. Strip the "GENERATED FILE — do not edit by hand" header from `template_catalog.py` and replace it with the editing rules: SQL is edited here; paraphrases and descriptions are regenerated by `derive_catalog.py`; every edit must keep the Test Report count with new slots absent.
6. One commit, message naming the switch. The SME note: the ministry now audits the committed file and its git history rather than a spreadsheet; that is the artefact that actually runs.

Prove: gates green immediately after T0 with zero SQL changes.

### T1 — Expose plan type (prerequisite for everything "main vs supplementary")

`v_activity` gets one column, `plan_type`, from `plan` via `plan_code`. Every one of the 12,704 activities joins (verified 2026-09-12: 12,704 of 12,704). Add `plan_type` to `v_asset` and `v_progress` the same way they already inherit `fiscal_year`. Register `plan_type` in `column_metadata.py` and as a categorical entity type in `entity_validator.py` (`PARAM_ENTITY_TYPES["plan_type"] = "plan_type"`, values loaded from the DB: `Main`, `Supplementary`). Add `plan_type` to the D18 defaulted-slot table with **no default**, because "how many activities are planned" with no qualifier means both plan types, and that is the signed-off row count.

Prove: `validate_catalog.py` unchanged (346 execute, same counts) after the view change alone.

### T2 — Option 2: universal optional filter slots (migration M1)

A one-shot script, `tools/migrations/m1_universal_slots.py`, run once against `template_catalog.py`, diff reviewed, then committed. For every non-SBM template whose statement reads `v_activity` (directly or through `v_asset` / `v_progress`), it injects optional predicates for the dimensions the view already carries and the statement does not already filter on:

| slot | column | entity type |
|---|---|---|
| `$plan_type` | `plan_type` | plan_type (new, T1) |
| `$status` | `status_label` | status |
| `$focus_area` | `focus_area_name` | focus_area |
| `$theme` | `theme` | theme |
| `$scheme` | `scheme_name` | scheme |
| `$tied_untied` | `tied_untied` | tied_untied (new categorical: Tied / Untied / Other) |

The script inserts `AND ($slot IS NULL OR v.col = $slot)` into the WHERE clause of the innermost SELECT that reads the view, using the alias the statement already uses, and appends the matching entries to `param_slots`. It **skips** a dimension when the statement already references that column in a predicate or in an aggregate `CASE` (e.g. STS-003 keeps its own `$status`; BUD-006 groups by theme and gets no `$theme` filter unless the statement's own predicate is absent — decide per the SQL, and print each decision).

Where injection is not mechanically safe (CTEs that aggregate before the geography join, the 17 LEFT-JOIN-from-roster shapes), the script prints the id and leaves it. **Those are then edited by hand**, one at a time, in the same commit or the next. Nothing is left without the slots; the report lists which ids were scripted and which were hand-edited.

Paraphrases: `derive_catalog.py` (T0) already emits scope-phrased paraphrases for geography (D2). Extend the same generator to emit dimension-phrased paraphrases for each new slot — one per dimension, from a short phrase table (`"…under {focus_area}"`, `"…in the main plan"`, `"…for ongoing activities"`, `"…funded from tied grants"`). Keep it to one paraphrase per dimension per template; the retriever scores MAX over a template's vectors, so more phrasings help recall and cannot crowd the window (§3). Re-run `derive_catalog.py` after the migration.

Reranker: `rerank_context.py` is regenerated by `derive_catalog.py`; its "accepts filters:" line picks up the new slots automatically. The `_DISAMBIGUATION` hand-authored notes get two additions: "plan type is a filter on activities, not on plans" and "focus area is a filter, sector means focus area".

Prove: every changed statement, bound with the new slots NULL, returns the Test Report row count. `derive_catalog.py --check` green.

### T3 — Option 3: a breakdown slot (migration M2)

Generalise `grouped_geo` (9 templates today) into `$group_by`, a slot whose value is chosen by the router from a whitelist and written **into the statement as a CASE by the migration script**, never interpolated at query time:

```sql
GROUP BY CASE $group_by
           WHEN 'district'   THEN v.district_name
           WHEN 'block'      THEN v.block_name
           WHEN 'gp'         THEN v.gp_name
           WHEN 'theme'      THEN v.theme
           WHEN 'focus_area' THEN v.focus_area_name
           WHEN 'status'     THEN v.status_label
           WHEN 'scheme'     THEN v.scheme_name
           WHEN 'plan_type'  THEN v.plan_type
           WHEN 'fiscal_year' THEN v.fiscal_year
           ELSE 'All' END
```

The script applies it to templates whose statement is a single aggregate over `v_activity` / `v_asset` with either no GROUP BY or a GROUP BY on exactly one of the whitelisted columns. For the latter, the existing column becomes the slot's default (BUD-006 defaults to `theme`), so absent-slot behaviour is unchanged. For the former, absent slot yields one row labelled `All`, which is the plain total gap B needs. Templates the script cannot classify are hand-edited, as in T2.

The select list gets a matching `CASE … END AS group_label` column; the original group column is renamed where one exists so the frame shape stays stable for the operations layer (`operations.py` reads column positions for min/max/share — check `test_operations.py` still passes).

Fold duplicates while here: where two ids are the same measure with a different fixed breakdown (BUD-006 per theme and BUD-018 per focus area; PLN-024 and PLN-050; EXP-014 and EXP-025), keep one id, set the other's breakdown as an alias in the retained entry's paraphrases, and retire the second id. The Test Report gains one line per retired id recording which surviving id and `$group_by` value reproduces its count.

Entity side: `$group_by` is not extracted from text by the LLM. It is read by a deterministic prefill (like the `$date_range` reader promoted in WP-5 T1) from a small phrase table: "district-wise", "by block", "per theme", "theme-wise breakdown", "for each focus area", "year-wise", "across districts". No match → slot absent → default.

Prove: with `$group_by` absent, every rewritten statement returns the Test Report rows. With `$group_by = 'district'` on AST-001, the frame has one row per district and the sum equals the ungrouped total. Retire `grouped_geo` once all 9 carriers migrate.

### T4 — Option 4: list-valued filters and multi-year spans

Allow the categorical slots (`focus_area`, `theme`, `scheme`, `status`, `plan_type`, `district_name`, `block_name`, `date_range`) to bind a list. Migration M3 rewrites the optional-filter idiom to `($slot IS NULL OR v.col IN (SELECT UNNEST($slot)))` for DuckDB (or the adapter's list-bind equivalent — `db_adapters.py` decides; keep one form). A scalar still binds as a one-element list, so nothing else changes. This is a pure textual substitution of a fixed idiom, so it should need no hand edits; any statement where the idiom is spelled differently is normalised by hand first.

Extractor: `ExtractedEntity` gains `values: list[str]` beside `resolved_value`; the validator resolves each element through the same categorical path and refuses the whole list if any element fails (never a silent partial bind). Sentinel and enum tests extend accordingly.

Date spans: the `$date_range` reader already understands "FY 24-25" and "last year". Teach it "2024 to 2026" → `['2024-2025', '2025-2026']` and "last three years" → the three most recent loaded years. **Keep the current no-default rule**: a question with no year still clarifies.

Comparison rendering: when a list-valued filter and `$group_by` name the same dimension, the frame is the comparison ("tied spend, water vs sanitation" = `focus_area IN (Drinking water, Sanitation)` + `group_by = focus_area`). The router sets `$group_by` to that dimension automatically when a list is bound and no breakdown was requested, so the two values are never summed into one number. Echo names both values.

Prove: EXP-009 with the two-value list returns two rows whose sum equals two scalar calls. PLN-001 with a two-year list equals the sum of two single-year calls.

### T5 — Option 1: the genuinely new templates, and the glossary

Add directly to `template_catalog.py`, each with a Test Report line (execute once, record the count), then run `derive_catalog.py`:

1. **GPs with expenditure recorded but zero physical progress** — roster-shaped (LEFT JOIN from `gram_panchayat`), `total_expenditure > 0` and `has_progress_evidence = 0` at activity level, grouped to GP. Partial, caveat: physical progress is photo/GPS evidence uploads, not a stage model (1,675 of 12,704 activities have any).
2. **District-wise asset creation summary** — falls out of T3 on AST-001. Add only if the SME wants a fixed summary shape (count, cost, expenditure per district) rather than a breakdown of one measure.
3. **Total planned activities / total planned cost, no breakdown** — falls out of T3 on PLN-024 / BUD-006 with `group_by` absent. No new row.
4. **Top GP by planned activities across all themes** — PLN-031 with `$theme` made optional (edit the predicate to the D2 idiom, mark the slot optional). It is one of the 13 "subject-of-the-question" required slots; the operator's decision to relax it goes in the entry's `notes`.

Glossary (validator aliases, loaded like the existing alias table):

| officer says | resolves to | note |
|---|---|---|
| sector | focus area (the dimension, for `$group_by`) | SME to confirm |
| Sankalp theme(s) | LSDG theme | caveat: 6 of 9 present |
| main GPDP / main plan | `plan_type = Main` | |
| supplementary plan | `plan_type = Supplementary` | |
| Swachh Bharat / SBM | focus area Sanitation | lossy; caveat on every answer that used the alias |
| piped water supply | focus area Drinking water | SME to confirm |

Any alias marked lossy appends its own caveat sentence, verbatim, the way Partial caveats do (D3).

### T6 — Eval_1 into the gold set

Add the 28 distinct Eval_1 questions as gold rows (`eval/gold/build_eval_questions.py`), one canonical phrasing each plus the paraphrase with the lowest lexical overlap to the catalogue wording, with their expected ids from the 2026-09-12 matching table. Fix the two authoring defects first: rows 83–94 carry a year inside the question that conflicts with the appended year; rows using "2024 to 2026" become the T4 span form. Coverage table updated; `--check` green.

### T7 — Measure, then report

1. `recall_eval.py` before T2 and after T4, same K=30, same gold CSV plus the T6 rows. Report recall@30 by language and the rank of every T6 row. **Gate: no T6 row outside the window; English recall not below WP-4c's 95.4%.**
2. 3× full replay through `eval_spend.py`. Expect at or above WP-5's numbers; every T6 row served or correctly clarified.
3. `python prdw_gates.py` green, with `derive_catalog.py --check` in place of the workbook drift check and three new static checks: (a) every new slot is absent-safe (Test Report counts), (b) no `$group_by` value outside the whitelist appears in any statement, (c) `plan_type` present in the three views.
4. `handoffs/WP6_REPORT.md`: the scripted/hand-edited id lists per migration, the retired ids and their surviving equivalents, the recall table before/after, the replay table, the SME decisions taken (sector, Sankalp, Swachh Bharat, piped water), and the template count (expect it to **fall**, because T3 folds the fixed-breakdown pairs and the 9 `grouped_geo` carriers into single entries).

## 3. Does more templatising hurt vector recall@30?

Short answer: **options 2–4 do not add candidates to the window; they add vectors behind existing candidates, and the retriever was built for exactly that.** Option 1 adds a handful of ids. The real risk is on the reranker, not the retriever, and it is manageable.

Why the retriever is safe:

- The window is counted in **distinct query_ids**, and a template's score is the **MAX over all its vectors** (`vector_retriever.py`). Adding a dimension-phrased paraphrase to STS-003 gives "road works in progress" a vector to land on, and STS-003 still occupies one slot in the top-30. This is the mechanism D2 already relies on for geography, validated at recall@30 = 95.4% English (WP-4c §3.1).
- Options 2–4 **reduce** the id count. Today, BUD-006 (per theme) and BUD-018 (per focus area) are two ids for one measure; after T3 they are one id with a breakdown slot. The 9 `grouped_geo` carriers fold in the same way. Fewer, broader ids means less near-duplicate crowding, which is the failure the recall harness was written to watch for.
- Option 1 adds roughly 2–4 ids on a base of 376. At K=30 that is noise.

Where the risk actually moves:

- **To paraphrase coverage.** A universal slot is invisible to retrieval unless a paraphrase mentions it. "Main GPDP totals" will not retrieve PLN-024 on the word *main* unless the builder emits a plan-type paraphrase. T2's generator is the load-bearing piece, and the T6 gold rows are how you find out it worked.
- **To the reranker.** With universal slots, many templates accept the same filters, so the "accepts filters:" line stops discriminating and the "↳" family description carries the choice. Those descriptions are generated from the SQL, so they stay accurate, but the `_DISAMBIGUATION` notes need the two additions in T2. Measure with the replay, not the recall harness.
- **To Odia and code-mixed queries**, where recall is already the weak register (52.9% Odia script, WP-4c). Dimension paraphrases are English; they do nothing for those rows. Not a regression, but not a fix either — F2 stays deferred.

What would hurt: going the other way. Materialising the combinations as separate templates (30 focus areas × 6 statuses × N measures) is exactly the sibling-variant crowding that D2 was introduced to remove. That is why option 1 is limited to the two genuinely new shapes.

## 4. SME decisions needed before T2 starts

1. Does *sector* always mean focus area?
2. Do *Sankalp themes* answer from the six LSDG themes present, with a caveat, or refuse until the theme map is complete?
3. Is *Swachh Bharat* acceptable as an alias for the Sanitation focus area, with a caveat, or should it refuse with the alternative?
4. Which of the 13 subject-of-the-question required slots may become optional (at minimum PLN-031's theme)?

## Gate (definition of done)

1. `python prdw_gates.py` exits 0 with the three new checks.
2. `tools/derive_catalog.py --check` green; every changed statement absent-safe against the Test Report; the workbook archived and no longer read by any tool.
3. All 28 Eval_1 questions retrieve their expected id within K=30; English recall ≥ 95.4%.
4. 3× replay at or above WP-5's numbers; every Eval_1 row served or correctly clarified.
5. Template count reported, and not higher than 346 + the T5 additions.
