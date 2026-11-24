# WP-D15d report — the "could not find a place" reply is removed

**Brief:** `handoffs/WPD15d_not_found_off.md`. **Decisions:** D84, D85 (R29).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d15d`, from tree `e3483fd` (the PM's records commit after `f3f7982`; clean, holding D84, D85 and this brief).
**Commits (on `master`, not pushed):** `f6f1f08` T1, `833d4f7` T2, then this report. No model call, no API key.

**Outcome.** The reply and the turn-ending stop are deleted, not switched off; there is no setting. Reading a misspelt place is unchanged. All five pass marks hold.

---

## Pass marks

| # | Pass mark | Result | Evidence |
|---|---|---|---|
| 1 | All 369 recorded questions read the same in every field that still exists; only `not_found` is gone | **PASS** | `handoffs/WPD15d_not_found/compare.json`: 369 of 369 identical, the `not_found` key dropped on all 369, 0 other differences (`before.json` and `after.json` beside it). Before, 14 of the 369 would have ended with the message (set C's 2 and Appendix A's 12); after, 0 |
| 2 | None of Appendix A's 12 STOP questions ends without a search | **PASS** | `NoStopTests.test_the_twelve_are_searched_and_read_as_with_the_pass_off`: for each of the 12, no loose reading, a reading equal to the reading with `DISCOVERCHAT_LOOSE_PLACES=0`, and the turn reaches the (stubbed) search, with no "could not find" |
| 3 | The harness on the new code: set B exactly WP-D15b's; set C 14 of 14 with the two rows changed | **PASS** | `handoffs/WPD15d_not_found/harness/RESULTS.md`: set B 7+ letters 3,975 of 4,092 (97.1%), 5–6 letters 162 of 246 (65.8%), 12 wrong readings, 0 outside the near-names, identical to WP-D15b. Set C 14 of 14; "How is Laxmipoor block doing?" and "How is Rampur block doing?" now show no line. Set A unchanged (the same two misspellings read, "Kordha" and "Bhubaneshwar"). Size p95 55 ms |
| 4 | With `DISCOVERCHAT_LOOSE_PLACES=0`, gate and suite as today with it off; `place-switch-off-identical` green | **PASS** | Gate 51/53 (the two D69 reds), `place-switch-off-identical` and `place-spelling-never-stops` green; suite: all 304 tests outside `test_place_spelling.py` pass (that file tests the pass on, as before) |
| 5 | Gate 51 of 53, the same two reds; suite 0 failed | **PASS** | Gate 51/53 (reds: `judge-model-evidenced`, `classifier-model-evidenced`). Suite **324 passed**, 0 failed: 325 − 5 deleted + 4 added |

---

## "What this package does", expected against actual

| The officer types | Expected after | Actual |
|---|---|---|
| How many works in Tribal block areas are still ongoing? | searched and answered, no line | no line, nothing stops it. **In the real service this question was never stopped:** the rules send "how many" to Ask (the lookup move) before any search. See item 1 below |
| How is MGNREGA block convergence going? | searched and answered, no line | searched, no line |
| Kitne GP me kaam adhura hai? | searched and answered, no line | searched, no line |
| Show Adivasi GP spending | searched and answered, no line | searched, no line |
| What about Jeypore block? | as before WP-D15b, no line | searched, no line |
| How is Bhedan block doing? | as before WP-D15b; no line, no close names | searched, answered, no line (gate line) |
| How is Rampur block doing compared with Barpali block? | the Barpali block answer, no line about Rampur | Barpali block answered; nothing about Rampur in the first line or the lead (test) |
| How is Barpalli block doing? | `Reading "Barpalli" as Barpali block.` | the same, word for word (test, gate line) |
| What should I know about Kalimella? | `Reading "Kalimella" as Kalimela block. For the Gram Panchayat, ask about "Kalimela GP".` | the same, word for word |
| How is Sharagada block doing? | `Reading "Sharagada" as Sheragada block.` | the same, word for word |

---

## What was deleted

| Where | Deleted |
|---|---|
| `DiscoverChat/slots.py` | The block in `read_places` that found "a word marked as a place that reads as nothing" (with its capital-letter rule); the `not_found` key of `read_places()` and its removal in `geography()`; the field `Slots.not_found`; `CLOSE_NAME_FLOOR` |
| `DiscoverChat/assemble.py` | The early `extract()` and stop before the search; `_not_found_answer` (and with it `place` `mode: "not_found"`); the "could not find" part of `_spelling`'s first line |
| `DiscoverChat/place.py` | `not_found_message`, `not_found_first_lines`; the `not_found` argument and key of `spelling_payload` |
| `DiscoverChat/config.py` | The comment sentence describing the reply (now one line saying it is gone) |
| `DiscoverChat/gates.py` | The line `place-spelling-not-found`; the `not_found` assertion in `place-spelling-exact-unchanged` |
| `DiscoverChat/tests/test_place_spelling.py` | Tests: `test_close_name_offered`, `test_nothing_close`, `test_lowercase_marked_words_are_not_places`, `test_the_turn_ends_with_the_message`, `test_another_place_read_first_line_above` |

**Added:** the gate line `place-spelling-never-stops` ("a word marked as a place that reads as no place stops nothing: the turn is searched and answered, with no line about the word"): 'Bhedan block', 'Rampur block' and 'Tribal block' are each searched and answered, with no line about the word, and the two message builders do not exist. Tests (class `NoStopTests`): `test_the_reply_is_gone`, `test_the_twelve_are_searched_and_read_as_with_the_pass_off`, `test_another_place_is_answered_with_no_line_about_the_word`, `test_the_unchanged_lines_word_for_word`.

**Changed, argument only:** `test_unmarked_is_left_alone` (no longer reads `not_found`; asserts the key is absent) and `test_several_close_names` (calls `spelling_payload` without `not_found`). The class that held the turn tests is split into a test-less base `_Turns` (the stubbed search) and `TurnTests`, so that `NoStopTests` reuses the stub without running those tests twice.

**What is left in `DiscoverChat/` that mentions the reply:** only the new guards, which assert it is gone (the gate line and `NoStopTests`). `config.py`'s `model_not_found` is unrelated.

**Harness** (`handoffs/WPD15b_spelling/harness.py`): its reads of `not_found`, its "could not find" counts and the two set C expectations changed, and nothing else. `results.json` and `RESULTS.md` of WP-D15b are untouched; the new run is under `handoffs/WPD15d_not_found/harness/`.

---

## The gate and the suite, baseline against final

| | Baseline (untouched mirror) | Final, pass on | Final, `DISCOVERCHAT_LOOSE_PLACES=0` |
|---|---|---|---|
| Gate | 51/53 | **51/53** | 51/53 |
| Suite | 325 passed | **324 passed** (−5, +4) | 304 passed (the 20 spelling tests deselected) |

---

## Decision journal

1. **The new gate line's 'Tribal block' question** is "What stands out in Tribal block areas?", not the brief's Appendix A row 2 ("How many works in Tribal block areas are still ongoing?"). The latter is a "how many" question; the rules route it to Ask before any search, so a gate line requiring it to be searched would fail for a reason that has nothing to do with this package. My first run of the line used it and failed on exactly that.
2. **The test of the 12 questions forces the route to a search** (the stubbed classifier of the old test), as the brief asks, so it proves that the place reading no longer stops any of them, whatever the classifier would decide.
3. **"The reading equals the reading with the pass off"** is compared on the five fields both readings share (`gp_lgd_codes`, `gp_names`, `blocks`, `districts`, `mentions`), plus no loose reading: with the pass off, `read_places` has no `readings` key at all.

## What in this brief was wrong or silent

1. **Appendix A row 2 was never stopped by the service.** "How many works in Tribal block areas are still ongoing?" routes to Ask by rule (the lookup move runs before the stop did), so the officer got the Ask message, not "could not find". The probe read `read_places` alone. The other 11 have no rule and reached the search path, where the stop would have applied. After this package it does not matter: none can stop.
2. **The baseline commit:** the brief names tree `f3f7982`; the PM's records were committed on top as `e3483fd` (briefs and plan only). The code is the same.
