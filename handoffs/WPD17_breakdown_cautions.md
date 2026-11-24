# WP-D17 brief — breakdown sentences carry only their own numbers

**Workstream:** Discover. **Nature: BUILD, a store rebuild, then a short live
check** (embedding calls for the changed records; writer calls on the held
picks; no judge call expected). **Authored:** PM, 2026-11-24.
**Decisions:** D81 (the finding), D82 (the approach), D83 (the operator's
ruling). **For:** the operator-controlled implementation agent.
**Comes after:** WP-D15c. **Not at the same time as** WP-D15b: both edit
`DiscoverChat/gates.py`.

## The problem

The breakdown builder holds a table of four cautions, typed by hand, one per
measure. It adds the caution to the end of **every** breakdown of that
measure, whatever the breakdown is about.

| Caution, as stored today | Records | Of them about the whole sample |
|---|---|---|
| "A rise here is a rise in recording completeness unless the cashbook total rises with it; the linked share went from 2.7% to 53.2% across these six years." | 407 | 12 |
| "The sanctioned basis covers only the activities with a sanction record on file, about one in six." | 7,759 | 85 |
| "Only 17 completions are recorded in the whole sample, so this splits a near-empty column." | 1,417 | 41 |
| "A swap between the SC and ST components is suspected and unconfirmed; do not read one against the other." | 1,685 | 46 |
| **Total** (PM-measured on the committed store, 66,779 records) | **11,268** | |

Three faults follow.

1. **A number typed into code goes stale.** These were true of the
   20-Gram-Panchayat sample on the day they were typed. On new data they are
   wrong, and nothing says so.
2. **A whole-sample number sits inside a sentence about one place.** The
   writer cannot tell it from the place's own figures. In the WP-D15 trial it
   gave the sample's figure as the place's own in 14 of 20 of today's
   answers. For Khordha: "Only 23.1% of cashbook payments were linked to a
   planned activity … although the annual linked share rose from 2.7% to
   53.2% over the period."
3. **The number check approves it**, because the digits are in the record the
   sentence cites.

## The ruling (operator, 2026-11-24, D83)

**R28 — drop the cautions altogether. A stored sentence carries only
figures.** The PM had offered keeping them as word-only notes; the operator
chose to remove them. All four go, the SC/ST one included.

What replaces the lost figures: nothing in this package. Each place's own
version is already on its profile sheet (the share of payments linked to a
plan, approvals on file, completions out of the sample's total).

## What this package delivers

1. The builder writes breakdown sentences with no caution.
2. A check that makes a typed-in number fail the build.
3. The breakdown store rebuilt, with proof that nothing else changed.
4. The chat's held test material brought in line with the new store.

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d15-pm`, tree `a3b81f5`)

| Fact | Where |
|---|---|
| The table is `_MEASURE_CAVEAT`: eight measures, four texts. `build_sentence` appends the text as the last line of the sentence. | `Insights/src/phase5f_decompose.py:294-313`, `592-594` |
| The text that is embedded for search begins with the sentence, so a changed sentence means a new vector for that record. Vectors of the previous build are reused by the hash of that text. | `build_embed_text`, lines 694-696; the reuse at 1087-1116 |
| The builder's options: `--no-embed`, `--force-embed`, `--views`, `--embed-text`. It writes into `Insights/metainsights/`. | lines 1260-1268 |
| The store: `decompose_corpus.json.gz` (12 MB), `decompose_corpus.part0.npy` and `part1.npy` (68 MB each), `decompose_corpus_stamp.json`. | `Insights/metainsights/` |
| The mined insights (`retrieval_corpus.*`, 4,404 records) carry none of the four texts. | measured |
| The builder reads the view parquets, which are not in git. The copies the last builds used are in `C:\dev\odisha-d11b\Insights\views_prdw\`. | D76 |
| Candidate set of both stores: `610cb3d26dff7bf3`. It comes from the mined candidates, so this rebuild should not change it, and the profile sheet store stays valid. Confirm, do not assume. | stamps |
| The chat's gate reads the breakdown store in `corpus-pin`, `corpus-deterministic-text`, `decompose-reconciles`, `decompose-evenness-honest`, `decompose-signed-not-a-magnitude`, `no-match-honest`, `numerals-traceable` and others. | `DiscoverChat/gates.py` |
| `place-switch-off-identical` compares 76 offline answers, byte for byte, with a baseline made on the code before WP-D15, replaying stored query vectors. A changed breakdown sentence changes those answers. | `gates.py:1281-1333`; `handoffs/WPD15_trial/offline_baseline_*`; WP-D15 report §7 item 13 |
| The held judge picks keep each insight's stored sentence and refuse a store whose sentence differs. Its builder has `--list`, `--check`, `--redo`. | `DiscoverChat/experiments/held_picks.py:70`, `build_judge_picks.py` |
| The sheet builder's check 4 compares sheet figures with breakdown records. It reads numbers, not sentences. | `Insights/src/phase5g_profile_sheets.py` (`check_insights`) |
| The same two typed-in numbers are in the insight **report's** reading notes. Those are whole-sample notes in another product. Not this package. | `Insights/src/phase5b_report.py:689`, `2048` |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] The tree is clean and holds this brief and D83 in
      `handoffs/PROJECT_PLAN.md`; WP-D15c is committed and its report exists.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d17`. Copy the four view parquets in. Copy results back
      at the end of each task.
- [ ] Baselines kept as files beside the mirror: the gate, the suite,
      `python Insights/src/phase5g_profile_sheets.py --check`.
- [ ] **Prove the store can be rebuilt before you change anything.** Run the
      builder as it is. The result must equal the committed store: every
      record, every field, the order, and the vectors, with no embedding
      call. If it does not, STOP and report what differs. Without this the
      comparison of T3 means nothing.
- [ ] Keep a copy of the committed store beside the mirror. T3 compares
      against it.
- [ ] The embedding key and the writer key are in the mirror's `.env` files.
      Never commit them, never print them.

---

## T1 — the builder

Remove the caution table and its use. A breakdown sentence ends with its last
computed line. Change nothing else about how a sentence is built: not the
order of its lines, not a format, not a word.

The fixed line the chat adds under a breakdown when it hands it to the writer
("a breakdown of the recorded totals, not a mined pattern …") is the chat's,
is not a caution of this table, and stays.

---

## T2 — a typed-in number fails the build

**The rule.** Every number in a stored breakdown sentence is a figure the
builder computed for that record's own subject, or part of a name taken from
the data (a fiscal year, "Theme 4", "5th State Finance Commission"). Fixed
text contributes no digit.

1. **In the builder, exact.** As a sentence is written, the builder knows
   every figure it formats into it. For every record, every numeral in the
   sentence must be one of those, or part of a data name of that record. A
   record that fails stops the build and is named. The method is yours.
2. **Proof it works.** A test that puts the old table back (or one typed-in
   figure into fixed text) and shows the check fail, naming the record.
3. **In the chat's gate, on the stored file**, a new line
   `breakdowns-own-numbers`: none of the four caution texts is in any stored
   sentence; and the strongest proof of the rule you can make from the stored
   record alone. If the stored record does not hold every figure its
   sentence states (the size line, the ratio line), say so, and say what the
   gate line proves and what only the builder's check proves. Do not add
   fields to the stored records for this without saying why it is safe for
   the chat's loader.
4. **An audit, once, reported and not a gate:** look for the same fault in
   the other two stores. For the mined insights: any sentence part that holds
   a digit and appears word for word on many records about different
   subjects. For the profile sheets: say which existing check already proves
   a sheet sentence is rebuilt from the sheet's own figures. List what you
   find; fix nothing there.

---

## T3 — the rebuild, and proof that nothing else changed

Rebuild the breakdown store with the changed builder.

**The comparison, record by record, old store against new** (a script under
`handoffs/WPD17_cautions/`, and its output):

1. The same 66,779 ids in the same order.
2. Exactly 11,268 sentences changed, and each change is exactly one of the
   four texts removed from the end: 407, 7,759, 1,417 and 1,685. Any other
   count, or any other kind of change, is a STOP.
3. Every other field of every record is identical.
4. Only those 11,268 records were embedded again. The vector of every other
   record is bit for bit the old one.
5. The candidate set is unchanged; the profile sheet checks pass 9 of 9 on
   the untouched sheet store.

**What the change does to search**, reported: for the 76 offline gate
questions (stored query vectors, so no query is embedded again) and the 53
held questions, how much of each top-100 pool is the same before and after;
how many held insights left their question's pool; whether any "no match"
question now clears the floor. A "no match" question that now finds
something is a STOP.

---

## T4 — the chat's held material

1. **Held judge picks: refresh, do not re-judge.** The picks stay the judge's
   picks; only the stored sentences move to the new store. Add a mode to
   `build_judge_picks.py` that, for every held insight, replaces the sentence
   with the store's, **only** when the old sentence is the new one plus one
   of the four texts (or they are equal). An insight that fails that test is
   not refreshed: list it, and re-judge that question with `--redo` (a judge
   call; say how many). The file records that it was refreshed, when, and why.
   `--check` is clean afterwards.
2. **The switch-off baseline.** `place-switch-off-identical` must keep its
   meaning: with the sheets off, the service answers as it did before WP-D15.
   Re-make `offline_baseline_answers.json.gz` the way WP-D15 made it: the
   chat's code as it was before WP-D15 (commit `f0c5efb`), the **new**
   breakdown store, the stored query vectors. If that code cannot be run
   against the new store, STOP and say why. Do not make the baseline from
   today's code.
3. **Fixtures and tests** that quote one of the four texts: bring them in
   line. Do not change what a test proves.
4. No change to the service's own code is expected. If one is needed, STOP.

---

## T5 — the live check (writer calls only)

The 50 held questions that reach the writer, through the service path, once
each, with the shipped defaults. Results under `handoffs/WPD17_cautions/`.

**Pass marks.**

1. **Wrong numbers shown: 0**, by the runner's independent second pass.
2. **Answers lost: no more than the `rule_off` arm of WP-D15c lost, plus
   one** (one run each, so one answer is within run-to-run difference).
3. **No answer states "2.7%" beside "53.2%", "about one in six" or "17
   completions"** unless the record it cites states that figure for its own
   subject. List every hit with its cited record.

**Reported.** Kept, lost and on which step; passed first time; seconds;
words; insights cited; place facts used; beside the same figures from
WP-D15c's `rule_off` arm.

**For the operator, in full, before (WP-D15c `rule_off`) and after:** GEO-29
(Khordha), L01 (Kandhamal), L06 (Kalimela).

---

## T6 — tests, gate lines, report

**Gate.** New: `breakdowns-own-numbers`. Every line that was green stays
green; the two D69 reds stay as they are.

**Report** `handoffs/WPD17_REPORT.md`, in the form of the WP-D15 report: §0
the pass marks with evidence; §1 what was built, file by file; §2 the T0
rebuild proof; §3 the comparison of T3 and the search report; §4 the T2
check, its proof and the audit of the other two stores; §5 the held picks
(refreshed, re-judged) and the baseline; §6 the live check and the three
answers; §7 the gate, the suite and the sheet checks, baseline against final;
§8 every model call and its cost; §9 the decision journal; §10 anything in
this brief that was wrong or silent.

**Commit per task on the current branch (`WP-D17 T<n>: …`). Do not push.**
The rebuilt store is about 150 MB of binary files; say in the report what the
commit added to the repository.

---

## Files in scope (you may write ONLY these)

```
Insights/src/phase5f_decompose.py                       T1, T2
Insights/metainsights/decompose_corpus.json.gz          T3 — rebuilt
Insights/metainsights/decompose_corpus.part0.npy        T3
Insights/metainsights/decompose_corpus.part1.npy        T3
Insights/metainsights/decompose_corpus_stamp.json       T3
DiscoverChat/gates.py                                   T2 point 3; fixtures that quote a caution
DiscoverChat/tests/**                                   a new test file; existing tests only where they quote a caution
DiscoverChat/experiments/build_judge_picks.py           T4 — the refresh mode
DiscoverChat/experiments/held_picks.py                  T4 — only if the refresh needs it
DiscoverChat/experiments/judge_picks.json               T4 — refreshed
handoffs/WPD15_trial/offline_baseline_answers.json.gz   T4 — re-made
handoffs/WPD17_cautions/**                              new — scripts, comparison, audit, live check
handoffs/WPD17_REPORT.md                                new
```

**DO NOT TOUCH:** the view parquets and everything that builds them; the
mining outputs (`view*_candidates.json`, `view*_ranked.json`, the feeds);
`retrieval_corpus.*`; `profile_sheets*`; `Insights/src/phase5b*.py`,
`phase5d*.py`, `phase5g*.py`; the chat's service code (`assemble.py`,
`checks.py`, `writer.py`, `place.py`, `slots.py`, `render.py`, `main.py`,
`layout.py`, `glossary.py`, `config.py`, `corpus.py`, `retrieval.py`,
`judge.py`, `classifier.py`, `context_brief.py`);
`handoffs/WPD15_trial/offline_baseline_vectors.npy` and every other file
under `handoffs/WPD15_trial/` and `handoffs/WPD15c_trial/`; `Ask/**`;
`frontend/**`; `deploy/**`; `Data/**`; every `.env`;
`handoffs/PROJECT_PLAN.md`; `handoffs/PROFILE_SHEET_SPEC.md`.

## Read first (with why)

| File | Why |
|---|---|
| `Insights/src/phase5f_decompose.py` (`build_sentence`, `build_embed_text`, the vector reuse, `main`) | What you change and how a rebuild reuses vectors |
| `handoffs/WPD10_REPORT.md` | How the store is laid out, and why a rebuild of unchanged text makes no embedding call |
| `handoffs/WPD15_REPORT.md` §4.8, §7 item 13, §8 item 5 | The finding, and how the switch-off baseline was made |
| `handoffs/WPD15c_REPORT.md` | The numbers T5 is measured against |
| `DiscoverChat/experiments/held_picks.py`, `build_judge_picks.py` | T4 |
| `DiscoverChat/gates.py` (`place-switch-off-identical`, `corpus-deterministic-text`) | The lines a rebuild moves |

## Escalation

- **STOP and end the run:** a precondition fails, above all the T0 rebuild
  proof; the comparison of T3 shows any change other than the four texts; a
  "no match" question now finds something; the candidate set changed; the
  old code cannot make the baseline; the service's code would have to change;
  pass mark 1 of T5 fails.
- **Report and continue:** pass mark 2 or 3 of T5 fails.
- **Decide and document:** how the builder's check collects the figures of a
  sentence; what the gate line can prove from the stored record; the
  threshold of the audit.
- **Never:** keep a caution as a note (R28); reword any other part of a
  sentence; re-judge a held question that the refresh covers; make the
  baseline from today's code; touch the mined insights, the sheets or the
  report's reading notes; push.

## Gate — green as one set

1. The T0 rebuild proof; the T3 comparison exact; the T5 pass marks.
2. `python -m DiscoverChat.gates`: the baseline plus `breakdowns-own-numbers`
   green, nothing that was green now red. `python -m pytest
   DiscoverChat/tests -q` green. The sheet checks 9 of 9.
3. The report holds the comparison counts, the audit and the three answers.

Gate holder: the PM rebuilds the store in its own mirror and compares it with
the committed one, re-runs the comparison against the old store, replays the
gate and the suite, and shows the operator the three answers before and
after.

## Not this package

- The insight report's reading notes, which hold the same typed-in numbers
  (whole-sample notes, another product).
- "a 20-Gram-Panchayat sample" in the writer's background text: the
  operator's file.
- Anything that needs the views or the mining run again (repeated spend
  rows, the "Buildings" status label, payment year against plan year).
- The page (WP-D16) and misspelt place names (WP-D15b).
