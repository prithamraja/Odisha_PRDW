# WP-5 — Gates and pre-pilot hardening (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `handoffs/WP4c_REPORT.md` (§5.2, §7.4–§7.6, §7.5 are your spec); `PROJECT_PLAN.md` **D31**, D30.4, D18, §3a; `ODISHA_PRDW_BOOTSTRAP.md` (the gates concept and model-risk lessons).
**Scope:** the last package before a pilot. Two pre-pilot fixes, the single-command gates file, and the alignment items. **Not in scope:** F2/Odia work (operator-deferred), thresholds (ruled not-warranted), the finding-C relative-period ruling (operator-deferred).

## Hard constraints

As before: Ask-side paths only (D14), Drive `.duckdb` read-only, `.env` untouched, §3a disciplines. **T0 requires a clean tree for Ask-side paths** — as of 2026-08-18 the tree holds uncommitted follow-up-visibility work (`Chatbot/main.py`, `router.py`, `echo.py`, `interpretation.py`, frontend files, `handoffs/FOLLOWUP_VISIBILITY_*`); the operator must land or shelve that first. Stop and report if Ask-side dirt remains. **LLM spend only in T1's replay proof**, through `eval_spend.py`.

## Tasks

**T1 — Promote the `$date_range` reader to a prefill (D30.4, operator-ratified).** Move `_fiscal_year_from_text` from the extractor-empty branch to a prefill beside `amount_from_text`; the extractor remains the fallback for the slot (reader-first — its vocabulary is narrow: "last year" resolves, "the year before" does not); delete the now-dead `_order_paired_fiscal_years` re-ordering (the reader's split IS the catalogue's convention — keep the direction *pins*, they are the regression net); confirm no default year is introduced (WP-4c §4.3: no-year questions still clarify, ~2% of the set). **Prove with a 3× replay** (spend-guarded): expect ≥ WP-4c's 85.8/87.2/87.2%, `wrong_direction` still zero, disagreement log quiet, and the ~12% extractor all-None rate now irrelevant to `$date_range`.

**T2 — The truncated-table operations guard (§5.2 — the one pre-pilot fix, D31.2).**
  a) In the operations layer: if the frame's `bound_params` carries a `top_n` (or the frame's result is otherwise a truncated view) and the requested operation is population-dependent (min, max, bottom_n, average, share-of-total — enumerate from `operations.py`), **never compute on the truncated table**: use `OperationMode.REQUERY` to re-run through the template without the limit where the template supports it, else `OperationMode.REJECTED` with a reason naming the truncation. Both escape hatches already exist and `_requery_for_frame` is already wired.
  b) **Operations answers get an echo** (the D3 gap the defect exposed): a deterministic sentence naming the operation and its scope ("Lowest planned expenditure among all focus areas, 2024-2025:"), with the frame's caveat carried. `query_description` must never be `None` on a served answer — add the assertion.
  c) Tests pinned to the recorded shapes: #1404 ("highest…?" → "and the lowest?") and #1042 (Hinglish) must re-query or reject — never serve the one-row minimum.

**T3 — `prdw_gates.py`: gate-green becomes one command** (replaces `pmkisan_gates.py`; delete the AP file). Exit 0 = green; each check prints one line; failures name the check. Contents:
  1. Full suite (fresh caches per §3a).
  2. `validate_catalog.py` (346 execute, row counts).
  3. `tools/build_catalog.py --check` (catalogue ↔ workbook drift).
  4. `eval/gold/build_eval_questions.py --check` + `check_harness_format.py`.
  5. **Model identity**: the four pinned models (extraction/rerank/abstraction `gpt-5.4-mini`, embedding `text-embedding-3-large`) checked against config AND the live model list (one cheap call, spend-guarded); on any mismatch, fail with the bootstrap's reminder to run the completion-budget check before accepting a swap.
  6. **Served-refusal invariant**: `result is None`, never `[]` (lift `test_served_refusal` verbatim).
  7. **Direction pins**: `test_paired_year_direction` (executed, no LLM).
  8. **Refusal-recall line (D31.4)**: retrieval rank of every unanswerable entry against its gold question, reported as its own line — in-window asserted for ratified registers (currently English; BEN-001 must stay ≤30), reported-not-asserted for deferred registers.
  9. Static invariants: no `date_filter` on any template; no `$tag$` quoting; every Partial carries a caveat; extraction sentinel wired; spend guards present on the three paid harnesses.
  No live LLM calls except check 5's single guarded call.

**T4 — Gold/grader alignment (D31.3, D31.5, D31.6).**
  a) Collision rows: a `tier_collision` clarification grades as a **pass** where it is the D18.P3-ratified outcome (#1524's gold row updated; grader handles the general case).
  b) **+~12 categorical gold rows** naming a theme, scheme, or status explicitly (the three slot families with no deterministic reader) — this is what makes the D30.1 retry decision rulable later. Rebuild via `--install`, `--check` green, coverage table updated.
  c) **BEN-003's register (D31.5)**: author a code-mixed retrieval surface for the beneficiary refusal entries in the generator (the Hinglish phrasing pattern of the gold row itself); measure its rank before/after the way §2.3 did for BEN-001 (deterministic, no LLM — the embedding call is part of index build). Target: in-window.
  d) `.jsonl` write path (D31.7): eval harnesses write results to a local temp path and copy the finished file into the repo folder — the streamed-flush-into-Drive pattern damaged all three WP-4c results files.

**T5 — Report** `handoffs/WP5_REPORT.md`: gates output verbatim (the one command, green); T1 replay table vs WP-4c; T2 before/after on the two recorded shapes; BEN-003 rank movement; and a **pilot go/no-go checklist** — the D31.2 fix confirmed, the three disclosures stated pilot-ready (Odia-script guidance, 20-GP denominator, fragment weakness), and the open-items list for the pilot's operators (six SME behavior calls, deferred finding C, deferred F2).

## Gate (definition of done)

1. `python prdw_gates.py` exits 0 and its checks include every item in T3 — "gate-green is a command, not a judgment call" (bootstrap, finally honored).
2. T1's 3× replay at or above WP-4c's numbers, `wrong_direction` 0, no new confirmed failures.
3. #1404/#1042 shapes re-query or reject with echo; `query_description` never `None` on served answers.
4. `--check` green with the new gold rows; BEN-003 in-window or its residual honestly reported.
5. `pmkisan_gates.py` deleted; suite green; zero threshold changes.
