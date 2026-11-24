# WP-D15 brief — place profile sheets: into the chat

**Workstream:** Discover. **Nature: BUILD + TRIAL.** The service changes, behind
one switch. The trial makes live writer calls. **Authored:** PM, 2026-11-24.
**Decisions:** D75, D76 (the sheets), D77 (the build accepted, fixes ruled),
D78 (the operator's five rulings on this package). **For:** the
operator-controlled implementation agent.
**Comes after:** WP-D14b (`handoffs/WPD14b_profile_fixes.md`). Do not start
until its store, with the name table, is committed.

**The spec is `handoffs/PROFILE_SHEET_SPEC.md`** (§3, §7, §11). Where this
brief and the spec disagree, stop and say so in your report.

## What this package delivers

When an officer asks about a place, the answer is written from that place's
**profile sheet** as well as from the mined insights.

1. **Finding the place.** The chat already reads place names. This package
   turns them into one, two or three sheets, and settles a name that is both a
   Gram Panchayat and a block.
2. **Handing the sheet to the writer**, with the insights, in one request. The
   writer chooses which sheet lines to use.
3. **The number check extended** to sheet lines, with two old gaps closed and
   one new log.
4. **What the officer sees when the writer's answer is refused.**
5. **The answer payload** says which place was answered and which sheet lines
   were used, so the page (WP-D16) can highlight them.
6. **A trial** on held questions, each written three times, with pass marks.

The page itself is WP-D16. Do not touch `frontend/`.

## The rulings this brief encodes

| # | Ruling (operator, 2026-11-24) | What it means for you |
|---|---|---|
| R4 | A name that is both a Gram Panchayat and a block is answered for the **block**, unless the question clearly says Gram Panchayat | T1 |
| R5 | The model chooses what to use from a sheet. No code-set "notable" marks | Every sheet line is optional. You rank and filter nothing on a sheet. |
| R16 | One place named: its full sheet. Two or three places named: lines A1–A7 of each. No place named: no sheet for now | T1, T2 |
| R17 | The writer sees the **whole** sheet (about 62 lines). A fixed core of about 25 lines is the fallback plan if the trial shows the whole sheet is too much for a mid-size model | T2; the trial's mid-size arm |
| R18 | One paragraph is added to the writer's prompt, in the operator's words | T2 — character for character, nothing else in that file |
| R19 | **No fixed set of figures drawn by code.** "Let the model pick the most interesting finding to highlight." | T4, T5: the page will highlight the lines the writer used; you return them in order |
| R20 | Numbers written as words are **logged** during the trial, not blocked | T3 step 7 |

Not changed in this package, on purpose: the rule that every mined insight
handed to the writer must be cited stays as it is. The trial measures an arm
without it, so the operator can rule on it separately.

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d14-pm`)

| Fact | Where |
|---|---|
| One turn: classify → search → judge → writer → number check → one retry → bare sentences → layout. All of it is `Assembler.answer`. | `DiscoverChat/assemble.py:247` |
| Places are read by `SlotExtractor.geography(text)`: Gram Panchayats as **codes** (`gp_lgd_codes`, with `gp_names`), blocks and districts as **names** (`blocks`, `districts`). It returns no positions in the text. | `DiscoverChat/slots.py:143` |
| One typed word can come back as both: `"What should I know about Kalimela"` → Gram Panchayat `119936` **and** block `Kalimela`. Adding "GP" changes nothing today: `"…Kalimela GP"` gives the same two. Four names are both (Bheden, Boipariguda, Kalimela, Laxmipur). A fifth pair comes through an alias: `"Kalyansinghpur"` → Gram Panchayat `121162` and block `Kalyansingpur`. | measured |
| For all 20 Gram Panchayats, 16 blocks and 9 districts, the name the chat returns is exactly the sheet's name. | measured |
| After WP-D14b the reader gives `place(level, code)` and `find(level, name)` from the index alone, besides `available()`, `stamp()`, `get()`, `sentences()`, `sentence(id)`. `sentences()` returns `{"id", "row", "sentence", "note"}` in the hand-over order. | `DiscoverChat/profile_store.py` |
| The writer is handed `[id] sentence` lines under the word `FINDINGS`, after the background brief, the operator's prompt, the run date and the question. A breakdown carries one indented bracket line with its scope note. | `writer.py:227-278` |
| The number check is `checks.check_citations(prose, findings, …)`: step 1 ids known, 2 every numeral in a stored sentence cited in the same sentence, 3 causal words (log), 4 every finding cited, 5 direction words (block). It reads `finding.id`, `.sentence`, `.display_sentence()`, `.is_decomposition`, `.data`. | `checks.py:437` |
| Numerals are read with `\d{4}-\d{2,4}\|\d+(?:[.,]\d+)*`. So "2nd" is read as `2` and a rank is already checked. A year written `2023–24` (short dash, short form) does not match the stored `2023-2024` and fails an honest answer. | `checks.py:49`, D74 |
| Two attempts, then the fall-back: the bare stored sentences of every finding. Failed prose is kept in `logs/citation_failures.jsonl`. | `writer.py:326`, `assemble.py:338` |
| `citations` (id → sentence, display sentence, scope, standing, view, stamp, url) is what the page's hovers are built from; `/record/{id}` serves one record. | `render.py:35`, `main.py:306` |
| `layout.build` draws cards and charts from the mined findings the prose cited. A tag it does not know is ignored. | `layout.py:303` |
| The writer's prompt is pinned by a gate check that lists its ratified additions. | `gates.py:981` (`_prompt_is_appendix_a`) |
| Held questions for writer tests: 50, of which 47 reach the writer; **18 name a place**, all of them exactly one: 5 a Gram Panchayat only, 3 a name that is both a Gram Panchayat and a block (L06 Kalimela, GEO-07 Boipariguda, GEO-18 Laxmipur), 4 a block, 6 a district. Under R4 that is 5 Gram Panchayat sheets, 7 block sheets and 6 district sheets. None names two places. The list is in T6. | `DiscoverChat/experiments/judge_picks.json` |
| `run_writer_trial.py` runs `writer.consolidate` on the held picks: writer calls only, with `--model`, `--only`, `--workers`, `--allow-unused-findings`, `--compare`. | `DiscoverChat/experiments/` |
| For L06 ("What should I know about Kalimela?") the judge kept 18 records, all breakdowns scoped to Kalimela Gram Panchayat. Only 2 of the 18 repeat a sheet list exactly (planned cost by focus area; planned cost by plan year). | measured |
| The writer and judge model is `gpt-6.2-sol`; the classifier's is the smaller `gpt-6-luna` (D69). The gate is `python -m DiscoverChat.gates`, the suite `python -m pytest DiscoverChat/tests -q`. | config, D69 |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] WP-D14b is committed: `python Insights/src/phase5g_profile_sheets.py
      --check` is green and `profile_store.find("block", "Kalimela")` returns
      `["3843"]`.
- [ ] `DiscoverChat/experiments/` is committed (`judge_picks.json`,
      `held_picks.py`, `run_writer_trial.py`, `build_judge_picks.py`,
      `writer_trial_questions.json`). If it is not in your mirror, STOP and ask
      the operator.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d15`. Copy results back to the Drive repo at the end of
      each task.
- [ ] Baselines, kept as files beside the mirror: the gate and the suite before
      any change.
- [ ] The trial (T6) needs the operator's API key in the mirror's `.env`. Ask
      the operator for it if the mirror has none. Never commit it, never print
      it. T1–T5 need no key.
- [ ] Run live calls in parallel. Log every model call and its cost.

---

## T1 — from the question to the places

A new module (suggested `DiscoverChat/place.py`). Pure code: no model call.

**Input:** the text that is searched for this turn, and what
`SlotExtractor.geography` found in it. **Output:** the places to answer for
(level, code, label), how much of each sheet (`full` or `main`), any
alternative the officer may have meant, and a plain note.

Rules, in order:

1. **Names to codes.** A block or a district name becomes a code through
   `profile_store.find`. **Pass `find` the name `geography` returns, never the
   officer's typed words**: `find` matches the stored spelling only. A typed
   "Kalyansinghpur" comes back from `geography` as block `Kalyansingpur`, and
   that spelling finds block 3914; the typed one finds nothing (PM-verified on
   the WP-D14b store: for all 16 blocks and 9 districts, the name `geography`
   returns finds exactly the right code). A name with no sheet is dropped and
   logged. A name
   with more than one code (statewide) is dropped and logged as ambiguous:
   asking "which one?" is not in this package.
2. **One mention, two levels (R4).** When one mention in the text resolved to
   both a Gram Panchayat and a block, keep the **block** — unless the mention
   says Gram Panchayat. "Says Gram Panchayat" means the words `GP`, `G.P.`,
   `Gram Panchayat` or `panchayat` directly after the name, or `GP`, `Gram
   Panchayat` or `panchayat` (optionally with `of`) directly before it. The
   word `block` directly after the name keeps the block. The level not chosen
   becomes the **alternative**.
   - "One mention" is decided by position in the text, not by comparing names:
     the alias pair Kalyansinghpur / Kalyansingpur must behave like the other
     four. You may add the matched positions to what `geography` returns, as a
     new field. Its existing fields and their values must not change.
3. **A place named with its own parent.** "Itipur in Bhubaneswar block" names
   two places in two mentions. The Gram Panchayat is the subject; a named
   parent (its block, its district) is dropped.
4. **Count what is left (R16).** One place: `full`. Two or three: `main` for
   each (lines A1–A7 only). None, or more than three: no sheet, and the turn
   runs exactly as today.
5. **The note**, only when rule 2 chose between two levels: `This answer is
   about Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".`
   (and the mirror image when the officer said GP). The quoted words must
   resolve, by these same rules, to the alternative.

**Which turns.** Sheets are used on a turn that searches: the `retrieve` and
`decompose` moves, and a `navigate` turn that falls through to a search. Not
on `lookup` (still sent to Ask) and not on `why` (still the reframe). A walk
that `navigate` answers on its own is unchanged.

**The table your tests must reproduce:**

| Text | Result |
|---|---|
| What should I know about Kalimela? | block 3843, full; alternative Gram Panchayat 119936; note |
| What should I know about Kalimela GP? | Gram Panchayat 119936, full; alternative block 3843; note |
| How is Kalimela Gram Panchayat doing | Gram Panchayat 119936, full |
| the panchayat of Kalimela | Gram Panchayat 119936, full |
| How is Kalimela block doing | block 3843, full |
| Kalyansinghpur | block 3914 (Kalyansingpur), full; alternative Gram Panchayat 121162; note |
| How is Chikilli doing? | that Gram Panchayat, full; no alternative, no note |
| How is Barpali block doing? | block 3676, full |
| How is Khordha district doing overall? | district 321, full |
| How is Itipur doing in Bhubaneswar block | Gram Panchayat Itipur, full (the parent is dropped) |
| Compare Kalimela and Bheden | blocks 3843 and 3678, main each; two alternatives |
| Compare Kalimela, Bheden, Laxmipur and Boipariguda | no sheet (four places) |
| Which blocks stand out on expenditure? | no sheet |

---

## T2 — what the writer is handed

1. **Place facts come before the findings**, one block per place, headed by the
   place's label:

```
PLACE FACTS — Kalimela block
[p-block-3843-A1] Kalimela block has 852 planned activities, the 5th most of 16 blocks. The middle value for these 16 is 712.
[p-block-3843-A2] 392 of them (46.0%) have no cost attached.
…
[p-block-3843-F1] 168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. The middle value is 104.
    (An activity with no approval on file is not known to be unapproved; the record may simply be missing.)
…

FINDINGS
[d1-30946] …
```

   - `full`: every sentence `profile_store.sentences()` returns, in its order.
     `main`: rows A1–A7 only.
   - Sentences exactly as stored. A sentence with a note carries it on one
     indented bracket line, as a breakdown carries its scope note.
   - No scores, no marks, no ordering of your own (R5).
2. **The prompt paragraph (R18).** Add this paragraph to
   `DiscoverChat/context_brief.py`, character for character, as its own
   constant, and put it into the writer's prompt **only on a turn that hands
   place facts**, directly before the prompt's last line ("Return only the
   finished prose."):

> Some answers also come with PLACE FACTS: standard figures about the place the officer asked about, each with an id starting p-. Start from the place facts that answer the question, then bring in the findings. You do not have to use every place fact. Tag them the same way as findings.

   This is the operator's file. That paragraph is the only change you may make
   to it. Add it to the gate's list of ratified additions, citing D78.
3. **How many insights go with a sheet.** On a turn that hands place facts, at
   most **8** mined insights are handed to the writer: the first 8 in the
   order the service already uses. The cap is one setting. Insights past the
   cap are not shown and are counted in the payload. A turn with no place
   facts keeps today's cap of 20.
   - No "already on the sheet" filter. The PM measured it on L06: 2 of 18. The
     writer's prompt already tells it to merge repeats, and check 4 of the
     build proves a sheet and an insight give the same digits.
4. **A place question with no mined insight is still answered**, from the
   sheet alone. Today it ends in "the analysis has nothing on this"; with a
   sheet it goes to the writer with place facts and no findings. This is the
   normal case statewide, where places are not mined.
5. **A turn with no place facts must be untouched**: the prompt text built for
   it is byte-identical to today's. A test proves it.

---

## T3 — the number check

`checks.check_citations` learns about the place facts handed on this turn. For
a turn with none, every result is what it is today, except for the two fixes
marked "all answers".

| Step | Change |
|---|---|
| 1 ids known | The ids of the place facts handed on this turn are known ids. |
| 2 numerals | A numeral may be supported by the stored sentence of a place fact cited in the same sentence, exactly as by a finding's. **All answers:** before numerals are read, the short and long dashes in the prose are read as a hyphen, and a fiscal year written short (`2023-24`) matches the stored long form (`2023-2024`) when the years are consecutive. Nothing else about matching loosens: `Rs 7.65 crore` still cannot become `Rs 7.7 crore`. |
| 3 causal | Unchanged. |
| 4 all findings cited | **Place facts are never required.** The rule covers the mined insights handed on this turn only. |
| 5 direction | The A7 line ("Spending is Rs 5.90 crore below plan.") is held to the same wrong-word test as a breakdown of `overspend_vs_plan`: a sentence that cites it must not say the opposite. Use the existing word list; add none. |
| 6 standing (new) | See below. Its own setting: `block`, `log` or `off`. |
| 7 number words (new, R20) | See below. `log` or `off`. Never counts against an answer. |

**Step 6 — standing phrases.** In a sentence of the prose that cites at least
one place fact, every standing phrase must be found in the stored sentence of
some record cited in that same sentence. A standing phrase is one of:

- an ordinal and an end word: `2nd highest`, `5th lowest`, `joint 10th most`,
  `3rd fewest`;
- the first-place form: `the highest of|among|in`, `the lowest …`, `the most
  …`, `the fewest …`, with or without `joint`;
- a quarter: `lowest quarter`, `lower-middle quarter`, `upper-middle quarter`,
  `highest quarter`.

"Found" means the same rank with the same end word (or the same quarter word)
stands in the cited sentence. So "the 4th lowest of 16 blocks" passes when it
cites A6, and "the 4th highest" fails. A sentence that cites no place fact is
not checked. Ship it as `block`; the trial decides whether it stays there (T6,
pass mark 4).

**Step 7 — numbers written as words.** A scan of the shown prose for words
that state a number without digits: ordinals from "second" to "twentieth";
"half", "third", "quarter" (but not the stored phrase "… quarter of the"),
"two-thirds", "three-quarters"; "double", "twice", "triple", "tenfold";
"majority". The list is data, beside the other trigger lists. Each hit is
written to `logs/citation_failures.jsonl` with `kind: number_words_shown`,
`fell_back: false`, the words and their sentences, in the way causal words are
logged today. It changes no answer.

The retry message (`citation_failure_reason`) gains one plain sentence for a
step 6 failure, naming the phrase and the line it should have matched.

---

## T4 — when the writer's answer is refused, or there is no writer

R19: the model picks what to show; code supplies a fixed set only when the
model picked nothing.

| Case | What the officer sees |
|---|---|
| Both attempts refused | Under the place's label, **the place facts the writer cited in its last attempt** (ids among those handed, in the order first cited, each once), in their stored wording. Then the mined insights' bare sentences, as today. |
| The same, but the last attempt cited no place fact; or the writer call failed or returned nothing | Under the place's label, lines **A1–A7**. Then the mined insights' bare sentences. |
| The model is off (`allow_model=False`) or consolidation is off | Lines A1–A7 under the label, then today's text. Deterministic, so the offline gate can pin it. |
| Two or three places | One labelled group per place, by the same rules. |

Each group starts with a line holding the place's label, so "Its planned cost
is…" is never shown without its place.

---

## T5 — what the service returns

1. **`citations`** gains one entry per place fact handed, in the shape of
   today's entries, so the present page's hovers work with no front-end
   change: `id`, `sentence` (as stored), `display_sentence` (the label and a
   colon in front when the sentence does not itself begin with the label:
   `Kalimela block: Its planned cost is Rs 7.65 crore, …`), `scope` (the
   label), `standing` (the note, or empty), `view` (`Place profile`),
   `is_decomposition: false`, `is_profile: true`, `stamp`, `url`.
2. **`/record/{id}`** answers for a `p-` id: the sentence, the label, the row,
   the stored figures of that row as the sheet holds them, the note, the run
   stamp. JSON and the HTML form.
3. **`answer_html`** (the reference render) wraps place-fact tags like any
   other.
4. **A new field `place`** on the response (`{}` when no sheet was used):

```
{"version": 1,
 "mode": "full" | "main",
 "answered":     [{"level", "code", "name", "label"}, …],
 "alternatives": [{"level", "code", "label", "ask": "Kalimela GP"}, …],
 "note": "This answer is about Kalimela block. For the Gram Panchayat, ask about \"Kalimela GP\".",
 "lines_offered": 61,
 "lines_used": ["p-block-3843-A6", "p-block-3843-A1", …],
 "insights_offered": 8,
 "insights_held_back": 10}
```

   - `lines_used` is the place facts in the answer the officer is shown, in
     the order first used. On a fall-back it is the lines of T4. **This is what
     WP-D16 will highlight** (R19).
   - The same facts go into `retrieval` for the call log.
5. **The note is also the first line of `answer`**, when there is one, so the
   present page shows it. Code writes it; it is outside the prose and outside
   the number check.
6. **`findings`, `layout`, the session's anchors: unchanged.** Place facts are
   not findings and make no cards in this package.
7. **Start-up.** The service opens the sheet store once when it starts. If the
   store is missing or refused, the service runs without sheets, says why in
   `/health`, and answers as it does today. It never fails to start because
   of the sheets.
8. **Switches** (in `config.py`, shown in `knobs()`):

| Setting | Default | Meaning |
|---|---|---|
| `DISCOVERCHAT_PROFILE_SHEETS` | see the gate | `0` restores today's service, byte for byte |
| `DISCOVERCHAT_PROFILE_INSIGHT_CAP` | `8` | insights handed with a sheet |
| `DISCOVERCHAT_PROFILE_MAX_PLACES` | `3` | more places than this: no sheet |
| `DISCOVERCHAT_STANDING_CHECK` | `block` | step 6: `block`, `log`, `off` |
| `DISCOVERCHAT_NUMBER_WORDS` | `log` | step 7: `log`, `off` |

---

## T6 — the trial

Extend `run_writer_trial.py` so a run can hand place facts the way the service
now does (T1–T4 as shipped, no copy of the logic). Writer calls only; the held
judge picks are not re-made.

**Questions.** The 18 held questions that name a place:

L01 Kandhamal, L04 Cuttack, L06 Kalimela, T02 Chikilli, T04 Barpali block, T14
Ganjam, GEO-06 Biswamathpur, GEO-07 Boipariguda, GEO-12 Haldikudar, GEO-18
Laxmipur, GEO-19 Mendarajpur, GEO-20 Sharagada, GEO-22 Attabira block, GEO-24
Lahunipara block, GEO-26 Sheragada block, GEO-29 Khordha district, GEO-30
Koraput, GEO-32 Sundargarh district.

Add three questions that name two places (for example "Compare Kalimela and
Bheden") to `writer_trial_questions.json` and hold their judge picks with
`build_judge_picks.py`. Those three judge calls are the only ones allowed. The
50 held entries must be byte-identical afterwards.

**Arms.**

| Arm | What | Runs |
|---|---|---|
| `current` | today's path: no place facts, the held picks as they are | 1 per question |
| `sheet` | this package as shipped | **3 per question** |
| `sheet_choose` | the same with `--allow-unused-findings` (mined insights optional too) | 3 per question |
| `sheet_midsize` | `sheet`, written by the smaller model this project already calls (`gpt-6-luna`), unless the operator names another | 1 per question |

**Measured, per answer and per arm:**

- kept or lost (lost = both attempts refused), and the step that refused it;
- **wrong numbers shown**: re-read every shown answer with a second,
  independent pass — every numeral must stand in the stored sentence of a
  record tagged in its sentence. The count must be 0;
- place facts used: how many, which rows; whether the answer uses the share of
  plan spent (A6) and at least one line with a standing;
- **how far three runs differ**: for each question, the place facts used in
  all three runs, in two, in one;
- words, sentences, words per sentence (the measures the runner already has);
- every step 6 refusal, each judged by you as a true catch or a false alarm,
  with the sentence;
- every step 7 log line, each judged as supported by the cited sentences or
  not;
- fall-backs: how many place facts they showed (the largest and the middle
  value);
- any answer that gives two different by-year spending series (the sheet's is
  by plan year; a held insight from the month cube is by payment year) — count
  and quote them;
- writer time and tokens, `current` against `sheet`.

**To read.** For L06 Kalimela, the report prints in full: the `current`
answer, the three `sheet` answers, the three `sheet_choose` answers and the
`sheet_midsize` answer. The PM shows these to the operator beside the raw
model's answer of 2026-11-24.

**Pass marks.**

1. Wrong numbers shown: **0**, in every arm.
2. The `sheet` arm loses no larger a share of its answers than the `current`
   arm does on the same 18 questions, plus one answer in 18 of slack.
3. With `DISCOVERCHAT_PROFILE_SHEETS=0`, the offline behaviour suite's answers
   are byte-identical to the baseline.
4. Step 6 made **no false alarm**. If it made one, set its default to `log`,
   say so, and that is a finding for the PM, not a failure of the package.
5. Reported, not a pass mark: the share of kept `sheet` answers that use A6
   and a standing line; the three-run agreement; the mid-size arm's lost share
   and length against `sheet` (this is the evidence for R17's fallback plan);
   `sheet_choose` against `sheet` (the evidence for the every-insight rule).

**If marks 1–3 hold, ship `DISCOVERCHAT_PROFILE_SHEETS` default on. If any
fails, ship it default off, and STOP for the PM.** Either way, do not push and
do not deploy.

Outputs: `handoffs/WPD15_trial/` (the runner's JSON and the answers as
markdown), and the tables in the report.

---

## T7 — tests, gate lines, report

**Tests** (`DiscoverChat/tests/test_place_answers.py`, offline, no model):
the T1 table; the T2 payload for a `full` and a `main` turn; the prompt
paragraph present only with place facts, and a no-place prompt byte-identical
to today's; a sheet-only answer when the judge kept nothing; each row of the T3
table with one passing and one failing sentence (in the manner of the WP-D13
tables); the short fiscal year and the dashes; the four cases of T4; the
`citations`, `/record` and `place` payloads; the service starting with no
store. Every existing test passes unchanged.

**Gate lines** (new): `place-resolution` (the T1 table); `place-facts-optional`
(an answer that cites no place fact passes step 4); `place-standing-check`
(the step 6 examples); `place-prompt-ratified` (the R18 paragraph, character
for character, D78); `place-switch-off-identical` (pass mark 3).

**Report** `handoffs/WPD15_REPORT.md`, in the form of the WP-D14 report: §0 the
gate table with evidence; §1 what was built, file by file; §2 the T1 table,
expected against actual; §3 one full prompt as sent for L06 (the place facts
and the findings); §4 the trial tables and the L06 answers in full; §5 the
gate and the suite, baseline against final; §6 every model call and its cost;
§7 the decision journal; §8 anything in the spec or this brief that was wrong
or silent.

**Commit per task on the current branch (`WP-D15 T<n>: …`). Do not push.**

---

## Files in scope (you may write ONLY these)

```
DiscoverChat/place.py                          new — T1, and building the place-fact lines
DiscoverChat/assemble.py                       T1, T2, T4, T5
DiscoverChat/writer.py                         T2, T4
DiscoverChat/checks.py                         T3
DiscoverChat/render.py                         T5
DiscoverChat/main.py                           T5
DiscoverChat/config.py                         T5 — the five settings
DiscoverChat/slots.py                          T1 — matched positions as a new field, nothing else
DiscoverChat/context_brief.py                  T2 — the one approved paragraph, nothing else
DiscoverChat/gates.py                          the new lines; the ratified addition
DiscoverChat/tests/test_place_answers.py       new
the step 7 word list                           new, as data beside the other trigger lists
DiscoverChat/experiments/run_writer_trial.py   T6 — the place-facts arms
DiscoverChat/experiments/writer_trial_questions.json, judge_picks.json   T6 — the three new questions appended
handoffs/WPD15_REPORT.md, handoffs/WPD15_trial/**                        new
```

**DO NOT TOUCH:** `Insights/**` (the builder and the store are done — if the
reader or the store needs a change, STOP); `DiscoverChat/profile_store.py`,
`judge.py`, `classifier.py`, `retrieval.py`, `corpus.py`, `layout.py`,
`glossary.py`, `navigate.py`, `session.py`; every other file in
`DiscoverChat/experiments/`; `Ask/**`; `frontend/**`; `deploy/**`; `Data/**`;
every `.env` (read it, never write or commit it); `handoffs/PROJECT_PLAN.md`;
`handoffs/PROFILE_SHEET_SPEC.md`.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/PROFILE_SHEET_SPEC.md` §3, §7, §11, Appendix A | What a sheet is, the rulings, what the lines look like |
| `handoffs/WPD14_REPORT.md` §3 and `handoffs/WPD14b_REPORT.md` | The real sheets, line by line |
| `DiscoverChat/assemble.py` (`Assembler.answer`) | The one place a turn is put together |
| `DiscoverChat/writer.py` (`consolidate`, `build_consolidation_prompt`) | The request, the retry, the fall-back |
| `DiscoverChat/checks.py` (`check_citations`, `bind_numerals`, `check_direction`, the causal log) | The steps you extend, and the form a `log` step takes |
| `handoffs/WPD13_report_fixes.md` (Fix 1b, Fix 6) and `handoffs/WPD13b_REPORT.md` | How a new check was shipped as a word list, and what a false alarm cost last time |
| `DiscoverChat/render.py`, `main.py` | Hovers and `/record` |
| `DiscoverChat/experiments/run_writer_trial.py`, `held_picks.py` | The trial tool you extend |

## Escalation

- **STOP and end the run:** a precondition fails; the reader or the store
  needs a change; a no-place answer changes with the switch on; the trial
  shows a wrong number in an answer the officer would see; pass mark 1, 2 or 3
  fails; the R18 paragraph cannot go in character for character.
- **Decide and document** (report §7): how the place facts travel through the
  code beside the findings; where the matched positions come from; the layout
  of the `/record` payload for a place fact; the exact word list of step 7.
- **Never:** rank, filter or mark sheet lines (R5, R19); add a figure, a card
  or a fixed highlight set by code; let the writer or the service work out a
  number; change a sheet sentence; edit the prompt beyond the R18 paragraph;
  re-run the judge on the 50 held questions; change the judge, the classifier
  or the search; touch `frontend/`; push or deploy.

## Gate — green as one set

1. The T1 table reproduced by tests and by the `place-resolution` gate line.
2. A no-place turn is untouched: prompt byte-identical, answers identical with
   the switch off (pass mark 3).
3. `python -m DiscoverChat.gates`: the baseline plus the five new lines green,
   the two D69 reds unchanged, nothing that was green now red.
   `python -m pytest DiscoverChat/tests -q` green.
4. Trial pass marks 1 and 2 hold; mark 4 is reported with every step 6
   refusal judged.
5. The report holds the trial tables, the L06 answers in full and the cost of
   every model call.

Gate holder: the PM replays the offline gate and suite, reads the trial
answers, and shows the operator the Kalimela answers side by side.

## Not this package — notes for WP-D16 (page)

- Highlighting the lines in `place.lines_used`, in the writer's order (R19).
- A one-click switch built from `place.alternatives` in place of the text
  note.
- Asking "which one?" when a name has several codes (statewide).
- A sheet for a question that names no place, or more than three (R16 parks
  it).
- Whether the every-insight rule is relaxed (the `sheet_choose` arm is the
  evidence).
