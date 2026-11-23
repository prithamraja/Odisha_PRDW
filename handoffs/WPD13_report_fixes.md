# WP-D13 — Insight report fixes (running list)

**Workstream:** Discover. **Authored:** PM, started 2026-11-21. **For:** the
operator-controlled coding agent.

This file is a running list. Each fix is a self-contained section with its
own status. **Build only fixes marked READY.** A fix marked WAITING or QUEUED
is here so you can see what is coming — do not start it, and do not build
towards it. The PM adds fixes and changes statuses; you do not edit this
file. Report each fix in `handoffs/WPD13_REPORT.md`, one section per fix.

| # | Fix | Status |
|---|---|---|
| 1 | Direction in words: "Rs 3.18 crore below plan", and a check that catches a reversed direction | **BUILT** (`6faea99`..`e4c2229`) — wording accepted; check shipped in `log`, see Fix 1b |
| 1b | A direction rule that fits how the writer writes, then switch the check to `block` | **BUILT and ACCEPTED** (`17b2327`..`4c40b90`, D70). The check now ships in `block`. One small follow-up is in Fix 9 |
| 2 | Short answer and section headlines — TRIAL with an operator review sheet | **MOVED** to its own brief, `handoffs/WPD13b_headline_trial.md`. Trial run; **review ON HOLD** (operator, 2026-11-22, D67) until the writer model is chosen |
| 3 | Plain words for remaining jargon ("costless", "linked share", …) | QUEUED — **ON HOLD with the WP-D13b review** (D67): the word list comes from that sheet |
| 4 | "Show the rows" behind a warning | **PARKED** by the operator, 2026-11-21: "let's park that" |
| 5 | Download (report as PDF, rows as a spreadsheet) | **The PDF half is reopened as Fix 10** (operator, 2026-11-23). The spreadsheet of rows stays **PARKED** |
| 6 | The cause-and-effect check stops blocking chat answers (a switch, set to log); the writer's instructions stay as they are; a caution line at the bottom of every Insight report | **BUILT and ACCEPTED** (`9097653`..`f7a1f84`, D70). Live run was on `gpt-5.6-sol`; to be repeated on the chosen writer (Fix 8) |
| 7 | Display repairs found in the WP-D12 review: doubled words ("LSDG LSDG theme"), cited phrases that break the line, warnings on mixed-sign records | **BUILT and ACCEPTED** (`993764a`..`e853475`, D70) |
| 8 | The new models: writer and judge `gpt-6.2-sol`, classifier and chat verifier `gpt-6-luna` | **DEFAULTS CHANGED by the operator, by hand, 2026-11-22. Tests ON HOLD.** Two gate checks are red until they run — see the standing rules |
| 9 | Small repairs from the review of Fixes 1b, 6 and 7 | **BUILT and ACCEPTED** (`ab6f909`..`bce10e5`, D71) |
| 10 | A "Download PDF" button on every Insight report; the Copy button is removed | **READY** (operator, 2026-11-23, D72). Frontend only |

**Fix 10 is the only READY fix as of 2026-11-23.** Everything else left is
on hold or parked by the operator (Fixes 2, 3, 4, the spreadsheet half of
Fix 5, and the Fix 8 tests).

Related: `handoffs/WPD12_report_layout.md` (cards, charts, warning box).
**Fix 1 lands before WP-D12**, and WP-D12 reuses its helper (§1.2).

## Standing rules for every fix in this file

- **Design around mid-size models** (D62 ruling 7). Change what the model is
  handed before changing what it is told. Put checks after the model, not
  rules in its prompt. Never fix a failure by proposing a bigger model.
- **No prompt change unless a fix says so in the operator's own approved
  words.** `DiscoverChat/context_brief.py` is the operator's file.
- **No corpus rebuild, no re-embedding.** Stored sentences and vectors stay
  as they are. Wording changes happen at display time.
- **Prose length stays as it is** (operator, 2026-11-21). No fix shortens
  the prose, caps figures per sentence, or adds a length rule.
- Work from a fresh local mirror (`C:\dev\odisha-d13`), never the Drive
  path. Baselines first: `python -m DiscoverChat.gates` and
  `python -m pytest DiscoverChat/tests -q`, counts recorded.
- **The model defaults changed on 2026-11-22 (operator, by hand — D69).**
  Writer and judge are `gpt-6.2-sol`; classifier and chat verifier are
  `gpt-6-luna`. The edits are in `DiscoverChat/config.py` and
  `Insights/src/discover_config.py`. Leave both files as you find them.
  Two gate checks are **red by the operator's decision** until Fix 8's
  tests are run: `judge-model-evidenced` and `classifier-model-evidenced`.
  Do not fix them, do not re-run their evidence scripts, do not edit the
  evidence files, and do not change the models back. **Wherever a fix says
  "gate green", read "green apart from those two checks".** Record the
  baseline with them named. Any other red check is yours to report.
- Live turns now run on the new models. Say which model produced each
  result, and do not read a difference from a `gpt-5.6-sol` number as the
  effect of your change alone.
- Run live turns in parallel. Log every model call you make and its cost.
- Unrelated dirty paths (`Ask/bench/**`, root `prdw-*.html`) are not yours.
- Commit per task on the current branch (`WP-D13 F<fix> T<n>: …`). No push.
- A thing in a brief that turns out wrong is logged in the report and left —
  not worked around.

---

# Fix 1 — Direction in words, and a check that catches a reversed direction

**Status: BUILT** (`6faea99`..`e4c2229`, reported in
`handoffs/WPD13_REPORT.md`). **Do not build again** — the follow-on is
Fix 1b. **Decision: D63** (operator, 2026-11-21: "ok let's fix this").

## 1.1 The problem, measured

The writer says "Rs -3.18 crore" and "the signed spending-against-plan
measure" because the sentences it is handed say exactly that. And nothing
checks direction. On 2026-11-21 the PM ran `checks.check_citations` on record
`d1-00248` (true figure: Rs 51.96 crore **below** plan):

| Prose | True? | `all_pass` |
|---|---|---|
| "…totals Rs -51.96 crore [id]." | yes | True |
| "Recorded spending is Rs 51.96 crore below plan [id]." | yes | True |
| "Recorded spending is Rs 51.96 crore **above** plan [id]." | no | **True** |
| "Spending **exceeded** the plan by Rs 51.96 crore [id]." | no | **True** |
| "Recorded spending is Rs 61.96 crore below plan [id]." | no | False |

Cause: step 2 compares digits (`_NUM` has no minus sign) and nothing reads
the words around a figure. There is no verifier on the consolidated path.
This gap exists today, with or without any wording change.

**Corpus facts (measured, current corpus):**

- Negative figures occur only in decomposition records of the two signed
  measures, `overspend_vs_plan` and `overspend_vs_sanction`: 5,717 records —
  5,420 `all_negative`, 281 `mixed`, 16 `all_positive`.
- Every negative figure has one of three shapes: `Rs -N`, `Rs -N lakh`,
  `Rs -N crore` (18,984 tokens in 5,676 sentences). No other shape.
- All 5,717 carry the sentence "This measure is signed: a positive figure is
  spending above … and a negative figure is spending below …".
- No pattern finding (the 4,404) contains a negative figure.
- In 49 records the same money token appears both with and without a minus.

## 1.2 T1 — hand the writer the direction in words

At display time only. The stored sentence, the embeddings and the corpus
files do not change.

Add one deterministic step after the existing column-name translation, so
that `Finding.display_sentence()` returns, for a decomposition whose
`measure` is in `_SIGNED_DIRECTION` (import it from `phase5f_decompose`; do
not copy the words):

1. Every `Rs -N[ lakh| crore]` becomes `Rs N[ lakh| crore] below plan`
   (or `below sanction`) — the minus sign removed, the stored "below" words
   appended. Digits untouched.
2. The "This measure is signed: …" sentence is **removed when `signs ==
   "all_negative"`** (every figure now states its own direction). It is
   **kept unchanged** for `mixed` and `all_positive` records, where it is
   still what tells the reader how to read an unmarked figure.

Nothing else in any sentence changes. Every other record's display sentence
is byte-identical to today's.

Put the helper in `DiscoverChat/glossary.py` — one function for the token
rewrite, usable on a bare formatted value as well as inside a sentence —
because WP-D12's cards and charts must produce the same words from the same
function. Update that module's docstring: it currently says "NOT A REWRITE.
Only whole-token column names are substituted", which stops being true.

Everything that shows the display sentence picks this up with no further
change: the writer's input, the bare-sentence fallback, the hover card, the
record page's "Reads as" row.

- **Done when:** the corpus sweep in §1.4 test 1 is green and
  `findings-verbatim` still passes.

## 1.3 T2 — the direction check

A fifth step in `checks.check_citations`, `5_direction`, with a plain-English
reason in `citation_failure_reason`. It uses the same sentence split and the
same bindings as step 2 (`bind_numerals`) — do not write a second binder.

**Which figures it looks at.** A *negative money figure* is a numeral token
that the **stored** sentence of a signed decomposition shows as `Rs -N…`. A
token the stored sentence shows both with and without a minus (the 49
records) is not checked; report how many such tokens you skipped.

**The rule.** For every prose sentence in which at least one negative money
figure is bound to a signed record:

- **R1.** The sentence contains that record's stored "below" words —
  `below plan` or `below sanction` (allow "below the plan"). Exact words; no
  synonym list.
- **R2.** No minus sign stands directly before a figure in the sentence
  (a fiscal-year range like 2023-24 is not a minus sign).
- **R3.** The sentence does not contain the opposite stored words (`above
  plan` / `above sanction`), unless a figure the stored sentence shows as
  positive money is also bound in it.

A sentence that cites a signed record with shares or counts only is not
checked. One `below plan` covers every figure in the same sentence.

**The retry reason**, fed back exactly as the other reasons are: say which
sentences failed and that each figure's direction must be written as the
finding gives it — "Rs 51.96 crore below plan", not a minus sign and not
other wording.

**Mode.** `DISCOVERCHAT_DIRECTION_CHECK` in `config.py`: `block` (counts
towards `all_pass`, so: one retry, then the bare sentences — the existing
failure process, unchanged), `log` (recorded in the results, does not count),
`off`. Default per §1.5.

**Not in scope:** the pre-D7 connective-prose path (`check_prose`); pattern
findings on the signed measures (they carry no figure — "lowest spending
measured against plan" is a known soft spot the PM is holding, do not touch
it).

## 1.4 Tests and gate

New `DiscoverChat/tests/test_direction.py`, offline:

1. **Corpus sweep, all 5,717 signed records.** No `Rs -` in any display
   sentence; the count of "below" phrases added equals the count of `Rs -`
   tokens in the stored sentence; `numerals(display) == numerals(stored)`;
   the "signed" sentence is absent exactly when `signs == "all_negative"`.
   And for every other record in both corpora: display sentence identical to
   the pre-fix output.
2. **The five sentences of §1.1** on `d1-00248`, in `block` mode: the raw
   minus now fails (R2), the true sentence passes, "above plan" fails,
   "exceeded the plan by" fails (R1), the wrong number fails on step 2.
3. **Shape cases.** Several negative figures in one sentence with one
   `below plan` → pass. A sentence with shares only → not checked. A
   follow-on sentence with a negative figure and no "below" words → fail,
   and the reason names it. A sentence binding one positive and one negative
   figure with both phrases → pass.
4. **Modes.** `log` leaves `all_pass` as it would be without the step; `off`
   omits it.

Add to `gates.py`: the corpus sweep as a named check, and one reversed-
direction case in the existing `citation-checks-fire` check. The gate stays
a single command and green.

## 1.5 T3 — measure it live, then set the default

The strict rule can reject a correct sentence ("Rs 98.42 lakh of this
shortfall", "under plan"). How often is an empirical question about the
writer model, so measure before blocking.

- New `DiscoverChat/experiments/run_direction_trial.py`. Twelve questions
  whose answers cite signed records — take them from the recorded question
  sets in `DiscoverChat/experiments/`, and include "What should I know about
  Cuttack?".
- For each: retrieval and the judge **once**, then `writer.consolidate` on
  the same findings twice — once in `log` mode, once in `block`. In parallel.
  Cap: 80 model calls in total.
- Record per answer and per attempt: every `5_direction` failure with the
  sentence verbatim; whether the answer fell back, and on which check.
- Classify each direction failure yourself as a **true catch** (the sentence
  was wrong or showed a minus sign) or a **false alarm** (the sentence was
  right in other words). Put every failing sentence in the report so the
  operator can overrule your call.

**The rule for the default:** if at most 1 of the 12 answers falls back
because of a false alarm, ship `block`. Otherwise ship `log`, STOP, and
report — the PM will rule on a looser R1 with the sentences in hand. Do not
loosen the rule yourself and do not add a synonym list.

## 1.6 Files

**In scope:** `DiscoverChat/glossary.py`, `DiscoverChat/corpus.py`
(`display_sentence` only), `DiscoverChat/checks.py` (step 5 and its reason),
`DiscoverChat/config.py` (the mode), `DiscoverChat/gates.py` (the two gate
additions), `DiscoverChat/tests/test_direction.py` (new),
`DiscoverChat/experiments/run_direction_trial.py` and its output (new),
`handoffs/WPD13_REPORT.md`.

**Do not touch:** `DiscoverChat/context_brief.py` (no prompt change — the
prompt already says "use figures exactly as they appear in the findings",
and after T1 the figure appears with its direction), `writer.py`, `judge.py`,
`render.py`, `Insights/**` (import only), both corpus files and their
vectors, `frontend/**`, `Ask/**`, `handoffs/PROJECT_PLAN.md`.

## 1.7 Report

Baseline vs final gate and test counts; the corpus sweep numbers; skipped
ambiguous tokens; the trial table and every failing sentence; the default
you shipped and why; the Cuttack answer before and after, in full.

---

# Fix 1b — A direction rule that fits how the writer writes

**Status: BUILT and ACCEPTED (D70, 2026-11-22). Do not build again.**
Report: `handoffs/WPD13_REPORT.md`. Follow-up: Fix 9 T1.
The operator approved the rule and its word list on
2026-11-22: "I like the idea of blacklist of wrong words instead of a
whitelist of correct words."
**Decision: D65** (PM rulings on the Fix 1 report, 2026-11-21), **D66**
(operator approval, 2026-11-22).

## 1b.1 PM rulings on the Fix 1 report

PM replay on the Drive copy, 2026-11-21: gate 35/35 green; tests 111 passed
and the same one old failure — both as reported.

- **T1 (direction in words) is ACCEPTED.** The sweep is exact (18,984 figures
  reworded, no digit changed, 65,466 other records untouched) and the writer
  wrote no minus sign and no "above plan" in 46 live attempts.
- **T2 (the check) is ACCEPTED as built.** The three calls the agent made
  where the brief was open — ambiguous tokens, R3's exception, what counts
  as a minus sign — all stand.
- **Shipping `log` and stopping was correct.** The agent did not loosen the
  rule or add words, as told.
- **R1 was the PM's design and it was wrong for this writer.** It demanded
  "below plan" in every sentence that carries a figure. The writer says it
  once and then speaks of "the gap" and lists its parts. All 43 failures were
  correct sentences; R2 and R3 never fired.

## 1b.2 The rule change (approved by the operator, 2026-11-22)

R1 asked whether the right words were **present**. R1′ asks whether the
wrong words are **absent**:

- **R1′.** A sentence in which a negative money figure is bound to a signed
  record must not contain a word that states the opposite direction:
  - exceed, exceeds, exceeded, exceeding
  - overspend, overspent, overspending; overshoot…; overrun, overran
  - surplus; in excess
  - over [the] plan, over [the] sanction
  - more / higher / greater than [the] plan, …than [the] sanction
- **R2** (no minus sign before a figure) and **R3** (no "above plan" /
  "above sanction") are unchanged. R1 is removed.

One list, in one place beside the step, matched on whole words, ignoring
case. This is a word list in a check after the writer — the same kind of
thing as the cause-and-effect check — not a rule in the prompt.

**The PM's evidence (offline, no model call).** Run over every recorded
attempt of both trials — 77 attempts, 697 sentences: **0 hits**. The words
the writer actually used for direction: "below plan" 211 times, "gap(s)"
108, "shortfall" 32, "below sanction" 10, "underspend…" 10.

**The known limit, accepted:** a reversed direction said in words outside
the list ("spending outran the plan") passes. The writer, once handed the
direction in words, did not reverse it once in 83 attempts.

## 1b.3 Tasks

- **T1.** Replace R1 with R1′ in step 5. Reword the retry reason to match
  (name the offending word; give the figure as the finding has it).
- **T2. Tests.** The five sentences of §1.1: raw minus fails (R2), the true
  sentence passes, "above plan" fails (R3), "exceeded the plan by" fails
  (R1′), the wrong number fails on step 2. **All 43 sentences listed in
  `handoffs/WPD13_REPORT.md` §5 now pass** — use them as fixtures. Each word
  family in the list fails once. A share-only sentence is still not checked.
- **T3. Offline replay — no model calls.** Run step 5 over every recorded
  attempt in `DiscoverChat/experiments/direction_trial_results.json` and
  `handoffs/WPD13b_headline_trial/trial_results.json`. Report failures by
  rule, with each sentence verbatim. **Default rule:** no failure on a
  correct sentence → ship `block`. Any such failure → ship `log`, STOP, list
  them.
- **T4. The one old test failure.**
  `test_citations.py::WriterPromptTests::test_the_prompt_is_the_operators_text`
  looks for a line the operator's own edit of 2026-09-11 replaced. Bring the
  test's expected text up to the operator's current wording in
  `context_brief.py`. The test follows the operator's file; never the
  reverse. The suite then has no failures.

**In scope:** `DiscoverChat/checks.py` (step 5 and its reason),
`DiscoverChat/config.py` (the default), `DiscoverChat/gates.py` (only if the
seeded reversed-direction case needs its expected rule renamed),
`DiscoverChat/tests/test_direction.py`, `DiscoverChat/tests/test_citations.py`
(that one test only), `handoffs/WPD13_REPORT.md` (a "Fix 1b" section).
**Do not touch:** `context_brief.py`, `glossary.py`, `writer.py`,
`Insights/**`, `frontend/**`. **No model calls in this fix.**

**Done when:** gate green; the test suite green with no failures; the
offline replay reported; the default set by the rule above.

---

# Fix 2 — Short answer and section headlines (trial)

**MOVED, 2026-11-21, to its own brief: `handoffs/WPD13b_headline_trial.md`**
(report: `handoffs/WPD13b_REPORT.md`). Moved unchanged so it can be handed
over separately while Fix 1 is running. Nothing about Fix 1 changed.

---

# Fix 6 — The cause-and-effect check stops blocking answers; a caution line is added

**Status: BUILT and ACCEPTED (D70, 2026-11-22). Do not build again.**
Report: `handoffs/WPD13_REPORT.md`. **Decision: D68** (operator, 2026-11-22). It changes
how D41 (correlations only) is enforced in the chat service; D41 itself
stands. History and measurements: D66.

## 6.1 This was fixed once, and the fix was later taken out

| Date | What happened | Source |
|---|---|---|
| 2026-09-03 | 13.3% of answers fell back to bare sentences, every one on this check: "therefore" 11, "because" 5, "driven by" 1, "driving" 1 | `WPD7_REPORT.md` §4 |
| 2026-09-04 | The operator added to the writer prompt: *Do not make causal claims ever and do not use "therefore", "because", or "driven by".* Fall-backs went from **13.3% to 0.0%** | `WPD9_REPORT.md` §0, §2a |
| 2026-09-14 | The operator's own later edit replaced that line with one general sentence — *It is very important that you do not make causal claims - none of our data can be used to determine causality.* — under the ruling "one general sentence, no banned-word list". The three words left the prompt. **The check did not change: it still rejects them.** | `WPD11b_profile_followon.md` ruling 2; commit `cc72e71` |
| 2026-09-14 | The general sentence was measured on the reports (hits roughly halved, not cleared) and on six live chat turns (0 fall-backs) | `WPD11b_REPORT.md` |
| 2026-11-21 | Three separate runs, same result: **7 of 32 answers lost their narrative to this check** (3 of 12, 2 of 15, 2 of 5 live) | `WPD13_REPORT.md`, `WPD13b_REPORT.md`, `WPD12_REPORT.md` §9 |

So the writer is checked against a word list it is no longer shown.

## 6.2 What fails, measured (PM, offline, no model call)

Every number in this section is for the writer `gpt-5.6-sol`. The operator
is going to try other writer models (D67); a different model will give
different numbers, so T4 is run on whichever model is in use.

Over every recorded attempt of the two WP-D13 trials:

- **Written today's way: 22 of 60 attempts failed this check.** With the
  WP-D13b wording ("state facts only, and give no advice"): **1 of 17**.
- The words: "therefore" 12, "because" 10, "driving" 3, "affect/affecting" 2.
- **None of the 28 failing sentences says one thing in the data caused
  another.** They are of three kinds:
  1. A reason given for a recommendation or a caution: "Asset classification
     needs attention because 412 activities, or 64.4%, are uncategorised";
     "treat the Theme 3 sanction comparison cautiously because the
     sanctioned basis covers only activities with a sanction record on file".
  2. "therefore" joining a fact to a recommendation: "Attention should
     therefore cover all 16 blocks".
  3. The officer's own word, in a denial: asked "Who is driving the
     shortfall?", the writer answers "No single Gram Panchayat is driving the
     shortfall". The check already lets denials through ("not", "cannot",
     "never", "without"), but "no" is not in its list.
- **The retry recovers about two in three.** 17 answers failed the first
  attempt on this check; 6 failed it again and were lost. In 3 of those 6
  the writer swapped one rejected word for another ("therefore" →
  "because"), because the rejection message names only the word it used.

## 6.3 The operator's decision (2026-11-22, D68)

> "Let's remove the causal check (just comment it out, don't delete the
> code). We'll keep the context brief as-is and then let's add a disclaimer
> at the bottom."

So, for the chat service:

1. **The cause-and-effect check stops blocking answers.** No code is
   deleted.
2. **The writer's instructions do not change.** `context_brief.py` still
   tells the writer not to make causal claims. Options A, B and C that the
   PM put forward are **withdrawn**.
3. **A fixed caution line is shown at the bottom of every Insight report.**

**What does not change:** D41 as a policy (the writer is still told not to
claim causes; a "why" question still gets the limits stated, not an answer);
the report builds, which keep their own check; the word list itself.

**PM reading of "comment it out" — a switch, set to log.** The operator's
aim is "stop blocking, keep the code". A switch does that, can be reversed
without a code change, and is how the direction check is already built
(`DISCOVERCHAT_DIRECTION_CHECK`, `config.py`). In its `log` setting the scan
still runs quietly and records what it finds, which is the only way to see
whether a different writer model starts making real cause claims (D67). If
the operator wants it literally commented out instead, that is a one-line
change to this section.

## 6.4 T1 — the switch

`DISCOVERCHAT_CAUSAL_CHECK` = `block` | `log` | `off`. **Default `log`.**
Read and validated exactly like `DISCOVERCHAT_DIRECTION_CHECK`.

- **`block`** — today's behaviour, unchanged in every byte.
- **`log`** — the scan runs and its result is kept under the same key, with
  `counts: false`. It does **not** count towards `all_pass`, causes **no**
  retry and **no** fall-back, and adds nothing to the retry reason.
- **`off`** — the scan is not run and its key is absent.

The same mode applies at both places the chat service applies the scan:
`checks.check_citations` (step `3_causal`, the live path) and
`checks.check_prose` (`e_causal`, the path behind `DISCOVERCHAT_CONSOLIDATE=0`).

**Keep a record.** In `log` mode, when the scan finds words in an answer
that is shown, write one line to the existing
`citation_failures.jsonl` log: the question, the turn id, the words found
and the sentences they are in, marked so it cannot be counted as a
fall-back. Add the mode to the settings dump.

**Nothing is deleted or edited in** `DiscoverChat/causal_gate.py` or
`Insights/src/prose_gate.py`.

## 6.5 T2 — the gate and the tests follow the mode

- `causal-gate-catches` stays as it is: the scanner still has to work.
- `causal-scan` and the three live lines that assert `e_causal` pass
  (`gates.py`): they **gate** under `block`; under `log` or `off` they
  **report the count** and do not fail.
- Existing tests that assert a causal sentence is rejected pin `block` and
  keep their assertions.
- New tests:
  - `log`: prose containing "because" and "therefore" gives `all_pass`
    true, with `3_causal` recorded as not passing and `counts` false.
  - `log`: with a stub writer that writes "because", `consolidate` returns
    the narrative on attempt 1 — no second call, no fall-back.
  - `log`: a real failure of another step (an untagged figure) still
    retries and still falls back. Only the causal step is silenced.
  - `off`: the key is absent. An unknown value raises at start-up.

## 6.6 T3 — the caution line (frontend)

**The text, exactly** (the operator asked the PM to phrase it):

> Produced with AI, so it may contain mistakes. It shows patterns in the
> records and cannot tell what caused them. Please check the source records
> before acting.

- **One constant in one place** in the frontend, so the operator can change
  the words by editing one line.
- **Where:** in the report's footer, on its own full-width line directly
  above the "as of … / Copy" row. On every Insight report: with a layout,
  without one, and on a fall-back.
- **Look:** 12px, `report-ink-muted`, plain text. No icon and no box — it
  must not compete with "Needs checking".
- **Mark it `data-report-chrome=""`**, like the hint and the Copy button, so
  the "no layout renders as before" comparison still holds.
- **Copy carries it.** The copied text becomes the question, the answer,
  then the caution line, each separated by a blank line. A pasted answer
  should take its caution with it.

**Tests:** shown on an answer with a layout, on one with `{}`, and on a
fall-back; Copy includes it (update the existing Copy test); no horizontal
scroll at 360px. `npm test` and `npm run build` green; lint with no new
error.

**Screenshots:** Cuttack at desktop width and at 390px.

## 6.7 T4 — measure it live

The 15 WP-D13b questions, today's writer wording, mode `log`, in parallel.
Cap: 45 model calls. Report:

- Answers that lost their narrative, and on which step. **Pass mark: none
  lost to the cause-and-effect step** (today: 2 of 15 on these questions).
- Writer attempts, against 20 in the WP-D13b baseline arm.
- **Every sentence the scan flagged, verbatim**, in one list for the
  operator to read. There is no pass mark on these: the operator's reading
  is now the safeguard.
- Which writer model produced them.

## 6.8 Files, and done when

**In scope:** `DiscoverChat/config.py`, `checks.py` (the two call sites and
`all_pass`), `writer.py` (the log line only), `gates.py` (the checks named
in T2), `DiscoverChat/tests/`;
`frontend/ab-dashboard-main/src/components/insights/ReportFooter.tsx` and
its tests; a "Fix 6" section in `handoffs/WPD13_REPORT.md`.

**Do not touch:** `context_brief.py` (the operator: "keep the context brief
as-is"), `causal_gate.py`, `Insights/**` (the word list and the report
checks), `classifier.py` and the code-written "why" replies.

**Done when:** gate green in `log` and, pinned, in `block`; service tests
green apart from the one old failure (fully green if Fix 1b's T4 has
landed); frontend tests and build green; the two screenshots; the T4
table. One commit per task, no push.

---

# Fix 7 — Display repairs found in the WP-D12 review

**Status: BUILT and ACCEPTED (D70, 2026-11-22). Do not build again.**
Report: `handoffs/WPD12_REPORT.md`, the Fix 7 section. **Decision: D66**
(PM rulings on the WP-D12 report, 2026-11-22). Three small tasks, independent of each other. No model calls.
No prompt change. No corpus rebuild and no re-embedding.

## 7.1 PM rulings on the WP-D12 report

PM replay, 2026-11-22: gate 36/36 green and tests 150 passed with the same
one old failure (Drive copy); frontend tests 146 passed
(`C:\dev\ab-dashboard-odisha`, files identical to the committed ones). All
as reported. Screenshots read against the mock-up.

- **WP-D12 is ACCEPTED.** The layout is drawn by code, costs 1–5 ms, and an
  answer that falls back to bare sentences keeps its cards, charts and
  warning.
- **§6 decisions 1–4 and 6–10 stand as built.** That includes decision 2
  (a time chart with more than 12 periods shows the 12 largest, in time
  order, and says so) and the value in the app's normal sans (§7, DM Sans
  is not loaded upright).
- **§6 decision 5 is changed:** a mixed-sign record raises no warning (T3).
- **§7 "LSDG LSDG theme" and "long underlined phrases break the line" are
  to be fixed** (T1, T2). Both are older than WP-D12, and both are now in
  plain view.

## 7.2 T1 — doubled words in display sentences

**Measured (PM):** 6,656 of 71,183 display sentences carry a doubled word
that the stored sentence does not: "LSDG LSDG" 5,414, "reported reported"
1,240, "calendar calendar" 2. Examples: `d1-00072` ("across 7 LSDG LSDG
theme values"), `d4-00008` ("reported reported households"), `d2-01252`.

**Cause:** the breakdown sentences are stored already in officer words.
`glossary.render` then finds `theme values` inside "LSDG theme values" and
translates it a second time.

**Rule:** a replacement is skipped where the text at that place already
reads as the replacement.

**Tests:**
- Whole corpus: no display sentence has a doubled word (3 or more letters,
  ignoring case) that its stored sentence lacks. 0 of 71,183.
- Whole corpus: the 64,527 other display sentences are byte-identical
  before and after; the 6,656 change only by losing the repeated word.
- No digit changes anywhere (`findings-verbatim` stays green).
- Member labels and scope lines in the layout are unchanged
  (`layout-formatter-parity` stays green).

**In scope:** `DiscoverChat/glossary.py` (`render` only),
`DiscoverChat/tests/`. If a saved frontend fixture carries a doubled word,
recompute it offline and say so.

## 7.3 T2 — cited phrases wrap like ordinary text

**Seen in:** `handoffs/WPD12_shots/3_mostly_patterns.png` (every sentence
starts a new line inside a paragraph) and `8_chikilli_desktop.png`
("…across 6" / "fiscal years; this may reflect…").

**Cause:** in `CitationSpan.tsx` the cited phrase is a `<button>`. A
browser never splits a button across lines, so a long phrase jumps whole
to the next line and leaves a gap.

**Change:** make the trigger an element that wraps like text (for example
a `span` with `role="button"` and `tabIndex={0}`). Keep everything else:
hover and focus open the card; Enter and Space open it; Escape closes it;
the underline shows on hover and focus only; the focus ring.

**Tests:** the existing tests pass (change only what depended on the tag
name); one new test that the keyboard opens the card. `npm test` green,
`npm run build` green, lint with no new error.

**Screenshots:** the same two answers before and after, at desktop width
and at 390px.

**In scope:** `frontend/ab-dashboard-main/src/components/insights/CitationSpan.tsx`
and its tests. Frontend mirror: `C:\dev\ab-dashboard-odisha`.

## 7.4 T3 — no warning from a mixed-sign record

For a record whose parts move both ways, the "not recorded" share is a
share of all the money moving, not of the net, so "They account for 45% of
spending measured against plan" is loose. Cards and charts already skip
these records. Warnings now skip them too (29 records in the corpus).

**Tests:** a mixed-sign record with a large "not recorded" member raises no
warning; the whole-corpus sweep reports how many records lose a warning.
Recompute the `layout` field of the saved fixtures offline and report any
change.

**In scope:** `DiscoverChat/layout.py`, `DiscoverChat/tests/test_layout.py`.

## 7.5 Done when

Gate green; service tests green apart from the one old failure (or fully
green if Fix 1b's T4 has landed); frontend tests and build green; the two
before/after screenshots; a "Fix 7" section added to
`handoffs/WPD12_REPORT.md` with the sweep numbers. One commit per task, no
push.

**Do not touch:** `context_brief.py`, `checks.py`, `writer.py`,
`Insights/**`, any colour value, any component outside `insights/`.

---

# Fix 8 — Move to the new models

**Status: DEFAULTS CHANGED BY THE OPERATOR, by hand, 2026-11-22. Tests ON
HOLD** ("actually hold off on the tests"). Nothing here is for the agent
to build. **Do not run the tests in §8.4 until the operator reopens
them.** **Decision: D69.**

## 8.1 What changed (PM read of the working tree, 2026-11-22 — not committed)

| Job | Before | Now | Where it is set |
|---|---|---|---|
| Writer | `gpt-5.6-sol` | `gpt-6.2-sol` | `Insights/src/discover_config.py` line 29 — `DISCOVER_PROSE_MODEL` (the chat writer borrows it at `DiscoverChat/config.py` `WRITER_MODEL`) |
| Judge | `gpt-5.6-sol` | `gpt-6.2-sol` | `DiscoverChat/config.py` line 156 — `DISCOVERCHAT_JUDGE_MODEL` |
| Classifier | `gpt-5.4-nano` | `gpt-6-luna` | `DiscoverChat/config.py` line 147 — `DISCOVERCHAT_CLASSIFIER_MODEL` |
| Chat verifier | `gpt-5.6-luna` | `gpt-6-luna` | `DiscoverChat/config.py` line 96 — `DISCOVERCHAT_VERIFIER_MODEL` |

Not changed: the feed build's verifier (`Insights/src/insight_prose_config.py`,
still `gpt-5.6-luna`), the search embeddings, and Ask.

One comment also changed: `config.py` line 142, the note on how to put the
classifier back, now names `gpt-6.2-sol` where it named `gpt-5.5`. It has
no effect. The classifier it replaced was `gpt-5.4-nano`.

**What follows from the change, before any test is run:**

- The stored evidence is for the old models: the judge's on `gpt-5.6-sol`
  (2026-09-04), the classifier's on `gpt-5.4-nano` (2026-09-03). So the
  gate checks `judge-model-evidenced` and `classifier-model-evidenced` are
  red until §8.4 is run. The standing rules above tell the agent to leave
  them.
- The next build of the feed or the editions will be written by
  `gpt-6.2-sol`.
- A running service keeps the old models until it is restarted. Production
  does not change until this is committed, pushed and deployed, and a
  Railway variable, if one is set, still wins over the default.
## 8.2 Open points for the operator (PM, from reading the code — nothing run)

1. **Both ids are valid** — confirmed by the operator, 2026-11-22
   (`gpt-6.2-sol` and `gpt-6-luna`, version numbers as written).
2. **The writer setting is shared with the report writers.** Changing
   `DISCOVER_PROSE_MODEL` also changes who writes the feed and the editions
   at their next build. The chat writer has no setting of its own.
3. **There are two verifiers.** The chat one is not used on the live answer
   path (gate `inline-verifier-off`), so changing it changes no answer
   today. The feed build has its own: `Insights/src/insight_prose_config.py`
   — `DISCOVER_VERIFIER_MODEL`. Which one is meant?
4. **The gate is tied to the models the evidence was measured on.**
   `judge-model-evidenced` **fails** when the judge id differs from the one
   in `experiments/judge_arm_results.json`: the "never answers an
   out-of-scope question" result (0.0% over the recorded runs) belongs to
   one judge model. `classifier-model-evidenced` does the same for the
   classifier. So changing the defaults before the tests makes the gate red
   by design, and Fixes 1b, 6 and 7 all need a green gate.
5. **The answer budgets were sized on the old models** (writer D17 budget,
   judge 12,000, classifier 2,000, verifier 9,000). A model that thinks
   longer can spend the whole budget and return nothing, with no error;
   that has happened twice in this project.
6. **The classifier moves from a nano to a full-size model.** It was put on
   a nano on 2026-09-03 for cost and to take about 3 seconds off a turn.
7. **Model settings are read when the service starts, before any `.env`
   file is loaded.** A model name placed in `Insights/.env` has no effect on
   the chat service. It has to be set in the shell that starts the service,
   or in Railway's Variables.

## 8.3 PM recommendation

The PM advised trying the models by environment variable first. The
operator chose to change the defaults. What is left of the advice:

- **Run §8.4 before this reaches officers.** Until then nothing shows
  that the new judge still declines a question the findings cannot
  answer, or that the new models fit inside the answer budgets.
- **Commit the two files before the agent starts**, so it works from a
  clean tree.
## 8.4 The tests, for when the operator reopens this (not READY)

All with the new ids set by environment variable, in parallel:

- One small call to each id (both confirmed valid by the operator).
- `experiments/run_judge_arm.py` — the out-of-scope evidence, on the new
  judge. Pass mark as before: no out-of-scope question answered.
- `experiments/run_classifier_nano.py --repeats 4` — the routing evidence,
  on the new classifier. No empty and no unreadable reply.
- A budget check per job: tokens spent on thinking against each ceiling.
- The 15 WP-D13b questions end to end, old models against new on the same
  findings: answers lost and on which step, attempts, seconds and cost per
  answer, and five answers side by side for the operator to read.
- **Fix 6's live run, repeated on the chosen writer** (added 2026-11-22,
  D70). It was run on `gpt-5.6-sol`. No code change is needed:
  `DISCOVER_PROSE_MODEL=<id> python DiscoverChat/experiments/run_causal_log_trial.py`
  (about 16 to 20 writer calls). Report answers lost and on which step,
  and list every sentence the scan flags, as before.
- **Count advice wording on each writer** (added 2026-11-22, D70):
  sentences in the shown answer with "should", "must", "needs to" or
  "recommend…". On `gpt-5.6-sol` it is 7 of 15 answers with the
  cause-and-effect check in `log`, against 1 of 15 when it blocked.
- Then the headline trial is re-run on the chosen writer (D67).

---

# Fix 9 — Small repairs from the review of Fixes 1b, 6 and 7

**Status: BUILT and ACCEPTED (D71, 2026-11-23). Do not build again.**
Report: `handoffs/WPD13_REPORT.md`, the Fix 9 section. One thing left as
found: `experiments/run_direction_trial.py` still costs a model with no
price at $0. It is not on the Fix 8 test list; repair it the same way
before it is next run on a new model.
**Decision: D70** (PM review, 2026-11-22). No
model call. No prompt change. No frontend change. Four small tasks,
independent of each other. (A fifth, adding word forms to the wrong-word
list, was dropped by the operator on 2026-11-23.)

## 9.1 T1 — the wrong-word rule gets the exception the "above plan" rule has

**The problem** (your own note, Fix 1b report §7). R3 lets a sentence say
"above plan" when a figure the stored sentence shows as positive money is
also bound in it. R1′ has no such exception. So a true sentence about a
record whose parts move both ways fails if it uses a list word for the
positive part:

> One focus area exceeded its sanction by Rs 1.73 lakh, while Sanitation
> was Rs 1.33 crore below sanction.

The check now blocks, so this costs a retry. It touches the 281 mixed-sign
records only.

**The change.** In `checks.check_direction`, an R1′ word does not fail a
sentence that meets the condition R3 already uses (`positive_bound`). Use
the same condition; do not write a second one. Update the comment block
beside the rule, which says "No exception".

**Tests.**
- The sentence above, on a mixed-sign record with both figures bound,
  passes.
- The same words with no positive figure bound still fail on R1′.
- "Spending exceeded the plan by Rs 51.96 crore" still fails.
- The five sentences and the 77-attempt replay are unchanged: 0 failures.

**The word list itself does not change.** The PM proposed adding three
forms (`overspends`, `overruns`, `overrunning`); the operator dropped that
on 2026-11-23. `OPPOSITE_DIRECTION_WORDS` stays exactly as built.

## 9.2 T2 — one comment in `writer.py` is out of date

The D7.3 note says the citation check is "Blocking, all four". Step 3 now
blocks only under `DISCOVERCHAT_CAUSAL_CHECK=block`. Correct the comment.
No code change.

## 9.3 T3 — two experiment scripts break when the check is `off`

`experiments/run_answer_compare.py` and `experiments/measure_prose.py` read
the causal result by its key (`3_causal`, `e_causal`). Under `off` the key
is absent and they stop with a KeyError. Read it safely and record "not
run". Nothing changes under `block` or `log`.

## 9.4 T4 — a trial must not report a cost of $0 for a model it has no price for

`experiments/run_causal_log_trial.py` holds a price for `gpt-5.6-sol`
only, and shows $0 for any other model (your note, Fix 6 report §7). The
same is likely true of the other trial scripts that price calls.

- For a model with no price on file: report the tokens, and print
  "price not set for <id>" in place of a cost. Never $0.
- **Do not put in a price for `gpt-6.2-sol` or `gpt-6-luna`.** The
  operator supplies those.
- If the trial scripts share one price table, fix it there. If each has
  its own, fix `run_causal_log_trial.py` and `run_headline_trial.py`, and
  list any others in the report without changing them.

## 9.5 Files, and done when

**In scope:** `DiscoverChat/checks.py` (the direction step only),
`DiscoverChat/writer.py` (the one comment), the experiment scripts named
above, `DiscoverChat/tests/`; a "Fix 9" section in
`handoffs/WPD13_REPORT.md`.

**Do not touch:** `context_brief.py`, `causal_gate.py`, `Insights/**`,
`frontend/**`, and the model settings (see the standing rules).

**Done when:** the gate is green apart from the two model-evidence checks
(standing rules); service tests green; no model call made. One commit per
task, no push.

---

# Fix 10 — Download the report as a PDF; the Copy button goes

**Status: READY.** **Decision: D72** (operator, 2026-11-23):

> "add a button to pdf download any report generated" · "drop the 'copy'
> button" · "I just want a pdf download of the report as-is - no further
> processing/thinking"

Frontend only. **No service change, no model call, no new npm package.**
The PDF is the report that is already on the screen, made by the browser.
Nothing is sent anywhere and nothing is written again.

This reverses "No Download" in WP-D12 ruling 4 and replaces the Copy button
that ruling added. The Copy rules in §6.6 no longer apply; the caution line
itself stays.

## 10.1 What the officer gets

- A **"Download PDF"** button in the report's footer, in the place the Copy
  button has today: same size, same style, a download icon. Mark it
  `data-report-chrome=""` as Copy was.
- It shows **wherever Copy shows today**: on every finished report, with a
  layout, without one, and on a fall-back.
- Clicking it opens **the browser's own print box**, where the report is
  saved as a PDF. Use `window.print()` with a print stylesheet. Do not add a
  PDF library and do not call the service.

## 10.2 What the PDF holds: the report as it is, nothing added

Everything inside the report card, in the order it is on screen: the
"Insight report" label, the question, the caption, the cards, the prose
with its charts, the "Needs checking" box, the caution line, the run stamp.
The same words, numbers, colours and order.

**Add nothing.** No sources list, no reference numbers, no extra header, no
date line, no summary.

**Leave out the controls only:** the dismiss button, the Download button,
the "point at / tap any number" hint, any open hover box, and the "Put this
question to Ask" button. "Open record" links stay, as links.

**Nothing else on the page prints:** no navigation, no question box, no
feed below the report.

## 10.3 What the print layout must get right

- **The whole report prints, however long.** The page scrolls inside
  fixed-height boxes (`h-screen overflow-hidden` in `pages/Index.tsx`,
  `overflow-y-auto` in `AnomaliesView.tsx`). Left as they are, the PDF stops
  after one page. Release them for print.
- **It starts at the top of page 1.** No blank first page, no empty space
  where the hidden parts were.
- **A4 portrait**, margins about 15 mm, the report filling the width.
- **Colours print.** The bars, card tints and the warning box are
  background colours, which browsers drop from print by default
  (`print-color-adjust: exact`).
- **Nothing is cut in half:** no page break inside a card, a chart or a
  warning item.
- **The suggested file name** is
  `Insight report - <the question, first 60 characters, file-safe> - YYYY-MM-DD`.
  Browsers take it from the page title: set it for the print and put the
  old title back afterwards.
- **Printing anywhere else is unchanged.** The print rules apply only
  while a report is being downloaded, so Ctrl+P on the Ask page or on the
  feed behaves as it does today.
- **The screen is unchanged** apart from the button swap.

## 10.4 The Copy button is removed

Remove the button, the clipboard code and its timer from
`ReportFooter.tsx`, and replace the Copy tests. Update the comments that
describe Copy (the footer's own, and the one in `ReportLayout.test.tsx`).
The caution line and the stamp stay where they are.

## 10.5 Tests and evidence

- **Unit tests:** the button is there on a report with a layout, with `{}`
  and on a fall-back; there is no Copy button and the clipboard is never
  touched; a click calls `window.print` once, sets the file-name title, and
  restores the old title after printing.
- **Three real PDFs**, made with Playwright (already a dev dependency) from
  the built page: Cuttack with a layout; a fall-back answer; one report
  long enough to run past one page. Save them in
  `handoffs/WPD13_fix10_pdf/`. For each, state the page count and confirm:
  only the report, colours present, nothing cut in half, nothing added.
- **At 390px wide:** the button fits and there is no sideways scroll.
- `npm test` and `npm run build` green; lint with no new error.

## 10.6 Files, and done when

**In scope:** in `frontend/ab-dashboard-main/src/`:
`components/insights/ReportFooter.tsx`, `InsightReport.tsx` (print markers
only), `AnomaliesView.tsx` and `pages/Index.tsx` (only if a print marker is
needed there), `index.css` (the print rules), and the tests beside them; a
"Fix 10" section in `handoffs/WPD13_REPORT.md`.

**Do not touch:** `DiscoverChat/**`, `Insights/**`, the Ask page's
behaviour, `package.json` dependencies, and the model settings (see the
standing rules). The standing rule about gate and service baselines does not
apply: this fix changes no service code. Record the frontend baseline
instead (`npm test` count before you start).

**Done when:** the tests and build are green; the three PDFs are in the
folder with their checks; the report says what the print box shows in
Chrome and in Edge, and what happens in a phone-sized window. **A real
phone is not tested: say so.** One commit per task, no push.

---

# Queued (not briefed — do not build)

- **Fix 3 — remaining jargon.** The word list comes from the operator's
  marks on the WP-D13b review sheet. Likely a display-time vocabulary change in
  the same place as Fix 1.
- **Fix 4 — show the rows. PARKED.** Each warning keeps its "Open record"
  link (WP-D12) and nothing more. Notes for if it is reopened: the PM leaning
  was for Discover to serve the rows from the view files the insights were
  built from, so the count matches the card by construction; open questions
  were whether those files may ship with the service, which columns to show,
  and whether a row carries an identifier an officer can act on.
- **Fix 5 — download.** The report as a PDF is now Fix 10 (READY). The
  rows as a spreadsheet stay **PARKED**.

Parked means: not to be built or designed for until the operator reopens it.
