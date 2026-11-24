# WP-D15c brief — four small changes after the WP-D15 review

**Workstream:** Discover. **Nature: BUILD, then a short live check** (writer
calls only, on the held judge picks). **Authored:** PM, 2026-11-24.
**Decisions:** D81 (the review), D82 (the operator's three rulings).
**For:** the operator-controlled implementation agent.
**Comes after:** WP-D15, executed and accepted (D81). **Comes before:**
WP-D15b (spelling), which edits some of the same files.
**Read `handoffs/WPD15_REPORT.md` first.**

## What this package does

| # | Change | Why |
|---|---|---|
| 1 | The writer may leave an insight out. An answer is no longer refused for it. | R25 |
| 2 | The line "More than 8 findings clear the relevance bar …" is not printed on an answer that used a profile sheet. | R26 |
| 3 | The note "This answer is about … For the …, ask about …" is not printed when the officer's own words named the level. | R27 |
| 4 | The standing check (step 6) stops refusing correct sentences. It stays on `log`. | PM decision, D81 |

Nothing else. The writer's prompt is not edited.

## The rulings (operator, 2026-11-24, D82)

| # | Question | Ruling |
|---|---|---|
| R25 | Must the writer mention every insight the judge picked? | **No, for every answer**, place or no place. The operator was told the cost: an insight left out is not shown anywhere on the present page. |
| R26 | The closing line "More than 8 findings clear the relevance bar for this question; these are the 8 closest to what you asked." | **Not on place answers.** |
| R27 | The R4 note when the officer already wrote "GP" or "block" | **No note.** It stays for a bare name ("Kalimela"). |

Standing rulings that apply: R19 and the operator's pattern behind it (the
model chooses what to say; code guards the numbers). So R25 is done in the
check, not by a new instruction to the writer, and there is **no floor** on
how many insights an answer must use.

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d15-pm`, tree `a3b81f5`)

| Fact | Where |
|---|---|
| Step 4 of the citation check: every insight handed must be cited, else the draft is refused. Place facts are already exempt. Its result is `{"pass", "dropped", "of"}`. | `DiscoverChat/checks.py:529-534` |
| A refused draft is retried once with a reason. For step 4 the reason ends "Every finding supplied belongs in the answer." | `checks.citation_failure_reason`, lines 586-589 |
| Other steps already have a mode (`block` / `log` / `off`) and a `counts` flag that `all_pass` respects. | `checks.py` (`_counts`), `config.py:348-438` |
| The trial switched step 4 off by wrapping the check, for the test process only. The service has no setting for it. | `experiments/run_writer_trial.py:137-159` (`let_the_writer_choose`) |
| The page's cards and charts are built from the insights the prose cites; on a fall-back every insight counts as cited. | `DiscoverChat/layout.py` |
| The "More than N findings" line is printed in two places: the cap of 20 on an ordinary turn, and the cap of 8 on a sheet turn. | `DiscoverChat/assemble.py:408-411`, `478-481` |
| The R4 note is built by `place.note_for(choices)`. `resolve()` adds a place to `choices` whenever a name exists at two levels, also when `_says()` found the level in the officer's words. | `DiscoverChat/place.py:205-248` |
| Step 6 compares a rank phrase with the cited sheet line "with the same end word". It refused five correct sentences in the trial: "highest" where the line says "most" (four times) and "among the highest" (once). | report §4.5 |
| Trial numbers this package is measured against. Rule on: 60 of 63 first drafts refused on step 4, 4 of 63 answers lost, 19.8 s. Rule off: 0 of 63 lost, 60 passed first time, 9.7 s, a middle of 4 of 8 insights cited. | report §4.1 |
| Held questions: 53, of which 50 reach the writer. | `experiments/judge_picks.json` |
| Baselines to expect: gate 46 of 48 (red: `judge-model-evidenced`, `classifier-model-evidenced`, by D69); suite 285 passed. | D81 |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] The tree is clean and holds this brief and D81 and D82 in
      `handoffs/PROJECT_PLAN.md`, or the operator tells you to proceed.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d15c`. Copy results back at the end of each task.
- [ ] Baselines kept as files beside the mirror: the gate and the suite.
- [ ] Before any change, record what `check_citations` and
      `citation_failure_reason` return for a fixed set of inputs of your
      choosing (at least: a clean answer, a left-out insight, an unknown id, an
      uncited figure, a sheet turn). T1 compares against it.
- [ ] The API key for T5 is in the mirror's `.env`. Never commit it, never
      print it.

---

## T1 — the writer may leave an insight out (R25)

1. **A setting**, in the style of the other check modes:
   `DISCOVERCHAT_EVERY_INSIGHT_CHECK`, `block` or `log`, default **`log`**. In
   `knobs()`.
2. **`log`:** step 4 runs as today and records the same result (`pass`,
   `dropped`, `of`), but it does not count toward `all_pass`, and its sentence
   is **not** part of the retry reason. A draft that is retried for another
   reason is not told to add the insights it left out.
3. **`block`:** today's behaviour, exactly. For the inputs recorded at T0,
   `check_citations` and `citation_failure_reason` return what they returned.
4. **Every other step is untouched**: ids known, every figure tagged and found
   in its record, causal, direction, standing, number words.
5. **The fall-back is untouched**: after two refused drafts the officer still
   sees every insight handed, as bare sentences.
6. **No floor.** An answer that cites one insight of fifteen passes. So does a
   place answer written from the sheet alone, and an answer that declines an
   out-of-scope question and cites nothing.
7. **What was left out is kept**, for the log and for a later page package:
   the ids of the insights handed and not cited, in the order handed, in the
   answer's existing prose record. Empty on a fall-back. Say in the report
   whether the `/chat` response already carries that record.
8. **The trial runner** uses the setting. `--allow-unused-findings` sets
   `log` and its absence leaves the default; remove the wrapper. Add a way to
   force `block` for T5.
9. Tests that assert a left-out insight fails the **whole** check now pin
   `block` for that assertion, and say so in a comment. Tests that read step
   4's own `pass` need no change.

**Do not** edit `context_brief.py`. **Do not** add a sentence to the writer's
request about choosing insights.

---

## T2 — the "More than N findings" line (R26)

On a turn answered with a profile sheet, the line is not printed, however many
insights were held back. `place.insights_held_back` stays in the response and
the log. The line on a turn with no sheet (the cap of 20) is unchanged.

---

## T3 — the note when the officer named the level (R27)

A place joins the note only when **R4 chose** its level: the name exists at
two levels and the words beside it did not say which. When the officer's words
said the level, that place gets no note. `place.alternatives` is unchanged in
both cases: the page will use it for a switch.

| Text | Answered | Note | Alternatives |
|---|---|---|---|
| What should I know about Kalimela? | block 3843 | `This answer is about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".` | GP 119936 |
| What should I know about Kalimela GP? | GP 119936 | none | block 3843 |
| How is Kalimela Gram Panchayat doing | GP 119936 | none | block 3843 |
| the panchayat of Kalimela | GP 119936 | none | block 3843 |
| How is Kalimela block doing | block 3843 | none | GP 119936 |
| Kalyansinghpur | block 3914 | as today | GP 121162 |
| Compare Kalimela and Bheden | blocks 3843, 3678 | the two-place note, as today | GP 119936, GP 116438 |
| Compare Kalimela GP and Bheden | GP 119936, block 3678 | `This answer is about Bheden block. For the Gram Panchayat, ask about "Bheden GP".` | block 3843, GP 116438 |
| How is Chikilli doing? | GP 117835 | none | none |

The other rows of the WP-D15 table are unchanged.

---

## T4 — the standing check stops refusing correct sentences (PM decision)

1. **"highest" and "most" are one end; "lowest" and "fewest" are the other.**
   A sentence passes when the cited line states the same rank at the same end,
   whichever word either uses. The sheet's rule that counts say "most" and
   "fewest" is a rule for the builder, not for the writer.
2. **"among the highest", "one of the highest"** (and the same with most,
   lowest, fewest) claim no single rank and are not checked as one.
3. **Still caught:** the other end ("4th highest" where the line says "4th
   lowest"); a first place the line does not give ("the most" where it says
   "5th most"); a rank the line does not give ("3rd" for "5th"); a quarter the
   line does not state.
4. The default stays **`log`**.
5. **Offline evidence, no model call:** run the changed step over the tagged
   text of all 168 stored trial answers (`handoffs/WPD15_trial/*.json`).
   Report every sentence it flags, with the cited line and your judgement.
   The PM's own pass, with the same two rules, flagged none of 104 standings.

---

## T5 — the live check (writer calls only)

All 50 held questions that reach the writer, through the service path
(`run_writer_trial.py --sheets`, without `--place-only`), once each per arm,
run in parallel:

| Arm | Setting | Label |
|---|---|---|
| `rule_on` | `DISCOVERCHAT_EVERY_INSIGHT_CHECK=block` | today's behaviour, with T2–T4 in place |
| `rule_off` | the shipped default (`log`) | the package as shipped |

About 150 writer calls. No judge call. Results under `handoffs/WPD15c_trial/`.

**Pass marks.**

1. **Wrong numbers shown: 0**, in both arms, by the runner's independent
   second pass. A single one is a STOP.
2. **`rule_off` loses no more answers than `rule_on`** (an answer is lost when
   both drafts are refused).
3. **`block` restores today's check** (T1 point 3, by test).
4. **No answer of `rule_off` carries the "More than" line on a sheet turn, and
   none carries a note the T3 table says it should not.**

**Reported, not pass marks.** For each arm: answers kept and lost and on which
step; passed on the first try; seconds per answer; words and sentences;
insights handed and cited (middle; how many answers cite fewer than half; how
many cite none). Split every figure by place answers and no-place answers.
How many `rule_off` answers show fewer cards or charts than their `rule_on`
twin. Every answer that was handed insights and cites none of them, in full.
Step 6 and step 7 log lines, judged.

**For the operator, in full, both arms side by side:** L06 (Kalimela), and the
first three held questions by id that name no place.

---

## T6 — tests, gate lines, report

**Tests.** T1: `log` and `block`, the retry reason with and without the step 4
sentence, the left-out ids, the fall-back unchanged. T2: the line absent on a
sheet turn with insights held back, present on an ordinary capped turn. T3:
the table. T4: the five sentences of report §4.5 pass; the four "still caught"
cases fail. Rename the stale test
`test_the_service_does_not_import_the_reader` to say what it now proves (only
`place.py` opens the store); change nothing else in it.

**Gate lines.** New: `every-insight-check-mode` (in `log` a left-out insight
is recorded, does not fail the answer and is not in the retry reason; in
`block` it fails as before). Updated: `place-resolution` (the T3 table);
`place-standing-check` (the T4 cases); `place-facts-optional` pins `block`
where it asserts a left-out insight fails. Nothing that was green turns red.

**Report** `handoffs/WPD15c_REPORT.md`, in the form of the WP-D15 report: §0
the pass marks with evidence; §1 what was built, file by file; §2 the T3
table, expected against actual; §3 the T4 offline run; §4 the live check, its
tables, and the four answers in full; §5 the gate and the suite, baseline
against final; §6 every model call and its cost; §7 the decision journal; §8
anything in this brief that was wrong or silent.

**Commit per task on the current branch (`WP-D15c T<n>: …`). Do not push.**

---

## Files in scope (you may write ONLY these)

```
DiscoverChat/checks.py                         T1, T4
DiscoverChat/config.py                         T1 — the one setting
DiscoverChat/writer.py                         T1 — only what the retry reason and the left-out ids need
DiscoverChat/assemble.py                       T1 (the left-out ids), T2
DiscoverChat/place.py                          T3
DiscoverChat/gates.py                          T6
DiscoverChat/tests/test_citations.py           T6
DiscoverChat/tests/test_place_answers.py       T6
the test file that holds the stale test name   T6 — the rename only
DiscoverChat/experiments/run_writer_trial.py   T1 point 8
handoffs/WPD15c_trial/**                       new
handoffs/WPD15c_REPORT.md                      new
```

**DO NOT TOUCH:** `DiscoverChat/context_brief.py`; `slots.py` (WP-D15b's);
`profile_store.py`, `judge.py`, `classifier.py`, `retrieval.py`, `corpus.py`,
`layout.py`, `render.py`, `main.py`, `glossary.py`;
`experiments/judge_picks.json` and `writer_trial_questions.json`;
`Insights/**`; `Ask/**`; `frontend/**`; `deploy/**`; `Data/**`; every `.env`;
`handoffs/PROJECT_PLAN.md`; `handoffs/PROFILE_SHEET_SPEC.md`;
`handoffs/WPD15_trial/**` (read it; write your results elsewhere). If a change
cannot be made without one of these, STOP and say what is needed.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD15_REPORT.md` §2, §4.1, §4.5, §7, §8 | What shipped, the trial this is measured against, the five false alarms |
| `DiscoverChat/checks.py` (`check_citations`, `citation_failure_reason`, `check_standing`, `_counts`) | The steps you change and the mode pattern to follow |
| `DiscoverChat/experiments/run_writer_trial.py` (`let_the_writer_choose`, `--sheets`) | How the trial relaxed step 4, and the path T5 runs |
| `DiscoverChat/place.py` (`resolve`, `note_for`) | T3 |
| `DiscoverChat/assemble.py` (`_answer_with_sheets`, and the ordinary path above it) | T2, and where the left-out ids are known |

## Escalation

- **STOP and end the run:** a precondition fails; pass mark 1 fails; a change
  needs a file on the do-not-touch list.
- **Report and continue:** pass mark 2 fails (finish the report; the PM takes
  the default back to the operator).
- **Decide and document:** where the left-out ids are kept; how the runner
  forces `block`; the wording of any case the T3 table does not cover (and
  list it in §8).
- **Never:** edit the writer's prompt; tell the writer in the request to use
  or to drop insights; add a floor on insights cited; change any other step
  of the number check; turn step 6 to `block`; call the judge; push.

## Gate — green as one set

1. Pass marks 1 to 4.
2. `python -m DiscoverChat.gates`: the baseline plus the one new line green,
   nothing that was green now red. `python -m pytest DiscoverChat/tests -q`
   green.
3. The report holds the T3 table, the T4 offline run and the four answers in
   full.

Gate holder: the PM replays the gate and the suite, re-checks the numbers in
the live answers with a pass of its own, and shows the operator the four
answers.

## Not this package

- The typed-in figures in the breakdowns' cautions ("the linked share went
  from 2.7% to 53.2%", "about one in six"): a package of its own on the
  builder, once the operator agrees the approach (D82).
- Misspelt place names: WP-D15b, next.
- The page: highlighting `place.lines_used`, a switch from
  `place.alternatives`, a list of the insights left out: WP-D16.
- A mid-size writer for place answers (it tags the end of a paragraph, not
  each sentence): known, not worked on; the live writer is `gpt-6.2-sol`.
- The plain-writing lines for the prompt and whether answers may give advice
  (D74): the operator's.
