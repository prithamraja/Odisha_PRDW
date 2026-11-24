# WP-D14b brief — place profile sheets: fixes after the build review

**Workstream:** Discover. **Nature: FIX, offline.** No model call, no embedding
call, no change to the running service. **Authored:** PM, 2026-11-24.
**Decisions:** D77 (the review of WP-D14 and the operator's six rulings on
it). **For:** the operator-controlled implementation agent.
**Comes before:** WP-D15 (`handoffs/WPD15_profile_serve.md`), which needs the
name table of T3.

**The spec is `handoffs/PROFILE_SHEET_SPEC.md`, as amended (D77, D78).** Its
Appendix A is now the one current list of sentence patterns; the copy in the
WP-D14 brief is history. Where this brief and the spec disagree, stop and say
so in your report.

## What this package delivers

1. **One figure corrected.** The money "planned on" abandoned works (row E3)
   counted amounts on works that are not marked abandoned. The PM's spec was
   wrong, not the build.
2. **Three points of wording**, ruled by the operator: which group a middle
   value belongs to; the approvals line and the cashbook-link line brought into
   the shape of the other ranked lines; plain wording for three zero cases.
3. **A name table in the store's index**, and two small reader calls, so the
   chat can go from a place's name to its sheet without opening every sheet.
4. The checks, the reference figures and the scale test brought up to date.

Wiring the sheets into `/chat` is WP-D15. Do not start it here.

## The rulings this brief encodes (operator, 2026-11-24, D77)

| # | Ruling | What it means for you |
|---|---|---|
| R10 | Fix the money on abandoned works | T1 |
| R11 | When a sentence names two groups, say which one the middle value belongs to | T2a |
| R12 | F1 (approvals) and G3 (payments linked to a planned activity) each get a standing and a middle value | T2b |
| R13 | Plain wording for three zero cases (E5, H2, G3) | T2c |
| R14 | A flag for fewer than one person per household: **ignore for now** | Build nothing |
| R15 | The small variants the WP-D14 agent added (one of something, joint ranks, a single approver) are fine | Keep them; they are now written into spec Appendix A |

PM rulings on the WP-D14 report, no work for you unless a task says so: the
50 ms lookup target is per lookup once the store is open (met); a block's
statewide sentence gives district and state, like a Gram Panchayat's
(accepted); the whole is named by the one setting, never the fixed words "the
state" (accepted); check 4 matches a block or a district by level and name
(accepted).

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d14-pm`)

| Fact | Where |
|---|---|
| WP-D14 is committed, `d66923f..a971891`, not pushed. Rebuilt by the PM from the committed code: the part and the index are byte-identical to the committed ones (`d78a55f4…`, `b8a9598d…`). 8 of 8 checks green; gate 40/42 (the two D69 reds); suite 235 passed. | PM replay |
| The store holds 46 sheets and 2,871 sentences. | `--check` |
| E3's money is `SUM(fund_abandoned_total) AS E3_planned`, summed over every row of the place. | `Insights/src/phase5g_profile_sheets.py:790` |
| In `view1`, `is_abandoned` is 1 on 420 rows. On those rows `total_cost` equals `fund_abandoned_total`, row for row (0 differences). 19 rows with `is_abandoned = 0` carry a non-zero `fund_abandoned_total` (Rs 32.85 lakh): Bandhpali 8, Kalyansinghpur 8, Hirlipali 2, Bheden 1. | measured |
| The F1 sentence takes the standing phrase and drops the middle value (`phrase, _ = _ranked_tail(...)`). The G3 sentence takes the middle value and never asks for the standing phrase. | same file, lines 447–477 |
| The G3 sentence is written whenever G2 is not zero, so a G3 of zero prints "0.0% of the payments…". E5 prints its money sentence whenever the planned cost is not zero, so nothing spent prints "Rs 0 of their … (0.0%)". H2 always prints "planned cost is {money}". | lines 434–445, 472–490 |
| `ranked()` writes "The middle value is {median}." for every ranked row but A1, which writes "for these {n}". `standing_phrase()` adds the second group ("and in the … quarter of the 6,800 in {whole}") when the first group is not the whole and the whole has more than 50 peers. | lines 295–367 |
| The index (`profile_sheets_index.json.gz`) holds `sheets: level -> code -> [part, offset, length]` and no names. | measured |
| The chat resolves a Gram Panchayat to its code but a block or a district to its **name** (`DiscoverChat/slots.py`, `SlotExtractor.geography`). For all 16 blocks and 9 districts of the sample the name it returns is exactly the sheet's name. | measured |
| The test `test_appendix_a_examples_are_the_brief_text` reads `handoffs/WPD14_profile_build.md`. | `DiscoverChat/tests/test_profile_sheets.py:395` |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] `handoffs/PROFILE_SHEET_SPEC.md` is committed and holds
      "## Appendix A — the sentence patterns (current)". If it does not, STOP:
      the PM's files have not been committed.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d14b`. Copy results back to the Drive repo at the end of
      each task.
- [ ] The view parquets in `Insights/views_prdw/` of your mirror (copy them
      from `C:\dev\odisha-d11b\Insights\views_prdw\`). Their SHA-256 must equal
      the `view_parquets` values in `decompose_corpus_stamp.json`. If not, STOP.
- [ ] Uncommitted files you may meet and must leave alone:
      `DiscoverChat/experiments/**`, `handoffs/Kalimela insights.pdf`.
- [ ] Baselines, kept as files beside the mirror: `--check`, the gate and the
      suite before any change. Expected: 8 of 8, 40/42, 235 passed.
- [ ] Keep a copy of every sentence of the committed store (id and text) before
      you change anything. T5 needs it.
- [ ] No API key is needed.

---

## Tasks

### T1 — the money on abandoned works (R10)

E3's "planned on them" becomes **the sum of `view1.total_cost` over the place's
rows with `is_abandoned = 1`** (a missing cost counts as zero). The count of
abandoned works and the "plan year with the most" do not change.

- Same set-based form as today: one grouped query per level.
- The stored field keeps its name (`rows.E3.planned`).
- Nothing else reads `fund_abandoned_total` for a sheet figure after this. If
  something does, say so in the report; do not change it.

**What must come out** (spec §13, "The money on abandoned works, as
corrected"): 11 sheets change and no other.

| Sheet | Works | Planned on them | Sentence |
|---|---|---|---|
| Hirlipali Gram Panchayat (116350) | 29 | 4,019,174 | 29 works are marked abandoned, with Rs 40.19 lakh planned on them. 16 of them were planned in 2022-2023. |
| Bandhpali Gram Panchayat (116397) | 25 | 5,651,792 | 25 works are marked abandoned, with Rs 56.52 lakh planned on them. 10 of them were planned in 2020-2021. |
| Bheden Gram Panchayat (116438) | 52 | 8,781,358 | 52 works are marked abandoned, with Rs 87.81 lakh planned on them. 26 of them were planned in 2021-2022. |
| Kalyansinghpur Gram Panchayat (121162) | 31 | 4,457,998 | 31 works are marked abandoned, with Rs 44.58 lakh planned on them. 14 of them were planned in 2021-2022. |
| Attabira block (3674) | 29 | 4,019,174 | as Hirlipali |
| Barpali block (3676) | 40 | 7,957,981 | 40 works are marked abandoned, with Rs 79.58 lakh planned on them. 19 of them were planned in 2022-2023. |
| Bheden block (3678) | 52 | 8,781,358 | as Bheden Gram Panchayat |
| Kalyansingpur block (3914) | 31 | 4,457,998 | as Kalyansinghpur Gram Panchayat |
| Bargarh district (306) | 121 | 20,758,513 | 121 works are marked abandoned, with Rs 2.08 crore planned on them. 43 of them were planned in 2022-2023. |
| Rayagada district (329) | 31 | 4,457,998 | as Kalyansinghpur Gram Panchayat |
| The whole | 420 | 58,463,049 | 420 works are marked abandoned, with Rs 5.85 crore planned on them. 105 of them were planned in 2023-2024. |

Kalimela stays at 22 works and Rs 2.72 lakh.

### T2 — wording

Spec Appendix A is the authority; this is a guide to what changed in it.

**T2a — two groups named (R11).** When the standing clause names two groups,
the middle-value sentence reads `The middle value for these {n} is {median}.`,
where `{n}` is the number of peers in the first group named. With one group it
stays `The middle value is {median}.` A1 is unchanged (it always says "for
these {n}"). This applies to every ranked row that carries a middle value: A3,
A4, A5, A6, E1, E4, and now F1 and G3. No sentence of the real store changes,
because the sample never names two groups; the made-up state of T5 shows it.

**T2b — F1 and G3 (R12).**

- F1: `{F1} of the {A1} activities ({share}) have an administrative approval on
  file, the {standing}. The middle value is {median}.` The middle value is that
  of the count of approvals, the figure F1 is ranked on. F1 keeps its fixed
  note.
- G3: `{G3} of the payments are linked to a planned activity, the {standing}.
  The middle value is {median}.`
- Both follow the general rules: no peer group of at least 5 (and always the
  whole) means no standing clause and no middle-value sentence; two groups
  named means the T2a form.

**T2c — three zero cases (R13).**

| Row | When | Sentence |
|---|---|---|
| E5 | the count is above zero, their planned cost is above zero, nothing has been spent | `{count} works planned in {cut-off year} or earlier are still marked ongoing. Nothing has been spent of their {planned} planned cost.` One work: `1 work planned in {cut-off year} or earlier is still marked ongoing. Nothing has been spent of its {planned} planned cost.` |
| H2 | the count is above zero and their planned cost is zero | `{H2} activities have no LSDG theme mapped; none of them has a cost attached.` One activity: `1 activity has no LSDG theme mapped; it has no cost attached.` |
| G3 | G2 is above zero and G3 is zero | `None of the payments is linked to a planned activity.` No standing clause and no middle value. |

None of the three occurs in the real store. Each needs a test that builds the
sentence from a made-up sheet row.

### T3 — the name table and two reader calls

So that WP-D15 can go from a name to a sheet without opening every sheet.

- **The index gains `places`**: for every sheet, its name and its parents'
  codes — `places[level][code] = {"name": …, "block": <code>, "district":
  <code>}` (a block has only `district`; a district and the whole have
  neither). Names are the trimmed names the sheets already carry.
- **The index gains a format number** (`"format": 2`). The reader refuses an
  index with no `places` ("built before WP-D14b; rebuild the store"), in the
  same way it refuses an altered file.
- **The reader gains two calls**, both answered from the index alone:

```
place(level, code) -> dict | None   {"level", "code", "name", "label", "parents"};
                                    "label" is the sheet's own (`Kalimela block`,
                                    `Kalimela Gram Panchayat`, `the whole sample`);
                                    "parents" as on a sheet (code and name each)
find(level, name) -> list           the codes at that level whose name equals `name`,
                                    ignoring case and outer spaces; [] when none;
                                    more than one when a name repeats at that level
```

- The name-to-codes map is built on the first `find` for a level, not when the
  store opens.
- The reader still computes nothing and still uses the standard library only.
- Statewide, Gram Panchayat names repeat. `find` returning several codes is
  correct; it is WP-D15's job to ask which. Do not make a name unique by
  guessing.

### T4 — checks, reference figures, tests

1. **Check 1 (equal to the views)** also proves E3's money: for every Gram
   Panchayat, the stored figure equals the sum of `total_cost` over its
   `view1` rows marked abandoned, re-summed by the check's independent path
   (pandas, as the rest of check 1 is).
2. **Check 7 (reference)**: add the 11 rows of the T1 table to the reference
   figures, and make the builder's copy of the examples the text of **spec
   Appendix A** (its "Examples to reproduce character for character", which now
   includes the amended F1 and G3 lines, the whole's E3, F1, G3 and one DS
   line, and two lines for other places).
3. **The test that compares the examples with a document** reads
   `handoffs/PROFILE_SHEET_SPEC.md`, not the WP-D14 brief.
4. **Check 5 (sentences hold only stored figures)** must still pass on every
   sentence, including F1's middle value and G3's standing.
5. **A new check, in `--check` and in the gate (`profile-sheets-places`)**:
   every sheet's level, code, name and parents equal its entry in `places`;
   every entry in `places` has a sheet; `find(level, name)` returns the code
   of every sheet.
6. **Tests that plant one error each** and assert the check fails: an E3 money
   figure that includes a row not marked abandoned (check 1); a name changed in
   `places` (the new check); an index with no `places` (the reader refuses).
7. **Tests for the forms the real store does not reach**, each from a made-up
   row: the three zero forms of T2c with their one-of-something forms; a
   two-group sentence for A3, F1 and G3 (T2a).

### T5 — rebuild, compare, scale

1. **Rebuild the real store** and commit it.
2. **Compare every sentence with the copy you kept in T0**, by id. Expected:
   - E3 changes on exactly the 11 sheets of T1;
   - F1 changes on every sheet whose F1 sentence had a standing clause, by
     gaining ` The middle value is {median}.`;
   - G3 changes on every sheet whose G3 sentence had a middle value, by
     gaining `, the {standing}`;
   - no id appears or disappears, and nothing else changes. Sentence count
     stays 2,871.
   **Any other difference is a STOP.**
3. **Two builds give byte-identical store files**, as before.
4. **Every other file in `Insights/metainsights/` is unchanged** (the 23 files
   of the WP-D14 report §10).
5. **Run the scale test again** (`handoffs/WPD14_scale/run_scale.py`), with
   `place` and `find` added to what it times. Targets, each once the store is
   open: one `get`, one `place`, one `find` each under 50 ms (median and p95
   over 1,000 keys); memory added by opening under 100 MB, and after the first
   `find` at each level still under 100 MB; store under 300 MB; largest file
   under 95 MB; build under 10 minutes. Report the time to open as its own
   line; it has no target. A missed target is a STOP for the PM.
6. Print three two-group sentences from the made-up state (A3, F1, G3 of one
   Gram Panchayat) in the report.

### T6 — report

`handoffs/WPD14b_REPORT.md`, in the form of `handoffs/WPD14_REPORT.md`:

- §0 the gate table below, each item PASS or FAIL with its evidence;
- §1 what changed, file by file;
- §2 the T1 table, expected against actual;
- §3 the sentence comparison of T5.2: counts by row, and the full before and
  after for E3 (11 sheets) and for Kalimela Gram Panchayat, Kalimela block and
  the whole (F1, G3);
- §4 `--check` and the gate, baseline against final; the suite, baseline
  against final;
- §5 the scale table;
- §6 anything in the spec or this brief that was wrong or silent.

**Commit per task on the current branch (`WP-D14b T<n>: …`). Do not push.**

---

## Files in scope (you may write ONLY these)

```
Insights/src/phase5g_profile_sheets.py       T1, T2, T3, T4
Insights/metainsights/profile_sheets*        the rebuilt store and its stamp
DiscoverChat/profile_store.py                T3 — the two calls and the format refusal
DiscoverChat/gates.py                        the one new check line only
DiscoverChat/tests/test_profile_sheets.py    T4
handoffs/WPD14_scale/run_scale.py            T5 — the two new timings
handoffs/WPD14_scale/measurements.json       T5 — the new numbers
handoffs/WPD14b_REPORT.md                    new
```

**DO NOT TOUCH:** `Data/**` (and do not read it); `Insights/domain_pack_prdw/**`
and `build_views.py`; every other file in `Insights/metainsights/`; every other
file in `Insights/src/`; `DiscoverChat/main.py`, `assemble.py`, `writer.py`,
`judge.py`, `checks.py`, `layout.py`, `render.py`, `classifier.py`,
`retrieval.py`, `slots.py`, `corpus.py`, `glossary.py`, `context_brief.py`,
`config.py`; `DiscoverChat/experiments/**`; `Ask/**`; `frontend/**`;
`deploy/**`; every `.env`; `handoffs/PROJECT_PLAN.md`;
`handoffs/PROFILE_SHEET_SPEC.md`; the WP-D14 brief and report.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/PROFILE_SHEET_SPEC.md` §4, §5 (row E3), §11 (R10–R15), §13, Appendix A | The amended definitions and every sentence pattern |
| `handoffs/WPD14_REPORT.md` §3 (shapes not in the first appendix), §7, §8, §9 | What the first build decided and found |
| `Insights/src/phase5g_profile_sheets.py` (`standing_phrase`, `main_sentences`, `write_store`, the `check_*` functions, `REFERENCE`, `APPENDIX_A`) | Where every change lands |
| `DiscoverChat/profile_store.py` | The reader you extend |
| `DiscoverChat/slots.py` (`SlotExtractor.geography`) | Why names are needed: read it, do not change it |

## Escalation

- **STOP and end the run:** a precondition fails; a sentence outside E3, F1 and
  G3 changes in the real store; a T1 figure cannot be reproduced; a scale
  target is missed; a spec Appendix A example cannot be reproduced character
  for character.
- **Decide and document:** how `places` is laid out inside the index; how the
  name map is held; the wording of a form Appendix A still does not cover (and
  list it in §6).
- **Never:** change a view or read `Data/`; fix or drop a data oddity; add a
  flag, a mark or a note the spec does not hold (R14 is "ignore for now");
  work out a figure in the reader; call a model; wire the reader into the
  service; edit a prompt; push.

## Gate — green as one set

1. The T1 table reproduced exactly, and Kalimela's E3 unchanged.
2. Spec Appendix A's examples reproduced character for character.
3. The T5.2 comparison shows only the expected changes.
4. `--check` green on every check, with the E3 proof in check 1 and the new
   places check.
5. `python -m DiscoverChat.gates`: 41/43, the two D69 reds unchanged, nothing
   that was green now red. `python -m pytest DiscoverChat/tests -q` green.
6. Two builds byte-identical; the other 23 files of `Insights/metainsights/`
   unchanged.
7. The scale table filled in, every target met.

Gate holder: the PM replays the build, `--check`, the gate and the suite, and
reads the before-and-after sentences.
