# WP-6d — Bottom-10 rankings, the D34 conditions, and three pilot polish fixes (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `handoffs/WP6c_REPORT.md` (§4.1 the fund-split misses, §8 what the next package should know); `PROJECT_PLAN.md` **D34** (items 2, 3, 4); `Ask/query_router/router.py` (the "never default a threshold" block ~L292, `slot_defaults`, `_extract_slot_values` ~L371, `_rehome_and_guard`, `_extract_fill_values` ~L1062, `_readable_values` ~L2003, the reranker no-match chip path ~L2370); `Ask/query_router/zones.py` (`_readable`, `readable_question`, `resolved_question`, `_APPEND_NOUNS`); `Ask/query_router/suggestions.py` (`_chip_for`, which already appends for the same reason as T6); `Ask/query_router/breakdown.py` (the "(broken down by …)" / "(as one total)" suffixes ~L231); `Ask/query_router/subject_reader.py` (`VOCABULARY_GUARDED`, `written_values`, `_NOT_READ`); `Ask/tools/migrations/m5_scheme_breakdown.py` (the pattern M6 follows); `Ask/eval_questions_full.json` row **G1613**.
**Sequencing:** WP-6c has landed (`414930a`, `a271c8f`, `7762de7`). **Build on `7762de7`**, in a fresh mirror (`C:\dev\odisha-wp6d`, a plain copy of `Ask/`).
**Scope:** five items, all ruled by the operator on 2026-09-28 —
1. rate rankings answer with the bottom 10 instead of asking for a threshold (T1–T3);
2. the three D34 conditions, still owed since 2026-09-14 (T4, T8);
3. example phrasings for the fund-split and plain-count misses (T5);
4. suggestion chips keep what the officer named, **and a place that is both a block and a gram panchayat is read as the block** (T6);
5. the answer's echo reads as English, not raw values in brackets (T7).

**Not in scope:** "sector" and "Sankalp" (parked by the operator, D33 stands); IMP-013 (its hidden rupee threshold is real; WP-6c made the ask usable); any `top_n` template other than IMP-009 / IMP-019 / IMP-020; the block-versus-GP reading on the **answer** path (T6 covers chips only — see §9); the repeated year in "between 2022-2023 and 2022-2023" (seen once in WP-6c's Eval_1 echoes, §9); Eval_1 row 212.

## 0. Why this package exists

**Item 1 — rankings asking for a threshold.** The operator asked why these four questions ask "For which threshold?" (now "At least how many activities?" after WP-6c):

- Which focus area has the smallest activity completion rate in FY 2025-26?
- Which focus area has the lowest completion rate in FY 2025-26?
- Identify the focus area with the lowest completion percentage for FY 2025-26.
- For FY 2025-26, which focus area ranks last by completion rate?

All four match **IMP-009**. Its SQL, as written in the original question workbook, ends with a floor the question text never mentions:

```sql
GROUP BY 1
HAVING COUNT(*) >= $threshold
ORDER BY completion_rate_pct ASC, planned_activities DESC
LIMIT $top_n
```

The floor ("only rank focus areas with at least N activities") is a small-denominator guard. The Parameter Registry marks it required, and the router never defaults a threshold, so the officer is asked for a number whose meaning they cannot know. IMP-019 and IMP-020 have the same shape. Gold G1613 was classified "clarify" in WP-4a for exactly this reason, with an open SME question: "is there a sensible default … that would let this answer outright?". **Operator ruling, 2026-09-28: no floor by default; show the bottom 10.**

The PM ran IMP-009 offline for FY 2025-26 with floor 1 and length 10. All ten rows sit at **0% completion**: Maintenance of community system 427 planned, Poverty alleviation programme 400, Sanitation 354, Health 316, Women and child development 284, Drinking water 207, Rural housing 149, Education 116, Agriculture 91, Social welfare 89. With length 1, only "Maintenance of community system" is named, and it wins only because it is the largest of at least ten ties. **That is why the length stays 10 even for a question worded in the singular.**

**Item 2 — D34.** (2) one gold replay on HEAD, never run since WP-6b; (3) a PLN-007 paraphrase for "districts behind on GPDP submission" (row 315 was served the PLN-022 refusal); (4) the extractor inventing `plan_type = Main` on questions that never say "main" (#253, #1006, #1014, #2035), which silently drops 481 supplementary activities.

**Item 3 — phrasing gaps.**
- WP-6c §4.1: four fund-split questions were declined outright by the reranker before any value was read. Three were *sanctioned amount* questions naming schemes: 1005 "split the sanctioned funds into SFC and Own Funds for 2024-25", 1007 "What share of the sanctioned budget came from SFC and 15th Finance Commission in 2024-25?", 1009 "How much of the 2024-25 sanctioned amount is from the State Finance Commission?". BUD-003 now answers one row per scheme since M5, but the reranker picked nothing.
- The operator's "What is the count of planned activities in Kalimela in 2024?" also matched nothing. The catalogue has no plain "how many activities are planned in a place" entry. The nearest are PLN-024 (per theme) and PLN-049 (per focus area), both worded "in {gp_name}", although both filter on block through the universal optional slots.

**Item 4 — chips lose what the officer named.** That same question produced three chips reading "…in **a gram panchayat** in 2024-2025?" — Kalimela gone. The PM reproduced the text exactly with `zones.readable_question`. The mechanism:

- **Kalimela is both a block and a GP** in the data; `validate("Kalimela", "block")` and `validate("Kalimela", "gp")` are both exact.
- The chip pre-fill most likely read it as the block. With a block fill or with no fill, the chip text is identical.
- The chip questions have only a `{gp_name}` gap, and `readable_question` fills gaps only, so the block was dropped and the GP gap rendered as a stand-in.
- A chip tap sends only the text and routes as a new question, so nothing downstream can recover the place.

The same drop hit WP-6c's pilot: tapping the BUD-003 chip on rows 1005 / 1007 / 1009 loses the schemes. `resolved_question` (the answer echo) and `suggestions._chip_for` already append values that have no gap. `readable_question`, the renderer the no-match chips use, does not. **Operator ruling, 2026-09-28: when a place is both a block and a GP, the chip reads it as the block.**

**Item 5 — the echo.** Every bracketed fragment in the WP-6c Eval_1 and pilot echoes, tallied by the PM:

| fragment | count | problem |
|---|--:|---|
| (total), (fiscal_year), (district), (gp), (focus_area) | ~100 | raw `$group_by` value, repeated by the "(as one total)" / "(broken down by …)" suffix beside it |
| (10), (1) | 25 | raw `top_n` |
| (Main), (Supplementary), (Tied) | ~60 | filter value with no noun |
| (Sanitation), (Roads), (Drinking water) | ~40 | a focus area, but the reader can't tell it's a filter |
| (5TH STATE FINANCE COMMISSION, XV Finance Commission and Own Funds) | 3 | raw database labels |
| (Ganjam district), (Andhrua GP) | 13 | already fine: they carry their noun |

The worst case reads: "How many activities in all blocks are in WORK ONGOING status for 2024-2025 and 2025-2026 (Roads) (fiscal_year)? (broken down by year)".

## 1. Hard constraints

- **Catalogue SQL: no text changes.** Catalogue changes go only through a script in `Ask/tools/migrations/`: **M6, slot declarations only.** Paraphrases go in the catalogue file directly, the way WP-6b T5b did (`54c0344`).
- `derive_catalog.py --check` and `validate_catalog.py` (343 / 0) stay green. Gate 9 (j) keeps holding: M6 must not remove the `unit` / `direction` keys WP-6c derived.
- Test Report row counts hold. The oracle runs IMP-009 with its recorded `threshold: 50, top_n: 10` and must still reproduce.
- **Display is not binding.** T6 and T7 change text only. Every bound value and every SQL parameter stays byte-identical, and a test asserts it.
- Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched; every paid run through `confirm_spend`; Ask stays on `gpt-5.4-mini`; retrieval thresholds untouched; no file that serves "sector" or "Sankalp" changes.

## 2. T1 — Migration M6: the floor defaults to 1, the length is fixed at 10

`Ask/tools/migrations/m6_ranking_floor.py`, in the M5 pattern. It applies to IMP-009, IMP-019 and IMP-020 only, with the three ids listed in the script rather than matched by pattern. It must be idempotent and support `--check`.

- **`threshold` slot:** add `"optional": True, "default": "1"` beside the existing `unit` / `direction`. It must be a default, not merely optional. An absent optional binds NULL, and `HAVING COUNT(*) >= NULL` drops every row. `COUNT(*) >= 1` is always true for a group, so default 1 is exactly "no floor".
- **`top_n` slot:** keep `default: "10"` and add `"superlative_means_one": False`.

WP-6c's T1b ask ("At least how many activities?") simply stops being reached on these three. Leave it in place: it is still the right ask on PLN-045 / PLN-069.

## 3. T2 — The router honours "always 10" on those three

In `_extract_slot_values`, beside `_rehome_and_guard`, add one rule for a `top_n` slot declaring `superlative_means_one: False`. Keep the extractor's value only if that number appears in the question, as digits or as a number word from one to twenty. Otherwise drop it, log `top_n: superlative read as list (declared)`, and let the default 10 apply.

| question | rows |
|---|---|
| "Which focus area has the lowest completion rate?" | 10, lowest first |
| "bottom 3 focus areas by completion rate" | 3 |
| "the single lowest focus area" | still 10, the lowest is row 1 |

The extractor prompt is **not** changed, so no other template can be affected. Amend the "never default a threshold" comment (~L292) to say: a threshold that only guards small denominators in a ranking may default to its no-op value where the catalogue declares it; a threshold that changes the population may not. Name the three templates.

## 4. T3 — The gold row changes its expectation

`eval_questions_full.json` **G1613**: `expected_behavior` "clarify" becomes "answer", `case_type` "ambiguity" becomes "standard", and the notes gain "Operator ruling 2026-09-28 (WP-6d): no floor by default, bottom 10." G2041 / G2042 (the "sector" rows that list IMP-009 as acceptable) are untouched.

## 5. T4 — The D34 conditions

1. **PLN-007 paraphrase** (D34.3): add "Which districts are behind / lagging on GPDP submission in a given year?". Regenerate, and re-measure crowding on the gate 8 line.
2. **Plan-type invention guard** (D34.4): add `plan_type` to `subject_reader.VOCABULARY_GUARDED`.
   - **Trap:** `written_values` builds its word list with `_vocabulary`, which **removes `_NOT_READ` words, and "main" is one of them** (WP-6b §3: "main" is also "the main reasons"). Wired as-is, the guard would drop `plan_type = Main` even when the officer wrote "main GPDP".
   - **Fix:** the guard's word list is the full alias table plus registry values, with nothing removed. `_NOT_READ` stays as is for the reader's prefill. Put a separate vocabulary for guarded types in `subject_reader`, and test that the two lists differ exactly by `_NOT_READ`.
   - **Prove it on both sides.** Stub the extractor to return `plan_type = Main` on the phrasings of #253, #1006, #1014, #2035: the value is dropped and logged. Eval_1 rows 1–2 ("main GPDPs") and every other row that says "main" or "supplementary" still bind their plan type.

## 6. T5 — Example phrasings

Add these directly in the catalogue file (the WP-6b T5b pattern), then run `derive_catalog.py` and re-measure crowding.

- **BUD-003**, two or three phrasings: "Split the sanctioned funds into SFC and Own Funds in a given year", "How much of the sanctioned amount came from a given scheme in a given year?", "What share of the sanctioned budget came from SFC and the 15th Finance Commission?".
- **PLN-024**, one phrasing: "How many activities are planned in a given block in a given year?". With no "total" cue, the breakdown reader leaves PLN-024 on its own per-theme breakdown, so the officer gets per-theme counts for the block, not one figure. **Report what it returns.** The PM decides afterwards whether "count of …" should read as a total.

If WP-6c pilot rows 1005 / 1007 / 1009 still reach no template after this, stop and report. Do not add more phrasings or reranker notes without the PM.

## 7. T6 — Chips keep what the officer named; a block-and-GP name reads as the block

**a) Block first.** In `_extract_fill_values`, which feeds every chip pre-fill (the reranker no-match, the ambiguous zone, `_no_match`):
- If the extractor returns `gp = X`, X also validates **exactly** as a block, and the question has no GP cue ("GP", "gram panchayat", "panchayat") beside X, then X moves to `block_name`.
- If both `gp` and `block` carry the same name, keep the block only.
- An explicit cue wins: "Kalimela GP" stays a GP. Log `chip fill: X read as block (also a GP)`.
- The answer path is unchanged.

**b) Nothing the fill knows is dropped from a chip.** `readable_question` gains the same no-silent-drop rule as `resolved_question` and `_chip_for`, with the T7 wording:
- **Geography:** when a geography gap is unfilled and the fill carries another geography slot, the stand-in becomes that place with its noun. "…each GPDP theme **in {gp_name}** in {date_range}" with `block_name = Kalimela` renders "…each GPDP theme **in Kalimela block** in 2024-2025?". Do not append "(Kalimela block)" after "in a gram panchayat": that would name two scopes.
- **Every other filled slot** with no gap (schemes, focus area, plan type, tied/untied) is appended in the T7 form, so the tap re-extracts it.
- A chip's `send_text` equals its label, as today.

**Prove (offline).**
- PLN-024 / PLN-049 with `block_name = Kalimela` render "…in Kalimela block in 2024-2025?".
- `gp = Kalimela` with no cue becomes block; "Kalimela GP" stays a GP; `gp = Andhrua` (GP only) is unchanged.
- BUD-003 chip with `scheme = [SFC, Own Funds]` carries both schemes.
- The chip text, routed back through `_extract_slot_values` with the extractor stubbed to read "Kalimela block" as `block_name`, binds the block.

## 8. T7 — The echo reads as English

One renderer, used by `resolved_question` (answers) and `readable_question` (chips). All of this is display only: bound values are unchanged, and the database labels stay raw in SQL.

1. **The breakdown is never appended as a raw value.** `$group_by` is described once, by the existing "(as one total)" / "(broken down by year)" suffix, and never also as "(total)" / "(fiscal_year)" / "(district)" / "(gp)" / "(focus_area)".
2. **The list length reads as a length:** "(top 10)" / "(bottom 10)" from the statement's first `ORDER BY` key (ASC is bottom). `top_n = 1` reads "(the highest)" / "(the lowest)". Never a bare number.
3. **Every appended filter carries its noun**, and several join in one bracket:

| filter | reads as |
|---|---|
| plan type | "main GPDP" / "supplementary plan" |
| tied/untied | "tied funds" / "untied funds" |
| focus area | "Sanitation focus area" |
| theme | "Theme 5 – Clean and Green Village" |
| status | "completed work" / "ongoing work" |
| scheme | "SFC and Own Funds" |

   Example: "…in 2024-2025 (Sanitation focus area; main GPDP)?". Geography keeps its current noun form ("Ganjam district", "Andhrua GP").
4. **Display names for raw database labels, echo only.** One table in `zones.py`:

| database label | display name |
|---|---|
| 5TH STATE FINANCE COMMISSION | 5th State Finance Commission (SFC) |
| XV Finance Commission | 15th Finance Commission (CFC) |
| 4TH STATE FINANCE SCHEME | 4th State Finance Commission |
| WORK COMPLETED / WORK ONGOING / WORK ABANDONED / UNDER APPROVAL | completed / ongoing / abandoned / awaiting approval |

   Any label not in the table shows as it is stored.
5. **The IMP-009 family:** "(bottom 10)". A floor the officer set shows as "(bottom 10, focus areas with at least 50 activities)". The default floor of 1 is never shown.

Existing tests that pin `query_description` strings will change. Update them in the same commit, list each changed pin in the report, and assert that `bound_filters` in the pinned cases is unchanged.

**Prove (offline).** Re-render the echo for every served row of `handoffs/WP6c_eval1_replay.jsonl` from its recorded template and bound values:
- no raw `$group_by` value, bare number, raw scheme label or noun-less plan type / tied-untied value appears;
- every bound filter is still named in the echo;
- the report shows ten before/after pairs, including the "WORK ONGOING … (Roads) (fiscal_year)" row above.

## 9. T8 — Measure, then report

1. **Offline suites** for T1–T7, all green. They include a control: "Which GP spent the most?" with `top_n = 1` still returns 1 row.
2. **New rows**, added to `handoffs/WP6c_pilot_questions.json` as a fifth standing group (~22 rows):
   - rankings × 10: the four in §0, two each for IMP-019 / IMP-020, "bottom 3 …", "… with at least 50 activities";
   - plan-type guard × 4: the D34.4 phrasings;
   - Kalimela × 4: the operator's question, then a **chip tap** of the per-theme chip, then two more block-and-GP names with and without "GP";
   - plain count × 2: "count of planned activities in <block> in <year>".

   `run_custom_eval.py` gains a chip-tap second turn: pick the chip whose label contains a given template's wording and send it with `from_chip`. Also re-run WP-6c's 22 pilot rows for the T5 effect.
3. **Eval_1 replay** (314 rows), graded unchanged, diffed against `handoffs/WP6c_eval1_replay.csv` (290 / 10 / 0 / 2). Target: no group loses more than one row, and incorrect ≤ 2. Row 315 answers on PLN-007.
4. **Gold replay, one run** (275 rows, D34.2), compared row by row against the WP-6 majority. G1613 answers; #1423 / #1402 / #1522 behave as in WP-6c. Any row the majority got right that this run gets wrong is fixed or ruled.
5. `prdw_gates.py` green.
6. `handoffs/WP6d_REPORT.md`:
   - per-row outcomes of the new group and of the re-run pilot rows;
   - how many focus areas tie at the bottom rate in FY 2024-25 and 2025-26 (reported, not acted on);
   - every `superlative read as list`, plan-type `dropped` and `read as block` log line;
   - the ten echo before/after pairs and the list of changed test pins;
   - what the PLN-024 plain-count phrasing returned;
   - spend.

**Expected spend**, all through `confirm_spend`, ~2,000 calls:

| run | calls |
|---|--:|
| new rows | ~70 |
| pilot re-run | ~70 |
| Eval_1 | ~1,000 |
| gold | ~800 |

**Seen and deliberately left for the PM** (report only, do not fix):
- the block-versus-GP reading on the answer path;
- the repeated year in "between 2022-2023 and 2022-2023";
- Eval_1 row 212.

## Gate (definition of done)

1. M6 applied and idempotent; `derive_catalog.py --check` green with the new phrasings; `validate_catalog.py` 343 / 0; no SQL text changed; gate 9 (j) holds.
2. All T8.1 offline cases pass; the full suite is green; changed echo pins are listed and their bound values are unchanged.
3. The new rows pass:
   - rankings: every phrasing answers with the bottom 10, or the number named;
   - plan-type guard: invented "Main" dropped, "main GPDP" still binds;
   - Kalimela: the chip names "Kalimela block" and the tap answers for the block;
   - plain count: answers.
4. Eval_1 meets T8.3; the gold replay meets T8.4; G1613 answers.
5. No echo in either replay contains a raw `$group_by` value, a bare list length or a raw scheme label.
6. This brief and the report committed, one commit per task, not pushed.
