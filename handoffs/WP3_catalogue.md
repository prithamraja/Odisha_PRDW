# WP-3 — Catalogue (handoff brief)

**For:** the operator-controlled implementation agent.
**Precondition:** `create_views.sql` present in the repo. **Do not start without it.** Also: the operator must close `AI_Chatbot_Questions.xlsx` in Excel first (no `~$` lock file present) so the parse reads the saved file.
**Read first:** `ODISHA_PRDW_BOOTSTRAP.md`; `PROJECT_PLAN.md` (D1–D3, D9–D11, §3a); `handoffs/REPORT.md` §8; `handoffs/WP2_REPORT.md` §6 (dim_code cast trap), §9 (the AP leftovers you now own).
**Scope:** the catalogue and everything that serves it. This is the largest package — the biggest authoring task in the bootstrap's build order.

## Hard constraints

Same as WP-1/WP-2 (repo-only, Drive `.duckdb` never opened writable, `.env` untouched, no live LLM calls in tests — the reranker/extractor are exercised with mocks; §3a cache-deletion + clean-tree check before T0).

## Tasks

**T0 — Baseline.** Fresh caches, clean tree, full suite; expect WP-2 close (359/33/0).

**T1 — Views.** Wire `create_views.sql` into the `duckdb_file` startup path. Recommended approach: execute it into the **writable in-memory catalog** at adapter startup (exactly how `cache_tables.sql` already works under WP-1's ATTACH inversion — views live in `memory.main`, their unqualified base-table references resolve through `search_path` to the read-only attached file; the Drive file is never modified). Validate: all seven `v_*` views exist and `SELECT COUNT(*)` on each matches expectations; run WP-1's collision check (view names must not shadow file tables). Replace WP-2's four `# TODO(create_views)` substitutions in `entity_validator._DB_SOURCES` with the view-based queries from the Parameter Registry sheet and confirm value counts don't change (if they do — e.g. the views `TRIM()` the theme labels — follow WP-2 report §4.1's marked switch).

**T2 — D10 geography-predicate decision.** Inspect the views: which LGD-code columns do they expose?
- `gp_lgd_code` is known to exist in `v_activity` → every `$gp_name` slot becomes `{"bind": "code", "optional": ...}` binding a WP-2-resolved LGD code, and the SQL predicate `v.gp_name = $gp_name` is rewritten to `v.gp_lgd_code = $gp_name` (keep the bind name; document that its value is now a code).
- Block/district: if the views expose their codes, bind codes the same way. If they only expose names, bind the **registry-validated canonical name** (collision-safe only if unique — check: district names are unique statewide; verify block-name uniqueness against `gram_panchayat`; if statewide block names can collide, report it as a view-change request to the operator rather than shipping name-bound blocks).
Record the decision and evidence in your report.

**T3 — Template catalogue.** Parse the **Questions sheet** → rewrite `template_catalog.py` as the PR&DW catalogue (the AP one is retired here; keep the file's contract documentation style):
- Per entry: `query_id` (workbook Question ID), question text, **scope-phrased paraphrases** (D2 — for each geography-optional template, index "…in {District}…", "…in {Block}…", "…for {GP}…" phrasings resolving to the one entry; reuse the workbook's Original/Parameterized/Example question columns as additional paraphrases), SQL (named `$params`, verbatim except T2's predicate rewrites), `param_slots` built from the "Parameters (bind order)" column via WP-2's `PARAM_ENTITY_TYPES`, with `optional: True` exactly where the Parameter Registry says NULL-skips-filter, `caveat` from the Answerability Note (every Partial; also Yes rows whose note is user-relevant), plus bracket/module/submodule and question-type metadata.
- Only `Answerable from DB` = Yes/Partial rows become templates (346). No/Dropped rows go to T5.
- Traps you own: the `dim_code` double-cast (WP-2 report §6) if any SQL needs touching; no `$tag$` quoting anywhere (WP-1 report §8.4); `date_filter: None` on every entry (D9); `%` in `LIKE` patterns is fine on the DuckDB path.
- **`top_n` audit (D11.4):** list templates using `$top_n` whose statewide result could exceed 1000; report.

**T4 — Rerank context + dashboards.**
- `rerank_context.py`: rewrite with one family-level "↳" description per question *family* (group by Module/Submodule, splitting only where members would mislead the reranker; parameter variants share descriptions word-for-word). Read the AP file's docstring first — it documents the authoring contract, and `test_rerank_context.py` enforces full coverage / no template in two families.
- `dashboard_catalog.py`: propose 15–25 cached entries for the highest-frequency whole-of-sample questions (state-level counts/rankings per bracket). Mark them clearly as a **proposal for operator ratification** in your report.

**T5 — Known-unanswerables.** Wire the 17 No rows + 13 Dropped rows (Dropped sheet) into the fallback path: these questions retrieve and route to an honest "the database cannot answer this because…" response built from their Answerability Note / drop reason — not a generic miss. (Mechanism: your choice — a non-executable catalogue tier or a fallback lookup — but retrieval must find them, since officers *will* ask about beneficiaries.)

**T6 — Retire the AP leftovers you now own** (WP-1 report §8.2, WP-2 report §9): `fragment_reroute.GEO_SLOTS` + `main.GEO_SLOTS_WIDEST_FIRST` → `gp`/`block`/`district`; `router._scope_sibling` retired (D2 makes it moot); the bare-name path re-pointed at `gp` (or removed if redundant with the registry cascade — justify); `zones._SLOT_PHRASES`, `suggestions.py`, `fallback.py`, `preprocessor.py` domain copy → PR&DW; `_CONSTANT_ENTITY_TYPES` cleanup; `EntityCandidate.village` → tier-neutral rename (D11.3). The four retrieval-layer modules must handle optional slots sensibly (an optional geography slot is *offerable* as a follow-up chip, never demanded).

**T7 — Caveat rendering (D3).** The answer layer must surface `caveat` **verbatim** — append it to the rendered answer outside the LLM text (post-generation concatenation or a dedicated response field the frontend renders), never pasted into the LLM prompt where it can be paraphrased away. Test that a caveated entry's caveat reaches the API response on all three serving paths (WP-1 report §6).

**T8 — Execution gate.** Execute all 346 templates against the sample DB with the sample parameters from the workbook's **Test Report sheet**; compare rows returned. Target: exact agreement (325 with matching row counts, 21 legitimately zero-row). SQL is deterministic — any mismatch is a real defect (in conversion, predicate rewrite, or view wiring), not replay noise. List every mismatch with its diff.

**T9 — Full suite + `handoffs/WP3_REPORT.md`.** Structural tests are the definition of done and were *expected* to fail mid-package: `test_rerank_context`, `test_param_binding`, `test_extraction_enums` all green against the PR&DW catalogue at HEAD. Report: T2 decision + evidence, T8 results table, dashboard proposal, top_n audit, retired/changed tests with justifications, oddities, open decisions.

## Gate (definition of done)

1. All seven views live; registry substitutions replaced; value counts reconciled.
2. 346/346 templates execute; row counts match the workbook Test Report (mismatches = fail unless the operator rules otherwise on a listed diff).
3. Structural tests green: every template in exactly one described family; every slot binds; enums agree.
4. Caveat verbatim-rendering test green on all three serving paths.
5. Full suite green modulo documented, justified swaps; boot smoke test under `DB_ENGINE=duckdb_file`.
