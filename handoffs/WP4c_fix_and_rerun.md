# WP-4c — Fix F1, re-run the evals (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `handoffs/WP4_REPORT.md` (your spec — especially §5.1, §5.2, §7); `PROJECT_PLAN.md` **D28** (the rulings this brief implements), D18, §3a.
**Scope:** make the eval numbers mean something. The engineering is done; F1 is the gate.

## Hard constraints

As WP-4: repo-only, Ask-side paths only (Discover's files are not yours — D14), Drive `.duckdb` read-only, `.env` untouched, §3a disciplines. **LLM spend authorized only in T4's runs and the T5 A/B**, through `eval_spend.py` guards. Thresholds (`config.py`) may move **only** in T6, only on post-F1 evidence, with 3× replay proof — and if evidence is equivocal, propose in the report instead of changing.

## Tasks

**T1 — F1 (D28.1).** In `entity_extractor.py`: (a) retry once when every slot returns `None` on a non-empty question; (b) replace the bare `except Exception → all-None` swallow with logging + a distinct sentinel so an API failure is distinguishable from "nothing was named" (the router may clarify on both today — but the log must tell them apart, and the retry must not fire on the sentinel). Unit tests with mocked null/exception responses. **No model change, no `reasoning_effort` change** — that's the escalation path, operator-gated, only if T4 still shows >1% all-None.

**T2 — Behavior fixes (D28.3–5).**
  a) Tier-collision clarification on the **classifier path**: when the LLM follow-up classifier produces an executable `frame_edit` whose value also resolves at another executable tier, the `tier_collision` clarification fires there too (G1524 must stop bypassing it). Test both paths.
  b) Bound-tier replacement (D28.4): the already-bound tier competes as a *replacement* reading; exactly one viable reading auto-serves, two → tier-qualified clarification. Never a silent precedence pick. Update the `main.py` precedence comment to the new contract; tests for the original-screenshot shape.
  c) The three generic declines (`BEN-001`, `BEN-003`, `PLN-022`): diagnose why their `UNANSWERABLE_CATALOG` entries lose to `ambiguous_templates`/`broad_question` (retrieval score? rerank description? zone handling?) and fix the *mechanism* — e.g. an unanswerable candidate in the ambiguous zone must appear as a chip, and a reranker win must serve the refusal. 3/3-stable today, so before/after is cleanly measurable.

**T3 — Instrumentation (D28.8).** All three harnesses accumulate `resp.usage` (prompt/completion/reasoning tokens) and report totals. Reasoning-token spend per extraction call is the F1 telltale — surface it.

**T4 — Re-run.** Full eval **3 replays** + recall (embeddings cache warm) via the spend guards; `triage_replays.py` with the ≥2-of-3 rule. Compare: end-to-end vs 96–97%, recall@30 vs 97%, consistency vs ~3% (now meaningful for the first time — F1's variance is gone, so this measures routing). Report per-language recall unchanged from WP-4 format. Expected shape if F1's fix works: the 55 extraction-null failures collapse; residual failures triaged same as WP-4 T6. The two held fragments (`#1003`, `#1016`, D28.6) get re-judged here.

**T5 — F2 A/B (CONDITIONAL — only if the operator confirms the SME has ratified the 19 Odia-script rows).** Two candidate fixes, measured with `rerank_eval --compare` (before/after on the same gold set):
  1. **Script→Latin transliteration at preprocess** (cheap; evidence: transliterated Odia retrieves at 100%).
  2. **Odia-script paraphrases in the retrieval index** (per-template cost; no runtime change).
  Report both deltas; recommend; **no embedding-model change** without a separate operator decision (model-risk discipline: identity + completion-budget checks first). If the SME has NOT ratified the rows, skip T5 entirely and say so — measuring against unratified phrasing is measuring nothing.

**T6 — Thresholds, evidence permitting.** Only after T4: if the triage shows systematic mis-zoning (e.g. correct templates consistently landing in the clarify band), propose new values with the distribution evidence, apply, and prove with a fresh 3× replay that the change helps beyond noise. If the benchmarks are already met at current thresholds, touch nothing.

**T7 — Report** `handoffs/WP4c_REPORT.md`: before/after eval tables, token spend (now instrumented), F1 residual rate, T2 before/afters, threshold decision with evidence (or the explicit "not warranted"), and the SME-package delta (which WP-4a §4 items now have stable evidence for the metric-definition arguments).

## Gate

1. F1 residual all-None rate ≤1% across the 3 replays; the swallow is gone (logged sentinel proven by test).
2. Benchmarks met — or every remaining gap root-caused with replay-confirmed evidence and an operator decision attached.
3. Consistency measured and reported against ~3%.
4. Zero threshold changes without the T6 evidence trail.
5. Suite green; `validate_catalog` all-clear; catalogue untouched except via the generator.
