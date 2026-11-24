# WP-D14b report — place profile sheets: fixes after the build review

**Brief:** `handoffs/WPD14b_profile_fixes.md`. **Spec:** `handoffs/PROFILE_SHEET_SPEC.md`, as amended (D77, D78).
**Executed:** 2026-11-24, mirror `C:\dev\odisha-d14b`, results copied back to the Drive repo after each task.
**Commits (on `master`, not pushed):** `9cc620c` PM records (see below), `fb7ca86` T1, `8bd5a54` T2, `edce0ef` T3, `aff499b` T4, `7f104cf` T5 store, `0e26b32` T5 scale, then this report (T6).

**Before starting.** T0's first precondition failed: the amended spec was on disk but not committed (nor were the WP-D14, WP-D14b and WP-D15 briefs). I stopped and asked; the operator told me to commit them. `9cc620c` commits those four files and nothing else. The uncommitted `handoffs/PROJECT_PLAN.md` change was left alone.

---

## §0 Status

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | The T1 table reproduced exactly; Kalimela's E3 unchanged | **PASS** | 11 of 11 rows match, and Kalimela stays at 22 / 272,440 / 2024-2025 (21) (§2); check 7 holds all 12 |
| 2 | Spec Appendix A's examples character for character | **PASS** | All 51 examples (check 7, and 51 test subtests). A test reads the spec and proves the builder's copy holds exactly the spec's examples, in both directions |
| 3 | The T5.2 comparison shows only the expected changes | **PASS** | 2,871 sentences before and after, same ids. E3 changed on exactly the 11 sheets; F1 gained its middle value on all 43 sheets that had a standing; G3 gained its standing on all 45 that had a middle value; 0 other differences (§3) |
| 4 | `--check` green on every check, with the E3 proof in check 1 and the new places check | **PASS** | 9 of 9 green (§4). Check 1 now compares 620 figures, including E3's money for all 20 Gram Panchayats against view1 re-summed by pandas |
| 5 | Gate 41/43, the two D69 reds unchanged, nothing green turned red; suite green | **PASS** | Gate 40/42 → 41/43: the only change is the new `profile-sheets-places` line, green. Suite 235 → 247 passed, 0 failed |
| 6 | Two builds byte-identical; the other 23 metainsights files unchanged | **PASS** | Part `0f657b8a…`, index `fd76cc92…` the same in two builds and in the committed store; stamps differ only in `generated_at`. 23 of 23 other files hash the same |
| 7 | The scale table filled in, every target met | **PASS** | All nine targets met (§5). Opening the store: 190 ms p95, reported on its own line, with no target |

---

## §1 What changed, file by file

| File | Change | Task |
|---|---|---|
| `Insights/src/phase5g_profile_sheets.py` | E3's money = `SUM(total_cost)` over `is_abandoned = 1`, one grouped query per level as before; `fund_abandoned_total` dropped from the columns the builder requires (nothing reads it now) | T1 |
| | `names_two_groups()` and `middle_sentence()`: "The middle value for these {n} is …" when the standing clause names two groups; F1 and G3 now go through the same `ranked()` path as A3–A6, E1, E4; the three zero forms of R13 | T2 |
| | `write_store()` writes `places` and `"format": 2` into the index | T3 |
| | Check 1 proves E3's money; check 7 gains the 11 T1 rows (`REFERENCE_E3`) and spec Appendix A's 51 examples; new check 8 `check_places()` | T4 |
| `DiscoverChat/profile_store.py` | `INDEX_FORMAT = 2`; refuses an index without `places` ("…rebuild the store"); new `place(level, code)` and `find(level, name)`, on the class and at module level | T3 |
| `DiscoverChat/gates.py` | One new check, `profile-sheets-places` | T4 |
| `DiscoverChat/tests/test_profile_sheets.py` | 47 → 59 tests (§4) | T4 |
| `Insights/metainsights/profile_sheets_index.json.gz`, `profile_sheets.part0.bin`, `profile_sheets_stamp.json` | The rebuilt store, format 2 | T5 |
| `handoffs/WPD14_scale/run_scale.py`, `measurements.json` | Times `place()` and `find()`, and memory after the first `find` at every level; new numbers | T5 |
| `handoffs/WPD14b_REPORT.md` | This report | T6 |

**How `places` is laid out (my decision).** A second map beside `sheets` in the index: `places[level][code] = {"name", "label", "block", "district"}`, in the same order as `sheets`. I added `label` (the sheet's own, e.g. `Kalimela block`) to what the brief listed, so `place()` copies the label rather than building it — the reader computes nothing. A block's entry has only `district`; a district's and the whole's have neither. `place()` fills each parent's name from that parent's own entry.

**How the name map is held (my decision).** `find()` builds a dict per level, `casefold(strip(name)) → [codes]`, on the first `find` for that level, and keeps it on the store object. It returns a copy of the list, so a caller cannot alter it. Nothing is built when the store opens (a test asserts the map is empty after opening and holds only `block` after one block lookup).

**Nothing else reads `fund_abandoned_total`.** After T1 no sheet figure reads it; I searched the builder.

---

## §2 The T1 table — expected against actual

Works marked abandoned / planned cost on them / plan year with the most (count).

| Sheet | Expected: works / planned on them / top year | Actual | Match |
|---|---|---|---|
| Hirlipali Gram Panchayat (116350) | 29 / 4,019,174 / 2022-2023 (16) | 29 / 4,019,174 / 2022-2023 (16) | yes |
| Bandhpali Gram Panchayat (116397) | 25 / 5,651,792 / 2020-2021 (10) | 25 / 5,651,792 / 2020-2021 (10) | yes |
| Bheden Gram Panchayat (116438) | 52 / 8,781,358 / 2021-2022 (26) | 52 / 8,781,358 / 2021-2022 (26) | yes |
| Kalyansinghpur Gram Panchayat (121162) | 31 / 4,457,998 / 2021-2022 (14) | 31 / 4,457,998 / 2021-2022 (14) | yes |
| Attabira block (3674) | 29 / 4,019,174 / 2022-2023 (16) | 29 / 4,019,174 / 2022-2023 (16) | yes |
| Barpali block (3676) | 40 / 7,957,981 / 2022-2023 (19) | 40 / 7,957,981 / 2022-2023 (19) | yes |
| Bheden block (3678) | 52 / 8,781,358 / 2021-2022 (26) | 52 / 8,781,358 / 2021-2022 (26) | yes |
| Kalyansingpur block (3914) | 31 / 4,457,998 / 2021-2022 (14) | 31 / 4,457,998 / 2021-2022 (14) | yes |
| Bargarh district (306) | 121 / 20,758,513 / 2022-2023 (43) | 121 / 20,758,513 / 2022-2023 (43) | yes |
| Rayagada district (329) | 31 / 4,457,998 / 2021-2022 (14) | 31 / 4,457,998 / 2021-2022 (14) | yes |
| The whole sample (all) | 420 / 58,463,049 / 2023-2024 (105) | 420 / 58,463,049 / 2023-2024 (105) | yes |
| Kalimela Gram Panchayat (119936) | 22 / 272,440 / 2024-2025 (21) | 22 / 272,440 / 2024-2025 (21) | yes |

---

## §3 The sentence comparison (T5.2)

Every sentence of the rebuilt store compared by id with the copy kept in T0 (`C:\dev\odisha-d14b-sentences-before.json`):

| | Count |
|---|---|
| Sentences before / after | 2,871 / 2,871 |
| Ids appeared / disappeared | 0 / 0 |
| E3 — money corrected | **11**, exactly the 11 sheets of T1 |
| F1 — gains ` The middle value is {median}.` | **43** of the 43 F1 sentences that had a standing clause |
| G3 — gains `, the {standing}` | **45** of the 45 G3 sentences that had a middle value |
| Any other difference | **0** |

The comparison also checked the shape of each change: an F1 sentence must be the old text plus exactly " The middle value is N.", and a G3 sentence the old text with exactly ", the …" inserted before its middle value. (Of the 46 F1 sentences, 3 have no standing and did not change: the whole, which has no peers, and Chikilli Gram Panchayat and Khallikote block, which have no approvals on file and take the zero form "None of the 640 activities has an administrative approval on file." G3 has no standing only on the whole.)

### E3, all 11 sheets

| Sheet | Before | After |
|---|---|---|
| Hirlipali Gram Panchayat (`p-gp-116350-E3`) | 29 works are marked abandoned, with Rs 44.19 lakh planned on them. 16 of them were planned in 2022-2023. | 29 works are marked abandoned, with Rs 40.19 lakh planned on them. 16 of them were planned in 2022-2023. |
| Bandhpali Gram Panchayat (`p-gp-116397-E3`) | 25 works are marked abandoned, with Rs 70.66 lakh planned on them. 10 of them were planned in 2020-2021. | 25 works are marked abandoned, with Rs 56.52 lakh planned on them. 10 of them were planned in 2020-2021. |
| Bheden Gram Panchayat (`p-gp-116438-E3`) | 52 works are marked abandoned, with Rs 88.81 lakh planned on them. 26 of them were planned in 2021-2022. | 52 works are marked abandoned, with Rs 87.81 lakh planned on them. 26 of them were planned in 2021-2022. |
| Kalyansinghpur Gram Panchayat (`p-gp-121162-E3`) | 31 works are marked abandoned, with Rs 58.29 lakh planned on them. 14 of them were planned in 2021-2022. | 31 works are marked abandoned, with Rs 44.58 lakh planned on them. 14 of them were planned in 2021-2022. |
| Attabira block (`p-block-3674-E3`) | 29 works are marked abandoned, with Rs 44.19 lakh planned on them. 16 of them were planned in 2022-2023. | 29 works are marked abandoned, with Rs 40.19 lakh planned on them. 16 of them were planned in 2022-2023. |
| Barpali block (`p-block-3676-E3`) | 40 works are marked abandoned, with Rs 93.72 lakh planned on them. 19 of them were planned in 2022-2023. | 40 works are marked abandoned, with Rs 79.58 lakh planned on them. 19 of them were planned in 2022-2023. |
| Bheden block (`p-block-3678-E3`) | 52 works are marked abandoned, with Rs 88.81 lakh planned on them. 26 of them were planned in 2021-2022. | 52 works are marked abandoned, with Rs 87.81 lakh planned on them. 26 of them were planned in 2021-2022. |
| Kalyansingpur block (`p-block-3914-E3`) | 31 works are marked abandoned, with Rs 58.29 lakh planned on them. 14 of them were planned in 2021-2022. | 31 works are marked abandoned, with Rs 44.58 lakh planned on them. 14 of them were planned in 2021-2022. |
| Bargarh district (`p-district-306-E3`) | 121 works are marked abandoned, with Rs 2.27 crore planned on them. 43 of them were planned in 2022-2023. | 121 works are marked abandoned, with Rs 2.08 crore planned on them. 43 of them were planned in 2022-2023. |
| Rayagada district (`p-district-329-E3`) | 31 works are marked abandoned, with Rs 58.29 lakh planned on them. 14 of them were planned in 2021-2022. | 31 works are marked abandoned, with Rs 44.58 lakh planned on them. 14 of them were planned in 2021-2022. |
| The whole (`p-all-E3`) | 420 works are marked abandoned, with Rs 6.17 crore planned on them. 105 of them were planned in 2023-2024. | 420 works are marked abandoned, with Rs 5.85 crore planned on them. 105 of them were planned in 2023-2024. |

### F1 and G3 — Kalimela Gram Panchayat, Kalimela block, the whole

| Id | Before | After |
|---|---|---|
| `p-gp-119936-F1` | 168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats. | 168 of the 852 activities (19.7%) have an administrative approval on file, the most of 20 Gram Panchayats. The middle value is 96. |
| `p-gp-119936-G3` | 33.3% of the payments are linked to a planned activity. The middle value is 42.2%. | 33.3% of the payments are linked to a planned activity, the 9th lowest of 20 Gram Panchayats. The middle value is 42.2%. |
| `p-block-3843-F1` | 168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. | 168 of the 852 activities (19.7%) have an administrative approval on file, the 4th most of 16 blocks. The middle value is 104. |
| `p-block-3843-G3` | 33.3% of the payments are linked to a planned activity. The middle value is 46.5%. | 33.3% of the payments are linked to a planned activity, the 6th lowest of 16 blocks. The middle value is 46.5%. |
| `p-all-F1` | 2,101 of the 12,704 activities (16.5%) have an administrative approval on file. | 2,101 of the 12,704 activities (16.5%) have an administrative approval on file. *(unchanged)* |
| `p-all-G3` | 37.0% of the payments are linked to a planned activity. | 37.0% of the payments are linked to a planned activity. *(unchanged)* |

The whole's F1 and G3 do not change: the whole has no peers, so no standing and no middle value (general rule).

### Two-group sentences from the made-up state (T5.6)

One Gram Panchayat of the 6,800 (`p-gp-901100`, "Hirlipali 100"), run with the whole named `the state`:

```
A3  Its planned cost is Rs 3.69 crore, the 8th lowest of the 22 Gram Panchayats in Block 093 block and in the upper-middle quarter of the 6,800 in the state. The middle value for these 22 is Rs 4.88 crore.
F1  89 of the 777 activities (11.5%) have an administrative approval on file, the 5th fewest of the 22 Gram Panchayats in Block 093 block and in the lowest quarter of the 6,800 in the state. The middle value for these 22 is 104.
G3  74.3% of the payments are linked to a planned activity, the 5th highest of the 22 Gram Panchayats in Block 093 block and in the highest quarter of the 6,800 in the state. The middle value for these 22 is 46.1%.
```

("Block 093 block" is the made-up block's name plus the level word, as in WP-D14.)

### Forms the real store does not reach

Each is built by a test from a made-up row, and the wording is the spec's: E5 nothing spent (several works and one), H2 no planned cost (several and one), G3 zero, and two-group sentences for A3 (the spec's own illustration, reproduced exactly), F1 and G3. I used no wording that Appendix A does not now hold.

---

## §4 Checks, gate and suite — baseline against final

### `--check`

| | Baseline (T0) | Final |
|---|---|---|
| Result | 8 of 8 green | **9 of 9 green** |

```
  profile sheets --check  (C:\dev\odisha-d14b\Insights\metainsights)
  PASS  1 equal to the views                   620 Gram Panchayat figures equal the view3 sums (re-summed by pandas), the view4 lifetime columns, and E3's money the view1 planned cost of the works marked abandoned
  PASS  2 the parts add up                     1,352 parent figures equal the sum of their members (Gram Panchayat -> block -> district -> whole)
  PASS  3 shares re-derived                    184 shares re-derived from their own parts, 9 places with more than one member; Rangeilunda block 23.1%, not the members' average 28.8%
  PASS  4 equal to the insights                records compared: gp 276, block 393, district 507, all 150; the whole's A7 = d1-00248 (Rs 51.96 crore below plan)
  PASS  5 sentences hold only stored figures   2,871 sentences: every numeral is a stored value through the stored formatter; 760 display strings regenerated; 2,871 ids unique, at most 60 characters, no space or bracket
  PASS  6 every place has a sheet              gp 20, block 16, district 9, all 1 sheets, one per place in the master; 0 with no activity
  PASS  7 reference figures                    126 spec §13 reference figures reproduced; 51 Appendix A examples character for character
  PASS  8 the name table (places)              46 places: name, label and parents equal the sheet's; find() returns every sheet's code; names repeated within a level: none
  PASS  stamp matches the corpus               candidate set 610cb3d26dff7bf3, as of 2026-09-11T09:31:44Z, 3 view hashes = the decomposition corpus's, 2 files verified

  all green
```

### The gate

| | Baseline | Final |
|---|---|---|
| Result | 40/42 green, 2 failed | **41/43 green, 2 failed** |
| Red | `judge-model-evidenced`, `classifier-model-evidenced` (D69) | the same two |
| Changed | — | one line added, `profile-sheets-places`, green; a diff of every PASS/FAIL name shows nothing else |

```
  PASS  profile-sheets-stamp       the profile sheet store is the one built beside this corpus: same candidate set and view parquets, every file verified (WP-D14)
        candidate set 610cb3d26dff7bf3, as of 2026-09-11T09:31:44Z, 3 view hashes = the decomposition corpus's, 2 files verified
  PASS  profile-sheets-add-up      every profile sheet sum equals the sum of its member places' (spec §9 check 2)
        1,352 parent figures equal the sum of their members (Gram Panchayat -> block -> district -> whole)
  PASS  profile-sheets-shares      every profile sheet share is re-derived from its own parts, never averaged (spec §9 check 3)
        184 shares re-derived from their own parts, 9 places with more than one member; Rangeilunda block 23.1%, not the members' average 28.8%
  PASS  profile-sheets-insights    every profile sheet figure a breakdown also states equals it, at every level (spec §9 check 4)
        records compared: gp 276, block 393, district 507, all 150; the whole's A7 = d1-00248 (Rs 51.96 crore below plan)
  PASS  profile-sheets-formatter-parity every numeral in a profile sheet sentence is a stored figure through the stored formatter (spec §9 check 5)
        2,871 sentences: every numeral is a stored value through the stored formatter; 760 display strings regenerated; 2,871 ids unique, at most 60 characters, no space or bracket
  PASS  profile-sheets-places      the profile sheet name table agrees with every sheet, and find() returns every sheet's code (WP-D14b)
        46 places: name, label and parents equal the sheet's; find() returns every sheet's code; names repeated within a level: none
  PASS  profile-sheets-reference   the spec §13 figures and the Appendix A sentences are reproduced exactly (spec §9 check 7)
        126 spec §13 reference figures reproduced; 51 Appendix A examples character for character

  41/43 checks green — 2 FAILED
```

### The suite

| | Baseline | Final |
|---|---|---|
| `python -m pytest DiscoverChat/tests -q` | 235 passed, 108 subtests | **247 passed, 114 subtests, 0 failed** |

New or changed tests in `test_profile_sheets.py`:
- the examples test now reads **the spec**, and checks both ways (51 examples, none missing, none extra);
- E5 nothing spent, H2 no cost, G3 zero, each with its one-of-something form;
- two-group sentences for A3 (the spec's illustration, exact), F1 and G3; one group keeps the short middle value;
- `place()` and `find()` (case and outer spaces ignored; an unknown name gives `[]`; `Kalyansingpur` finds the block and `Kalyansinghpur` does not);
- `find()` returns every code when a name repeats (planted in a copied store);
- the name map is built on the first `find`, not on open;
- an index with no `places` is refused, with "rebuild the store";
- planted errors: Bandhpali's E3 money at its old WP-D14 figure fails check 1 (runs where the view parquets exist); a block renamed in `places` fails the places check;
- changed: `test_no_sheet_held_until_asked` asserted the index holds no place name. That is no longer true by design (T3). It now asserts the index holds names and no sheet content (no sentence, no figure, no standing).

---

## §5 Scale test

Same machine and method as WP-D14 (`handoffs/WPD14_scale/measurements.json` holds every number and the method text). Made-up state rebuilt at `C:\dev\odisha-d14b-scale\` (outside the repo). 1,000 keys drawn with the same seed (948 Gram Panchayats, 44 blocks, 7 districts, the whole), each in a new process. All timings are with the store open.

| Measure | Target | Measured | Met? |
|---|---|---|---|
| Build, parquets to finished store | under 10 minutes | **92.6 s** | yes |
| Store size | under 300 MB | **41.1 MB** (index 147 KB, was 65 KB before the name table) | yes |
| Largest file | under 95 MB | **41.0 MB** | yes |
| One `get` | under 50 ms, median and p95 | **1.44 ms median, 3.16 ms p95** (max 9.3) | yes |
| One `place` | under 50 ms, median and p95 | **0.024 ms median, 0.055 ms p95** | yes |
| One `find`, the first at its level (builds that level's name map) | under 50 ms, median and p95 | **5.6 ms median, 11.0 ms p95** (max 34.4) | yes |
| One `find`, a repeat | (same) | 0.015 ms median, 0.030 ms p95 | yes |
| Memory added by opening | under 100 MB | **5.1 MB max** | yes |
| Memory after the first `find` at every level | under 100 MB | **6.6 MB max** | yes |
| Sheets written | 6,800 + 314 + 30 + 1 | **6,800 + 314 + 30 + 1** | yes |
| *Opening the store (no target)* | — | *143.8 ms median, 189.7 ms p95* | — |

Checks 2, 3, 5 and 6 on the made-up store: all green (451,529 sentences). No made-up name repeats, so `find` returned one code for every key.

**The machine was slower this run, throughout.** Against the WP-D14 run on the same machine: making the made-up state (code this package did not touch) took 210 s against 66 s; the build 92.6 s against 26.9 s; `get` 3.16 ms against 0.86 ms p95; opening 190 ms against 63 ms p95. The ratio is about the same (2–3×) for the steps that did not change as for those that did, so I read it as load on the machine, not slower code. Every target still holds with a wide margin.

---

## §6 Where the spec or this brief was wrong or silent

1. **T0's precondition** caught that the PM's files were uncommitted; resolved by the operator's instruction (see the top). No other precondition failed: view hashes matched, baselines were exactly 8 of 8, 40/42 and 235.
2. **`places` holds `label` as well as name and parents** — the brief listed name and parent codes; `place()` must return the label, and storing it keeps the reader from building one. Recorded in §1.
3. **`find()` is an exact match** (case and outer spaces aside), as the brief says. So `find("block", "Kalyansinghpur")` returns `[]`: the block is spelled "Kalyansingpur" (spec §12 item 14). The chat's slot reader resolves the typed name to both; WP-D15 will need to pass `find` the name the slot reader returns, not the typed one, or this block is missed.
4. **My WP-D14 test that the index held no place names** contradicted T3 by design; changed as described in §4. Not a spec issue, noted so the PM sees why a WP-D14 test changed.
5. **Appendix A's examples count 51**, not stated anywhere; the test pins 51 so a later edit to the appendix is noticed.
6. Nothing in Appendix A needed a wording of mine this time.

**Files not touched:** everything on the brief's do-not-touch list, including `config.py`, `slots.py`, the spec and the WP-D14 brief and report. `Data/` was not read. No model call, no API key.

**What the PM should replay** (fresh mirror, view parquets from `C:\dev\odisha-d11b\Insights\views_prdw\`):

```
python Insights/src/phase5g_profile_sheets.py           # part 0f657b8a…, index fd76cc92…
python Insights/src/phase5g_profile_sheets.py --check   # 9 of 9
python -m DiscoverChat.gates                            # 41/43
python -m pytest DiscoverChat/tests -q                  # 247 passed
```

Outputs kept beside the mirror: `C:\dev\odisha-d14b-baseline-*.txt`, `-final-gates.txt`, `-final-pytest.txt`, `-check.txt`, `-compare.txt`, `-scale-run.txt`, and the before/after sentences `C:\dev\odisha-d14b-sentences-both.json`.
