# WP-D13b report — short answer and section headlines (trial)

**For:** the PM and the operator. **Executed:** 2026-11-21, mirror
`C:\dev\odisha-d13`, after WP-D13 Fix 1 T1 and T2 were green.
**Nothing live changed.** The review sheet is ready to mark:
`handoffs/WPD13b_headline_trial/REVIEW_SHEET.md` (nothing pre-ticked).

## 1. Direction mode

Fix 1 shipped **`log`** (see `handoffs/WPD13_REPORT.md` §5: under `block`,
2 of 12 answers fell back on false alarms, over the limit of 1). The trial ran
with `DISCOVERCHAT_DIRECTION_CHECK=log`: the direction step is recorded but does
not cause a retry or a fall-back. The writer was handed the Fix 1 display
sentences ("Rs 51.96 crore below plan") in both arms.

## 2. The two pass marks the code computes

| Measure | Result | Pass mark | |
|---|---|---|---|
| Fall-backs with the new wording vs today's writer | **1** of 15 vs **2** of 15 | no more than 2 above | **PASS** |
| Answers with a short answer and at least one headline | **14** of 15 | 12 or more | **PASS** |

The other three marks (no *wrong*, at most 1 in 10 *misleading*, no
suggestion *not warranted*) wait on the operator's reading. The sheet has
**52 items to mark** (14 short answers, 38 headlines) and **1 suggestion**.

## 3. Per question: attempts and the check that failed

Step names: 2 = a figure not tagged with, or not found in, the finding it
cites; 3 = cause-and-effect wording; 4 = a finding left out. "headline:" or
"short answer:" means the item failed when checked on its own.

| # | Question | Findings | Today: attempts (failed on) | New wording: attempts (failed on) | Short answer / headlines |
|---|---|---|---|---|---|
| 1 | Is spending on track? | 5 | 2 (3; pass) | 1 (pass) | yes / 3 |
| 2 | How is Chikilli doing? | 12 | 2 (3; 3) — **fell back** | 1 (pass) | yes / 5 |
| 3 | Where is money planned but not spent? | 12 | 1 (pass) | 1 (pass) | yes / 4 |
| 4 | How is Barpali block doing? | 12 | 2 (4; pass) | 1 (pass) | yes / 4 |
| 5 | Which places are behaving differently from the rest? | 12 | 1 (pass) | 1 (pass) | yes / 3 |
| 6 | Which blocks account for the shortfall? | 1 | 1 (pass) | 1 (pass) | yes / 2 |
| 7 | Where does the gap sit? | 1 | 1 (pass) | 1 (pass) | yes / 2 |
| 8 | Break down spending by block | 1 | 1 (pass) | 1 (pass) | yes / 2 |
| 9 | How is the total split across districts? | 1 | 1 (pass) | 1 (pass) | yes / 2 |
| 10 | Who is driving the shortfall? | 1 | 2 (3; 3) — **fell back** | 2 (3 + short answer: 3; pass) | yes / 1 |
| 11 | How is tied grant planned split across fiscal years? | 1 | 2 (2; pass) | 1 (pass) | yes / 1 |
| 12 | Break it down by fiscal year | 1 | 1 (pass) | 1 (pass) | yes / 1 |
| 13 | Tell me about untied grants. | 9 | 1 (pass) | 2 (headline: 2; 2 + headline: 2 ×2) — **fell back** | no / 0 |
| 14 | Anything I should be looking at in Ganjam? | 8 | 1 (pass) | 1 (pass) | yes / 5 |
| 15 | What is the position on abandoned works? | 7 | 1 (pass) | 1 (pass) | yes / 3 |

Writer attempts: today 20, new wording 17.

## 4. Reported, not blocking

| | Count |
|---|---|
| Short answers over two sentences | 0 |
| Headlines over 14 words | 5 (Q4 ×3, Q10, Q14) |
| Advice wording in the model's text ("should", "must", "needs to", "recommend…", an imperative opening) | **0** with the new wording; 2 sentences in today's writer |
| Direction step (log only) failing on the whole answer | 4 attempts (Q1, Q3, Q10, Q14) — none caused a retry |

Headlines over 14 words, verbatim:
- Q4: "Activities are evenly divided between the two Gram Panchayats, while Bandhpali has a larger share of planned cost."
- Q4: "The spending shortfall against plan is concentrated in Bandhpali, and many activities lack recorded costs or sanctions."
- Q4: "General-component spending is spread across 7 LSDG themes, led by village infrastructure and water sufficiency."
- Q10: "The spending gap is spread across the sample, rather than concentrated in one Gram Panchayat."
- Q14: "Many activities have no planned cost, and sanction records cover about one in six activities"

## 5. The code-written suggestion

**1 of 15 answers triggered it:** Q13 "Tell me about untied grants.", on
record `d1-36910`. Within output type Code 101, the 2,309 rows with no
sanctioning authority hold 70.4% of untied grant planned (Rs 24.89 crore of
Rs 35.37 crore). The text:

> Suggested first step: 2,309 rows have no sanctioning authority on file and
> account for 70.4% of untied grant planned. Check those records before
> drawing conclusions from this figure.

Q13 is also the one answer that fell back with the new wording. The sheet
still shows the suggestion for marking, because it is code-written and does
not depend on the model's text.

## 6. Model calls and cost

| | Calls | Cost |
|---|---|---|
| Judge | 15 | |
| Writer (today 20, new wording 17) | 37 | |
| **Total** (gpt-5.6-sol, $4 / $20 per 1M tokens in / out) | **52** (cap 90) | **$2.08** |
| Query embeddings (OpenRouter) | 15 | under $0.01 |

The sol price is the promotional one, recorded as running "through at least
2026-11-21", the day of this run. Per-call detail is in
`trial_results.json` → `calls.log`.

## 7. Things found, logged and left

- **"Code 101" counts as a figure in a headline.** Q13's only fall-back with
  the new wording comes from this. Its headlines name the category "Code 101"
  with no tag, and the per-headline check (§3 of the brief: "a figure in a
  headline must be tagged in that headline") reads "101" as an untagged
  figure. On attempt 2 the same untagged headline was also joined by the
  sentence split to the paragraph below. That paragraph's finding
  (`1-01793`) does not contain "101", so the whole-answer check failed too.
  The check is doing what it says; a category code with digits is the edge.
  Not worked around.
- **The whole-answer check alone would have let an untagged headline
  through.** This was confirmed offline before the run: a headline with an
  untagged figure is joined to the tagged sentence below it and passes. The
  per-item check catches it, as the brief intended.
- **§4 of the brief was ambiguous on one point.** It asks for the
  suggestion's figures "with the direction in words from Fix 1's helper", but
  the fixed text has no money figure, only rows and a share. I kept the text
  exactly as approved. The amount behind it (via `format_measure`, with
  direction in words when the measure is signed) is shown on the sheet's
  "Triggered by" line instead.
- **The judge kept exactly one finding for 7 of the 15 questions** (Q6–Q12,
  the "break it down" questions). Those answers have 1–2 headlines. Stated as
  a fact about the retrieval step, which this trial does not change.
- Today's writer's prose is not on the sheet, to keep the reading to what is
  being marked. It is in `trial_results.json` under each question's
  `baseline`.

## 8. Commits (current branch, not pushed)

| Commit | Task |
|---|---|
| `f8d62ac` | T1: the trial script (+ the brief) |
| T2 commit | T2: the trial run — `trial_results.json`, `REVIEW_SHEET.md` — and this report |
