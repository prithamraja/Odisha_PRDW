# WP-3 — Catalogue: implementation report

**Brief:** `handoffs/WP3_catalogue.md` (Path A)
**Date:** 2026-08-13
**Scope delivered:** T0–T9 complete.
**Gate:** all five conditions met (§2).

---

## 1. Commits

| Commit | Contents |
|---|---|
| `ea7cdef` | T1/T2: `create_views.sql` wired into the `duckdb_file` startup path; registry switched to the view-based allowed-values queries; D10 decided on evidence |
| `5dbfd44` | T3/T4/T5: the generator, `template_catalog.py` (346), `unanswerable_catalog.py` (30), `rerank_context.py` (327 families), the execution oracle |
| `0e16873` | T5/T6/T7: dashboard fast-path fix, AP retrieval layer retired, caveat rendering |
| `09716fc` | T8/T9: execution gate, `validate_catalog.py` rewritten, AP test fixtures swapped |

Baseline `3a6a0bc` untouched. `Chatbot/.env` never opened, never staged.
`Chatbot/data/panchayat_1.duckdb` opened read-only throughout — size and mtime
unchanged at the end of the run, no `.wal` or other file beside it, and three
write attempts against it (`CREATE TABLE`, `CREATE VIEW`, `DELETE`) were each
refused by DuckDB itself rather than by our own discipline.

## 2. Gate

| # | Condition | Result |
|---|---|---|
| 1 | All seven views live; registry substitutions replaced; value counts reconciled | **Yes** — §3 |
| 2 | 346/346 templates execute, row counts match the Test Report | **Yes** — zero mismatches, §7 |
| 3 | Structural tests green (families, slots, enums) | **Yes** — §8 |
| 4 | Caveat verbatim-rendering test green on all three serving paths | **Yes** — §6 |
| 5 | Full suite green; boot smoke under `DB_ENGINE=duckdb_file` | **Yes** — §8 |

### Test counts, baseline vs final

| | T0 baseline | Final | Δ |
|---|---|---|---|
| passed | 359 | **391** | +32 |
| skipped | 33 | 28 | −5 |
| **failed** | **0** | **0** | — |
| **errors** | **0** | **0** | — |
| subtests passed | 456 | 4,130 | +3,674 |

T0 was re-established after deleting `Chatbot/**/__pycache__` and
`Chatbot/.pytest_cache` on a clean tree (§3a discipline) and reproduced the WP-2
close exactly: 359 / 33 / 0 / 456.

The five skips that went away were AP endpoint tests in
`test_followup_fragment.py`; that module is rewritten and its endpoint half is
now opt-in rather than accidentally skipped (§8.2). No live API call happens
anywhere in a default run.

The 28 remaining skips break down as: 23 in `test_context_window_endpoint.py`
(18) and `test_date_phrase_endpoint.py` (5), 1 opt-in live-extraction test, and
4 opt-in live-routing tests. **The 23 are still AP content and still carry the
WP-1 §7.2 path landmine** — see §13.

---

## 3. T1 — the views

`Data/create_views.sql` is copied to `Chatbot/sql/create_views.sql`
**byte-identical** (SHA-256 verified) and is executed at adapter startup into the
writable in-memory catalog, exactly as `cache_tables.sql` already is. The view
bodies reference base tables unqualified and those names resolve through
`search_path` into the read-only attached file, so nothing in either body of SQL
needed rewriting and the Drive file is never modified.

Verified at startup: seven views defined, each one `SELECT`ed once (binding a
view is not proof it reads — an unresolved column in a LEFT JOIN target would
otherwise surface on a user's question rather than at boot), collision check
empty, 19 file tables unchanged.

| view | rows |
|---|---|
| `v_exp` | 12,724 |
| `v_approval` | 2,101 |
| `v_activity` | 12,704 |
| `v_plan` | 204 |
| `v_asset` | 12,704 |
| `v_progress` | 8,267 |
| `v_voucher` | 12,440 |

A missing `create_views.sql` is **fatal**, not degraded: all 346 catalogue
queries read a view, so a backend that boots without them answers nothing and
would fail 346 times at query time instead of once at startup.

### 3.1 Two things found while wiring it

**The collision check had an operator-precedence bug waiting for it.**
`INTERSECT` binds tighter than `UNION`, so extending
`check_cache_table_collisions()` to cover in-memory *views* as
`a UNION b INTERSECT (…)` would have parsed as `a UNION (b INTERSECT …)` and
reported every cache table as a collision. Both sides are parenthesised now.

**A view-less adapter fails SOFTLY, which is worse than failing.**
`EntityValidator._query` catches a failing allowed-values query, logs a warning
and returns `[]`. So an adapter built without views loads the status and asset
registries **empty**, and every assertion over them passes vacuously — including
the ones in `test_extraction_enums.py`, whose entire purpose is to catch that
class of drift. `db_factory.open_analytical_db()` is now the one way to open this
database, and the test uses it.

### 3.2 Registry reconciliation (the four `# TODO(create_views)` substitutions)

All four now use the sheet's own view-based queries. Three values moved:

| entity | WP-2 substitute | view-based | change |
|---|---|---|---|
| `status` | 6 | 6 | `'\tWORK COMPLETED'` → `'WORK COMPLETED'` |
| `asset_category` | 27 | 28 | `+ 'Uncategorised'` |
| `asset_subcategory` | 138 | 139 | `+ 'Uncategorised'` |
| `focus_area` (ranked) | 30 | 30 | identical, same order |

Each change is load-bearing, not cosmetic:

* **status** is WP2_REPORT §4.1's marked switch. `v_activity.status_label` TRIMs
  and de-tabs the `dim_code` decode, so binding WP-2's tabbed form against the
  view would have returned zero rows — the answer "no activities are complete",
  with no error anywhere.
* **`'Uncategorised'`** is not padding. It is 8,439 of the 12,704 asset rows, the
  single largest bucket, and a legitimate thing to ask about. Omitting it would
  refuse a question the view can answer.

`theme` deliberately still reads `dim_lsdg_theme`, because that is the query the
sheet gives for it; the trailing space on `'Theme 5 - Clean and Green Village '`
survives into the view and so survives in the registry. `v_activity.theme`
carries a seventh value, `'Unmapped theme'`, for the 13 focus areas with no LSDG
mapping — a view artefact rather than a theme, so it is not offered as one.

Final registry: `district=9 block=16 gp=20 fiscal_year=6 focus_area=30 theme=6
scheme=5 status=5 asset_category=28 asset_subcategory=139`.

---

## 4. T2 — the D10 geography decision, and its evidence

### 4.1 What the views actually expose

| view | `gp_lgd_code` | `block_code` | `district_code` |
|---|---|---|---|
| `v_activity`, `v_plan`, `v_voucher`, `v_approval` | **yes** | no | no |
| `v_asset`, `v_progress` | **no** | no | no |

`gram_panchayat` carries `block_code` and `district_code`; no view projects them.

### 4.2 Decision

**GP binds the resolved `gp_lgd_code`.** Every one of the 302 `$gp_name`
predicates was rewritten, and 304 slots across the catalogue declare
`{"bind": "code"}`. The slot keeps its workbook name; its value is now a code.

| predicate sits on | count | rewrite |
|---|---|---|
| `v_activity` | 274 | `v.gp_name = $gp_name` → `v.gp_lgd_code = $gp_name` |
| `v_plan` | 13 | same |
| `gram_panchayat` | 1 | same |
| `v_voucher` | 1 | same |
| `v_asset` | 13 | resolves through the parent activity — see below |
| `v_activity` (`IN` list, TRD-010) | 1 pair | `v.gp_lgd_code IN ($gp_name, $gp_name_2)` |

**The 13 `v_asset` predicates** could not be a column swap, because that view
carries geography but not the code. They became
`v.activity_code IN (SELECT activity_code FROM v_activity WHERE gp_lgd_code = $gp_name)`,
which is exactly equivalent on this data and provably so: every `v_asset` row's
`activity_code` exists in `v_activity` (0 orphans), no `activity_code` is
duplicated in `v_activity` (0), and none maps to two GPs (0). Spot-checked
per-GP row counts match by name and by code, and the T8 gate re-confirms all 13.

**Block and district bind their registry-validated canonical NAME**, because no
view exposes their codes. In the sample this is collision-free — 16 block names
to 16 block codes, 9 district names to 9 district codes, no name held by two
codes and no code with two spellings. **Statewide uniqueness is unverified and
unverifiable from this data**: the full LGD roster (30 districts, 314 blocks) is
still an open operator ask (PROJECT_PLAN §5.4). District names are unique
statewide by construction; block names are the real risk.

### 4.3 View-change request for the operator (§10.1)

Two additive one-line changes to `create_views.sql` would finish D10, and both
are the team's to make rather than ours — the brief says Path A uses the supplied
file verbatim, and `Chatbot/sql/create_views.sql` is byte-identical so that stays
auditable:

1. **`v_asset` and `v_progress`: add `a.gp_lgd_code`.** Both already join
   `v_activity`, which has it. That turns the 13 subquery predicates back into
   plain column comparisons.
2. **All geography-bearing views: add `g.block_code` and `g.district_code`.**
   `gram_panchayat` carries both. That is what would let blocks and districts
   bind codes statewide instead of names.

The entity layer already resolves names; both are predicate edits, not new
design.

### 4.4 One shape worth knowing about

`TRD-012` writes its filter as
`WHERE $district_name IS NULL OR district_name = $district_name OR TRUE`.
The trailing `OR TRUE` makes the district filter **inert** — every district is
always returned. The workbook's note says this is deliberate ("Every district is
returned alongside the state benchmark so the chosen district can be read in
context"), and the caveat carries it, but the slot does not narrow anything and
the reranker description says so explicitly.

---

## 5. T3/T4/T5 — the catalogue

### 5.1 Generated, not transcribed

`tools/build_catalog.py` builds four artefacts from
`AI_Chatbot_Questions.xlsx` and nothing else:

| file | contents |
|---|---|
| `query_router/template_catalog.py` | 346 templates (95 Yes, 251 Partial), 296 caveated |
| `query_router/unanswerable_catalog.py` | 30 known-unanswerables (17 No, 13 Dropped) |
| `query_router/rerank_context.py` | 327 family descriptions covering all 346 |
| `tests/data/workbook_test_report.json` | the 346-row execution oracle |

Hand-copying 346 signed-off SQL strings into Python would put a second,
divergeable copy of a ratified asset in the tree, and any re-ratification would
mean doing it again. Generating keeps one source of truth and makes "the
catalogue matches the workbook" a command — `python tools/build_catalog.py
--check` — rather than a review. The generated files are **committed**, so
nothing at runtime reads the xlsx and the ministry can audit the finite query set
as ordinary source. `openpyxl` is a build-time dependency only and is
deliberately not in `requirements.txt`.

The only edit made to any signed-off SQL is the D10 geography rewrite (§4.2).

### 5.2 Optional slots come from the SQL, not the Parameter Registry

A slot is optional iff its statement contains the guard `$p IS NULL OR`, because
that guard is what executes. The two sources disagree on **12 questions**, and in
every case the SQL is right:

| questions | slot | SQL says | Registry says | why the SQL is right |
|---|---|---|---|---|
| PLN-031, PLN-032 | `$theme` | required | optional | the theme is the question's subject |
| PLN-049, PLN-058, PLN-059 | `$focus_area` | required | optional | same |
| SCH-002, SCH-006, SCH-008 | `$scheme` | required | optional | same |
| TRD-010 | `$gp_name` | required | optional | a two-GP head-to-head; the note says both must be supplied |
| TRD-011 | `$block_name` | required | optional | same, for blocks |
| ALR-001, ALR-008 | `$date_range` | optional | required | the note says "Pass `$date_range` = NULL to sweep every year" |

The Registry's column is a property of the *bind name*; optionality is a property
of the *question*. Worth one edit to the sheet, and it is the only place the two
artefacts disagree.

Note ALR-001/ALR-008 make `$date_range` optional, which is a narrow exception to
D9's "a question with no year follows required-slot behaviour". The workbook's
own note endorses it and the SQL supports it.

### 5.3 Retrieval surface (decision D2)

1,766 paraphrases across the 346 templates, plus the entries themselves and the
30 unanswerables: **2,159 embedded vectors**. Each geography-optional template
carries a scope-phrased line per tier it can filter on, so the same entry is
retrievable at district, block and GP phrasing. This cannot crowd the candidate
list — the retriever keeps the MAX score over a template's vectors and counts
distinct `query_id`s toward *k*.

### 5.4 Families — and a finding

**327 distinct executable queries sit behind 346 template ids.** Fourteen groups
covering 33 ids have *byte-identical SQL and identical slots*:

| group | why |
|---|---|
| PLN-025/027/029, PLN-026/028/030, PLN-052/054/056, PLN-053/055/057 | the workbook's own scope variants ("in {GP}" / "in {Block}" / "in {District}"), which D2's optional filters collapse into one query |
| EXP-020/021/022 | "15th CFC at Block level" / "SFC at District level" — one query with `$scheme` and geography optional; the caveat says which value to pass |
| PLN-002/013, PLN-008/009, PLN-050/051, BUD-006/013 | scope or wording variants of one query |
| **EXP-031/032**, **BUD-014/017**, **EXP-009/011**, **EXP-026/030** | **genuine duplicates — same question text AND same SQL, twice** |

The last four pairs are workbook redundancy worth one look (§10.4). Everything
else is D2 working as designed.

A family is a maximal set of templates with identical SQL and slots, which is the
only grouping where "siblings repeat one description word-for-word" is *true*
rather than merely tidy. The other 313 templates each get their own description,
deliberately: the AP lesson about family-level descriptions concerns PARAMETER
variants, which the `accepts filters:` line already separates. It does not
transfer to 85 SBM templates that accept identical filters and differ only in a
keyword regex frozen inside their SQL — one shared description would leave the
reranker choosing between "community compost pits" and "household compost pits"
blind.

Descriptions are built from the SQL because what the reranker lacks is exactly
what the SQL knows and the question text does not: the measure and its accounting
basis, the row grain, the status filter, the SBM keyword pattern, and the scope
behaviour. `_DISAMBIGUATION` in the builder carries the hand-authored half — the
near-miss warnings no parsing can infer.

### 5.5 Known-unanswerables (T5)

30 entries, retrievable but not executable. They carry no SQL and no slots; the
router serves a matched id as an honest refusal built from the workbook's own
reason, verbatim, and offers the nearest answerable question as a chip where the
note names one (4 of them do).

They are indexed on purpose. Officers *will* ask these — the 13 dropped ones are
all beneficiary questions, and "how many people got a pension here" is an obvious
thing to want from a panchayat system. Left out of the index, such a question
retrieves nothing, scores below the no-match threshold and gets the generic
fallback, which is indistinguishable from the bot merely failing. They are a
separate dict from `TEMPLATE_CATALOG` because everything that iterates it — the
binder, the execution gate, `validate_catalog`, `_accepted_filters` — assumes an
entry has SQL and slots.

The reranker is told what they are, in their `↳` line. Without that, a
beneficiary question whose whole point is that it cannot be answered reads to the
model like any other candidate.

---

## 6. T6/T7 — the retrieval layer, and two silent wrong-answer bugs

### 6.1 Fifteen templates would have returned nothing, permanently

`_serve_query_id` dispatched dashboards on `query_id.startswith("D")`. That was
safe only while no AP template id began with D. **Fifteen PR&DW ids do** —
`DQY-001`…`DQY-011` and `DSS-001`…`DSS-006` — so every one of them would have
been served as a dashboard, returning the empty `dashboard_results.get(query_id,
[])` with no error and an answer reading "No records matched". Fifteen data-quality
and decision-support templates, silently empty forever.

Dispatch is on catalogue **membership** now. The same defect in reverse sat in
`/context/pop`, which set `tier="tier2" if frame.template_id.startswith("T")` —
twelve PR&DW ids begin with T (`TRD-001`…`012`) and 334 do not, so it would have
labelled almost every restored answer tier1.

### 6.2 An elicitation chip could silently drop the scope

`ELICITATION_MOVES["district"]` offers `EXP-001`, whose question reads "What is
the total actual expenditure incurred by **{gp_name}** in {date_range}?" — no
district placeholder anywhere. Formatting it with a district in hand produced a
chip naming no district at all, so tapping "what about Khordha?" would have
answered **state-wide** and presented it as Khordha's figure. A chip now
guarantees its anchoring value survives into the text.

Separately, `elicitation_chips` was keyed by entity type (`district`) while
templates want bind names (`district_name`), and every PR&DW template requires
`$date_range` — so before this work a bare place name would have produced **no
chips at all**. The router now passes the most recent loaded fiscal year as a
default, read from the data rather than the wall clock.

### 6.3 Retired and re-pointed

| item | disposition |
|---|---|
| `router._scope_sibling` | **retired** — D2 leaves no siblings to find |
| `inherit_frame_scope` | **re-pointed**: re-serves the SAME template with the frame's geography bound into the slot the question left empty. The defect is *easier* to hit under D2, not harder — every geography-optional template answers state-wide the moment nothing fills its district slot |
| `statewide_undo_chip` | **re-pointed**: sends this template's own question with the geography dropped and "across the whole state" appended. That wording is load-bearing — `_EXPLICIT_STATEWIDE` matches it, which is what stops the re-asked question re-inheriting the scope the chip exists to escape |
| `fragment_reroute.DRILL_MAP` | **retired**; `drill_target` returns the template itself when it can take the named tier, else None |
| `templates_share_subject` | re-keyed on bracket + module (the workbook's own classification) |
| `fragment_reroute.GEO_SLOTS` | → `("gp_name","block_name","district_name")`; `_FUNCTION_WORDS` gained the PR&DW unit nouns, `_DATE_WORDS` lost kharif/rabi |
| `main.GEO_SLOTS_WIDEST_FIRST` | → `GEO_TIERS_WIDEST_FIRST`, a paired list (§6.4) |
| `router._bare_name_*` path | → the three geography tiers, widest first, replacing the AP `farmer_name` probe |
| `router._CONSTANT_ENTITY_TYPES` | emptied (`aadhaar_length` retired); mechanism kept |
| `router._DEFAULT_ENTITY_VALUES` | `tolerance_pct` dropped; `top_n: "10"` kept |
| `zones._SLOT_PHRASES` | → the 19 workbook bind names |
| `suggestions.py` | PR&DW moves; requires only the **required** slots, so an optional geography slot is offerable and never demanded |
| `fallback.py`, `preprocessor.py` | PR&DW copy and abbreviations (GPDP, SBM, IHHL, CSC, SFC…) |
| `reranker._RERANK_SYS` | **rewritten** — it was telling the model this is an Andhra Pradesh agriculture database |
| `EntityCandidate.village` | → `parent_place` (D11.3) |

**The reranker prompt was the most consequential of these.** Its disambiguation
rules are now the distinctions this data actually punishes: the two expenditure
conventions, planned/approved/started/completed, absence questions read from the
roster, and the fact that SBM candidates differ only in a keyword pattern.

### 6.4 Bind names and entity types are no longer the same word

A context frame keys `bound_params` by the workbook's bind name
(`district_name`); the entity registry is keyed by entity type (`district`).
`registry_values("district_name")` returns `[]` rather than raising, so a mix-up
would empty the place vocabulary and stop every follow-up fragment working with
nothing in the logs. `main.GEO_TIERS_WIDEST_FIRST` pairs them explicitly.

### 6.5 T7 — caveats

The caveat is now **both** `QueryResponse.caveat` **and** appended verbatim to
the rendered answer, on all three serving paths.

WP-1 deliberately kept it out of the answer text, reasoning that answer text can
be regenerated by an LLM and a glued-in caveat could be paraphrased away. That
reasoning holds for LLM-generated text — and this answer is not LLM-generated:
`echo_answer` composes it deterministically from the resolved question, so
appending happens after every step a model could touch. What tipped the decision
is that **296 of 346 templates carry a caveat** and the only consumer that would
render the field distinctly is a frontend that is a separate, deferred
workstream. A caveat living solely in a field nothing renders is a caveat nobody
reads, which for 251 Partial questions is precisely the failure D3 exists to
prevent.

`tests/test_caveat_rendering.py` pins all three paths (`/query`,
`/context/pop`, `/operation`) with no network and no API key, asserting the text
appears **verbatim** and **last**. `/operation` is included because a recomputation
inherits the caveat of the rows it recomputes: a percentage of a 17%-covered
population is as misleading as the count it came from.

---

## 7. T8 — the execution gate

**346/346 templates reproduce the workbook's Test Report row counts exactly.
Zero mismatches, zero errors.** 325 return rows; the 21 documented zero-row
queries are pinned as a *set*, so a newly-empty query cannot hide among them by
coincidence of count.

It ran clean on the first attempt, which is the meaningful result: the geography
rewrite touched 302 predicates across 346 signed-off statements, and binding a
name where a code is expected returns zero rows with **no error anywhere**. The
oracle records what each query returned *before* the rewrite, so agreement is the
proof that the rewrite is semantically neutral.

The gate resolves the Test Report's sample GP names to codes through the **real
`EntityValidator`** rather than a lookup of its own, so a break in name→code
resolution fails here too instead of being papered over by a test-only shortcut.

Row counts are asserted **exactly**. Routing flips ~3% of questions on identical
replays and must never be regressed on a single miss; SQL does not, and nothing
in this path goes near the LLM. Any mismatch is a real defect.

Two forms, one oracle:
* `tests/test_catalog_execution.py` — 11 tests, 2,774 subtests, ~33 s
* `python validate_catalog.py` — the command-line form, for WP-5's gates file

`validate_catalog.py` was rewritten: it was AP-shaped throughout (counted `?`,
bound positionally, read `expected_empty_on_demo`, iterated the eight AP tables)
and would not have run at all.

---

## 8. Tests: everything swapped, retired or added

### 8.1 Added

| File | Tests | What it pins |
|---|---|---|
| `test_catalog_execution.py` | 11 (2,774 subtests) | the T8 gate, plus catalogue shape: no GP bound by name, every slot type agrees with the registry, no `date_filter`, no `$tag$`, every Partial carries a caveat |
| `test_caveat_rendering.py` | 5 | D3 on all three serving paths, verbatim and last |
| `test_dashboards.py` | 8 (84 subtests) | the proposal executes and matches its source templates row for row |

### 8.2 Swapped or retired

| File | Action | Why |
|---|---|---|
| `test_followup_fragment.py` | **REWRITTEN** | `DrillMapTests` tested a map D2 deletes. Its endpoint half was guarded by needing a Parquet drop that does not exist, so it skipped **by accident rather than by decision**, and computed that path as `parents[1].parents[1]` — which since the `Chatbot/` flattening resolves *outside this repo* (WP-1 report §7.2), so a stray `RTGS_Data/` in the shared parent would have pointed it at another project's data. Now opt-in via `PRDW_LIVE_ROUTING` and pointed at this repo's database |
| `test_named_binding.py` | **ONE ASSERTION REVERSED** | `test_the_caveat_is_a_separate_field_not_glued_onto_the_answer` asserted the opposite of what T7 requires. Renamed, and the reversal is argued in the test itself |
| `test_param_binding.py` | **FIXTURES SWAPPED** | Q098's crop and F09's farmer are gone. The mechanism they pin is exercised harder here — D2's idiom repeats a slot in all 346 templates. Two structural tests added: every `$name` has a slot and vice versa; every template sniffs as NAMED |
| `test_router_miss_path.py` | **FIXTURES SWAPPED** | AP's roster was people, PR&DW's is places. `FarmerElicitationTests` → `GramPanchayatElicitationTests`, same machinery, plus a new test that the chips carry a year so they execute |
| `test_zones_and_followups.py` | **FIXTURES SWAPPED** | AP frame → PLN-004; slot phrases → workbook bind names; a new test that an elicitation chip never silently drops the place (§6.2) |
| `test_rerank_context.py` | **4 AP-CONTENT TESTS REPLACED** | the AP scheme-set-logic collision does not exist here. Replaced by the PR&DW distinctions that actually collide: the two expenditure conventions, uploaded vs approved, absence-from-roster, SBM keyword patterns |
| `test_amount_units.py` | **ONE PIN UPDATED** | the `top_n` ceiling, 1,000 → 10,000 (D11.4) |
| `test_gp_collisions.py` | **RENAME ONLY** | `candidate.village` → `candidate.parent_place` |
| `test_extraction_enums.py` | **ONE HELPER CHANGED** | opens through `open_analytical_db` so the views exist (§3.1) |

Nothing else was touched.

### 8.3 Two engine fixes the catalogue forced out

* **`column_metadata` could not read `SELECT * FROM <cte>`.** ALR-013 is written
  that way, so it had **no declared columns at all** — and every consumer of that
  metadata (the operations layer's column typing, the follow-up classifier's
  dimension list, the chart hint) silently had nothing to work with for that
  question. CTE select lists are now resolved.
* **`zones` unit-swallowing compared the following word to the SLOT NAME** by
  backreference. That worked while slots were called `mandal`; it renders "in a
  block block" the moment they are called `block_name`. Replaced by a per-slot
  unit-noun table.

`column_types.json` gained PR&DW rules — the domain's counted nouns (GPs,
activities, years), its short-form expenditure columns, and exact entries for the
`STRING_AGG`'d lists (`activity_codes`, `schemes`, `years`) that the count
patterns would otherwise claim. Summing a comma-joined list is not an error
anyone would catch by reading the answer.

---

## 9. The `top_n` audit (decision D11.4)

**Audited; operator ruled the ceiling stays at 1,000** (2026-08-13). D11.4 asked
WP-3 to check whether any listing template legitimately needs more and raise it
if so. The audit says 38 templates can, the operator's answer is that they should
not be served that way, and the ceiling is unchanged.

Of the 91 templates that take `$top_n`, **38 can exceed 1,000 rows statewide**, in
two classes:

1. **Whole-roster rankings and listings at GP grain** — ~6,800 GPs statewide.
   `DSS-006` ("which GPs have the largest unspent balance"), `SAN-012`, `STS-004`,
   `PLN-031` and others. "List every gram panchayat" is a legitimate question and
   a 1,000 cap makes it unanswerable, which is the registry inventing a limit the
   catalogue does not have.
2. **Exception reports at ACTIVITY grain** — unbounded. `ALR-001`–`ALR-008`,
   `DQY-002`/`003`/`006`–`011`, `EXP-031`–`EXP-035`, `IMP-013`/`018`/`021`,
   `BUD-020`/`021`, `SCH-002`, `PLN-058`, `DSS-005`. 12,704 activities exist in a
   20-GP sample alone.

The remaining 53 templates group by a bounded dimension (theme ≤ 7, focus area
≤ 30, scheme ≤ 5, asset category ≤ 36) and are nowhere near the ceiling.

**The behaviour this ratifies:** an officer asking for more than 1,000 rows gets
a *clarification*, not an answer. That is the intended outcome for both classes —
neither a 6,800-row GP roster nor an unbounded exception report is a useful chat
answer at full length, and the ceiling is what surfaces "this is an export"
rather than dumping the rows. It is pinned in `test_amount_units.py` so raising
it later is a deliberate act, and it should only be raised alongside a product
decision about how a large result is actually delivered.

The 38 affected ids are listed above so the question can be revisited from pilot
logs if officers turn out to ask for full listings often.

---

## 10. Dashboard proposal — **for operator ratification**

`query_router/dashboard_catalog.py` holds **21 proposed entries** and ships
**switched off**: `DASHBOARDS_RATIFIED = False`, so `DASHBOARD_CATALOG` is empty
and nothing unratified reaches an officer. Flipping one flag activates them.

Every entry is **derived from a signed-off template**, not authored: `_state_wide()`
substitutes the template's own parameters (`$date_range` → the year literal,
`$top_n` → the page size, everything else → NULL, which the D2 idiom reads as "no
filter"). The product's first design principle is that the ministry can audit a
finite, validated query set; a dashboard whose SQL was written fresh here would be
unratified SQL in the one part of the catalogue that answers *without any user
input to qualify it*. `test_dashboards.py` executes each one and asserts it
returns exactly what its source template returns with the same binds.

| id | source | question |
|---|---|---|
| D01 | PLN-001 | How many GPs uploaded a GPDP? |
| D02 | PLN-005 | Which GPs have not uploaded a GPDP? |
| D03 | PLN-004 | District-wise GPDP submission rate |
| D04 | PLN-007 | Districts with the lowest submission rate |
| D05 | PLN-052 | Focus areas with the most planned activities |
| D06 | BUD-002 | Funding by source |
| D07 | BUD-005 | Tied versus untied split |
| D08 | BUD-006 | Planned expenditure by theme |
| D09 | EXP-003 | Percentage of the plan utilised |
| D10 | EXP-004 | Total unspent amount |
| D11 | EXP-006 | Expenditure by funding source |
| D12 | STS-001 | Activity status breakdown |
| D13 | IMP-005 | Completion rate by theme and focus area |
| D14 | IMP-011 | Focus areas with the most ongoing activities |
| D15 | SAN-002 | Activities awaiting administrative approval |
| D16 | SAN-007 | Administrative approval coverage |
| D17 | AST-002 | Assets created by category |
| D18 | SBM-SI-006 | IHHLs planned |
| D19 | SBM-SWM-001 | SWM activities planned |
| D20 | ALR-012 | GPs that recorded no activity |
| D21 | DQY-001 | Activities with no focus area recorded |

**Two decisions come with it.** (1) `DASHBOARD_FISCAL_YEAR` is pinned to
`'2024-2025'` rather than computed: `MAX(fiscal_year)` would roll onto 2025-2026
the moment a handful of next-year rows land, and a dashboard that quietly changes
which year it reports is worse than one that is a year stale. (2) Sixteen of the
21 carry a caveat, and a tile is where a caveat is most easily read past — they
are carried through to the response and the answer text, but whether a caveated
question belongs on a dashboard at all is a judgement for the SME.

**D02 and D20 return nothing on the 20-GP sample**, correctly: both are absence
questions and every loaded GP did file and did record. They are kept because
statewide they are exactly the tiles a review meeting wants; the test declares
them so a *newly* empty dashboard still fails.

---

## 11. Data oddities logged (validation logs, never fixes)

Adding to the running list in PROJECT_PLAN §3a:

1. **`v_asset` and `v_progress` expose no `gp_lgd_code`** although both join
   `v_activity`, which has it — §4.3.
2. **`TRD-012`'s district filter is inert** (`… OR TRUE`) — §4.4. Deliberate per
   the note, but the slot does not narrow anything.
3. **Four duplicate question pairs in the workbook**: `EXP-031`/`EXP-032` and
   `BUD-014`/`BUD-017` are the same question text *and* the same SQL twice;
   `EXP-009`/`EXP-011` and `EXP-026`/`EXP-030` likewise — §5.4.
4. **Twelve optional-slot disagreements** between the SQL and the Parameter
   Registry sheet — §5.2. The sheet is the one that needs the edit.
5. **`asset_category_label` is `'Uncategorised'` on 8,439 of 12,704 asset rows**
   (66%). Every asset question inherits that coverage gap; the caveats say so.
6. **`v_activity.theme` carries `'Unmapped theme'`** for the 13 of 30 focus areas
   with no LSDG mapping.
7. **`days_since_sanction` in `create_views.sql` computes to `CURRENT_DATE`**
   while its comment says "end of plan year" (flagged by the PM, confirmed here).
   Unused by the catalogue — `ALR-001`/`ALR-008` compute their own `DATE_DIFF`
   inline — so no answer is affected. Worth telling the team; do not touch the
   file.
8. **`create_views.sql`'s header says V4** while the workbook is V5. PM-validated
   as V5-compatible; cosmetic.
9. **`ALR-001` and `ALR-008` measure against `CURRENT_DATE`**, so their answers
   move as time passes. The workbook's note says so and it is in the caveat, but
   it means those two are the only templates in the catalogue whose result is not
   reproducible from the data alone — worth knowing before they are used in an
   eval set.

---

## 12. Open decisions for the operator

1. **The view amendment (§4.3)** — two additive lines would let blocks and
   districts bind codes and would simplify the 13 `v_asset` predicates. Until
   then, block/district bind names, which is safe for the pilot and unproven
   statewide.
2. **Statewide block-name uniqueness is unverified.** The sample's 16 blocks are
   collision-free; 314 statewide are not something this data can speak to. The
   full LGD roster is still an open ask.
3. ~~**`top_n` ceiling**~~ — **RULED 2026-08-13: stays at 1,000.** Requests above
   it clarify rather than answer; delivering a >1,000-row result is a separate
   product decision (export? pagination?) and is not blocking anything today.
   Revisit from pilot logs (§9).
4. **The dashboard proposal (§10)** — the selection, the pinned fiscal year, and
   whether caveated questions belong on tiles.
5. **The four duplicate question pairs (§11.3)** — keep both ids for traceability,
   or retire one of each?
6. **`ALR-001`/`ALR-008` making `$date_range` optional** is a narrow exception to
   D9. The workbook endorses it; confirm it stands.

---

## 13. Left for WP-4

* `reranker._RERANK_SYS`'s disambiguation rules were written from the data rather
  than from eval evidence. The bootstrap is explicit that domain ambiguity pairs
  should be rewritten **as they emerge from evals** — expect to revise them.
* The confidence thresholds are untouched and still AP-calibrated, per D-note in
  `config.py`: re-calibrate only from eval evidence, never from a single flipped
  question.
* The eval harnesses have **not** been audited for accidental live API calls
  (§3a asks for this before WP-4). The test suite has been, and is clean.
* `pmkisan_gates.py` and `build_stub_data.py` are still AP and still in the tree;
  they are WP-5's and a later package's respectively. `validate_catalog.py` is
  ready for the gates file to call.

* **Not done, and deliberately out of scope — flagged rather than left silent:**
  `test_context_window_endpoint.py` (18 tests) and `test_date_phrase_endpoint.py`
  (5) are still AP endpoint suites. They skip cleanly today because the flat
  Parquet drop is absent, but they carry the **WP-1 report §7.2 off-by-one**:
  both compute `_BACKEND.parents[1] / "RTGS_Data" / "flat"`, which since the
  `Chatbot/` flattening resolves to `LMIC AI Code repo\RTGS_Data\flat` — *outside
  this repo*, in the shared parent that holds every sibling project. If such a
  drop ever lands there, 23 AP tests would silently start executing against
  another project's data.

  I rewrote the third module with that defect (`test_followup_fragment.py`)
  because WP-3 had already broken it; these two still pass-by-skipping and the
  brief did not scope them. They are bucket-2 fixture swaps of a size worth their
  own slot — two sizeable endpoint suites against a domain whose templates no
  longer exist. Recommend WP-4 either port them to PR&DW ids and the
  `duckdb_file` path (making them opt-in the way `test_followup_fragment` now is,
  so they cost nothing by default) or retire them outright. Either is better than
  leaving a path that points out of the repo.
