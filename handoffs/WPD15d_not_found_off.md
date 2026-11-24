# WP-D15d brief — the "could not find a place" reply is removed

**Workstream:** Discover. **Nature: BUILD, offline.** No model call, no API
key. **Authored:** PM, 2026-11-24.
**Decisions:** D84 (the review, finding 3), D85 (the operator's ruling R29).
**For:** the operator-controlled implementation agent.
**Comes after:** WP-D15c, WP-D15b and WP-D17, all executed and accepted
(D84). Tree `f3f7982`.
**Read `handoffs/WPD15b_REPORT.md` §2 (the T3 table) and §6 item 5 first.**

## What this package does

One change. The chat no longer replies "I could not find a place called …",
and no longer ends a turn because of it. **The code is deleted, not switched
off.** There is no setting.

Reading a misspelt place name is **not** changed. `Reading "Kalimella" as
Kalimela block.` works exactly as it does today.

This is a small package. Do not widen it.

## The ruling (operator, 2026-11-24, D85)

| # | Question | Ruling |
|---|---|---|
| R29 | The "could not find a place called …" reply stops ordinary questions (below). Keep the line and always answer, take the line out, or leave it? | **Take it out** ("No, option B"). Asked whether to keep the code behind a switch for later: **"Drop the line"** — it is deleted. A question whose marked word matches no place is searched and answered as it was before WP-D15b, with no line about it. |

The operator also said, the same day: *"Don't over engineer the fuzzy search
on name. We can deal with that later."* So this package does **not** tune the
word list, the cut-off, the marks or anything else in the loose pass. It only
removes the reply.

**Why it goes.** The chat knows 45 places. For any other word it can only
guess. Today a word is taken for "a place the officer named" when it sits
directly before "block", "district", "GP" or "panchayat", starts with a
capital, has 5 letters or more, and is not on the list of 1,045 ordinary
words. That list was built from the project's own text, so it misses everyday
words the data does not use. To the chat, "Tribal block" and "Jeypore block"
look the same.

| The officer types | Today | After this package |
|---|---|---|
| How many works in Tribal block areas are still ongoing? | Only `I could not find a place called "Tribal" in the data.` Nothing searched. | Searched and answered. No such line. |
| How is MGNREGA block convergence going? | Only `I could not find a place called "MGNREGA" in the data.` | Searched and answered. No such line. |
| Kitne GP me kaam adhura hai? | Only `I could not find a place called "Kitne" in the data.` | Searched and answered. No such line. |
| Show Adivasi GP spending | Only `I could not find a place called "Show Adivasi" in the data.` | Searched and answered. No such line. |
| What about Jeypore block? (a real place, not in the sample) | Only `I could not find a place called "Jeypore" in the data.` | Searched and answered as before WP-D15b. No such line. |
| How is Bhedan block doing? (one letter from Bheden; scores 83.3, under the cut-off) | `I could not find a place called "Bhedan" in the data.` / `Close names in the data: Bheden block.` | Searched and answered as before WP-D15b. No line, no close names. |
| How is Rampur block doing compared with Barpali block? | `I could not find a place called "Rampur" in the data.` above the Barpali block answer | The Barpali block answer. No line about Rampur. |
| How is Barpalli block doing? | `Reading "Barpalli" as Barpali block.` | **Unchanged.** |
| What should I know about Kalimella? | `Reading "Kalimella" as Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".` | **Unchanged.** |
| How is Sharagada block doing? | `Reading "Sharagada" as Sheragada block.` | **Unchanged.** |

The operator knows the cost: a real place outside the data, and a near miss
under the cut-off, get a general answer with no notice, as they did before
WP-D15b.

---

## What exists (PM-verified 2026-11-24, in `C:\dev\odisha-d17-pm`, tree `f3f7982`)

Everything in the first table goes. Everything in the second stays.

**Goes**

| What | Where |
|---|---|
| The block that finds "a word marked as a place that reads as nothing" and returns it in `not_found`, with the capital-letter rule inside it. | `DiscoverChat/slots.py:392-415` (inside `read_places`) |
| `Slots.not_found`, the `not_found` key of `read_places()`, and the lines that carry it. | `slots.py:105`, `165`, `170` |
| `CLOSE_NAME_FLOOR` (used only by that block). | `slots.py:479-481` |
| The stop: on a searching move, an early `extract()` and the return of the "not found" answer. | `DiscoverChat/assemble.py:301-309` |
| The "could not find" part of the answer's first line. | `assemble.py:455-465` |
| `_not_found_answer`, with the `place` field's `mode: "not_found"`. | `assemble.py:480-488` |
| `not_found_message`, `not_found_first_lines`, and the `not_found` argument and key of `spelling_payload`. | `DiscoverChat/place.py:463-510` |
| The comment lines that describe the reply. | `assemble.py:555`, `config.py:467`, `place.py:404-405` |
| The gate line that asserts the stop. | `gates.py:1570-1587`, `place-spelling-not-found` |
| The tests of the stop and of the message. | `DiscoverChat/tests/test_place_spelling.py` (lines 125-178 and 211) |

**Stays**

| What | Where |
|---|---|
| The loose readings, the reading line, the other close names of a loose reading. | `slots.py`, `place.py` (`loose_choices`, `reading_note`) |
| The marks and `marked_level`. The loose pass uses them: a marked word is tried at the marked level only, and a level word beats an exact match at another level. | `slots.py:483-508`; used at `308` and `328` |
| The ordinary-word list, the cut-off, the 5-letter floor. | `ordinary_words.json`, `config.py:468-473` |
| `DISCOVERCHAT_LOOSE_PLACES` and `DISCOVERCHAT_LOOSE_MIN_LETTERS`. | `config.py` |
| The gate line `place-spelling-exact-unchanged` checks that no held question is "not found" (`gates.py:1536`). Keep the line; drop that one assertion with the key. | `gates.py` |

Other facts:

| Fact | Where |
|---|---|
| The page does not read `not_found` or `mode: "not_found"`. | no match under `frontend/` |
| The WP-D15b harness reads `not_found` in many places and its set C expects the message on 2 of 14 rows ("How is Laxmipoor block doing?", "How is Rampur block doing?"). | `handoffs/WPD15b_spelling/harness.py` (lines 115-119, 223, 284-294, 305-338, 434, 462, 488, 514) |
| The PM's probe: 57 everyday questions; 12 end with the message today, 9 of them wrongly. | Appendix A |
| Baselines to expect: gate 51 of 53 (red: `judge-model-evidenced`, `classifier-model-evidenced`, by D69); suite 325 passed. | D84 |

---

## T0 — preconditions and baselines (STOP on failure)

- [ ] The tree holds this brief and D84 and D85 in
      `handoffs/PROJECT_PLAN.md`, or the operator tells you to proceed.
- [ ] Work from a fresh local mirror, never the Drive path:
      `C:\dev\odisha-d15d`. Copy results back at the end of each task.
- [ ] Baselines on the untouched mirror, before any edit: the gate (51 of
      53) and the suite (325). If they differ, STOP.
- [ ] **Record today's reading**, before any edit: the full output of
      `SlotExtractor().read_places(question)` for every question of
      - set A of the WP-D15b harness (298: the 245 CSV rows and the 53 held
        questions),
      - set C of the harness (14),
      - Appendix A (57).

      That is 369 questions. Save it as
      `handoffs/WPD15d_not_found/before.json`. Pass mark 1 is measured
      against this file.
- [ ] No model call is needed anywhere in this package. If you find you need
      one, STOP.

## T1 — remove the reply

1. Delete everything in the **Goes** table. No setting, no flag, no dead
   branch left behind.
2. After the change, `read_places()` has no `not_found` key and `Slots` has
   no `not_found` field. No answer can end without a search because of a
   place name. The `place` field has no `not_found` key and never has `mode:
   "not_found"`.
3. Touch nothing in the **Stays** table. The reading of every question is the
   same as today in every other field.
4. The first line of an answer is built from the reading lines and the R4
   note only, joined as today.
5. When you are done, search `DiscoverChat/` for `not_found` and for `could
   not find`. Nothing may be left that belongs to this reply. (`config.py:126`
   mentions `model_not_found`; that is another matter and stays.)

## T2 — tests, the gate line, the harness

1. **Delete** the tests of the stop and of the message. List each deleted
   test by name in the report.
2. **Keep** every other test in `test_place_spelling.py`. Change one only
   where it passes `not_found` as an argument or reads it as a key.
3. **New tests:**
   - each of the 12 questions marked STOP in Appendix A: no loose reading;
     the reading equals the reading with `DISCOVERCHAT_LOOSE_PLACES=0`; and
     the assembler reaches the search (use the stubbed retriever that the
     old "searches nothing" test used, and assert the opposite);
   - "How is Rampur block doing compared with Barpali block?": Barpali block
     is read; the answer's first line holds nothing about Rampur;
   - the three "Unchanged" rows of the table above give their line word for
     word;
   - no answer text built by the chat's code can hold "could not find a
     place" (assert the two functions are gone from `place`).
4. **The gate.** Remove `place-spelling-not-found`. Add
   `place-spelling-never-stops` in its place: 'Bhedan block', 'Rampur block'
   and 'Tribal block' are searched, are answered, and carry no line about the
   word. The count stays 53.
5. **The harness** (`handoffs/WPD15b_spelling/harness.py`). Change it only
   as far as it needs to run on the new code: drop its reads of `not_found`
   and its "could not find" counts; set C rows "How is Laxmipoor block
   doing?" and "How is Rampur block doing?" now expect no line. Run it once
   and save its output under `handoffs/WPD15d_not_found/` (use `--out`). Do
   **not** write over `handoffs/WPD15b_spelling/results.json` or
   `RESULTS.md`; they are the record of WP-D15b.

## Pass marks

| # | Pass mark | How measured |
|---|---|---|
| 1 | For all 369 recorded questions, `read_places` equals `before.json` in every field that still exists. Nothing but the `not_found` key is gone. | Compare against T0's record; save `handoffs/WPD15d_not_found/after.json` |
| 2 | None of the 12 STOP questions of Appendix A ends without a search. | The new tests |
| 3 | The harness, run on the new code: set B's "read right" and "wrong readings" numbers are exactly WP-D15b's (97.1%, 65.8%, 12 wrong, all between the near-names); set C 14 of 14 with the two rows changed as T2 point 5 says. | The harness output |
| 4 | With `DISCOVERCHAT_LOOSE_PLACES=0`: the gate and the suite behave as they do today with it off; `place-switch-off-identical` green. | Run both |
| 5 | Gate 51 of 53, the same two reds. Suite: 0 failed; report the number deleted and the number added. | Run both |

A failure of pass mark 1 or 3 is a STOP.

---

## Files in scope (you may write ONLY these)

```
DiscoverChat/slots.py                           T1 — the "not found" parts only
DiscoverChat/assemble.py                        T1 — the stop, its answer, the first-line part
DiscoverChat/place.py                           T1 — the two message functions, the payload's key
DiscoverChat/config.py                          T1 — the one comment line
DiscoverChat/gates.py                           T2 point 4, and the one assertion at line 1536
DiscoverChat/tests/test_place_spelling.py       T2
handoffs/WPD15b_spelling/harness.py             T2 point 5
handoffs/WPD15d_not_found/**                    new
handoffs/WPD15d_REPORT.md                       new
```

**DO NOT TOUCH:** `DiscoverChat/ordinary_words.json` and its builder;
`DiscoverChat/context_brief.py`; `checks.py`, `writer.py`, `render.py`,
`layout.py`, `main.py`, `judge.py`, `classifier.py`, `retrieval.py`;
`experiments/**`; `handoffs/WPD15b_spelling/results.json`, `RESULTS.md`,
`t0_geography.json`; `Insights/**`; `Ask/**`; `frontend/**`; `deploy/**`;
every `.env`; `handoffs/PROJECT_PLAN.md`; every other brief and report. If
the change cannot be made without one of these, STOP and say what is needed.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD15b_REPORT.md` §2, §6 items 4, 5, 11, 12 | What the stop does today and the choices behind it |
| `DiscoverChat/slots.py` (`read_places`; lines 300-330 and 392-415) | What goes, and the uses of `marked_level` that stay |
| `DiscoverChat/assemble.py` (lines 301-309, 455-490, 555) | The stop and the first line |
| `DiscoverChat/place.py` (lines 404-510) | The message functions and the payload |
| `DiscoverChat/tests/test_place_spelling.py` | The tests to delete, and the stub to reuse |

## Escalation

- **STOP and end the run:** a precondition fails; pass mark 1 or 3 fails; the
  change needs a file on the do-not-touch list; you find you need a model
  call.
- **Decide and document:** the exact name and wording of the new gate line;
  which existing tests needed a changed argument.
- **Never:** add words to the ordinary-word list; change the cut-off, the
  marks or the 5-letter floor; put a different message in place of the old
  one; keep the reply behind a setting; change the reading line; push.

## Gate — green as one set

1. Pass marks 1 to 5.
2. The report, `handoffs/WPD15d_REPORT.md`, short: the pass marks with
   evidence; the table of "What this package does" as expected against
   actual; the list of what was deleted (functions, tests, the gate line);
   the gate and the suite, baseline against final; a decision journal; what
   in this brief was wrong or silent.

Commit per task with a clear message. Do not push.

Gate holder: the PM replays the gate and the suite and runs Appendix A
through the committed code.

## Not this package

- A full list of the state's place names, so the chat can tell "a place not
  in this data" from "not a place". With that list a reply of this kind
  could be built again, correctly. Parked by the operator (D84, D85).
- The cut-off (85 against 80), the ee / oo / garh spellings, a Hindi and Odia
  word list. Parked.
- The page (WP-D16).

---

## Appendix A — the PM's 57 probe questions, and what happens today

Made up by the PM to hunt for false stops, so the share is not a rate. STOP =
today the turn ends with "I could not find a place called …". The quoted word
is the one the message names.

| # | Question | Today |
|---|---|---|
| 1 | Which Gram Panchayat has the most abandoned works? | ok |
| 2 | How many works in Tribal block areas are still ongoing? | **STOP** "Tribal" — not a place |
| 3 | Show me SC block spending this year | ok |
| 4 | Compare Sanitation GP spending with Drinking Water GP spending | ok |
| 5 | In which District is spending lowest? | ok |
| 6 | Does every Block have a sanction on file? | ok |
| 7 | What is the Total GP expenditure in 2024-25? | ok |
| 8 | Do PESA blocks spend less than other blocks? | ok |
| 9 | Which Sarpanch block has the highest sanctions? | ok |
| 10 | Why is Jal Jeevan block spending so low? | ok |
| 11 | Is the Finance Commission district grant being used? | ok |
| 12 | How is MGNREGA block convergence going? | **STOP** "MGNREGA" — not a place |
| 13 | Which Scheme block has no cost recorded? | ok |
| 14 | What did the BDO of Kalimela block sanction? | ok (Kalimela read exactly) |
| 15 | Tell me about the Sarpanch of Chikilli GP | ok (Chikilli read exactly) |
| 16 | How are Roads district wise? | ok |
| 17 | Show Education GP wise spending | ok |
| 18 | Top GP by spending in Koraput district | ok (Koraput read exactly) |
| 19 | Which GP in Bargarh district spends the least on Sanitation? | ok (Bargarh read exactly) |
| 20 | Anything unusual in Rangeilunda block for Drinking Water? | ok (Rangeilunda read exactly) |
| 21 | What about Swachh Bharat GP level works? | ok |
| 22 | How is the Panchayat of Laxmipur doing on Housing? | ok (Laxmipur read exactly) |
| 23 | Is Odisha district spending improving? | ok |
| 24 | What is the State district average? | ok |
| 25 | How is Kalimela doing compared with the State? | ok (Kalimela read exactly) |
| 26 | Are Theme 4 GP plans funded? | ok |
| 27 | How many Completed block works are there? | ok |
| 28 | Which Ongoing GP works are oldest? | ok |
| 29 | Is Untied GP money planned well? | ok |
| 30 | How does Tied block money compare with Untied? | ok |
| 31 | What should I know about Bhubaneswar? | ok (read exactly) |
| 32 | What should I know about bhubaneshwar? | ok (read loosely as Bhubaneswar block, 95.7) |
| 33 | How is Khurda doing? | ok (alias of Khordha) |
| 34 | how is rampur block doing | ok (lowercase, left alone) |
| 35 | How is Sundargarh district doing? | ok (read exactly) |
| 36 | How is Sundergarh district doing? | ok (alias of Sundargarh) |
| 37 | How is Ganjam doing on drinking water? | ok (read exactly) |
| 38 | How is Gangam doing? | ok (left alone) |
| 39 | Kaunsa GP sabse zyada kharch karta hai? | **STOP** "Kaunsa" — Hindi for "which" |
| 40 | Which GPs in Malkangiri have photo evidence? | ok (Malkangiri read exactly) |
| 41 | Konta GP re sabu thu besi kharcha heichi? | **STOP** "Konta" — Odia for "which" |
| 42 | Kitne GP me kaam adhura hai? | **STOP** "Kitne" — Hindi for "how many" |
| 43 | Which Aspirational district has the lowest spending? | **STOP** "Aspirational" — not a place |
| 44 | Is any Maoist block behind on spending? | **STOP** "Maoist" — not a place |
| 45 | How do Coastal districts compare with Western districts? | ok |
| 46 | Which Scheduled block has most abandoned works? | ok |
| 47 | Does the Nabarangpur district appear in the data? | **STOP** "Nabarangpur" — a real place, not in the sample |
| 48 | How is Puri district doing? | ok (4 letters, left alone) |
| 49 | What about Jeypore block? | **STOP** "Jeypore" — a real place, not in the sample |
| 50 | Mayurbhanj district me kya chal raha hai? | **STOP** "Mayurbhanj" — a real place, not in the sample |
| 51 | Show Adivasi GP spending | **STOP** "Show Adivasi" — not a place |
| 52 | How is my GP doing? | ok |
| 53 | Is the Collector of Koraput district aware? | ok (Koraput read exactly) |
| 54 | Which Model GP is the best? | **STOP** "Model" — not a place |
| 55 | Are Urban blocks included? | ok |
| 56 | Is PMAY district wise data available? | ok |
| 57 | Which Backward block needs attention? | ok |

Twelve STOP rows: 2, 12, 39, 41, 42, 43, 44, 47, 49, 50, 51, 54. After this
package none of them stops.
