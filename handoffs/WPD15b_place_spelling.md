# WP-D15b brief — place names typed with spelling mistakes

**Workstream:** Discover. **Nature: BUILD, offline.** Code only: no model call,
no API key. **Authored:** PM, 2026-11-24. **Decision:** D80 (the operator's
four rulings). **For:** the operator-controlled implementation agent.
**Comes after:** WP-D15 (`handoffs/WPD15_profile_serve.md`), executed and
accepted. This package builds on what WP-D15 shipped: its place module, the
matched positions in the slot reader, the `place` field and the note line.
**Read `handoffs/WPD15_REPORT.md` first. Where this brief names a WP-D15
structure that shipped differently, follow what shipped and say so in your
report.**

## The problem

The chat recognises a place only when its name is spelled exactly as stored,
or is on a short list of known alternative names. A misspelt place is not
found, and nothing says so: the officer gets a general answer and no profile
sheet.

| Typed | Found today (PM-measured) |
|---|---|
| What should I know about Kalimella? | nothing |
| How is Malkangri doing? | nothing |
| How is Barpalli block doing? | nothing |
| Anything in Bhubaneshwar block? | nothing |
| How is Chikili doing? | nothing |
| Tell me about Khurda | Khordha (on the alias list) |
| how is kalimela doing | Kalimela (case does not matter) |

Ask already has a spelling-tolerant matcher. The chat never reaches it with a
misspelt word, because the chat looks only for exact names inside the text.

## What this package delivers

1. A **loose pass** in the chat's place reading: words of the question that
   matched no place exactly are tried against Ask's matcher.
2. **Never a silent correction.** Every loose reading is said to the officer,
   in one code-written line.
3. A plain **"could not find"** reply when the officer marks a word as a place
   and nothing is close.
4. A **test harness** that takes any list of place names, so it can be run
   again on the real statewide list before go-live.

## The rulings this brief encodes (operator, 2026-11-24, D80)

| # | Question | Ruling | What it means for you |
|---|---|---|---|
| R21 | One close match | **Answer, and say so**: `Reading "Kalimella" as Kalimela block.` | T2 |
| R22 | Several close matches | **Answer for the closest.** (The PM had recommended asking.) PM reading, stated to the operator: the answer says which name was read and names the other close ones, so the officer can switch. | T2 |
| R23 | A word marked as a place, with nothing close | **Say so**: `I could not find a place called "Rampur" in the data.` Do not answer it as a general question. | T3 |
| R24 | When | A small package of its own, after WP-D15 | This brief |

Standing rulings that apply: R4 (a name that is both a Gram Panchayat and a
block is answered for the block unless the question says Gram Panchayat) holds
for a loose reading exactly as for an exact one.

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d14b-pm`)

| Fact | Where |
|---|---|
| `SlotExtractor.geography(text)` tries every registry name and every alias as a whole-word pattern in the text. Longest name first. Nothing else. | `DiscoverChat/slots.py:120-178` |
| It resolves through Ask's validator: `self._validator.validate(surface, etype)`, read from Ask's database at start-up, so the statewide extract needs no edit here. | same |
| Ask's matcher is `EntityValidator` in `Ask/query_router/entity_validator.py`: exact → alias → fuzzy (`rapidfuzz`, `fuzz.WRatio`). The fuzzy cut-off for `district`, `block` and `gp` is **85**, in `REGISTRY_CONFIG`. An exact match never reaches the fuzzy step. With several names over the cut-off Ask raises `ClarificationNeeded`; with none it raises `EntityNotFound` and offers its three nearest. | lines 400–414, 1096–1179 |
| The alias lists are Ask's: 10 district entries, 3 block entries, none for Gram Panchayats. `"kalyansinghpur"` → block `Kalyansingpur` is one of them. | lines 146–171 |
| Handed the misspelt word directly, Ask's matcher reads nine of the PM's ten misspelt words right: Kalimella → Kalimela (as a block and as a Gram Panchayat), Malkangri → Malkangiri, Barpalli → Barpali, Bhubaneshwar → Bhubaneswar, Chikili → Chikilli, Mendrajpur → Mendarajpur, Atabira → Attabira, Kandhmal → Kandhamal, Koraputt → Koraput. It does not find "Laxmipoor" (it offers Laxmipur). | measured |
| 63 ordinary words of officers' questions ("spending", "block", "abandoned", "sanction", …), tried at all three levels: no match. | measured |
| Every word of 5 letters or more and every pair of neighbouring words in the 50 held questions (421 tries): no ordinary word matched a place. The only two loose hits were real near-names: the Gram Panchayat "Sharagada" loosely matches the block "Sheragada", and the reverse. | measured |
| Real question sets in the repo: the 50 held questions (`DiscoverChat/experiments/judge_picks.json`) and 245 rows in `test_questions_query_mapping.csv`. | repo |
| The sample holds 20 Gram Panchayats, 16 blocks and 9 districts. The state has about 6,800, 314 and 30. | spec §3 |

## What WP-D15 built that you build on (PM-verified 2026-11-24, in `C:\dev\odisha-d15-pm`, tree `a3b81f5`)

| Fact | Where |
|---|---|
| `geography()` now also returns `mentions`: every occurrence of every accepted name, with its level, code (Gram Panchayats), name and start and end position. The four older fields are computed as before and never read it. `Slots.mentions` is not in `as_dict()`, so the logged retrieval payload did not change. | `DiscoverChat/slots.py` |
| `place.resolve(text, mentions, store, max_places=)` returns a `Plan`: `places`, `mode` (`full` / `main` / empty), `alternatives`, `note`, `dropped`, `why_no_sheet`. The level words of R4 are read by `_says()`; the R4 note is built by `note_for()`. A loose reading should reach `resolve` as a mention like any other, with how it was read carried beside it. | `DiscoverChat/place.py` |
| The first line of an answer is `Answer.lead`. `render.to_html(..., lead=)` puts it at the start of the one narrative paragraph, not in a paragraph of its own: the page lines its hovers up against the answer text from the first character, and a separate paragraph switches every hover off. Set `lead`; do not add a paragraph. The lead is not passed through the number check. | `assemble.py`, `render.py` (report §7 item 10) |
| The response's `place` field is built by `place.payload()`. It is `{}` on a turn with no sheet. `retrieval["place"]` is written to the call log whenever a name was found, sheet or no sheet. | `place.py`, `main.py` |
| The gate line `place-switch-off-identical` replays 76 offline questions against a stored baseline, with the sheets off and on. None of the 76 holds a misspelt place, so it must stay green with the loose pass on, untouched. | `gates.py`, `handoffs/WPD15_trial/` |
| The held questions are now **53** (the 50, plus TWO-01, TWO-02 and TWO-03). | `DiscoverChat/experiments/judge_picks.json` |
| Baselines to expect: gate 46 of 48 (red: `judge-model-evidenced`, `classifier-model-evidenced`, by D69), suite 285 passed. | D81 |
| The R4 note: WP-D15 printed it whenever a name exists at two levels. The operator ruled (R27, D82) that it is not printed when the officer's own words named the level, and WP-D15c builds that before you start. Follow the code you find, and read `handoffs/WPD15c_REPORT.md` if it exists. | report §2; `handoffs/WPD15c_review_fixes.md` T3 |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] WP-D15 is committed and its report says the PM accepted it, or the
      operator tells you to proceed.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d15b`. Copy results back at the end of each task.
- [ ] Baselines, kept as files beside the mirror: the gate and the suite before
      any change.
- [ ] Record, before any change, what `geography` returns for every question of
      the two real question sets. T4 compares against it.
- [ ] No API key is needed. If your work wants one, you have left the scope.

---

## T1 — the loose pass

It runs inside the chat's place reading, after the exact pass, so the search
and the profile sheets both gain from it.

1. **What is tried.** Words of the officer's own text that the exact pass did
   not use: each single word, each pair and each triple of neighbouring words.
   A word that overlaps an exact match is never tried — so a correctly typed
   "Sharagada" cannot also become "Sheragada".
2. **What is not tried.** A single word shorter than 5 letters. An ordinary
   word. A number or a fiscal year. How you decide "ordinary" is yours to
   choose and document; one way that needs no outside data is the vocabulary
   of the analysis's own stored sentences and the chat's own word lists, less
   the registry's names. The pass marks of T4 judge the result, not the
   method.
3. **How it is matched.** With Ask's scorer and Ask's cut-off for that level,
   imported from `REGISTRY_CONFIG` and not restated. Compare against the
   registry values the validator already holds. Do not change anything under
   `Ask/`.
4. **What comes back for each word tried**, at each level: the names at or
   over the cut-off, with their scores.
5. **Choosing (R21, R22).**
   - One name: that is the reading.
   - Several names: **the highest score is the reading**; the others are kept
     as "other close names", up to three.
   - A tie in score: a block before a Gram Panchayat (the R4 order), then the
     name earlier in the alphabet. The choice must be the same every run.
   - One typed word that reads as a Gram Panchayat and a block of the same
     name is one reading with two levels, and R4 settles it as WP-D15 does.
6. **What the slot reader returns.** The fields it has today, now also filled
   by loose readings (so the search boosts them like any place), plus a new
   field that says, for every place, how it was read: `exact`, `alias` or
   `loose`, and for a loose one the officer's typed words, the score and the
   other close names. **For a question in which every place is spelled as
   stored, every existing field is exactly what it is today.**
7. **Aliases stay silent.** "Khurda" for Khordha is a known other name, not a
   correction, and gets no line.
8. **A switch**: `DISCOVERCHAT_LOOSE_PLACES`, `1` or `0`; `0` restores today's
   reading byte for byte. A setting for the shortest single word tried
   (default 5).
9. **A level word beats an exact match at another level.** "Sharagada" is a
   Gram Panchayat; the block is spelled "Sheragada" and scores 88.9 against
   it. When the officer writes "Sharagada block", the word matched exactly as
   a Gram Panchayat but is marked as a block. Try that one word loosely at the
   marked level. If it reads, that is the place, with its line. If it does
   not, keep the exact match. This is the only case in which a word that
   matched exactly is tried again.

**Scores the PM measured with Ask's scorer on the sample** (cut-off 85):
Kalimella → Kalimela 94.1; Sheragad → Sheragada block 94.1 (and Sharagada Gram
Panchayat 82.4, under the cut-off); Laxmipor → Laxmipur 87.5; Laxmipoor →
Laxmipur 82.4 (under); **Bhedan → Bheden 83.3 (under)**; Tangi → Tangi Choudwar
90.0. A six-letter name with one letter changed, or two swapped, scores 83.3
and is not read at this cut-off. That is a known limit, measured in T4, and
not yours to fix by lowering the number.

---

## T2 — saying so (R21, R22)

One code-written line, the first line of the answer, by the mechanism WP-D15
uses for its R4 note. It is outside the prose and outside the number check.

| Case | The line |
|---|---|
| One close match (`How is Barpalli block doing?`) | `Reading "Barpalli" as Barpali block.` |
| A match at both levels, with the R4 choice (`What should I know about Kalimella?`) | `Reading "Kalimella" as Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".` |
| Several close matches — form only; the sample has no such case, so the names here are made up and the test uses a made-up registry | `Reading "Rampor" as Rampur block. Other close names: Rampa block, Ramapur block.` |
| Two places, one misspelt (`Compare Kalimela block and Barpalli block`) | `Reading "Barpalli" as Barpali block.` (the correctly typed place gets no line) |
| A level word that contradicts an exact match (`How is Sharagada block doing?` — Sharagada is a Gram Panchayat; the block is spelled Sheragada) | `Reading "Sharagada" as Sheragada block.` (T1 point 9) |

- The typed words are quoted as the officer typed them.
- The line is shown **whenever a place was read loosely**, whether or not a
  profile sheet was used on that turn.
- The `place` field of the response carries the same facts: the typed words,
  how each place was read, and the other close names as alternatives with a
  ready question for each (the `ask` text of WP-D15). When no sheet was used,
  the field is still present, with a mode that says so.
- Every quoted `ask` text must resolve, by the chat's own reading, to the
  place it names.

---

## T3 — "could not find" (R23)

1. **Marked as a place** means the officer put a level word against the
   unmatched word: `block`, `district`, `GP`, `G.P.`, `Gram Panchayat` or
   `panchayat` directly after it, or `block of`, `district of`, `GP of`,
   `Gram Panchayat of`, `panchayat of` directly before it. (The same marks
   WP-D15 uses for R4.)
2. A marked word with no reading at that level, exact, alias or loose, is
   **not found**.
3. **When no place at all was read:** the turn ends with this message and
   nothing else is searched or written:

```
I could not find a place called "Bhedan" in the data.
Close names in the data: Bheden block.
```

   The second line appears only when a name scores at least 80 at the marked
   level (so: close, but under the cut-off); up to three names, highest score
   first; left out otherwise. For `How is Rampur block doing?` the nearest
   block scores 71.4, so the message is the first line alone. The run stamp
   follows as on every answer.
4. **When another place in the same question was read:** answer for that
   place, and put the first line above the answer.
5. An unmatched word that is **not** marked as a place is left alone: the turn
   runs as today. Code cannot tell "How is Rampur doing?" from "How is
   spending doing?". Count these in T4 so the PM can see how often it happens.
6. The `lookup` and `why` moves are unchanged. A lookup still goes to Ask,
   which does its own matching.

---

## T4 — the harness and the pass marks

A script under `handoffs/WPD15b_spelling/` that takes a **list of place names
by level** and a **list of questions**, and reports. Run it on:

**A. Correctly spelled questions**: the 53 held questions and the 245 rows of
`test_questions_query_mapping.csv`.

**B. Made misspellings of every place name in the sample**, each put into
three question frames (`How is {name} doing?`, `What should I know about
{name}?`, `Anything notable in {name} block|district|GP?`). One mistake per
name, by rule, every rule that applies:

- a letter dropped, a letter doubled, two neighbouring letters swapped;
- the swaps officers make when writing Odia names in English: `sh`↔`s`,
  `th`↔`t`, `kh`↔`k`, `gh`↔`g`, `bh`↔`b`, `ee`↔`i`, `oo`↔`u`, `a`↔`o`,
  `v`↔`b`, `w`↔`v`, `pur`↔`pore`↔`poor`, `garh`↔`gad`↔`gada`, a final `a`
  dropped or added.

**C. The PM's 13 hand-written examples** (the table at the top, plus
Mendrajpur, Atabira, Kandhmal, Koraputt, Laxmipoor and a question naming
"Rampur block").

**D. Size.** A made-up list of 6,800 + 314 + 30 names (the names of the
WP-D14 scale test will do for timing), and a 25-word question.

**Pass marks.**

1. **On set A, nothing changes.** Every existing field of the slot reader is
   identical to the T0 record for all 298 questions, and no loose reading and
   no "could not find" is produced. A single one is a STOP.
2. **On set B, for names of 7 letters or more:** at least 90% of the
   misspellings are read as the right place. Report every miss. (Names of 5
   and 6 letters are reported apart: at Ask's cut-off one changed letter in a
   six-letter name is not read.)
3. **On set B, wrong readings are counted and listed**: a misspelling read as
   a *different* place than the one it was made from. Expected only among the
   real near-names (Sharagada / Sheragada, Kalyansinghpur / Kalyansingpur). Any
   other wrong reading is reported to the PM with its scores; more than 1 in
   100 is a STOP.
4. **Every loose reading in sets B and C produced its line** (T2), and every
   `ask` text resolved to the place it names.
5. **Set C:** the nine misspelt words the matcher reads right (Kalimella,
   Malkangri, Barpalli, Bhubaneshwar, Chikili, Mendrajpur, Atabira, Kandhmal,
   Koraputt) are read right in a whole question; "Is Laxmipoor behind on anything?" is left alone (82.4, not
   marked); "How is Laxmipoor block doing?" gives the R23 message with
   "Close names in the data: Laxmipur block."; "How is Rampur block doing?"
   gives the R23 message with no second line.
6. **Size:** the whole place reading, exact and loose, for the 25-word
   question takes under 150 ms at state size (median and p95 over 200 runs,
   after start-up). Memory added at start-up under 50 MB. A miss is a STOP.
7. With the switch off, the gate's and the suite's answers are identical to
   the baseline.

**Reported, not a pass mark:** how many set A questions hold a word that looks
like a place to a reader but is not marked as one (T3 point 5); the set B
result for names of 5 and 6 letters; the number of words the loose pass tried
and skipped per question; how many unmarked words in sets B and C scored
between 80 and the cut-off and so were left alone (the "Bhedan" case).

**A what-if, for the PM, not shipped:** run sets A and B once more with the
cut-off at 80 in the harness only. Report what it gains (misspellings now read
right) and what it costs (wrong readings, and any ordinary word of set A read
as a place). The operator decides the cut-off from this; you do not change it.

**What this cannot show.** The sample has 45 names; the state has about
7,100. With that many names a misspelling is more often close to several
places, and an ordinary word more often close to one. The harness must run
unchanged on a real statewide name list when the operator supplies one. Say in
the report exactly how to run it.

---

## T5 — tests, gate lines, report

**Tests** (`DiscoverChat/tests/test_place_spelling.py`, offline): the T2 table;
the T3 cases; an exact name is never re-read loosely (the Sharagada case); the
tie rule; R4 on a loose reading; aliases silent; the switch off; a made-up
registry in which one misspelling is close to three names (R22), so the
"several" path is tested without waiting for statewide data. Every existing
test passes unchanged.

**Gate lines** (new): `place-spelling-exact-unchanged` (pass mark 1, on the
held questions); `place-spelling-says-so` (a loose reading always carries its
line); `place-spelling-not-found` (the R23 message).

**Report** `handoffs/WPD15b_REPORT.md`, in the form of the WP-D14 report: §0
the pass marks with evidence; §1 what was built, file by file; §2 the T2 and
T3 tables, expected against actual; §3 set B and C results, with every miss
and every wrong reading listed; §4 size; §5 the gate and the suite, baseline
against final; §6 the decision journal (how "ordinary" is decided; where the
loose pass sits); §7 how to run the harness on a new name list; §8 anything in
this brief that was wrong or silent.

**Commit per task on the current branch (`WP-D15b T<n>: …`). Do not push.**

---

## Files in scope (you may write ONLY these)

```
DiscoverChat/slots.py                          T1 — the loose pass, the new field
DiscoverChat/place.py                          T2, T3 — the lines, the `place` facts (as WP-D15 shipped it)
DiscoverChat/assemble.py                       T2, T3 — the first line; the "could not find" turn
DiscoverChat/config.py                         the two settings
DiscoverChat/gates.py                          the three new lines
DiscoverChat/tests/test_place_spelling.py      new
a word list, if your method needs one          new, as data beside the other word lists
handoffs/WPD15b_spelling/**                    new — the harness, its inputs and results
handoffs/WPD15b_REPORT.md                      new
```

**DO NOT TOUCH:** `Ask/**` (import the matcher and its settings; change
nothing); `Insights/**`; `DiscoverChat/profile_store.py`, `writer.py`,
`checks.py`, `judge.py`, `classifier.py`, `retrieval.py`, `corpus.py`,
`layout.py`, `render.py`, `main.py`, `context_brief.py`, `glossary.py`;
`DiscoverChat/experiments/**`; `frontend/**`; `deploy/**`; `Data/**`; every
`.env`; `handoffs/PROJECT_PLAN.md`; `handoffs/PROFILE_SHEET_SPEC.md`. If the
line or the `place` field cannot be carried without a change to `main.py` or
`render.py`, STOP and say what is needed.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD15_REPORT.md` and `handoffs/WPD15_profile_serve.md` (T1, T5) | What the place module, the note line and the `place` field really are |
| `DiscoverChat/slots.py` | The reading you extend |
| `Ask/query_router/entity_validator.py` (`REGISTRY_CONFIG`, `_validate_roster`, the alias tables, `registry_values`) | The matcher, its cut-offs, and why an exact match must never reach the fuzzy step |
| `DiscoverChat/retrieval.py` (how it uses the slots) | So a loose reading boosts the search like any other place |
| `handoffs/WPD14_scale/run_scale.py` | The made-up names for the size test |

## Escalation

- **STOP and end the run:** a precondition fails; pass mark 1, 3 (over 1 in
  100), 6 or 7 fails; the work needs a change under `Ask/` or a model call.
- **Decide and document:** how "ordinary word" is decided; whether the loose
  pass calls the validator or the scorer directly; the layout of the new
  field; the wording of a case the T2 and T3 tables do not cover (and list it
  in §8).
- **Never:** correct a spelling without the line; ask the officer a question
  (R22: answer for the closest); answer a marked, not-found place as a general
  question (R23); re-read an exactly typed name loosely; restate Ask's cut-off
  as a number of your own; add aliases; call a model; push.

## Gate — green as one set

1. Pass marks 1 to 7.
2. `python -m DiscoverChat.gates`: the baseline plus the three new lines
   green, nothing that was green now red. `python -m pytest
   DiscoverChat/tests -q` green.
3. The report lists every miss and every wrong reading of set B.

Gate holder: the PM replays the harness, the gate and the suite, and shows the
operator the lines of T2 and T3 on real examples.

## Not this package

- **Old and alternative names** that no close spelling reaches (Phulbani for
  Kandhamal; statewide, Balasore for Baleshwar, Keonjhar for Kendujhar). They
  need entries on Ask's alias lists, from someone who knows the names.
- **A place that is not marked and not close** ("How is Rampur doing?"). The
  fallback, if T4 shows it matters, is one small ask to the small model: which
  words of this question are place names.
- **Questions typed in Odia script.**
- **One name held by several Gram Panchayats** (statewide). WP-D15 drops such
  a name; choosing among them is a page matter for WP-D16.
