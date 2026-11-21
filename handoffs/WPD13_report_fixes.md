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
| 1 | Direction in words: "Rs 3.18 crore below plan", and a check that catches a reversed direction | **READY** |
| 2 | Short answer and section headlines — TRIAL with an operator review sheet | **READY** — start once Fix 1's T1 and T2 are green (wording and pass marks approved by the operator, 2026-11-21) |
| 3 | Plain words for remaining jargon ("costless", "linked share", …) | QUEUED — the operator marks the words on the Fix 2 review sheet (agreed 2026-11-21) |
| 4 | "Show the rows" behind a warning | **PARKED** by the operator, 2026-11-21: "let's park that" |
| 5 | Download (report as PDF, rows as a spreadsheet) | **PARKED** by the operator, 2026-11-21: "ignore the download function for now" |

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
- Run live turns in parallel. Log every model call you make and its cost.
- Unrelated dirty paths (`Ask/bench/**`, root `prdw-*.html`) are not yours.
- Commit per task on the current branch (`WP-D13 F<fix> T<n>: …`). No push.
- A thing in a brief that turns out wrong is logged in the report and left —
  not worked around.

---

# Fix 1 — Direction in words, and a check that catches a reversed direction

**Status: READY.** **Decision: D63** (operator, 2026-11-21: "ok let's fix
this").

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

# Fix 2 — Short answer and section headlines: a TRIAL the operator validates

**Status: READY.** The operator approved the wording in §2.2 and the pass
marks in §2.5, unchanged, on 2026-11-21. **Decision: D64.** Start once Fix
1's T1 and T2 are green, so the writer is handed direction in words; Fix 1's
STOP in §1.5 is about not loosening its rule and does not hold this fix up —
run the trial with whichever direction mode Fix 1 shipped, and say which.
**Nothing in the live service changes in this fix**: it produces a review
sheet, in the manner of WP-D4.

## 2.1 Operator rulings (2026-11-21)

1. **The failure process stays as it is.** One writer request, two attempts,
   then the bare sentences. No separate request or separate fallback for
   headlines: "it has worked ok so far and we can handle it in the future."
2. **Facts, largely.** The model states facts and gives no advice.
3. **Advice only where the evidence is strong** — "fix the records first"
   being the example. The PM's mechanism: **code decides and code writes it.**
   A rule fires on stored figures and adds a fixed sentence, shown apart from
   the model's text and labelled as a suggestion. The model is never asked
   to judge when advice is warranted.
4. **The operator validates** every short answer, headline and suggestion on
   a review sheet before anything goes live.

## 2.2 The added wording (operator-approved 2026-11-21 — use it verbatim)

Added to the consolidating writer's task, immediately before its last line
("Return only the finished prose."), **in the experiment script only** —
`context_brief.py` and `writer.py` are not edited in this fix. The script
builds its own prompt from the existing pieces and may copy the two-attempt
loop from `writer.consolidate`; say in the script that it is a copy.

> Begin with a short answer: one or two sentences giving the most important
> facts for this question, on a line starting "SHORT ANSWER:". Then write the
> narrative in short sections. Start each section with a one-line headline
> that states that section's main fact in plain words, on a line starting
> "## ". The short answer and the headlines follow the same rules as the
> rest: tag every figure, state facts only, and give no advice.

Parsing is forgiving: an answer with no "SHORT ANSWER:" line or no "## "
lines is not a failure — it is today's prose, shown as today.

## 2.3 Checks in the trial

- The whole output — short answer, headlines, paragraphs — goes through
  `check_citations` unchanged, including Fix 1's direction step. That is the
  pass/fail that drives the retry and the fall-back, exactly as today.
- **Each headline and the short answer is also checked on its own**, because
  a headline has no full stop and the sentence split may otherwise join it
  to the paragraph below and let that paragraph's tag cover it. Run steps 1,
  2, 3 and 5 on each one alone: a figure in a headline must be tagged in
  that headline. A failure here counts as a failed attempt.
- Strip the "SHORT ANSWER:" and "## " markers before checking, so they are
  never read as content. Tags are stripped on the review sheet.
- **Reported, not blocking:** short answer over two sentences; a headline
  over 14 words; advice wording in the model's text ("should", "must",
  "needs to", "recommend", an imperative opening). Count them; the operator
  decides later whether any becomes a check.

## 2.4 The code-written suggestion (ruling 3)

One rule in this trial, as a pure function over the cited records:

- **Trigger:** a cited decomposition whose "not recorded" member holds
  **50% or more** of a measure.
- **Text (fixed):** "Suggested first step: {rows} rows have no {dimension
  phrase} on file and account for {share} of {measure phrase}. Check those
  records before drawing conclusions from this figure."
- At most one per answer — the largest share. Every figure in it comes from
  the record through the corpus formatter.

## 2.5 The review sheet and the pass marks

Fifteen questions — the ones recorded in
`DiscoverChat/experiments/answer_compare.json`. For each, retrieval and the
judge once, then two writer arms on the same findings: today's task
(baseline) and the added wording. In parallel. Cap: 90 model calls in total.

Output in `handoffs/WPD13_headline_trial/`: `trial_results.json` and
`REVIEW_SHEET.md`. The sheet opens with a summary table, then one block per
question: the question; the short answer; each headline above its paragraph;
the suggestion with the figures that triggered it; the check results. Under
every short answer and headline: `[ ] correct  [ ] misleading  [ ] wrong`
and a comment line. Under every suggestion: `[ ] warranted  [ ] not`. At the
end of every block, one line: `Words an officer would not understand:` — the
operator's answers there are the word list Fix 3 is waiting for, so one
reading of the sheet serves both fixes.

**Pass marks (operator-approved 2026-11-21, fixed before any answer was
read):**

| Measure | Pass |
|---|---|
| Fall-backs with the candidate wording | no more than 2 of 15 above the baseline arm |
| Answers with a short answer and at least one headline | 12 of 15 or more |
| Operator marks "wrong" | none |
| Operator marks "misleading" | no more than 1 in 10 items |
| Suggestions marked "not warranted" | none |

The PM writes the production brief only after the operator has marked the
sheet.

## 2.6 Files, done-when, report

**In scope:** `DiscoverChat/experiments/run_headline_trial.py` (new),
`handoffs/WPD13_headline_trial/**` (new), `handoffs/WPD13_REPORT.md`.

**Do not touch:** anything the live service imports — `context_brief.py`,
`writer.py`, `checks.py`, `assemble.py`, `main.py`, `config.py` — and
`frontend/**`. If the trial seems to need a change to one of them, STOP and
say why.

**Done when:** both arms have run for all 15 questions; the review sheet and
the JSON are written; the first two pass marks (fall-backs, structure
present) are computed and stated; the sheet is ready for the operator with
nothing pre-ticked.

**Report:** the two computed pass marks; per question, attempts and the
check that failed in each arm; the counts of over-long short answers,
over-long headlines and advice wording; how many answers triggered the
suggestion and on which record; model calls and cost. Do not offer a view on
whether the headlines are good — that is the operator's mark to make.

---

# Queued (not briefed — do not build)

- **Fix 3 — remaining jargon.** The word list comes from the operator's
  marks on the Fix 2 review sheet. Likely a display-time vocabulary change in
  the same place as Fix 1.
- **Fix 4 — show the rows. PARKED.** Each warning keeps its "Open record"
  link (WP-D12) and nothing more. Notes for if it is reopened: the PM leaning
  was for Discover to serve the rows from the view files the insights were
  built from, so the count matches the card by construction; open questions
  were whether those files may ship with the service, which columns to show,
  and whether a row carries an identifier an officer can act on.
- **Fix 5 — download. PARKED.**

Parked means: not to be built or designed for until the operator reopens it.
