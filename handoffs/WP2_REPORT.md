# WP-2 — Entity layer: implementation report

**Brief:** `handoffs/WP2_entity_layer.md`
**Date:** 2026-08-13
**Scope delivered:** T0–T6 complete. Entity layer only — no catalogue content.
**Gate:** all four conditions met (§2).

---

## 1. Commits

| Commit | Contents |
|---|---|
| `de3b052` | T2: fiscal-year phrase mapping (`date_phrase.py`) + test fixture swap |
| `58ab3eb` | T1/T4/T5: PR&DW registry, GP→LGD resolution, amount normalization, collision guard, amount tests, two AP test retirements, two fixture swaps |
| `e2e745b` | T3: PR&DW few-shots, registry-generated extraction enums, agreement gate |

Baseline `5dfe609` untouched. `Chatbot/.env` never opened, never staged.
`Chatbot/data/panchayat_1.duckdb` opened read-only only (via `DuckDBFileAdapter`'s
in-memory + `ATTACH … (READ_ONLY)` inversion); no `.wal` or other file appeared beside it
and its mtime is unchanged.

**One caveat on the history:** commit `58ab3eb` leaves `test_extraction_enums.py` (still the
AP version at that point) failing; `e2e745b` rewrites it. The tree is green at HEAD and at
`de3b052`. Splitting further would have meant an entity registry and an extraction prompt
that disagree, which is the exact drift the agreement gate exists to forbid.

## 2. Gate

| # | Condition | Result |
|---|---|---|
| 1 | `test_extraction_enums.py` green against the PR&DW registry | **Yes** — 15 passed / 1 skipped, 375 subtests |
| 2 | `test_gp_collisions.py` green, synthetic duplicates exercised | **Yes** — 28 passed, 43 subtests |
| 3 | T0-green stays green except documented swaps/retirements; errors drop by 17 | **Yes** — 0 failures, **17 → 0 errors** |
| 4 | No live API calls anywhere in the run | **Yes** — and this was *not* true at T0; see §7.1 |

### Test counts, baseline vs final

| | T0 baseline | Final | Δ |
|---|---|---|---|
| passed | 293 | **359** | +66 |
| skipped | 32 | 33 | +1 (the newly opt-in live test) |
| **errors** | **17** | **0** | **−17** |
| **failed** | **0** | **0** | — |
| subtests passed | 33 | 456 | +423 |

T0 was re-established after deleting `Chatbot/**/__pycache__` and `Chatbot/.pytest_cache`
(§3a discipline) on a clean tree, and reproduced the WP-1 close exactly: 293 / 32 / 17 / 33.

---

## 3. Every test swapped, retired or added

| File | Action | Why |
|---|---|---|
| `test_name_collisions.py` (17 tests) | **RETIRED → `test_gp_collisions.py`** | AP farmer roster keyed on Aadhaar; PR&DW has no person roster and no Aadhaar. Also the source of all 17 baseline errors — its `_connect()` read `RTGS_Data/flat` with no existence guard. Concept ported in full (§5). |
| `test_land_units.py` (24 tests) | **RETIRED → `test_amount_units.py`** | acre/cent→hectare is agriculture-only. The analogous PR&DW trap — lakh/crore→rupees — is ported with the same structure, plus the deadline parse. |
| `test_date_phrase.py` (27 → 47 tests) | **FIXTURES SWAPPED** | Bucket 2. Season cases (`kharif`/`rabi`) deleted outright — not a PR&DW concept — and replaced by fiscal-year string resolution. Guard tests kept verbatim in shape with PR&DW nouns (an LGD code and a lakh figure replace an Aadhaar and an acreage). One behaviour change, deliberate: `FY 2024-25` now yields the real `2024-04-01 … 2025-03-31` window instead of the head calendar year (§4.2). |
| `test_extraction_enums.py` (5 → 15 tests) | **REWRITTEN, same contract** | The agreement gate itself. Its AP subject (`crop_status`, `ekyc_status`, `beneficiary_status`) no longer exists. Rewritten against the PR&DW registry and strengthened: it now also proves the prompt is *generated* rather than hand-written, and that every alias target names a real loaded value. `LiveExtractionTests` made opt-in (§7.1). |
| `test_param_binding.py` (1 assertion) | **FIXTURE SWAPPED** | Asserted the binder's error string `"did not resolve to one person"`; it is now the domain-neutral `"one record"`, because the same mechanism binds a GP's LGD code. Behaviour identical. |
| `test_pending_resolver.py` (1 test) | **FIXTURE SWAPPED** | Asserted `_STATE_LEVEL_TERMS` contained `"andhra pradesh"` / `"ap"`; now asserts Odisha's markers. Same shared source, same assertion shape; extended to cover a `gp` slot. |
| `test_gp_collisions.py` (28 tests) | **NEW** | T4. |
| `test_amount_units.py` (32 tests) | **NEW** | T5. |

Nothing else in the suite was touched. In particular `test_named_binding.py`,
`test_param_binding.py` (bar the one string), `test_pending_clarification.py`,
`test_router_miss_path.py`, `test_zones_and_followups.py`, `test_operations.py`,
`test_vector_retriever.py`, `test_rerank_context.py`, `test_reranker_parse.py`,
`test_context_store.py`, `test_column_metadata.py` and `test_sql_params.py` pass unmodified
— they stub the validator or test AP catalogue structure, so the registry rewrite does not
reach them.

---

## 4. What changed

### 4.1 T1 — the registry (`entity_validator.py`)

Fifteen entity types plus four `mirrors` pairs, all values loaded from the database
read-only at startup. **Nothing is hard-coded**, so the statewide extract behind the same
`db_factory` adapter grows 9 districts to 30 and 20 GPs to ~6,800 with no code change (D4).
Verified against the real sample:

```
district=9  block=16  gp=20  fiscal_year=6  focus_area=30
theme=6  scheme=5  status=5  asset_category=27  asset_subcategory=138
```

`PARAM_ENTITY_TYPES` maps the sheet's bind names to entity types as data, so WP-3 declares
`"entity_type": PARAM_ENTITY_TYPES["asset_sub_category"]` rather than guessing; a test
asserts the map covers the sheet exactly and points only at types that exist.

**The whitespace decision, and why the obvious reading is wrong.** The brief says
"normalize trailing whitespace on load … do not modify the DB". Taken literally — strip on
load, bind the stripped value — every theme question would return **zero rows**, because
`dim_lsdg_theme.lsdg_theme` genuinely holds `'Theme 5 - Clean and Green Village '` with the
space. So: **the registry stores the database's own bytes and normalises only the
comparison.** A user typing the label cleanly resolves; what binds is what the column holds.
The same rule rescues `'\tWORK COMPLETED'` (§7.2). Alias tables are written in clean form
and passed through `_canonical()`, which looks the target up in the registry — so an alias
can say `WORK COMPLETED` and still bind the tab.

If `create_views.sql` turns out to `TRIM()` these columns, the registry must switch to the
trimmed form. That is a one-line change to `_DB_SOURCES` and is marked.

**GP resolution.** `GramPanchayat(lgd_code, name, block, district)`, indexed by collapsed
name and by code. A name held by one panchayat resolves silently and carries
`resolved_code`; a shared name raises `ClarificationNeeded` with one candidate per
panchayat, qualified by block then district, with the LGD code as the last tiebreak. A bare
LGD code resolves directly (it is public, unlike an Aadhaar, so chips show and send it in
full). `"Naugaon of Barpali"` resolves outright, which is what lets a chip's reply survive
a round trip through a chained clarify without looping.

**Aliases.** Per-entity dicts of *lowercased user text* → *canonical label*, seeded with
English colloquials (§8 lists what is thin and why). Keys are plain strings, so Odia and
transliterated keys need no code change — only these dicts extended, or loaded from the
operator's dictionary file when it lands (D5). A test asserts every alias target names a
real loaded value, which is the one way a hand-written table can still silently point at
nothing.

**Numerics and dates.** `top_n` 1–1000 (not AP's 100: "list every block" is 314 rows
statewide, and refusing it would be the registry inventing a limit the catalogue does not
have). `threshold` / `amount_threshold` accept Indian notation, ≥ 0. `deadline` is
format-validated (§4.4).

### 4.2 T2 — fiscal years (`date_phrase.py`)

`resolve_fiscal_years(text, known_years)` maps every phrasing onto the stored full form:
`2024-2025`, `2024-25`, `FY 24-25`, `F.Y.`, `financial year`, `24-25`, en dashes, and a
bare `2024`. Relative phrases — "this year", "last year", "last two/three/N years" —
resolve **against the loaded years, not the wall clock**, and return `[]` when no years are
loaded rather than guessing. A phrase naming several years returns them oldest-first;
`resolve_fiscal_year` (singular) returns `None` for that case, because a slot binds one
value and picking the first would answer a different question. The paired slot
`fiscal_year_2` takes the later end, which is the only reading a comparison template has,
so "compare the last two years" fills both slots correctly.

`extract_date_window` survives for the genuine calendar questions (`$deadline` against
`plan.approval_date`) and now returns the **real fiscal window** `2024-04-01 … 2025-03-31`
for `FY 2024-25`. AP flattened it to the head calendar year because that domain compared an
integer crop-year column; here the only consumer is a real DATE column, where three missing
months at each end is a wrong answer. `_collect` now claims the whole match, so `2024-2025`
cannot also be read as a stray bare `2025` and stretch the window to December.

### 4.3 T3 — extraction (`entity_extractor.py`)

`build_prompt(registry_values)` fills every enum from the live registry;
`refresh_prompt_enums()` is called in `main.startup()` immediately after `EntityValidator`
reads the database — the one point where a real registry exists. `status`, `scheme`,
`theme` and `fiscal_year` are enumerated **in full** (a missing value there mis-binds
silently); `district`, `block`, `focus_area` and `asset_category` are sampled at 12 with an
ellipsis, since their job is to show the model what one looks like and the alias+fuzzy
cascade covers the rest, with an unresolvable place clarifying rather than mis-binding.

An empty enum logs a loud per-slot warning at startup and is quiet at import (where it is
expected). The gate test proves generation is real by feeding an invented registry and
checking the invented values appear.

Few-shots are officer phrasings including code-mix ("khordha me kitne GP ne 2024-25 ka plan
approve kiya?", "GPDP status of Andhrua"). Extraction emits the **raw surface form**
throughout — `"FY 24-25"`, `"1 lakh"`, `"khordha"` — and validation owns resolution.

### 4.4 T5 — amounts and deadlines

`parse_amount()` handles lakh/lac/crore/cr/thousand/k, the `₹`/`Rs.`/`INR` prefixes, the
`rupees` and `/-` suffixes, and Indian digit grouping (`1,00,000`). An **unknown unit raises**
rather than being read as bare rupees — "2 bighas" silently becoming ₹2 is a wrong answer
that looks right. `router.amount_from_text()` is the deterministic pre-pass, and it requires
a money marker (`₹`/`Rs`/a multiplier word/`rupees`): a bare "more than 50" is deliberately
**not** claimed, because `$threshold`'s unit varies by question (percent, rupees, days, or a
minimum activity count) and only the sentence says which.

`parse_deadline()` accepts ISO and unambiguous named-month forms, and accepts
`DD-MM-YYYY` / `DD/MM/YYYY` **only when the first field cannot be a month**. `06/07/2024` is
refused outright rather than read as one of the two dates it might be — a deadline decides
which plans count as late, so a guess there silently reclassifies the answer. The refusal
surfaces as an ordinary clarification.

### 4.5 Engine touch-ups (minimal, and why each was needed)

- `ExtractedEntity.person_aadhaar` → **`resolved_code`**, and the slot bind kind
  `{"bind": "aadhaar"}` → **`{"bind": "code"}`**. The AP spelling is still accepted, so the
  AP catalogue keeps binding while it is in the tree; WP-3 writes `"code"`. Delivering
  name→code *resolution* without a way to *bind* it would have left D10 half-built.
- `EntityCandidate` gains **`code`**, and `zones.candidate_tiebreak()` is now the single
  place that knows an LGD code is public and shown in full while an Aadhaar must be masked.
- `mask_aadhaar` is **kept but dormant** — no Aadhaar exists in this database, but `zones`
  and `router` call it on the shared candidate path, and a non-12-digit value passes through
  untouched so an LGD code is never mangled.

---

## 5. T4 — the collision guard

`test_gp_collisions.py` builds a **synthetic** roster in a fresh `tempfile.mkdtemp()` —
never in the repo and never on the Drive path, following WP-1 report §7.7. (The brief said
"in the scratchpad"; a committed test cannot hard-code one session's scratchpad path, and
`mkdtemp()` is the durable form of the same intent.) Nine panchayats, six distinct names:

| Collision | Fixture |
|---|---|
| Same name, different districts | Naugaon (Barpali, Bargarh) · Naugaon (Bhubaneswar, Khordha) |
| Same name, **same district**, different blocks | Rampur (Attabira, Bargarh) · Rampur (Barpali, Bargarh) |
| Same name, **same block** | Sundarpur ×2 (Khallikote, Ganjam) — only the code separates them |
| Unique | Andhrua · Chikilli · Haldikudar |

Asserted: every shared name clarifies; the prompt names each candidate's block *and*
district; the within-district pair proves district alone is not the qualifier; every
candidate carries its own code and none is truncated away; chip labels and replies are
mutually distinct; the same-block pair falls back to the LGD code; each chip resolves to the
panchayat it names and binds a **distinct** code; a resolved panchayat survives a second
round trip (or a chained clarify would loop forever); unique names resolve silently and are
not dressed up with a block; and — the last line of defence — a `{"bind": "code"}` slot
**raises** rather than binding a bare ambiguous name, while an *optional* one still binds
NULL (D2). `test_the_fixture_actually_collides` guards the guard: without it every
assertion could pass vacuously.

The builder is guarded (WP-1 report §7.3): it returns a skip reason instead of raising, so a
checkout without DuckDB skips cleanly rather than contributing errors — which is precisely
what the retired AP suite did wrong.

---

## 6. Substitutions for the missing views

Four allowed-values queries are **substitutes**, each marked `# TODO(create_views)` in
`entity_validator._DB_SOURCES`:

| Sheet says | Substituted with |
|---|---|
| `$status` → `v_activity.status_label` | `planned_activity` ⋈ `dim_code` on `variable='activity_status'` + `CAST(activity_status AS VARCHAR)` |
| `$asset_category` → `v_asset.asset_category_label` | `activity_asset` ⋈ `dim_code` on `variable='asset_category'` + `CAST(CAST(asset_category AS BIGINT) AS VARCHAR)` |
| `$asset_sub_category` → `v_asset.asset_subcategory_label` | same shape, `variable='asset_subcategory'` |
| `focus_area` ranking | `planned_activity` ⋈ `dim_code` on `variable='focus_area'` |

The `dim_code` join needs **both** halves per the data dictionary §4 — the `variable`
predicate and a VARCHAR cast. The asset columns are `DOUBLE`, so they need the extra BIGINT
cast first or `'77.0'` never matches `'77'`. That is a real trap for WP-3's SQL.

---

## 7. Oddities logged (validation logs, never fixes)

**1. The suite was making live API calls at T0.** `test_extraction_enums.LiveExtractionTests`
skipped only when `OPENAI_API_KEY` was absent — but it `load_dotenv()`s `Chatbot/.env`
first, and the key is there. So every baseline run of this suite, WP-1's included, made ~7
paid OpenAI calls. Now opt-in via `PRDW_LIVE_EXTRACTION=1`. **This is the most consequential
finding here**; the same pattern is worth checking in any eval harness before WP-4.

**2. `'\tWORK COMPLETED'` — a LEADING TAB** in `dim_code` code 178's description. New; the
brief warned about the theme trailing space but not this. Same class, same treatment: bound
verbatim, logged, matched whitespace-collapsed. A trimmed value would answer "no activities
are complete".

**3. `'Buildings'` is real** — code 173 in the `activity_status` decode, and it is a genuine
`asset_category` label, so the decoder plainly read from the wrong code list. Kept out of the
status enum, logged, and a test asserts it is still accepted as an *asset* category.

**4. `'Poverty allevation programme'` is misspelt in `dim_code`** (focus_area code 16). Bound
as stored; `"poverty alleviation"` is an alias onto it.

**5. The sheet lists 19 bind names, not 20.** `A1:H20` = header + 19 rows. The brief says 20.
Nothing is missing that I can see; `PARAM_ENTITY_TYPES` covers all 19 and a test pins the
list. Worth one look at the operator's current copy of the workbook.

**6. Sheet counts vs. loaded counts.** The sheet says 7 LSDG themes; `dim_lsdg_theme` holds
**6** distinct. It says 142 decoded asset subcategories; **138** distinct labels actually
occur in `activity_asset` (the registry is data-driven, matching the sheet's own
`SELECT DISTINCT … FROM v_asset` intent, so this is expected — recorded for completeness).
`asset_category` gives 27 non-null labels against the sheet's 28 (one code decodes to NULL),
and `'Community Sanitation'` is the description of **two** distinct codes.

**7. `Kalyansinghpur` the GP sits in `Kalyansingpur` the block** — one letter apart in the
same row. Aliased; not repaired.

**8. `SFC` unqualified is ambiguous** in principle: both the 4th and 5th State Finance
Commission appear in `scheme_name`. Per the brief it maps to the 5th (the current one), and
`"4th SFC"` reaches the other. Flagged in §8.

---

## 8. Open decisions for the operator

1. **A bare four-digit year reads as the fiscal year starting in it** — "expenditure in
   2024" → `2024-2025`. That is the convention the workbook's own sample values follow, but
   it *is* a silent pick between two possible readings. Alternative: clarify on every bare
   year. Recommend keeping it and revisiting from pilot logs. Pinned in
   `test_date_phrase.py` so a change is deliberate.
2. **`SFC` → 5th State Finance Commission** (§7.8). Confirm, or make it clarify.
3. **`EntityCandidate.village` carries the BLOCK for PR&DW.** The field keeps its AP name
   because `zones` renders it generically and WP-3 owns that file's copy. Renaming it to
   something tier-neutral (`locality`? `parent_place`?) is a small WP-3 edit; documented in
   `models.py` meanwhile.
4. **`top_n` ceiling of 1000** — chosen so "list every block" (314 statewide) is answerable.
   Confirm nothing in the catalogue wants more.
5. **Alias tables are seeded thin on purpose.** `_GP_ALIASES` is empty (20 of ~6,800 GPs are
   loaded — anything written today would be a guess) and `_BLOCK_ALIASES` has three entries.
   They fill from the dictionary file (D5) and the unanswered-question log; no code change
   is needed, only dict entries.

## 9. Left for WP-3 (unchanged from the brief, plus what this WP surfaced)

- **`fragment_reroute.GEO_SLOTS` and `main.GEO_SLOTS_WIDEST_FIRST` are still AP**
  (`village`/`mandal`/`district`). They are two of the four retrieval-layer modules WP-1
  report §8.2 scoped into WP-3, so they were left alone; `registry_values()` returns `[]` for
  the unknown types, so nothing crashes — but geography *fragments* ("in Ganjam?") will not
  work for PR&DW until they read `gp`/`block`/`district`. Two one-line constants.
- **`router`'s bare-name path** (`_bare_name_*`, ~lines 736–810) still validates against
  `farmer_name` and will simply find nothing. Domain copy, WP-3.
- **`zones._SLOT_PHRASES`** still names AP slots — user-facing copy, WP-3.
- **`router._CONSTANT_ENTITY_TYPES` / `_DEFAULT_ENTITY_VALUES`** still carry
  `aadhaar_length` and `tolerance_pct`; inert once the AP catalogue goes. `top_n: "10"`
  remains correct for PR&DW.
- WP-3 declares `{"bind": "code"}` on every `$gp_name` slot, and `PARAM_ENTITY_TYPES` is the
  bind-name→entity-type map to use.

**Still blocking downstream (unchanged):** `create_views.sql`. The four substitutions in §6
are marked and are a small edit when it arrives.
