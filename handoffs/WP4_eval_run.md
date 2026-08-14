# WP-4 — Eval integration and first runs (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `PROJECT_PLAN.md` (D9, D13, **D18**, §3a); `handoffs/WP4a_REPORT.md` (§0, §5, §6, §7 are your spec); `handoffs/WP3_REPORT.md` §13.
**Scope:** make the gold set live, fix what blocks a meaningful eval, run the evals, triage. **Explicitly NOT in scope: any threshold change** (`NO_MATCH_LOWER`, `CLARIFY_UPPER`, `CLARIFY_SCORE_MARGIN`) — calibration is WP-4c, after SME sign-off.

## Hard constraints

Repo-only; Drive `.duckdb` read-only; `.env` untouched/unprinted; §3a cache-deletion + clean-tree check at T0 (the tree currently has uncommitted WP-4a output — your first commit integrates it, see T1). **LLM spend is authorized ONLY in T5's eval runs** — everything else runs with mocks or no network. Before each paid run, print the question count and per-question call estimate, and write the token/call totals into the report afterwards.

## Tasks

**T0 — Baseline.** Integrate first (T1), then fresh-cache full suite; expect the WP-3 close (391/28/0) plus nothing broken by integration.

**T1 — Integrate.** Commit the WP-4a output as delivered (`eval/`, the two built harness inputs, `handoffs/WP4a_REPORT.md`, the pending `PROJECT_PLAN.md` edits). Then `python eval/gold/build_eval_questions.py --check` must pass from the committed tree.

**T2 — D18 catalogue fixes (edit the GENERATOR, then regenerate — never the generated files):**
  a) **`top_n` optional-with-default 10** (D18.P1): `build_catalog.py` marks `$top_n` slots `optional` with default `"10"`; regenerate; `--check` green; update the pins in `test_catalog_execution.py` / `test_param_binding.py` that assert required-ness. Ceiling stays 1,000 (operator-ratified; commit `96179d8`).
  b) **`$threshold` / `$amount_threshold` stay required** (D18.P2) — confirm no code change needed; the 15 templates clarify.
  c) **Odia digit normalization** (D18.P5): `str.translate` of Odia digits → ASCII in `date_phrase.py`'s preprocessing (and anywhere fiscal-year surfaces are read); tests for `୨୦୨୪-୨୫` → `2024-2025`; update gold row G1008 from clarify to answer, rebuild via `--install`, re-run `--check`.

**T3 — Unanswerable-gold upgrade** (WP-4a §5): flip the 19 rows from `gold: "no_match"` + `unanswerable_ref` to `gold: <unanswerable id>` so "declined for the right documented reason" is distinguishable from "declined generically". Extend `grade_full_eval.grade()` to accept a served-refusal id as a hit for those golds. Add the assertion (also destined for WP-5's gates): **a served refusal leaves `result` as `None`, never `[]`** — the one coupling that silently flips all 19 rows to `wrong_template`.

**T4 — Harness repairs** (flagged in WP-4a §6; harness edits are in-scope for THIS package):
  a) `grade_full_eval.py` line ~69: the stale `("tier1_dashboard", "tier2_template", "operation")` tuple → the tiers `main.py` actually emits; add a test with a legitimate `None`-rows template answer.
  b) `recall_eval.py`: make the `intent_catalog` import defensive; replace the dead crowding metric with paraphrase-aware crowding (distinct `query_id`s in top-K) or clearly label it removed — it must not print `mean: 0.0` as if measured.
  c) **Spend guards on all three paid harnesses** (`recall_eval`, `run_full_eval`, `rerank_eval`): print estimated calls and require `--yes` (or an env flag) before spending.
  d) `rerank_eval.py`: replace the hardcoded AP `GOLD_RAW` with the PR&DW gold set (derive reranker cases from `eval/gold/`); if that grows beyond a focused edit, report the scoping and defer the rest to WP-4c rather than half-porting.
  e) The two AP endpoint suites (`test_context_window_endpoint.py`, `test_date_phrase_endpoint.py`, 23 tests): port to PR&DW ids on the `duckdb_file` path as opt-in (the `test_followup_fragment.py` pattern), retiring what has no PR&DW analogue. This removes the last WP-1 §7.2 out-of-repo path landmines.

**T5 — The runs** (paid; spend-guard confirmations on):
  a) `recall_eval` over the 169-row mapping — benchmark: recall@30 ≈ 97% (AP parity).
  b) `run_full_eval` + `grade_full_eval` over all 205 — benchmark: ≈ 96–97% behaving-correctly.
  c) Consistency: replay the full-eval **3×** (`run_consistency_eval` / `aggregate_consistency` as the harnesses provide); expect ~3% flip rate. **No failure may be reported as a regression without appearing in ≥2 of 3 replays** (bootstrap discipline).
  d) Model-identity: record exact model names used (embedding + reranker + extractor) in the report — WP-5's identity gate needs them pinned.

**T6 — Triage, not tuning.** Classify every non-hit: (i) real routing/extraction defect (file it with evidence), (ii) gold-set authoring error (fix the row, log it, rebuild), (iii) replay noise (list, don't act), (iv) SME-pending judgment (tag with the WP-4a §4 item it waits on — do not "fix" these either way). If a threshold looks wrong, WRITE THAT DOWN with the evidence and stop — WP-4c acts on it after SME sign-off.

**T7 — Report** `handoffs/WP4_REPORT.md`: accuracy vs the two benchmarks, the consistency matrix, spend totals, the triage table, harness fixes with before/after, and the SME package status (which §4 items now have eval evidence attached).

## Gate (definition of done)

1. Integration committed; `--check` and the harness gate green from the committed tree.
2. D18 fixes in via the generator; execution oracle still 346/346; suite green with updated pins.
3. All three paid runs completed with spend recorded; consistency replays done.
4. Every reported failure is replay-confirmed and classified; zero threshold changes.
5. The 23 AP endpoint tests no longer reference paths outside the repo.
