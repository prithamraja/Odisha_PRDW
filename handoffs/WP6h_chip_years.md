# WP-6h — Chips keep every year the officer named (handoff brief)

**For:** the operator-controlled implementation agent.

**Read first:**
- `handoffs/WP6g_REPORT.md` §6.3 and §7.1;
- `handoffs/WP6d_REPORT.md` §6 (T6: chips keep places and schemes);
- `Ask/query_router/router.py` — `_extract_fill_values` (~L1080), `_extract_slot_values` (~L420, its `list_slots` parameter), `_list_slots`, `_reading_chips`, the three chip call sites: reranker no-match, ambiguous zone, `_no_match`;
- `Ask/query_router/zones.py` — `readable_question`, `_readable_values`-style joining;
- `Ask/query_router/date_phrase.py` (WP-6g's span reading).

**Sequencing:** WP-6g has landed (`d9f6562`..`0fa2c9c`). Build on `0fa2c9c`, in a fresh mirror (`C:\dev\odisha-wp6h`). The "found by" switch stays at 4.

**Scope:** one change — a chip carries every year the officer named, or is not offered.

**Not in scope:**
- the reranker declining short span wordings (WP-6g §6.3, a phrasing question);
- non-year lists joined into one string through a pause (WP-6g §7.2);
- a plain hyphen or unspaced dash as a span link (WP-6g §7.4);
- the fiscal-year naming convention;
- anything else.

## 0. Why this package exists

When the reranker declines a question, the officer gets up to three chips, each a catalogue question with the officer's own values filled in. WP-6d made chips keep places and schemes. **They still drop years.**

**Seen in WP-6g's live check.** "How many activities were planned from 2022-23 to 2024-25?" asked, and every chip read "…in 2024-2025". A tap answers for 2024-25 alone, a narrower question than the one asked, with nothing to say so. Rows 1060, 1062, 1063, 1064 and 1067 all showed it. It applies to every multi-year form: "2022 to 2025", "2023-2025", "from 2022-23 to 2024-25".

**The cause, verified by the PM.** `_extract_fill_values` calls `_extract_slot_values(user_query, slot_type, openai_client, validator=validator)` **without `list_slots`**. So the deterministic year prefill treats `$date_range` as a one-value slot and keeps only the latest year. On the answer path, the same call passes the template's list-capable slots, which is why answers keep every year.

**The templates, by year slot:**

| year slots | templates | a span of years can… |
|---|--:|---|
| `$date_range` takes a list | 329 | be carried on the chip in full |
| `$date_range` and `$date_range_2`, one year each (PLN-039, PLN-040, TRD-001, TRD-002, TRD-004) | 5 | be carried only when exactly **two** years were named — the comparison pair |

## 1. Hard constraints

- Only chip construction changes: `_extract_fill_values` and chip rendering.
- The answer path is unchanged: what a question binds when it is answered directly is byte-identical. Test it.
- No catalogue, SQL, note, phrasing or reader change. `derive_catalog.py --check` and `validate_catalog.py` (358 / 0) stay green untouched.
- WP-6d's chip behaviour holds: places with their tier noun, the block-first rule, schemes appended, no unwritten list length. Its tests stay green unchanged.
- Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched; every paid run through `confirm_spend`; Ask stays on `gpt-5.4-mini`.

## 2. Tasks

### T1 — Read the years as a list when building chips

`_extract_fill_values` passes `list_slots` = the union of the list-capable slots of the chip candidates (via `_list_slots`) to `_extract_slot_values`. It then keeps a list value for those slots, as it already does for schemes.

**Check that nothing else moves.** A focus-area or scheme list already comes back as a list today, so this should change only the years. Prove it:
- run the old and new pre-fill over every question that produced chips in the WP-6e, WP-6f and WP-6g replays, with the extractor stubbed to its recorded output where available, or to the deterministic readers only;
- list every chip whose text changes;
- **expected: only questions naming more than one year. Stop and report if anything else changes.**

### T2 — Render each chip for what its template can take

For each chip candidate:
- **The year slot takes a list** → the chip carries every year, in the stored form, joined the way the answer echo joins values: "…in 2022-2023, 2023-2024 and 2024-2025?". Tapped, the chip is re-read by the year reader, which reads every label, so the answer binds all three. Test the round trip.
- **A two-year comparison template** (one of the five) **and exactly two years named** → fill the pair: the earlier year in the slot the question names first. For TRD-002, "between {date_range_2} and {date_range}", that is `$date_range_2`. Read each template's wording to place them, and test all five.
- **A one-year template and more years named than it can hold** → **do not offer that chip.** A tap would answer a narrower question than the officer asked. If every candidate is dropped this way, offer them anyway, with the single year named and marked: "…in 2024-2025 (2024-25 only)?". The narrowing is then visible, and a tap answers exactly what the chip says.
- **One year named, or none** → as today.

The chip's `send_text` stays equal to its label.

### T3 — Tests

- For each of the three multi-year forms ("2022 to 2025", "2023-2025", "from 2022-23 to 2024-25"): a list-capable chip carries all years, and its tap binds all years.
- A two-year comparison chip fills both slots in the right order.
- A one-year chip with three years named is dropped, and when it is the only candidate it shows "(2024-25 only)".
- A single-year question's chips are unchanged.
- WP-6d's chip tests are unchanged.
- The answer path binds identically before and after.

### T4 — Live check, small

Run through `confirm_spend`, about 40 calls. Use WP-6g's seven asking rows (1060–1064, 1066, 1067), each as a **two-turn row that taps the first chip**. Report, for each:
- the chips as shown;
- the tap's answer and the years it bound.

**Expected:** each tap answers with every year the officer named, or the chip says "(… only)".

Add them to `handoffs/WP6c_pilot_questions.json` as an eighth standing group.

### T5 — Report

`handoffs/WP6h_REPORT.md`:
- the T1 chip-change list;
- the T2 decision for each of the five one-year templates;
- the live table;
- any test pins changed;
- spend.

## Gate (definition of done)

1. Chips on a multi-year question carry every year on list-capable templates; a tap binds every year; one-year templates are dropped or marked "(… only)"; single-year chips are unchanged.
2. T1's change list holds only multi-year questions.
3. The answer path is byte-identical; WP-6d's chip tests are unchanged; the full suite and `prdw_gates.py` are green; catalogue checks untouched (358 / 0).
4. The live taps answer with every year named, or visibly narrower.
5. This brief and the report committed, one commit per task, not pushed.
