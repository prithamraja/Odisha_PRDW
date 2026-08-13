# WP-4a — Gold eval set, first draft (handoff brief)

**For:** the operator-controlled implementation agent.
**Runnable NOW — including in PARALLEL with WP-3, in sandbox mode.** Content-only, no code changes.

**Sandbox mode (mandatory when WP-3 is running, fine anytime):** WP-3 owns the repo's working tree and git. You READ the repo freely (the workbook, the eval harness code) but WRITE everything — the `eval/gold/` tree and your report — to a staging directory OUTSIDE the repo (your session scratchpad or an operator-named folder), and perform **zero git operations**. Your output is purely additive, so integration afterwards is: copy `eval/gold/` + the report into the repo, one commit. State the staging path prominently at the top of your report. One soft dependency: the harness-format check imports `Chatbot/` code that WP-3 may be mid-rewrite on — if it fails strangely, note it and re-run the check after WP-3 lands instead of debugging.
**Read first:** `ODISHA_PRDW_BOOTSTRAP.md` (Stage 3–4, multilingual lessons); `PROJECT_PLAN.md` (D5, D9, D11); the Questions sheet of `AI_Chatbot_Questions.xlsx`.

## What this is

The gold question set that WP-4's recall/routing evals will grade against (AP benchmarks: recall@30 ≈ 97%, end-to-end ≈ 96/97). This draft is **for SME review** — the operator's domain expert ratifies phrasing and expected answers before anything is graded against it. Author it as data; do not touch `Chatbot/` code.

## Constraints

- New files only, in an `eval/gold/` tree (in your staging directory under sandbox mode; at the repo root only if WP-3 is not running). No code edits, no LLM calls, no DB writes (read-only DB access is fine for sampling realistic entity values).
- First inspect `recall_eval.py` / `run_full_eval.py` to learn the harness's expected input format, and match it (fields like question, expected query_id(s), expected entities). Do not modify the harnesses.
- §3a disciplines apply (clean tree; commit at the end).

## Authoring requirements

1. **≥120 questions** (buffer over the ≥100 gate), mapped to workbook Question IDs as expected routes. Grade by **acceptable answer set**, not exact-ID match: where sibling templates are both legitimate answers, list all acceptable IDs (bootstrap lesson — this is how replay noise is kept out of regression reports).
2. **Distribution ∝ catalogue**, all 10 brackets covered, weighted toward Planning, SBM, Expenditure, Budgeting (the big four). Include ≥10 targeting *dashboard-eligible* whole-of-sample questions.
3. **Phrased the way officers actually talk**, not the workbook's clean phrasing: clipped review-meeting style ("GPDP status Khordha?", "kitne GP plan upload nahi kiya 24-25?"), honorific-laden full sentences, and everything between. Mix:
   - ~60% English, ~25% code-mixed (Hindi/Odia-English), ~15% Odia (script and transliterated) — the bootstrap's bilingual lesson; these only work once aliases exist, which is exactly what the eval must measure.
   - Entity surface variety: "FY 24-25" / "2024-25" / "last year" (D9), "1 lakh"/"₹50,000" amounts, misspelled places ("Kordha", "Bhubaneshwar block"), the SFC/CFC scheme colloquials.
4. **Hard cases, each labeled with its expected behavior:**
   - ≥10 follow-up fragments ("and in Ganjam?", "what about last year?") with the prior question specified — expected: context-preserving reroute.
   - ≥8 ambiguity cases — expected: clarification (e.g. a GP name that will collide statewide; a bare "SFC vs CFC comparison" missing a year).
   - ≥10 known-unanswerables (beneficiary counts, PAI grades, asset unit costs — from the No/Dropped lists) — expected: the honest can't-answer response, **not** a wrong route to a nearby template.
   - ≥5 out-of-domain questions (weather, elections) — expected: graceful fallback.
5. **Expected-answer evidence:** for a sample of ≥30 questions, record the expected result shape (row count or key figures from the workbook's Test Report sample runs) so end-to-end grading has ground truth beyond route-ID agreement.
6. **Format:** one JSON/JSONL file per bracket under `eval/gold/`, plus `eval/gold/README.md` documenting the schema, the acceptable-answer-set convention, and a coverage table (bracket × language × case-type counts).

## Deliverable

`handoffs/WP4a_REPORT.md`: coverage table, authoring conventions used, questions you could not confidently map (for SME triage), and an explicit list of items needing SME sign-off. Commit everything under `eval/` + the report.

## Gate

Coverage counts met per §Authoring requirements; every question carries expected route(s) + expected behavior; harness-format compatibility checked by loading the files with the harness's own parser (import-level, no eval run); SME-triage list produced.
