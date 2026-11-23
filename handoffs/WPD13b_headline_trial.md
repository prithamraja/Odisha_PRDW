# WP-D13b brief — short answer and section headlines: a TRIAL the operator validates

**Workstream:** Discover. **Nature: TRIAL — a review sheet, no live change.**
**Authored:** PM, 2026-11-21. **Decision: D64.** **For:** the
operator-controlled coding agent — the same one running WP-D13 Fix 1.

> **Status, 2026-11-22 (D67): trial run and reported; the operator's review is
> ON HOLD.** The operator is going to try other writer models, and the
> headlines depend on the model. `REVIEW_SHEET.md` holds `gpt-5.6-sol`
> output and is not to be marked. Once the writer model is chosen, re-run
> `DiscoverChat/experiments/run_headline_trial.py` on that model (the first
> run cost $2.08 for 52 calls) and mark the new sheet. Nothing here goes
> live before that.

This was "Fix 2" in `handoffs/WPD13_report_fixes.md`; it was moved here
unchanged so it can be handed over on its own. Fix 1 stays in that file.

The Insight report has no headline and no summary: an officer reads four
dense paragraphs to find the point. This trial asks the writer, in its one
existing request, to open with a short answer and to head each section with a
one-line headline — and puts the results in front of the operator, who marks
every one before anything goes live.

**Status: READY.** The operator approved the wording in §2 and the pass marks
in §5, unchanged, on 2026-11-21 — before any trial answer existed.

## When to start

Once **WP-D13 Fix 1's T1 and T2 are green**, so the writer is handed
direction in words ("Rs 51.96 crore below plan"). Fix 1's STOP in its §1.5
is about not loosening its own rule and does not hold this trial up: run it
with whichever direction mode Fix 1 shipped, and say which in the report.

Work in the **same mirror** as Fix 1 (`C:\dev\odisha-d13`). Do not re-mirror
over uncommitted Fix 1 work.

## Standing rules

- **Design around mid-size models** (D62 ruling 7). Never fix a failure by
  proposing a bigger model.
- **Nothing the live service imports is edited.** This trial is an
  experiment script and its output. If it seems to need a change to a live
  file, STOP and say why.
- **No corpus rebuild, no re-embedding.**
- **Prose length stays as it is** (operator, 2026-11-21). Do not add a
  length rule or ask for shorter paragraphs.
- Run live turns in parallel. Log every model call and its cost.
- Unrelated dirty paths (`Ask/bench/**`, root `prdw-*.html`) are not yours.
- Commit per task on the current branch (`WP-D13b T<n>: …`). No push.
- A thing in this brief that turns out wrong is logged in the report and
  left — not worked around.

---

## 1. Operator rulings (2026-11-21)

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

## 2. The added wording (operator-approved — use it verbatim)

Added to the consolidating writer's task, immediately before its last line
("Return only the finished prose."), **in the experiment script only** —
`context_brief.py` and `writer.py` are not edited. The script builds its own
prompt from the existing pieces and may copy the two-attempt loop from
`writer.consolidate`; say in the script that it is a copy.

> Begin with a short answer: one or two sentences giving the most important
> facts for this question, on a line starting "SHORT ANSWER:". Then write the
> narrative in short sections. Start each section with a one-line headline
> that states that section's main fact in plain words, on a line starting
> "## ". The short answer and the headlines follow the same rules as the
> rest: tag every figure, state facts only, and give no advice.

Parsing is forgiving: an answer with no "SHORT ANSWER:" line or no "## "
lines is not a failure — it is today's prose, shown as today.

## 3. Checks in the trial

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
- **Reported, not blocking:** a short answer over two sentences; a headline
  over 14 words; advice wording in the model's text ("should", "must",
  "needs to", "recommend", an imperative opening). Count them; the operator
  decides later whether any becomes a check.

## 4. The code-written suggestion (ruling 3)

One rule in this trial, as a pure function over the cited records:

- **Trigger:** a cited decomposition whose "not recorded" member holds
  **50% or more** of a measure.
- **Text (fixed):** "Suggested first step: {rows} rows have no {dimension
  phrase} on file and account for {share} of {measure phrase}. Check those
  records before drawing conclusions from this figure."
- At most one per answer — the largest share. Every figure in it comes from
  the record through the corpus formatter (`format_measure`, one-decimal
  percent), with the direction in words from Fix 1's helper.

## 5. The review sheet and the pass marks

Fifteen questions — the ones recorded in
`DiscoverChat/experiments/answer_compare.json`. For each, retrieval and the
judge once, then two writer arms on the same findings: today's task
(baseline) and the added wording. In parallel. Cap: 90 model calls in total.

Output in `handoffs/WPD13b_headline_trial/`: `trial_results.json` and
`REVIEW_SHEET.md`. The sheet opens with a summary table, then one block per
question: the question; the short answer; each headline above its paragraph;
the suggestion with the figures that triggered it; the check results. Under
every short answer and headline: `[ ] correct  [ ] misleading  [ ] wrong`
and a comment line. Under every suggestion: `[ ] warranted  [ ] not`. At the
end of every block, one line: `Words an officer would not understand:` — the
operator's answers there are the word list WP-D13 Fix 3 is waiting for, so
one reading of the sheet serves both.

Write the sheet in plain English. The operator is the reader.

**Pass marks (operator-approved 2026-11-21, fixed before any answer was
read):**

| Measure | Pass |
|---|---|
| Fall-backs with the added wording | no more than 2 of 15 above the baseline arm |
| Answers with a short answer and at least one headline | 12 of 15 or more |
| Operator marks "wrong" | none |
| Operator marks "misleading" | no more than 1 in 10 items |
| Suggestions marked "not warranted" | none |

The PM writes the production brief only after the operator has marked the
sheet.

## 6. Files, done-when, report

**In scope:** `DiscoverChat/experiments/run_headline_trial.py` (new),
`handoffs/WPD13b_headline_trial/**` (new), `handoffs/WPD13b_REPORT.md`.

**Do not touch:** anything the live service imports — `context_brief.py`,
`writer.py`, `checks.py`, `assemble.py`, `main.py`, `config.py`,
`glossary.py` — beyond what Fix 1 is already changing under its own brief;
`frontend/**`; `Insights/**`; `handoffs/PROJECT_PLAN.md`; the two brief
files.

**Done when:** both arms have run for all 15 questions; the review sheet and
the JSON are written; the first two pass marks (fall-backs, structure
present) are computed and stated; the sheet is ready for the operator with
nothing pre-ticked.

**Report** (`handoffs/WPD13b_REPORT.md`): the direction mode Fix 1 shipped;
the two computed pass marks; per question, attempts and the check that
failed in each arm; the counts of over-long short answers, over-long
headlines and advice wording; how many answers triggered the suggestion and
on which record; model calls and cost. Do not offer a view on whether the
headlines are good — that is the operator's mark to make.
