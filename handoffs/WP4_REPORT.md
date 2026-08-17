# WP-4 — Eval integration and first runs: REPORT

> ## Where everything is
>
> ```
> Chatbot/eval_full_results_run{1,2,3}.jsonl   the three replays, raw
> Chatbot/eval_full_graded_run{1,2,3}.json     the same, graded
> Chatbot/consistency_results.jsonl            run x question x query_id
> Chatbot/triage_replays.py                    the >=2-of-3 rule, as a script
> Chatbot/eval_spend.py                        the spend guard all three harnesses go through
> Chatbot/tests/test_served_refusal.py         the refusal invariant WP-5 inherits
> handoffs/WP4_REPORT.md                       this file
> ```
>
> Commits: `1f9f726` (T2) · `55344ff` (T3+T4) · `5621bc7` (T5/T6) · `4a7eea6`
> (report) · `e3e70ff` (F1 fix + the pair-order bug it exposed).
> Re-run anything:
> ```
> python eval/gold/build_eval_questions.py --check      # gold set + catalogue cross-check
> python eval/gold/check_harness_format.py              # harness-format gate
> cd Chatbot && python -m pytest tests -q                # 461 passed / 16 skipped
> cd Chatbot && python tools/build_catalog.py --check    # catalogue vs workbook
> cd Chatbot && python validate_catalog.py               # 346 executed
> cd Chatbot && python triage_replays.py eval_full_graded_run{1,2,3}.json
> ```

---

## 0. For the PM — the two findings that matter

**The gate is NOT green, and the reason is not the router.** All the engineering
in this package landed and is green (§1, §2). The eval numbers are far below the
benchmarks, and the triage says why:

| # | finding | evidence | what it is |
|---|---|---|---|
| **F1** | **The entity extractor silently returns nothing on ~25% of calls.** Not a timeout, not a truncation, not a parse failure — `gpt-5.4-mini` with `reasoning_effort: "low"` sometimes stops thinking before it reads the year out of the question. | 12 **identical** calls on one question: 9 returned `date_range="2024-2025"`, **3 returned `None`**. All `finish_reason=stop`, all valid JSON, no exceptions. The three nulls spent **40/49/52 reasoning tokens**; every success spent **80–201**. | **FIXED** in `e3e70ff` — with a deterministic fallback, not a model change: the reader was already in the tree and unreachable. §5.1. |
| **F2** | **Odia script does not retrieve.** recall@30 is 100% in English, 100% code-mixed, 100% transliterated Odia, and **52.9% in Odia script**. Every single recall miss in the set is an Odia-script row. | §3.1. 8 of 17 Odia rows fall outside the top 30; two land at rank 220 and 330 of 376. | A real retrieval defect, **compounded by an SME dependency**: WP-4a §4.3 flags all 19 Odia rows as unratified phrasing, so we cannot yet tell "the retriever cannot read Odia" from "these sentences are not what an officer would write". |

F1 alone accounts for **55 of the 73 confirmed failures**. It is the `top_n`
problem again, one layer down: a uniform, artificial loss that makes the router
look far worse than it is, and exactly the thing WP-4a §5.2 warned must not be
answered by re-tuning anything. **It is now fixed** (§5.1), and fixing it
surfaced a silent wrong-answer bug in the year-pair split that no eval number
would ever have caught (§5.1a) — but **every figure in §3 was measured before
both**, so the accuracy line below stands until a re-run replaces it.

**Nothing was tuned.** `query_router/config.py` has not been touched since the
pre-adaptation baseline commit `7184d5e` — provable with `git log`. Zero
threshold changes, as the brief requires.

### What I need from the PM

1. **Authorise a re-run of the full eval.** F1 is fixed (§5.1) and 5.1a fixes
   a silent wrong-answer bug found alongside it, but every number in §3.3 was
   measured before both. Nothing else here is worth acting on until the eval is
   re-run, and no threshold may move until it is.
2. **Note that F2 is now the second SME-blocking item**, alongside the WP-4a §4
   list — and the cheapest one to unblock, since it needs a native reader for
   half a day, not a metric ruling.
3. **Rule on the two behaviour gaps in §5.2** (the tier collision reaches the
   clarification on only one of two code paths; three beneficiary questions
   decline without retrieving their documented reason).

---

## 1. Gate

| # | gate item | status |
|---|---|---|
| 1 | Integration committed; `--check` and the harness gate green from the committed tree | **PASS** — see §1.1, with one correction to the brief |
| 2 | D18 fixes in via the generator; execution oracle still 346/346; suite green with updated pins | **PASS** — 461 passed / 16 skipped (baseline 391/28); oracle 346/346; `validate_catalog` all clear |
| 3 | All three paid runs completed with spend recorded; consistency replays done | **PASS** — §3, §4 |
| 4 | Every reported failure replay-confirmed and classified; zero threshold changes | **PASS** — §5; `config.py` unchanged since `7184d5e` |
| 5 | The 23 AP endpoint tests no longer reference paths outside the repo | **PASS** — §2.7 |
| — | **Accuracy against the two benchmarks** | **FAIL — 62.2% against 96–97%**, root-caused to F1 and F2. F1 is fixed post-run (§5.1); the ceiling that implies is 86–88%, and only a re-run settles it |

### 1.1 A correction to the brief: T1 was already done

The brief says the tree "currently has uncommitted WP-4a output" and that T1's
first commit integrates it. It does not. `eval/`, `handoffs/WP4a_REPORT.md`,
`Chatbot/eval_questions_full.json` and `test_questions_query_mapping.csv` were
all committed at `8ffcf70`, and the pending `PROJECT_PLAN.md` edits landed at
`2ce419d`. Verified, then re-verified by rebuilding: `--install` produced
byte-identical files, so the committed harness inputs were current.

**The tree was not clean at T0, and the dirt was not mine.** The uncommitted
files were the concurrent **Discover** workstream — `Insights/`,
`handoffs/WPD*`, and the D24 row in `PROJECT_PLAN.md`. Per D14 (file-disjoint) I
left every one of them alone and staged only Ask-side paths; `git status`
confirms Discover's files are still unstaged across all three of my commits.
More Discover files appeared mid-run (`phase5_ranking.py`,
`handoffs/WPD2_REPORT.md`), so that session was live throughout — the §3a
"commit before trusting the tree" rule could not be honoured for the tree as a
whole, only for my half of it.

**T0 baseline: 391 passed / 28 skipped / 0 failed**, matching the WP-3 close
exactly, after deleting `__pycache__` and `.pytest_cache` per §3a.

---

## 2. What was built (T2, T3, T4)

### 2.1 T2a — `$top_n` is optional-with-default (D18.P1)

Edited the **generator**, never the generated file: `DEFAULTED_SLOTS` in
`tools/build_catalog.py`. Regenerating touched exactly 91 lines and nothing
else —

```
-  {'name': 'top_n', 'entity_type': 'top_n'},
+  {'name': 'top_n', 'entity_type': 'top_n', 'optional': True, 'default': '10'},
```

The runtime reads the declaration (`router.slot_defaults()`), so the generated
catalogue is the single source of truth. `_DEFAULT_ENTITY_VALUES` survives as
the entity-type fallback the AP test fixtures still use, and a new test asserts
the two agree so they cannot drift.

**One trap worth naming.** "Optional" here does *not* mean "bind NULL": `LIMIT
NULL` is **unbounded**, the exact opposite of a page size. `_resolve_slot_value`
backstops every bind path that does not go through validation, so a defaulted
slot can never reach the database empty.

**The brief expected pins to update in `test_catalog_execution.py` /
`test_param_binding.py`. There were none** — no test asserted `top_n`'s
required-ness. So instead of updating pins I added them: `$top_n` is optional
with default `"10"` on all 91 slots, the two default tables agree, a ranking
template binds `10` rather than NULL, and (D18.P2) `$threshold` /
`$amount_threshold` are on exactly 15 templates, required, undefaulted.

**Ceiling unchanged at 1,000**, per the operator ruling at `96179d8`.

### 2.2 T2b — thresholds stay required (D18.P2)

Confirmed: no code change needed. Now pinned, so a future generator change
cannot quietly default a slot that changes the population under study.

### 2.3 T2c — Odia numerals (D18.P5)

`date_phrase.normalize_digits()` translates U+0B66–U+0B6F to ASCII before the
year patterns run. A **1:1 code-point** map, deliberately: the module records
character spans (`consumed`, the money/quantity guards), and a normalisation
that changed offsets would silently mis-claim them. 8 new tests, including that
the guards still hold (`₹୨୦୨୫` is still not a year) and that length is
preserved.

Scope is **digits only**. `ମାର୍ଚ୍ଚ ୨୦୨୫` degrades to the bare-year window
rather than the March one, because `_MONTHS` is an English vocabulary and an
Odia month lexicon is a larger change than the ruling asked for. Pinned as a
test so it is a decision, not a surprise. Devanagari digits are deliberately
excluded — no gold row exercises them.

**Gold row G1008 flipped from `clarify` to `answer`, and it hit 3/3 in the live
run** — end-to-end proof, not just a unit test.

### 2.4 T2d — the echo of a partially-bound question

`router.py` built `query_description` with `abstract_question.format(**entity_values)`,
which is all-or-nothing: one unbound optional slot raises `KeyError` and the
fallback printed the **raw abstract question**, discarding even the
substitutions that *had* resolved. Latent in AP (every slot required, so the
`except` never fired); under D2 partial binding is the normal case.

Replaced with per-placeholder substitution (`zones.resolved_question`):

| case | before | after |
|---|---|---|
| year bound, GP not | `…incurred by {gp_name} in {date_range}?` | `…incurred by each GP in 2024-2025?` |
| nothing bound | `How many GPs in {district_name}/{block_name}…{date_range}?` | `How many GPs in all districts/all blocks…in 2024-2025?` |
| GP bound | (worked) | `…incurred by Andhrua in 2024-2025?` |

**"each GP" vs "all GPs" is decided by the SQL, not by guesswork.** A new
generated field `grouped_geo` records which geography a statement returns one
row *per*, read at build time from the outermost `GROUP BY` (155 of them are
written as bare ordinals, so the ordinals are resolved against the SELECT list).
36 templates carry it. EXP-001 groups by GP, so the filter being off reads
"each GP"; PLN-001 aggregates to one count, so it reads "all districts".

Asserted over **all 346 entries with zero entities bound**: no `{` survives.

**The eval run then found the other half of this defect** — see §5.3. Fixed in
`5621bc7`: a bound slot with no placeholder in the question text is now
appended (`…in 2024-2025 (Laxmipur block)?`) instead of rendering nowhere. 332
of 346 templates need that append when fully bound.

### 2.5 T2e — fragment tier selection

Implemented as specified: (i) candidate tiers are intersected with
`executable_geo_slots(frame.template_id)` **before** resolving; (ii) one fitting
tier auto-slots and the echo names it when the name was ambiguous; (iii) two
fitting tiers raise a **`tier_collision`** clarification with tier-qualified
chips (D18.P3), never the generic ambiguous-fragment prompt; (iv) the
standalone-fragment chip is dropped when it shares no subject with the frame —
kept only if nothing else would survive, because an empty clarification is worse
than a noisy one.

**A correction to the brief's diagnosis, with evidence.** It states that
`drill_target` found "the frame's template (`EXP-001`) has no `block_name`
slot". EXP-001 *does* have `$block_name` — all three tiers, verified against the
shipped catalogue. The real mechanism in the operator's screenshot is
different: the frame already had `gp_name` bound, `_fragment_edit` skips
already-bound slots, so only block/district competed, and `serve_drill_hop`
requires **every** slot to have a value — so it bound the old GP *and* the new
block, got zero rows, and abandoned the hop.

That means fix (i) alone would not have fixed the screenshot. Fixing it properly
needs the bound tier to compete as a **replacement**, which changes documented
tier-precedence behaviour ("a district-scoped question reads 'in Barpali?' as
the block it must be", `main.py`). **I did not make that change**: it is a UX
ruling, not a bug fix, and changing tier precedence hours before an eval run
would have contaminated the numbers against behaviour nobody has ratified.
Filed in §5.2 as an operator decision.

What (i) *does* fix is real and measurable: 36 of the 346 templates carry an
incomplete tier set, and (iii) now fires for every one of the three sample-live
collisions (Laxmipur, Bheden, Kalimela) on the 302 full-tier templates.

**Two gold fragment pairs added** (G1523/G1524 collision-without-constraint,
G1043/G1044 collision-with-constraint). G1043/G1044 hit **3/3**. G1524 exposed a
path gap — §5.2.

### 2.6 T3 — refusals are graded on their reason

The 19 known-unanswerable rows now carry `gold: <unanswerable id>` instead of
`gold: "no_match"`, so "declined for the right documented reason" is
distinguishable from "declined generically". `grade()` gained the refusal branch
and three honest buckets: `wrong_refusal`, `declined_generically`,
`refusal_with_rows`.

**The coupling is now asserted directly**, in `tests/test_served_refusal.py`, over
all 30 entries: a served refusal leaves `result` as `None`, never `[]`. If it
ever became `[]` the grader would read it as a template answer whose id is not a
template, and all 19 rows would flip in one move with nothing saying why. This
is the assertion WP-5's `prdw_gates.py` should lift verbatim.

### 2.7 T4 — harness repairs

| item | before | after |
|---|---|---|
| **a** `grade_full_eval` tier tuple | `("tier1_dashboard", "tier2_template", "operation")` — the enum MEMBER names. `main.py` emits the VALUES. The first clause was **always false** for a template answer; grading survived on the `n_rows` fallback, so a template answer returning `None` rows was misgraded. 21 templates return zero rows by design. | `("tier1", "tier2", "operation")`, plus a test with a legitimate `None`-rows answer |
| **b** `recall_eval` import | bare `from query_router.intent_catalog import INTENT_LOOKUP` — the last consumer of the retired AP retrieval layer | defended; the harness survives the retirement being finished |
| **b** crowding metric | printed `mean: 0.0, max: 0` every run, reading as "no crowding" when **nothing was measured** (INTENT_LOOKUP has 0 entries) | replaced by two measured numbers *and* an explicit "REMOVED, not measured-as-zero" note. §3.2 |
| **b** recall index | one vector per query_id — a retriever this system does not have | built as `VectorRetriever` builds it: paraphrases and unanswerables included, MAX per template, k counting distinct ids. 376 entries, **2,159 vectors** |
| **b** Hinglish prompt | asked for *health-insurance* questions naming PM-JAY, TAT, LAMA | PR&DW terms (GPDP, SBM, LSDG, SFC) |
| **c** spend guards | none on any of the three; one `python recall_eval.py` embedded the whole catalogue | new `eval_spend.py`: every harness prints a call estimate and refuses without `--yes` / `PRDW_EVAL_CONFIRM=1`. `run_full_eval` imports `main` **inside** `run()`, after the guard, because importing it constructs the client and embeds the catalogue |
| **d** `rerank_eval` gold | 79 AP rows hardcoded in a docstring (`Q125`, `G03-S`, PM-KISAN farmers) — **every row would have missed** | `eval/gold/*.jsonl`, 197 rows, the same source the other two harnesses read. Also indexes the unanswerables, without which the 19 refusal rows could never be retrieved |
| **e** endpoint suites | 23 tests behind `parents[1].parents[1] / "RTGS_Data" / "flat"` — a path **outside this repo**, so they skipped by accident and a stray drop would have pointed them at another project's data | ported to PR&DW on `duckdb_file`. §2.8 |
| — | `run_consistency_eval` | replayed a **non-existent** `eval_questions_33.json` 25 times with a fresh session per question — which would have routed the 13 follow-up fragments standalone and called the result instability | drives `run_full_eval.run()` once per replay, so consistency measures exactly the pass whose accuracy is reported |
| — | `run_custom_eval` | same out-of-repo `DATA_DIR` default | fixed (its input file does not exist either — the harness is dormant, and now dormant *and* harmless) |

### 2.8 T4e in detail — what was ported and what was retired

**`test_context_window_endpoint.py`** (18 AP tests) split in two:

* **6 tests now run in the ordinary suite, with no network.** The
  pending-clarification machinery is deterministic by design — closed
  vocabulary and registry lookups, no LLM — so the pause is seeded and the reply
  resolved directly. The AP versions could only ever run on a machine with a key
  *and* a parquet drop, so in practice they never ran at all. These pin: a named
  value resumes the paused question; a scope-widening reply ("all schemes") is
  understood rather than re-routed; an unusable reply is re-asked **once** and
  carries the pause forward; the escape chip sends the user's own words back;
  said twice, it is taken at face value.
* **5 tests are opt-in live** (scope inheritance, the operation type-guards, the
  no-placeholder-in-any-chip rule).
* **The 5-test farmer-disambiguation group is retired**, with its reason: its
  PR&DW analogue is the D4 GP-name collision, which the 20-GP sample **cannot**
  exercise — every loaded GP name is unique, which is precisely why WP-2 wrote
  that test with synthetic duplicates. Covered by `test_gp_collisions.py`.

**`test_date_phrase_endpoint.py`** (5 AP tests): the request-window contract
survives; the three `date_filter`-**injection** tests are retired because D9
removes that machinery (no PR&DW template carries a `date_filter`, asserted in
`test_catalog_execution.py`). Re-authored around the D9 analogue — the fiscal
year binding as an ordinary `$date_range` slot, and an assertion that no
template applies a date filter on the serving path.

**These live classes are ported but UNRUN.** The brief authorises LLM spend only
in T5's eval runs, and an opt-in endpoint suite is not an eval run. Run them
with `PRDW_LIVE_ROUTING=1` when spend is next authorised. The 6 deterministic
tests are running and green now.

---

## 3. The runs (T5)

**Model identity (T5d), checked against the live model list, not just config:**

| role | model | on the account | reasoning model |
|---|---|---|---|
| extraction | `gpt-5.4-mini` | yes | **yes** |
| rerank | `gpt-5.4-mini` | yes | **yes** |
| abstraction | `gpt-5.4-mini` | yes | **yes** |
| embedding | `text-embedding-3-large` | yes | no |

There is no separate reranker model — reranking is an LLM call on
`RERANK_MODEL`. Pin all four in WP-5's identity gate. **That the extractor is a
reasoning model is not incidental to F1; it is the cause.**

### 3.1 T5a — recall

Benchmark: recall@30 ≈ 97% (AP parity). **Measured: 95.3%** (163/171).

| K | recall |
|---|--:|
| @5 | 86.5% |
| @10 | 91.2% |
| @20 | 94.2% |
| **@30** | **95.3%** |

The headline hides the finding. By language:

| language | recall@30 | n |
|---|--:|--:|
| English | **100.0%** | 96 |
| code-mixed | **100.0%** | 45 |
| Odia transliterated | **100.0%** | 13 |
| **Odia script** | **52.9%** | 17 |

**Every miss in the set is an Odia-script row** (F2). Two sit at rank 220 and
330 of 376 — not near-misses, absent. Retrieval on the other three registers is
perfect, which is itself worth knowing: the transliterated rows resolve fine, so
the failure is the **script**, not the language.

One gold-set authoring error was found and fixed here (§5.4): G1524 is both an
ambiguity row and a fragment, and was scored against a template it has no
subject for. Fragments are now excluded from the recall set by
`session: "prev"` rather than by `case_type`.

### 3.2 Crowding — measured, not assumed

The AP metric was dead (§2.7b). Replaced with two:

* **Paraphrase crowding** — extra raw vectors walked to reach 30 distinct ids:
  **mean 21.8, max 94**. 40 of 171 queries pay nothing; the tail is long. The
  dedup-by-query_id rule is doing real work, and this is the price of D2's
  scope-paraphrase design.
* **Duplicate-row crowding** — the catalogue ships **4 groups of identical
  question text, 9 entries where 4 would do** (`BUD-014/017`, `EXP-009/011`,
  `EXP-010/026/030`, `EXP-031/032`), exactly as WP-4a §6.1 reported. Measured
  impact on the gold set is small (mean 0.02 siblings in top-30, max 2), so
  **de-duplicating is a tidiness decision, not an accuracy one** — which
  settles P4 on evidence: collapsing them will not move the number.

### 3.3 T5b/T5c — the full eval, three replays

Benchmark: ≈ 96–97% behaving correctly. **Measured: 59.8% / 64.6% / 62.2%.**

| | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| hit | 120 | 131 | 127 |
| partial | 2 | 2 | 1 |
| clarify_gold_offered | 3 | 2 | 2 |
| **behaving correctly** | **59.8%** | **64.6%** | **62.2%** |
| clarify | 75 | 67 | 75 |
| wrong_template | 6 | 4 | 0 |
| declined_generically | 3 | 3 | 4 |
| *of which extraction returned nothing* | *62* | *56* | *61* |
| **behaving correctly, excluding those** | **85.0%** | **88.2%** | **87.8%** |

Wall clock per replay: 619s / 2,025s / 1,102s — the middle replay hit an API
slowdown, not a code change.

**Consistency. 90 of 209 questions (43.1%) did not return the same result on all
three replays** — both by verdict and by `query_id` (the two counts coincide
because a question that flips between answering and clarifying flips its
`query_id` between a template and `None`). The benchmark is ~3%.

That gap is F1, not routing nondeterminism. The evidence is that it is
*concentrated*: on the 106 questions the extraction defect never touched,
behaviour is **stable at 83–84% across all three replays**, and 48 of the 103
affected questions were hit in exactly one replay of three — the signature of a
per-call coin flip, not of an unstable retriever. Until F1 is fixed, this number
measures the extractor's variance and says nothing about routing stability, so
**the ~3% consistency benchmark is untested by this run**.

---

## 4. Spend

Authorised in T5 only; every other step ran with mocks, caches or no network.
Estimates were printed before each run by `eval_spend.py`.

| run | calls |
|---|--:|
| `recall_eval` (catalogue embeddings 9 batches + queries) | 10 |
| `recall_eval` re-run after the CSV fix (cached index) | 1 |
| 3 × full-eval replay (209 q × [embed + rerank + extraction] + 13 classifications) | ≈ 1,845 |
| model-identity check | 1 |
| F1 diagnostics (3 + 6 + 12 extraction calls) | 21 |
| **total** | **≈ 1,878** |

**Token totals are not reported, because they were not instrumented.** None of
the three harnesses records `usage`, so any figure here would be a guess.
Recommendation for WP-4c: have `run_full_eval` accumulate `resp.usage` — the
diagnostic in §5.1 shows the field is available and immediately useful
(reasoning-token spend is what identifies an under-thought extraction).

---

## 5. Triage (T6)

`triage_replays.py` applies the rule mechanically: a failure is reported only if
it is a non-hit in **≥ 2 of 3** replays. **73 confirmed**, 49 listed as noise and
not acted on.

| class | count | disposition |
|---|--:|---|
| **(i) real defect — extraction returns nothing** (F1) | **55** | **FIXED**, §5.1 — 87.6% of them recover the gold year deterministically. Re-run to confirm. |
| **(i) real defect — Odia-script retrieval** (F2) | **13** | Filed, §5.1. Also **(iv)**: all 13 are rows WP-4a §4.3 flagged as unratified phrasing. |
| **(i) real defect — refusal not retrieved** | 3 | §5.2. `BEN-001`, `BEN-003`, `PLN-022` decline, but generically. |
| **(i) real defect — follow-up fragment** | 2 | §5.2. `#1003 "and Khajuripada?"`, `#1016 "what about last year?"`. |
| **(ii) gold-set authoring error** | 1 | **Fixed and logged**, §5.4. |
| **(iii) replay noise** | 49 | Listed in the triage output, **not acted on**. |
| **(iv) SME-pending** | 13 (the Odia rows above) + the 11 ambiguity rows | Tagged against WP-4a §4.2/§4.3. |

Classes are priority-ordered — a row that is *both* an ambiguity case and an
extraction-null lands in (i), because the extraction failure is what actually
happened.

### 5.1 F1 — the extraction defect, and what to do about it

**Evidence.** 12 identical calls to `extract_entities` on *"Which Gram
Panchayats have not yet uploaded their GPDP in 2024-2025?"*:

```
x9  parsed date_range='2024-2025'  finish=stop  reasoning_tokens=80..201
x3  parsed date_range=None         finish=stop  reasoning_tokens=40, 49, 52
```

Every call succeeded. Every response was valid JSON. No timeouts, no
truncation, no rate limits. The failures are **the model deciding not to
extract**, and they correlate exactly with spending under ~60 reasoning tokens.
`entity_extractor.py` sets `reasoning_effort: "low"`.

**A second, independent defect in the same function.** The call is wrapped in a
bare `except Exception: return {s: None for s in slots}`. A timeout, a 429 or a
JSON error is therefore **indistinguishable from "the user named nothing"**, and
the user is asked *"For which date range?"* about a question in which they
plainly stated the year. That swallow should log and re-raise or return a
distinct sentinel, whatever else is decided.

**A correction to the mechanism, before the fix.** I first wrote that the model
"stops thinking before it reads the question". That over-reads the data. What is
established is a clean *correlation* — the three nulls at 40/49/52 reasoning
tokens, the nine successes at 80–201, no overlap — but with n=3 nulls the
causality is not established, and a model that decides early there is nothing to
extract would spend fewer tokens for that reason rather than the reverse. It
matters practically: "raise `reasoning_effort`" only helps if under-thinking is
the *cause*.

**FIXED in `e3e70ff` — with a deterministic fallback, not a model change.**

The reader was already in the tree and unreachable. `date_phrase` is a
word-bounded regex pass built in WP-2 for exactly this mapping, and
`EntityValidator._validate_fiscal_year` already calls it, already consults the
loaded years for relative phrases, and already splits a two-year phrase across
the paired slots. It only ever received **the string the extractor produced**,
so a null meant it was never consulted. The router now hands it **the question**
when the extractor comes back empty.

Measured against WP-4's own recorded failures, three replays pooled (n=178):

| outcome | |
|---|--:|
| year recovered, matches gold | **87.6%** |
| not recovered — the year lives in the *frame*, not the sentence (all follow-up fragments) | 8.4% |
| correctly nothing to find | 3.9% |
| **wrong year** | **0** |

Per replay that clears 55 / 48 / 53 stalls, a ceiling of **86.1% / 87.6% /
87.6%** against the 59.8% / 64.6% / 62.2% measured. A ceiling, not a
prediction — clearing the stall does not guarantee the row then routes
correctly, and **only a re-run settles it**.

Three properties made this the right shape:

* **A fallback, not a prefill.** It runs only where extraction produced
  nothing, so no call that works today can change. `amount_from_text` takes the
  prefill approach for rupee figures and this could follow later —
  `_log_fiscal_year_disagreement` records where the two readers differ, which is
  the evidence that decision needs.
* **Deterministic**, so unlike a retry it adds no replay variance to a
  measurement whose variance is the problem.
* **Placed ahead of the declared defaults** (evidence from the user's own text
  beats a system-supplied value) **and ahead of the `optional` check**, because
  ALR-001/ALR-008 carry an optional `$date_range` where binding NULL answers
  across every loaded year about a question that named one — a silent wrong
  answer rather than a visible stall.

One gotcha worth knowing: `EntityNotFound` is swallowed deliberately. Letting it
propagate renders *"I couldn't find a date range called '<the entire
question>'"* — the officer's sentence quoted back as a malformed value, strictly
worse than the stall it replaces.

**What it does not fix.** It covers `$date_range` — 177 of the 179 observed
null-asks, so nearly all the measured damage. The model unreliability underneath
is untouched, there is no equivalent deterministic reader for a theme or a
scheme, and the bare `except Exception` swallow above still needs addressing on
its own account. If the wobble ever shifts to a categorical slot there is no
backstop. **The full eval must still be re-run before any accuracy number is
quoted, and no threshold may move until it is.**

### 5.1a A silent wrong-answer bug the fix walked into

Prototyping F1's fallback surfaced a **pre-existing** defect that would
otherwise have been inherited.

`_validate_fiscal_year` split a two-year phrase as `$date_range` = **earlier**,
`$date_range_2` = **later**. Every one of the five paired templates binds the
opposite —

```
COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS activities_year1,
COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)   AS activities_year2,
COUNT(*) FILTER (WHERE v.fiscal_year = $date_range)
- COUNT(*) FILTER (WHERE v.fiscal_year = $date_range_2) AS change_in_activities
```

— and their question text agrees: *"between {date_range_2} and {date_range}"*.
PLN-039, PLN-040 and TRD-004 compute `$date_range − $date_range_2`, so the old
order **inverts the sign**: *"which themes showed the greatest increase"* answers
with the greatest **decline**, silently, in a table that looks entirely normal.
That is the confidently-wrong class this project exists to prevent.

It stayed hidden because the extractor normally assigns the two slots itself and
got it right; the split only fires when **one string carries both years** — which
is exactly what the fallback hands over. Fixed in `e3e70ff`, with the direction
now pinned against the SQL, so a future template that reverses the convention
fails loudly instead of answering backwards.

**Worth noting for WP-5's gates:** this is a defect no eval number would ever
have caught, because the eval's gold rows were authored from the same reading the
extractor happened to produce. It was found by reading the SQL.

### 5.2 Behaviour gaps for a ruling

* **Tier collision reaches the clarification on only one of two paths.** G1524
  ("what about Laxmipur?" over a whole-of-state EXP-001 frame) *should* raise
  the `tier_collision` clarification per D18.P3. In the live run it did in 0/3
  replays: the LLM follow-up classifier reads the fragment as an executable
  `frame_edit` first, `serve_frame_edit` succeeds, and `_fragment_reading` — where
  my tier check lives — is never reached. The row still bound
  `block_name=Laxmipur` and returned the right row, so it grades `hit`; but the
  GP reading was never offered. The same check belongs on the classifier path.
* **The bound-tier replacement reading** (§2.5). The operator's original
  screenshot needs it; it changes documented tier precedence; it is a UX call.
* **Three refusals decline generically.** `BEN-001`, `BEN-003` (beneficiary
  counts) and `PLN-022` reach `ambiguous_templates` or `broad_question` instead
  of retrieving their `UNANSWERABLE_CATALOG` entry — 3/3 replays, stable. The
  workbook's documented reason exists and is not being shown. Now visible
  because of the T3 upgrade; under the old `no_match` encoding all three graded
  as clean hits.
* **Two follow-up fragments** (`#1003`, `#1016`) clarify rather than rerouting.
  Both are ambiguous-template clarifications, so the context *is* being kept —
  this is a retrieval-confidence question, not a lost-context one.

### 5.3 The echo defect the run found — fixed

Not hypothesised, measured. G1524 in replays 2 and 3 bound
`block_name = Laxmipur`, returned exactly one row, and echoed *"What is the
total actual expenditure incurred by **each GP** in 2024-2025?"* — no Laxmipur
anywhere. EXP-001's SQL filters on `$block_name`, but its question text names
only `{gp_name}` and `{date_range}`, so the bound value had nowhere to render.
Right answer, wrong question printed above it: the operator's original report in
different clothes.

Fixed in `5621bc7` — `resolved_question` now appends the scope the way
`suggestions._chip_for` already did: *"…in 2024-2025 (Laxmipur block)?"*. 332 of
the 346 templates need that append when fully bound, so this was not a corner
case.

### 5.4 Gold-set changes made in this package

| row(s) | change | why |
|---|---|---|
| G1008 | `clarify` → `answer`, `+date_range: 2024-2025` | D18.P5 fixed the Odia numerals. Hits 3/3 live. |
| 19 unanswerable rows | `gold: "no_match"` → `gold: <unanswerable id>` | T3 |
| G1523/G1524, G1043/G1044 | 4 rows added (2 frame-setters + 2 fragments) | T2e |
| — | fragments excluded from the RECALL set by `session: "prev"`, not `case_type` | **authoring error found by the run**: G1524 is both an ambiguity row and a fragment, and scored rank 107 against a template it has no subject for |
| — | `lang` column added to the recall CSV | made F2 visible |

Set is now **209 rows**; the recall CSV is **171**. All coverage thresholds still
clear.

---

## 6. SME package status

Which WP-4a §4 items now have eval evidence attached:

| item | status after WP-4 |
|---|---|
| **§4.3 — 34 Odia/transliterated phrasing rows** | **Now the top SME priority, with a number.** Transliterated rows retrieve at 100%; Odia-script rows at 52.9%. Until a native reader ratifies the 19 script rows we cannot separate "the retriever cannot read Odia" from "these are not sentences an officer would write". Cheapest item on the list to unblock and the one holding the largest measured loss. |
| **§4.2 B1–B3, B7–B8** (clarify-or-default) | No new evidence — these rows were dominated by F1. Re-measure after F1. |
| **§4.2 B4–B6** (tier collisions) | Partial evidence: the machinery now exists and works on the drill-hop path (G1044 3/3), but the live classifier path bypasses it (§5.2). The ruling still stands; the implementation needs the second path. |
| **§4.2 B9** (Odia numerals) | **CLOSED** — fixed under D18.P5, G1008 hits 3/3. |
| **§4.2 B10–B11** (judgement thresholds) | Unchanged and now pinned in tests (§2.2). |
| **§4.1 M1–M7** (metric definitions) | **No evidence yet, and none obtainable while F1 stands** — these need a stable accuracy number to argue over. |
| **§0 P4** (duplicate workbook rows) | **Evidence delivered, and it says "don't bother"**: measured crowding impact is mean 0.02 siblings in top-30 (§3.2). Collapsing them will not move the eval number. Operator call, now an informed one. |
| **§0 P6** (SBM under-weighting) | Unchanged — accepted as reasoned. |

---

## 7. What WP-4c does next

1. **Re-run the full eval** — three replays, same harnesses, same gold set —
   and only then compare against 96–97%. The numbers in §3.3 were measured
   before F1 and 5.1a were fixed; they are a measurement of the extractor, not
   of the router. Nothing else is worth doing first.
2. **Read `_log_fiscal_year_disagreement`'s output from that run.** If the
   deterministic reader never disagrees with a successful extraction, promote it
   from a fallback to a prefill (the `amount_from_text` pattern) and drop the
   slot from the extractor's job entirely.
3. **Get the 19 Odia-script rows read by a native speaker** before drawing any
   conclusion about F2. Then, if the phrasing is ratified, F2 is a retrieval
   change (an Odia paraphrase set, or a multilingual embedding model) and needs
   its own before/after — `rerank_eval --compare` exists for exactly that.
4. **Only after 1–3: thresholds.** They have not moved since `7184d5e` and must
   not move against a number that F1 is setting.
5. Instrument `usage` in the harnesses so the next report can state token spend
   rather than decline to.
6. Rulings wanted on the four §5.2 items.

---

## 8. Compliance with the brief

| constraint | status |
|---|---|
| Repo-only | Yes |
| Drive `.duckdb` read-only | Yes — `open_analytical_db` throughout |
| `.env` untouched and unprinted | Yes — key *names* listed once, no values |
| §3a cache deletion at T0 | Yes — `__pycache__` + `.pytest_cache` deleted before the baseline run |
| §3a clean-tree check at T0 | **Partial, and reported** — the tree held the concurrent Discover workstream's uncommitted work. Per D14 I touched none of it and staged only Ask-side paths (§1.1) |
| LLM spend only in T5's runs | Yes. Everything else runs on caches or no network. The F1 diagnostics (21 calls) were part of triaging a T5 run and are itemised in §4 |
| Call estimate printed before each paid run | Yes — `eval_spend.py` refuses to run without it |
| Edit the generator, never the generated files | Yes — `template_catalog.py` regenerated only |
| **No threshold change** | **Yes — `config.py` unchanged since `7184d5e`** |
| Every reported failure replay-confirmed | Yes — `triage_replays.py`, ≥ 2 of 3 |
| Commit before and after the run | Yes for Ask-side paths (`1f9f726`, `55344ff`, `5621bc7`); the Discover half of the tree was not mine to commit |
