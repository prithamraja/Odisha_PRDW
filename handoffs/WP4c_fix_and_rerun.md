# WP-4c — Close out F1's remainders, re-run the evals (handoff brief)

**Updated 2026-08-14** for the post-`e3e70ff` state: F1's core fix (the deterministic `$date_range` fallback) and the §5.1a pair-order fix are **already in the tree and accepted (D30)** — this brief no longer implements F1; it closes its remainders and re-measures.
**For:** the operator-controlled implementation agent.
**Read first:** `handoffs/WP4_REPORT.md` **as updated at `a770b33`** — §5.1 (the fallback and its gotchas), §5.1a (the pair-order inversion), §5.2, §7; `PROJECT_PLAN.md` **D30** and D28 (Ask), D18, §3a.
**Scope:** make the eval numbers mean something, now that they can.

## Hard constraints

As WP-4: repo-only, Ask-side paths only (D14 — Discover's files are not yours), Drive `.duckdb` read-only, `.env` untouched, §3a disciplines. Baseline expectation at T0: **461 passed / 16 skipped** (PM-verified at `a770b33`). **LLM spend authorized only in T4's runs and the T5 A/B**, through `eval_spend.py`. Thresholds (`config.py`) move **only** in T6, only on post-re-run evidence, with 3× replay proof — if equivocal, propose in the report instead of changing.

## Tasks

**T1 — F1 remainders (D30.1–2).**
  a) **The bare-`except Exception → all-None` swallow in `entity_extractor.py` is still unfixed — fix it**: log + distinct sentinel, so a timeout/429/JSON error is distinguishable from "the user named nothing"; the deterministic fallback may still run on the sentinel (it is exactly the right response to an API failure), but the log must attribute the cause. Unit tests with mocked exception responses.
  b) **Do NOT add the D28.1 retry** — shelved per D30.1. Instead, T4 must *measure* the categorical-slot all-None rate (theme/scheme/status/place slots) across the replays; if it is materially nonzero, report it with evidence as the reopener.
  c) Confirm test coverage exists for the fallback's two documented gotchas (`EntityNotFound` swallowed so the officer's sentence is never quoted back as a malformed value; fallback ordered ahead of declared defaults AND the `optional` check for ALR-001/ALR-008). Add any that are missing.

**T2 — Behavior fixes (D28.3–5, unchanged).**
  a) Tier-collision clarification on the **classifier path** (G1524 must stop bypassing it); test both paths.
  b) Bound-tier replacement (D28.4): bound tier competes as a replacement reading; one viable reading auto-serves, two → tier-qualified clarification; update the `main.py` precedence comment; test the original-screenshot shape.
  c) The three generic declines (`BEN-001`, `BEN-003`, `PLN-022`): diagnose why their `UNANSWERABLE_CATALOG` entries lose to `ambiguous_templates`/`broad_question` and fix the mechanism (refusal reachable as chip and servable on a rerank win). 3/3-stable, so cleanly before/after-able.

**T3 — Instrumentation and eval hardening.**
  a) All three harnesses accumulate `resp.usage` (prompt/completion/reasoning tokens) and report totals; surface per-call reasoning tokens on extraction (the F1 telltale).
  b) **Direction-sensitive gold rows (D30.3):** for the five paired-year templates (PLN-039, PLN-040, TRD-004 and the other two `$date_range_2` pairs — enumerate from the catalogue), add/extend gold rows with `expected_result` evidence that pins the **sign** of the change columns, so a pair-order inversion is eval-visible forever. Rebuild via `--install`, `--check` green.

**T4 — Re-run.** Full eval **3 replays** + recall (embeddings cache warm), spend-guarded; `triage_replays.py` ≥2-of-3. Compare: end-to-end vs 96–97% (the §5.1 ceiling estimate is 86–88% — where the number lands between those tells you how much non-F1 defect remains), recall@30 vs 97% with per-language table, consistency vs ~3% (**now meaningful** — F1's variance is gone and the fallback is deterministic). Additionally: (a) collect and analyze **`_log_fiscal_year_disagreement`** output across the replays — zero disagreements → include a promote-to-prefill proposal per D30.4 (do not implement without the operator's confirmation); (b) report the categorical-slot all-None rate (T1b); (c) re-judge the two held fragments (`#1003`, `#1016`, D28.6). Triage discipline unchanged: real defect / gold error / noise / SME-pending.

**T5 — F2 A/B (CONDITIONAL — only if the operator confirms SME ratification of the 19 Odia-script rows).** Measured with `rerank_eval --compare` on the same gold set: (1) script→Latin transliteration at preprocess (evidence: transliterated retrieves at 100%) vs (2) Odia-script paraphrases in the retrieval index. Report both deltas; recommend; **no embedding-model change** without a separate operator decision. If the SME has not ratified: skip entirely and say so.

**T6 — Thresholds, evidence permitting.** Only after T4: if triage shows systematic mis-zoning, propose with distribution evidence, apply, and prove with a fresh 3× replay. If benchmarks are met at current thresholds, touch nothing.

**T7 — Report** `handoffs/WP4c_REPORT.md`: before/after eval tables (against WP-4's 59.8/64.6/62.2 and the 86–88% ceiling), token spend (now instrumented), residual all-None rates (date and categorical), the disagreement-log analysis with the prefill recommendation, T2 before/afters, threshold decision with evidence or the explicit "not warranted", SME-package delta.

## Gate

1. The swallow is gone (sentinel proven by test); fallback gotcha coverage complete; **no retry added**.
2. Benchmarks met — or every remaining gap root-caused with replay-confirmed evidence and an operator decision attached.
3. Consistency measured against ~3% and reported as the routing-stability number for the first time.
4. Direction-sensitive gold rows in place; `--check` green; suite green from the 461/16 baseline.
5. Zero threshold changes without the T6 evidence trail; catalogue touched only via the generator.
