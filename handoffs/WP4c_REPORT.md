# WP-4c — F1's remainders closed, and the eval re-run: REPORT

> ## Where everything is
>
> ```
> Chatbot/eval_full_results_wp4c_run{1,2,3}.jsonl   the three replays, raw
> Chatbot/eval_full_results_wp4c_run{N}.usage.json  token spend + extraction outcomes, per replay
> Chatbot/eval_full_results_wp4c_run{N}.router.log  the disagreement / re-ordering / refusal log
> Chatbot/eval_full_graded_wp4c_run{1,2,3}.json     the same, graded
> Chatbot/consistency_results_wp4c.jsonl            run x question x query_id
> Chatbot/query_router/llm_usage.py                 the usage meter (new)
> Chatbot/tests/test_extraction_sentinel.py         T1a — the swallow, closed
> Chatbot/tests/test_paired_year_direction.py       T3b — the direction pins, executed
> Chatbot/tests/test_refusal_precedence.py          T2c — the refusal, reachable
> handoffs/WP4c_REPORT.md                           this file
> ```
>
> WP-4's own artefacts are untouched: `--tag wp4c` keeps this package's replays
> out of `consistency_results.jsonl`, so the before/after has two intact halves.
>
> Commits: `57049be` (T1–T3) · `90a2add` (T2c) · `0637e04` (T4 prep) ·
> `012b3cf` (T3b hardening) · `f7741fe` · `501be0b` · `8d69d1c` (the run, and this
> report). The replay artefacts themselves are **not tracked** —
> `.gitignore` excludes `Chatbot/eval_full_results*.jsonl` and
> `eval_full_graded*.json`, as it did for WP-4's, so they live on disk beside the
> repo and the numbers in §3 are the record.
> Re-run anything:
> ```
> python eval/gold/build_eval_questions.py --check      # gold set + catalogue + pins
> python eval/gold/check_harness_format.py              # harness-format gate
> cd Chatbot && python -m pytest tests -q                # 533 passed / 16 skipped
> cd Chatbot && python tools/build_catalog.py --check    # catalogue vs workbook
> cd Chatbot && python validate_catalog.py               # 346 executed
> cd Chatbot && python triage_replays.py eval_full_graded_wp4c_run{1,2,3}.json
> ```

---

## 0. For the PM — what the re-run says, and the four things it found

**The re-run lands at the ceiling.** WP-4 estimated that clearing F1 would put
end-to-end accuracy at 86–88% and that the gap to 96–97% would measure the
remaining non-F1 defect. Measured: **85.8% / 87.2% / 87.2%**. F1 accounted for essentially the
whole gap, and what is left is small, named and mostly one thing.

| # | finding | evidence | status |
|---|---|---|---|
| **A** | **The §5.1a pair inversion was LIVE, not latent.** WP-4 reported it as a defect the fallback would have walked into. Its own replays were serving it: on every paired-year row in all three runs the extractor delivered `date_range=2023-2024, date_range_2=2024-2025`, so PLN-039 answered *"which themes showed the greatest **increase**"* with `change_in_activities = +663` for a theme that **fell by 663**. Every one graded `hit`. | Read off `eval_full_results_run{1,2,3}.jsonl`, then reproduced by re-grading them against the new direction pins: `wrong_direction` 3 / 3 / 2. | **FIXED** (`_order_paired_fiscal_years`) and now eval-visible at three layers. §2.4 |
| **B** | **The documented refusals were never RETRIEVED.** WP-4 §5.2 read the symptom as the reranker losing to `ambiguous_templates`. The reranker was never handed the candidate: BEN-001 sits at **rank 51 of 376** against the gold question that is almost word-for-word its own, outside the 30-candidate window. Cause: a template carries 6.1 index vectors, the 13 dropped beneficiary rows carried **one**, and that one is three-fifths workbook filler ("a given Scheme in a given GP Name during a given Plan Year"). | Measured ranks before/after, §2.3. | **FIXED in the generator for BEN-001** — rank 51 → 4, and 0/3 → **3/3 hit** across the replays. **BEN-003, BEN-010 and PLN-022 did not move**: code-mixed, Odia script and Odia-transliterated respectively, so all three are **F2**, SME-gated under D28.2. §2.3 |
| **C** | **A relative period in a follow-up fragment silently answers the wrong year.** *"what about last year?"* over a 2024-2025 answer binds `date_range = 2024-2025` and echoes it as the year asked for. Right template, right GP, wrong year, stated confidently. WP-4 §5.2 filed this as "a retrieval-confidence question"; it is not. *"and for 2023-24?"* — an explicit year — works. | New `wrong_entities` bucket; fires on exactly 1 row in 211, and that row graded `hit` before. §4.4 | **ROOT-CAUSED, NOT FIXED — needs a ruling**, and the ruling has real content: a relative period in a follow-up is ambiguous between conversation-relative and data-relative, and the existing reader gives the data-relative answer, which is the wrong one here. §7.2 |
| **D** | **The disagreement log D30.4 turns on could not have worked.** It compared the extractor's raw surface form against a resolved value and mirrored the pair split backwards, so `'2023-24'` vs `'2023-2024'` logged as a disagreement — every officer writing a year the normal way. Nothing was collecting the log either: the three router decisions T4 asks about are `logging.info` and no harness configured logging. | Found by running two questions before the paid sweep. `0637e04`. | **FIXED**, and the analysis it enables is in §4.3 — with a clean answer for D30.4. |

**Nothing was tuned.** `query_router/config.py` has not been touched since the
pre-adaptation baseline `7184d5e` — `git diff 7184d5e -- Chatbot/query_router/config.py`
is empty. Zero threshold changes, as the brief requires. T6 is "not warranted",
on evidence (§7.1).

### Operator rulings on this report (received)

1. **Finding C — DEFERRED**, revisit later. §7.2 keeps the diagnosis and the design
   question for whenever it is picked up; no change made.
2. **D30.4 — PROMOTE the `$date_range` reader to a prefill.** Ratified; first task of
   the next package, with the extractor kept as a fallback for the slot. Confirmed
   alongside: **there is no default fiscal year** and the prefill does not introduce
   one — §4.3 has the inspection and a part-year caution.
3. **PLN-022 — treat as F2** (option (a)). Settled on a measurement: the same
   question in English retrieves the refusal at rank 0 and serves it, twice over by
   two mechanisms, so the refusal logic is sound and only the register fails. The
   catalogue-level alternative would have covered two templates; those go on the
   statewide checklist instead. §7.3.

### Still open

* **F2 is now blocking two things**, not one: the 8 Odia-script recall misses *and*
  all three remaining unreachable refusals (§2.3). Same cause, same SME dependency,
  and it is the largest single item left.
* **T5 was skipped**, correctly: the brief makes it conditional on the operator
  confirming SME ratification of the 19 Odia-script rows, and that has not
  happened. §6.

---

## 1. Gate

| # | gate item | status |
|---|---|---|
| 1 | The swallow is gone (sentinel proven by test); fallback gotcha coverage complete; **no retry added** | **PASS** — §2.1. `ExtractionUnavailable`, 17 tests; both documented gotchas pinned plus the two that were missing; no retry |
| 2 | Benchmarks met — or every remaining gap root-caused with replay-confirmed evidence and an operator decision attached | **PARTIAL, as designed** — **85.8% / 87.2% / 87.2%** against 96–97%, at the top of WP-4's own 86–88% ceiling. Every confirmed failure is root-caused in §5, and the two that need a decision carry one (§7.2, §6) |
| 3 | Consistency measured against ~3% and reported as the routing-stability number for the first time | **PASS** — §3.3 |
| 4 | Direction-sensitive gold rows in place; `--check` green; suite green from the 461/16 baseline | **PASS** — 5 of 5 paired templates pinned at three layers; `--check` green; **533 passed / 16 skipped** from 461/16 |
| 5 | Zero threshold changes without the T6 evidence trail; catalogue touched only via the generator | **PASS** — `config.py` unchanged since `7184d5e`; `unanswerable_catalog.py` regenerated via `tools/build_catalog.py`, the only generated file that changed |

---

## 2. What was built

### 2.1 T1 — the swallow, closed (D30.2)

`extract_entities` ended `except Exception: return {s: None for s in slots}`, so a
timeout, a 429, an auth failure, a truncated reasoning response and malformed JSON
were all returned as the dict the model produces when it reads the question and
finds nothing in it.

It now returns an **`ExtractionUnavailable`** — still a dict of nulls, so every
caller and the deterministic `$date_range` fallback behave exactly as before
(D30.2 asks for precisely that: the fallback *should* run on an API failure), but
carrying a cause from a closed vocabulary: `timeout`, `connection`, `rate_limit`,
`auth`, `bad_request`, `server_error`, `truncated`, `empty_response`, `bad_json`,
`unexpected_error`. Logged with the cause, metered separately from an honest empty
answer, and available to any caller as `extraction_failed(raw)`.

Two details worth naming:

* **The call and the parse are separate `try` blocks.** Wrapping both in one is
  how a JSON error came to look like a timeout came to look like an empty
  question.
* **`finish_reason == "length"` with no content is `truncated`, not
  `empty_response`.** That is a reasoning model spending its whole completion
  budget thinking — the D17 failure mode — and it must not read as "the user
  named nothing".

**No retry was added**, per D30.1.

**T1c — the gotchas.** Both documented gotchas already had coverage; two nearby
holes did not, and are now pinned:

| gotcha | was | now |
|---|---|---|
| `EntityNotFound` swallowed, so the officer's sentence is never quoted back | covered end-to-end (the prompt must not contain the question) | also pinned at the function, and that the reason is `missing_parameter` and never `unknown_entity` |
| fallback ahead of the `optional` check (ALR-001/ALR-008) | covered | unchanged |
| fallback ahead of **declared defaults** | **not covered** | pinned both ways: the question beats a declared default, and the default still applies when the question names no year |
| fallback runs on the **sentinel** | did not exist | pinned |

### 2.2 T2a/T2b — the tier collision, on both paths (D28.3, D28.4)

**A correction to WP-4's diagnosis, from its own recorded replays.** WP-4 §5.2
said G1524 bypassed the tier check because "the LLM follow-up classifier reads the
fragment as an executable `frame_edit`, `serve_frame_edit` succeeds, and
`_fragment_reading` is never reached". `serve_frame_edit` cannot have succeeded: a
context frame's `bound_params` holds only the slots that *validated*, so a
whole-of-state EXP-001 frame binds `date_range` alone, and the function raised
`missing 'district_name' in the current context` for every absent optional slot.
The replay record shows what actually happened — EXP-001 served with
`date_range` + `block_name` and nothing else, which is the **contextual re-route**
(item 1), reached because `classify_followup` returned `unexecutable_edit`; and on
that branch `_fragment_reading` is skipped by construction:

```python
unexecutable = (decision.edit if decision.kind == "unexecutable_edit" else None)
if unexecutable is None and decision.kind in ("new_question", "frame_edit"):
    unexecutable, tier_clarify, name_tier = _fragment_reading(...)
```

So there were **two** ways past the check, not one. Both are closed, and the
underlying reason the deterministic paths were unreachable is closed with them:

* **An optional slot the frame does not bind now stays unbound** in
  `serve_frame_edit` and `serve_drill_hop`. That is what D2 means by optional —
  the filter is off, which is the state the frame was already in. The old rule
  came from AP, where every slot was required so a frame bound all of them, and
  under D2 it made every state-wide frame uneditable and sent its follow-ups to an
  LLM re-route instead of the deterministic path written for them. A **required**
  slot missing still refuses.
* **The tier check is applied before either serving branch**, from one function,
  so the deterministic and classifier paths ask the identical question (pinned by
  test).
* **The bound tier competes as a replacement reading** (D28.4). It used to be
  skipped, which is what made a GP-scoped frame read a GP-and-block name as the
  block — and the hop then bound the old GP together with the new block, returned
  zero rows and abandoned a follow-up it could have answered. One viable reading
  auto-serves; two ask, tier-qualified; **a tier the user names out loud settles
  it** ("in Laxmipur block?" is not an ambiguous message, and "panchayat samiti"
  is a block, not a gram panchayat).
* **A reading at one tier drops bound geography narrower than it**, in the chip
  *and* on the serving path — otherwise the chip promises "for Laxmipur block" and
  the answer computes Andhrua-inside-Laxmipur. Wider scopes are kept: a district
  on screen still contains the block just named.

The `main.py` precedence comment now states the new contract.

### 2.3 T2c — the refusal was never retrieved (D28.5)

**The diagnosis is not the one in the brief, and the numbers say so.** WP-4 named
three rows declining generically; there are **four** (BEN-010 as well), and the
mechanism is upstream of the reranker.

Measured retrieval rank of each entry against its own gold question, over a
30-candidate window on a 376-entry index:

| row | lang | rank before | rank after | in window? |
|---|---|--:|--:|---|
| BEN-001 | en | **51** of 376 | **4** | yes — and the reranker picks it, 3/3 |
| BEN-003 | code-mixed | 64 | 64 | **no** |
| PLN-022 | Odia transliterated | 46 | 46 | **no** |

BEN-010's own gold row (#1974) is **Odia script**, and it stays out of the window
like every other Odia-script row. A Hinglish rendering of the same question, which I
wrote as a probe rather than taking from the gold set, retrieves it at rank 0 — worth
recording because it isolates the register from the entry, but it is not a
measurement of the gold set and BEN-010 remains 0/3.

The reranker never saw BEN-001, BEN-003 or PLN-022 at all, so no instruction to it
could have helped. The cause is an asymmetry of index surface, not of wording
quality:

```
templates          2,112 vectors over 346 entries = 6.1 each
unanswerables         47 vectors over  30 entries = 1.6 each
the 13 Dropped rows    1 vector each — and that one is workbook prose:
    "How many beneficiaries received benefits under a given Scheme
     in a given GP Name during a given Plan Year?"
```

A row with no SQL has no `{placeholders}`, so the workbook writes its parameters
out longhand, and the Dropped sheet has no Parameterized or Example column for the
generator to draw on. **So the generator makes the missing shape itself**: the
question with its geography and period stripped, which is the same thing
`SCOPE_SUFFIX` does for templates from the other side — the officer names the place
and the year, so the catalogue's copy of them only dilutes the measure words that
do the matching. 25 of 30 entries gain a line; every entry now has at least two
vectors, pinned by test. A paraphrase can only ever *raise* the entry it belongs
to, because an entry scores as the MAX over its vectors.

**BEN-003 and PLN-022 are F2**, root-caused and not closed: their gold questions
are code-mixed and Odia-transliterated, and the index has no surface in those
registers. D28.2 gates F2 work on SME ratification. **PLN-022 meanwhile is still
answered with PLN-020**, whose own caveat reads *"pending_approvals is 0 everywhere
because approval_date is always populated"* — a table of zeros served as the answer
to "which blocks are consistently delayed". That one wants a ruling (§7.3).

Two deterministic rules were added alongside, both proven by unit test and neither
fired in the replays (they are the backstop, not the fix):

* **A rank-0 refusal takes precedence** over a no-match verdict outright, and over
  a rerank pick only outside `CLARIFY_SCORE_MARGIN` — inside it, retrieval cannot
  separate the two and overruling the semantic layer with the surface layer would
  be the embedding-order bias the reranker exists to correct.
* **On a no-match verdict, the reranker's own near-miss list counts.** Naming a
  documented refusal among the *closest* candidates while also returning
  `no_match` is a contradiction, and it resolves in favour of the refusal.

Every clarification that carries a refusal now labels it (*"Why I can't answer:
…"*) and sends the entry's own question, which retrieves at rank 0 on the way back
in — so a tap serves the documented reason with no LLM in the loop.

**Measured outcome across the three replays: 16 of the 19 refusal gold rows serve
their documented reason 3/3, against 15 in WP-4.** BEN-001 moved from 0/3 to 3/3.
The near-miss rule fired twice in replay 2 (`the reranker returned no_match but
named BEN-001 as a near miss`), so it is doing work rather than sitting idle; the
rank-0 rule never fired, which is expected — once an entry is retrievable the
reranker generally picks it. The remaining three are the register failures above.

### 2.4 T3 — instrumentation, and the direction pins

**T3a — `query_router/llm_usage.py`.** All six LLM call sites (extraction, rerank,
classify, followup, and both embedding paths) hand their response to a passive
meter. It never raises and is always on: instrumentation that can break a call is
worse than none, and a meter you have to remember to enable is off on the run you
needed it for. All three harnesses reset it per run and report prompt / cached /
completion / **reasoning** tokens by site; `run_full_eval` writes a
`.usage.json` sidecar per replay.

It also carries the **extraction ledger** — per call, which slots were asked for,
which came back null, the cause if the call was unavailable, and the
reasoning-token count. That is what makes T1b measurable (§4.2) and it reproduces
WP-4's F1 signature at scale (§4.1).

**T3b — direction-sensitive gold rows (D30.3).** All five paired-year templates are
covered; PLN-040 and TRD-001 had no gold row at all. Each pin carries the
parameters, the year→slot mapping, the **first row** the template returns, and the
**inverted row** it returns with the two years exchanged — both executed against
the sample database, not transcribed.

Three layers now carry the pin, and each catches something the others cannot:

| layer | what it catches | where |
|---|---|---|
| the SQL convention | a future template that reverses `$date_range_2` = year1 | `test_fiscal_year_fallback` |
| the values | the SQL, the views or the data changing what year1 and year2 mean | `test_paired_year_direction` — executed, no LLM, always on |
| the route | extraction, validation or the fallback handing the slots over inverted | `grade_full_eval`'s `wrong_direction` bucket, every replay |

The third layer is what found finding A. Detection is by **positive
identification**: a returned row that matches `inverted_row` says the pair arrived
swapped. That matters because the obvious implementation — compare to the pinned
row value by value — reports a break whenever anything else differed, and the
likeliest "anything else" is a geography slot that did not bind; while the
scale-free sign tests alone miss PLN-039 entirely, whose ORDER BY is on the change
column, so under an inverted pair its top row is *still* a positive change for
"greatest increase", just a different theme.

**And the fix.** The inversion is a rule collision, not a wobble, which is why it
was stable in all three WP-4 replays: the extraction prompt defines the pair by
**mention order** ("'2024-25 vs 2023-24' → fiscal_year='2024-25'") while the
catalogue defines it **chronologically**, and the question text happens to name the
earlier year first. `_order_paired_fiscal_years` imposes the catalogue's order
after validation, because the ordering is a property of the SQL and no phrasing of
a prompt can be trusted to reproduce a property of the SQL.

---

## 3. The runs (T4)

### 3.1 T4a — recall

Benchmark: recall@30 ~ 97% (AP parity). **Measured: 95.4% (165/173)** — WP-4 was
95.3% (163/171); the denominator moved because T3b added two gold rows.

| K | WP-4 | WP-4c |
|---|--:|--:|
| @5 | 86.5% | 87.3% |
| @10 | 91.2% | 91.3% |
| @20 | 94.2% | 94.2% |
| **@30** | **95.3%** | **95.4%** |

By language, and this is the whole story:

| language | recall@30 | n |
|---|--:|--:|
| English | **100.0%** | 98 |
| code-mixed | **100.0%** | 45 |
| Odia transliterated | **100.0%** | 13 |
| **Odia script** | **52.9%** | 17 |

**Unchanged, and expected to be.** Every one of the 8 misses is an Odia-script row
(ranks 34, 43, 57, 65, 127, 129, 219, 331). Nothing in WP-4c touches F2 and nothing
moved it. The crowding figures are unchanged too (paraphrase crowding mean 21.9 /
max 94; duplicate-row crowding mean 0.02 / max 2), so the 25 paraphrases added in
2.3 cost the index nothing measurable.

### 3.2 T4b/T4c — the full eval, three replays

Benchmark ~ 96-97% behaving correctly; WP-4's post-F1 ceiling estimate 86-88%.

| | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| hit | 178 | 180 | 179 |
| partial | 1 | 1 | 1 |
| clarify_gold_offered | 2 | 3 | 4 |
| **behaving correctly** | **85.8%** | **87.2%** | **87.2%** |
| clarify | 21 | 17 | 18 |
| wrong_template | 6 | 6 | 6 |
| wrong_entities | 1 | 2 | 1 |
| declined_generically | 2 | 2 | 2 |
| **wrong_direction** | **0** | **0** | **0** |
| wrong_refusal / refusal_with_rows / error | 0 | 0 | 0 |

Query time per replay, summed from the records: **706s / 1,253s / 979s** (mean
3.3s / 5.9s / 4.6s per question); replay 3's reported wall clock was 682s. As in
WP-4, the spread between identical replays is API latency, not a code change.

**Against WP-4, graded by the same grader.** WP-4's report quotes 59.8% / 64.6% /
62.2%. Re-grading its own three replay files under WP-4c's grader gives **58.4% /
63.6% / 59.8%** — lower, because the rows now bucketed `wrong_direction` (3/3/2)
and `wrong_entities` (0/0/3) were counted as hits. That is the honest before-number,
and it is the one this comparison uses:

| | WP-4 | WP-4c | benchmark |
|---|--:|--:|--:|
| behaving correctly | 58.4 / 63.6 / 59.8% | **85.8 / 87.2 / 87.2%** | 96-97% (ceiling est. 86-88%) |
| consistency (verdict flips) | 43.1% | **4.7%** | ~3% |
| recall@30 | 95.3% | 95.4% | ~97% |

**The re-run lands at the top of the ceiling WP-4 predicted.** That is the finding:
F1 accounted for essentially the whole gap to 86-88%, and the distance from there
to 96-97% is accounted for row by row in section 5 — 56% of it one thing (F2).

One correction to the headline, in the honest direction: **one of the 27 confirmed
failures is the RATIFIED behaviour being counted as a failure.** #1524 ("what about
Laxmipur?") now raises the `tier_collision` clarification in 2 of 3 replays, which
is exactly what D18.P3 ruled it should do and what WP-4 measured at 0/3. Its gold
row predates the machinery and still expects EXP-001 answered. Left alone rather
than quietly re-scored — the gold row and the grader's treatment of a ratified
clarification are a WP-5 item (section 7.5).

### 3.3 Consistency — meaningful for the first time

Benchmark ~3% (PROJECT_PLAN section 6). **Measured: 4.7% by verdict (10 of 211) and
4.3% by `query_id` (9 of 211).** WP-4 measured 43.1% and said plainly that the
number was the extractor's variance rather than the router's, so "the ~3%
consistency benchmark is untested by this run".

It is tested now. 4.7% against ~3% is close enough that the remaining flips are
worth naming rather than tuning: 10 questions, three of them the `clarify` / `hit`
boundary on rows sitting near the retrieval cutoff (#1026, #1524, #1852). No
threshold may move against a 1.7-point gap on a sample of 211 (section 7.1).

### 3.4 Spend — instrumented, and reportable for the first time

WP-4 declined to state token totals because nothing recorded `usage`. Per replay,
by call site:

| site | calls/replay | tokens/replay | of which reasoning |
|---|--:|--:|--:|
| rerank | 188-189 | ~1,116,000 | 7,869-9,206 |
| extraction | 186-190 | ~366,000 | 15,493-16,221 |
| followup classification | 12-13 | ~19,000 | 1,582-1,888 |
| query embeddings | 200-202 | ~6,050 | — |
| **per replay** | **587-593** | **1,501,854-1,515,380** | **25,250-26,700** |

**Three replays: 1,769 calls, 4,524,263 tokens, of which 78,595 reasoning.** The
reranker is 74% of the token bill and the extractor 24%, which is worth knowing
before anyone prices a statewide run. Prompt-cache hits varied by a factor of three
between identical replays (836k / 345k / 1,003k cached prompt tokens), so a
per-question cost derived from one replay would be wrong either way.

The package as a whole:

| item | calls |
|---|--:|
| `recall_eval` (catalogue re-embed after the 25 new paraphrases, plus the query batch) | 10 |
| pre-sweep smoke and log checks (3 + 5 + 2 questions) | 39 |
| T2c retrieval diagnostics (2.3) — the measurements that found finding B | ~24 |
| aborted first sweep (13 questions; stopped to add the log capture) | 39 |
| 3 x full-eval replay | 1,769 |
| splice replays after the Drive artefact (3.5) | 27 |
| **total** | **~1,908** |

Every paid run printed its estimate first. One estimate was **wrong** and is fixed:
`recall_eval` printed "~1 call" and made 10, because it tested whether the cache
file existed rather than whether it would be used (`0637e04`).

### 3.5 An artefact worth reporting: the Drive sync layer damaged every results file

`run_full_eval` streams one JSON line per question and flushes each one. This repo
lives in a Google Drive folder (D6 already warns about it for DuckDB temp files),
and the sync layer left all three streamed files damaged:

| replay | lines | recoverable | lost |
|---|--:|--:|---|
| 1 | 213 | 211 | none — one record written twice, plus a redundant orphan fragment |
| 2 | 209 | 207 | **4 questions** (#1808, #1852, #1853, #1860) |
| 3 | 211 | 210 | **1 question** — and the identity of the missing record CHANGED between reads |

Three consequences, all handled and all disclosed:

1. **`grade_full_eval` refuses to grade a subset silently.** Fragments are rejoined,
   duplicates deduplicated, orphans dropped, every repair printed — and the
   recovered question numbers are checked against the spec file, raising if one is
   genuinely absent. `--allow-subset` is the explicit, noisy escape. Skipping the
   bad line would have reported 207 of 211 questions as though the whole set ran.
2. **`run_full_eval` now rewrites the whole file from memory at the end.** The
   streamed append is what survives a crash; `records` is what actually ran. This
   landed after the sweep, so it protects the next run rather than this one.
3. **The lost questions were replayed and spliced**, each marked `"spliced"` in its
   record: run 2 gained #1808, #1852, #1853, #1860; run 3 gained #1703, #1801,
   #1809, #1811. They come from `run_full_eval.run()` itself — same code, same
   client, same database — and a `session: prev` fragment was replayed with its
   prior immediately before it. One (#1811) had to be redone: the first attempt put
   another question between the fragment and its prior, so it attached to the wrong
   frame. **8 of 633 question-runs (1.3%) come from a splice.** Six of the eight grade `hit`
   in every replay. The two that do not are worth stating precisely rather than
   waved past: **#1809** fails (`clarify`) in all three replays including the two
   that were never spliced, so the splice changes nothing about it; **#1852** flips
   `clarify / wrong_template / clarify`, and the spliced replay is the
   `wrong_template` one — i.e. the spliced record differs from the other two, which
   is within the 4.7% flip rate but is a difference the splice may have contributed
   to. #1852 is an Odia-script row and is counted under F2 either way.

---

## 4. Extraction, in numbers for the first time

### 4.1 The F1 signature, reproduced at scale

WP-4 identified F1 from a hand-run diagnostic: 12 identical calls, 3 nulls at
40/49/52 reasoning tokens against 9 successes at 80-201. That is now measured on
every call of every replay:

| | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| extraction calls | 186 | 188 | 190 |
| all-None (the model answered) | 23 (12.4%) | 21 (11.2%) | 24 (12.6%) |
| **UNAVAILABLE (API/parse failure)** | **0** | **0** | **0** |
| reasoning tokens, median, when all-None | **46** | **43** | **52** |
| reasoning tokens, median, when read | **80** | **79** | **76** |

The separation WP-4 found with n=3 holds with n=68: an extraction that returns
nothing spends about half the reasoning of one that reads the question, in all three
replays. WP-4 was careful to call this a correlation rather than a cause, and that
caution still stands — but it is now a correlation over 564 calls.

**Zero UNAVAILABLE calls across all three replays.** No timeouts, no 429s, no
truncations, no malformed JSON. Which is worth stating plainly: the sentinel added in
T1a found nothing to report, so every all-None above is the model answering "this
question names nothing", not a call that failed. Before T1a those were the same
number, and there was no way to tell which.

### 4.2 T1b — the categorical all-None rate (the D30.1 reopener)

D30.1 shelved the retry on condition that this be measured. Two measurements, and
the second is the one to act on.

**Raw null rate by slot family**, pooled over the three replays — every slot the
extractor was asked for, and how often it came back empty:

| family | null | asked | rate |
|---|--:|--:|--:|
| date | 212 | 541 | 39.2% |
| place | 1,277 | 1,577 | 81.0% |
| categorical | 81 | 132 | 61.4% |
| numeric | 143 | 235 | 60.9% |

**These are not defect rates and must not be read as any.** A null is usually
correct: most questions name no district, no theme and no threshold, and the optional
filter is meant to stay off. The figure that means something compares what was bound
against what the gold set says should have been:

| family | expected but unbound | rate |
|---|--:|--:|
| **categorical** | **6 / 42** | **14.3%** |
| date | 62 / 528 | 11.7% |
| place | 21 / 279 | 7.5% |
| numeric | 1 / 27 | 3.7% |

**Answer to D30.1: the categorical rate is materially nonzero at 14.3% — but the
measurement has almost no power, and that is the finding.** Six misses, on three
distinct questions (#1026 `focus_area`, #1604 and #1623 `status`), out of 42
categorical expectations in the whole gold set. 42 is not a sample on which to
authorise a per-call cost change.

So: **do not reopen the retry yet; widen the gold set first.** The set carries 528
date expectations and 42 categorical ones, which is exactly why F1 was visible and
this is not. A dozen more rows naming a theme, a scheme and a status — the three
slots with no deterministic reader behind them — cost nothing and would turn
"14.3%, plus or minus a lot" into a number worth ruling on (section 7.5).

### 4.3 T4a — the disagreement log, and the D30.4 prefill proposal

**Recommendation on D30.4: promote the deterministic `$date_range` reader from a
fallback to a prefill. Yes.**

The log, now that it exists and now that it compares like with like (finding D):

| | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| `$date_range` recovered deterministically | 54 | 53 | 55 |
| **disagreements** | **8** | **10** | **8** |
| of which on a SINGLE-year question | **0** | **0** | **0** |
| paired-year re-orderings applied | 4 | 5 | 4 |

**Every disagreement in all three replays is a paired-year row, and in every one the
deterministic reader is the one that is right.** The signature is identical across
all 26 records:

```
disagreement on date_range  : extractor='2023-24' -> '2023-2024'  date_phrase -> '2024-2025'
disagreement on date_range_2: extractor='2024-25' -> '2024-2025'  date_phrase -> '2023-2024'
```

The extractor orders the pair by **mention** (its prompt says so in as many words)
and the catalogue orders it **chronologically** (its SQL says so). On every question
naming ONE year — around 160 per replay, including relative phrases and Odia
numerals — the two readers agree exactly.

That is stronger evidence than the "zero disagreements" D30.4 asked for: the
disagreements that exist all point the same way, with the reader correct, so
promoting it does not merely change nothing — it removes the class. Three
consequences, all in favour:

* the pair-order correction in `_order_paired_fiscal_years` becomes unnecessary,
  because the reader's split IS the catalogue's convention;
* the slot leaves the extractor's job, removing the only observed class of
  disagreement;
* about 160 fewer slots per replay for a model measured at a 12% all-None rate.

**Operator ruling: PROMOTE.** Confirmed, so it becomes the first task of the next
package: move `_fiscal_year_from_text` from the extractor-empty branch to a prefill
beside `amount_from_text`, delete the then-dead re-ordering, and prove it with a 3x
replay. **The extractor stays as a fallback for the slot** rather than being cut out
entirely — the reader's vocabulary is narrow (it reads "last year" and "this year"
but not "the year before"), so reader-first-then-extractor is strictly safer than
either order alone.

**Confirmed alongside, because the operator asked: there is NO default fiscal year,
and promoting the reader does not introduce one.**

* The only declared default anywhere in the catalogue is `$top_n = 10`;
  `_DEFAULT_ENTITY_VALUES` is `{'top_n': '10'}` and holds nothing else.
* `$date_range` is **required on 324 templates** and optional on exactly two
  (ALR-001, ALR-008 — the D13.3 exception).
* A question naming no year **clarifies**: "For which date range?", measured at
  **5 / 4 / 4 times per replay** out of 211 questions (~2%). That is D9 as ruled:
  required-slot behaviour for v1, revisited from pilot logs if officers turn out to
  mean the current year.
* Two places a year appears unasked, neither of them a default: **elicitation chips**
  pre-fill the most recent loaded year so the chip is tappable (a suggestion, not a
  bind), and **follow-ups inherit the frame's year** from context — which is 7.2's
  territory.
* The prefill changes none of it: the reader returns nothing when the question names
  no year, so those questions still clarify. It only changes questions where a year
  IS stated.

**A caution recorded for whenever a default is reconsidered.** The obvious rule,
"the most recent loaded year", currently points at the THINNEST year in the data:

| FY | activities | expenditure |
|---|--:|--:|
| 2023-2024 | 4,607 | 41,929,919 |
| 2024-2025 | 3,423 | 42,578,450 |
| **2025-2026** | **2,914** | **25,152,606** |

A silent default to a part-year would answer "how much have we spent?" with a little
over half the previous year's figure and nothing saying why. "Most recently
COMPLETE" is the safer rule if a default is ever wanted; not proposed here.

### 4.4 Finding C in detail — a relative period in a fragment answers the wrong year

Stable in all three replays, and graded `hit` until the `wrong_entities` bucket
existed:

```
#1015  "…the GPDP status of Andhrua Gram Panchayat for the financial year 2024-25?"
       -> PLN-012, date_range=2024-2025             correct
#1016  "what about last year?"
       -> PLN-012, date_range=2024-2025 (context)   WRONG — the gold says 2023-2024
       echo: "What is the status of the GPDP for Andhrua in 2024-2025?"
```

Right template, right GP, wrong year, and the echo asserts the wrong year
confidently. WP-4 section 5.2 filed this as "a retrieval-confidence question, not a
lost-context one". It is neither: the context is kept perfectly, and that is the
problem — the year is CARRIED rather than read.

**It is specific to a RELATIVE phrase.** #1624 *"and for 2023-24?"* — an explicit
year in a fragment — binds 2023-2024 correctly in all three replays. So the fragment
path works; what fails is that a fragment naming a period reaches the frame-edit
path, which can swap a bound value but holds no reading of "last year", while under
D9 the fiscal year is an ordinary slot rather than a date window — so editing the
request window, which is what the classifier expresses, moves nothing.

The reader for it already exists: `resolve_fiscal_years` against the loaded years,
which `_fiscal_year_from_text` already calls. Proposed fix in section 7.2.

---

## 5. Triage

`triage_replays.py` applies the >= 2-of-3 rule mechanically. **27 confirmed
failures** (WP-4: 73), and the shape of them is the useful part:

Classes are **priority-ordered** as in WP-4, so each row is counted once: a row that
is both an Odia-script row and an ambiguity row lands in F2, because the retrieval
failure is what actually happened to it.

| class | count | disposition |
|---|--:|---|
| **(i) real defect — Odia script / transliterated retrieval** (F2) | **15** | Filed, unchanged, SME-gated. Also **(iv)**: WP-4a section 4.3 flags this phrasing as unratified. Two of the 15 are documented refusals that cannot be reached (BEN-010, PLN-022), and PLN-022 additionally *answers* with a zero-filled near-miss (7.3). Section 6 |
| **(iv) SME behaviour call** — `case_type: ambiguity` | 6 | WP-4a section 4.2 B1-B8: "does this clarify or default?" is the SME's ruling, not a defect. One of them (#1524) is now the RATIFIED behaviour being scored as a failure — 3.2 |
| **(i) real defect — follow-up fragment** | 4 | #1016 finding C (5.1); #1042 and #1404 the superlative flip (5.2); #1503, where a fragment carrying a measure word re-routes as a new question and the frame's year does not come with it |
| **(i) real defect — refusal not retrieved** (code-mixed) | 1 | BEN-003 — same mechanism as the two F2 refusals, different register (2.3) |
| **(i) real defect — unstable route** | 1 | #1026, the only confirmed failure that is not stable: `clarify / hit / wrong_template` |
| **(ii) gold-set authoring error** | 1 | **Fixed and logged** — G1003, 5.3. Not in the 27; found while re-judging |
| (iii) replay noise (non-hit in a minority) | 5 | Listed by the triage, not acted on |

By language across the 27: **Odia script 13, English 9, code-mixed 3, Odia
transliterated 2**. So **15 of 27 (56%) are F2**, and 6 of the remaining 12 are SME
behaviour calls that were never defects. **The residue that is neither F2 nor an SME
ruling is 6 rows** — four fragments, one code-mixed refusal, one unstable route.

### 5.1 #1016 — see 4.4

The one `wrong_entities` row, stable 3/3, and a silent wrong answer. Root-caused;
fix proposed in 7.2.

### 5.2 A new stable defect: the superlative flip

Two rows, 3/3 each, and the same mechanism:

```
#1027 "Which focus area has the highest number of planned activities in 2024-25?" -> PLN-052
#1042 "aur sabse kam?"   ("and the lowest?")                          -> PLN-052   WRONG
                                                                 gold  PLN-053

#1403 "Which focus area has the highest planned expenditure in 2024-25?"          -> BUD-022
#1404 "and the lowest?"                                               -> BUD-022   WRONG
                                                                 gold  BUD-023
```

The catalogue carries each highest/lowest pair as two separate templates
(PLN-052/PLN-053, BUD-022/BUD-023). Reversing the superlative is therefore not a
slot edit at all — it is a hop to a sibling template — and nothing in the follow-up
machinery expresses that relation: `drill_target` maps geography tiers and nothing
else, so whichever path handles the fragment can only re-serve the frame's own
template. Observed outcome, 3/3 in both cases: the officer asks for the opposite of
what they get, under an echo that reads "highest".

Not fixed — it is a new finding, outside T2's ruled scope, and the fix wants a
decision about how sibling templates are related in the catalogue (a
`inverse_of` field emitted by the generator would do it deterministically).
Recommended for the next package (7.5).

### 5.3 Gold-set changes made in this package

| row(s) | change | why |
|---|---|---|
| G1025, G1904, G1906 | `expected_result.direction_pin` added | T3b / D30.3 |
| **G1045 (PLN-040), G1910 (TRD-001)** | **2 rows added** | T3b: the paired-year set is five templates and only three had a gold row, so the inversion was invisible on the decline side and on TRD-001 entirely |
| all five pins | `inverted_row` added | `012b3cf` — positive identification of an inversion; see 2.4 |
| **G1003** | `acc: [] -> ["PLN-003"]` | **authoring error found by the run.** Its own prior G1002 accepts PLN-003 as an equally legitimate reading of "status" at block scope, so when the prior was served as PLN-003 the fragment was graded `wrong_template` for correctly keeping that subject. A follow-up's acceptable set must be at least as wide as its prior's |

Set is now **211 rows**; the recall CSV is **173**. All coverage thresholds still
clear; `--check` and the harness-format gate are green.

### 5.4 What the `clarify` rows are

19 of the 27 confirmed failures have `clarify` as their modal verdict, and they are
not a residual mystery:

| | count |
|---|--:|
| F2 rows whose gold entry is outside the retrieval window | 11 |
| `ambiguity` rows where clarifying is the behaviour under SME review | 6 |
| #1503, the fragment that loses the frame's year | 1 |
| #1026, the unstable code-mixed row | 1 |

So every clarify in the confirmed list is either F2 or an open SME behaviour call,
bar two named rows. Nothing here argues for a threshold change (7.1): the F2 rows
among them are entries whose gold sits a long way outside the window — the eight
that the recall harness measures are at cosine ranks 34, 43, 57, 65, 127, 129, 219
and 331 — not entries sitting just outside a band.

---

## 6. T5 — F2 A/B: SKIPPED, and why

The brief makes T5 conditional: *"only if the operator confirms SME ratification of
the 19 Odia-script rows"*. That confirmation has not been given, so T5 was not run
and no F2 change was made. Measuring a transliteration or paraphrase-index change
against phrasing nobody has ratified would measure the phrasing, not the fix —
WP-4a §4.3 and D28.2 both say so.

What this package adds to the F2 file, without touching it:

* **Recall is unchanged** at 52.9% (9/17) on Odia script, 100% on English,
  code-mixed and transliterated Odia (§3.1). Nothing here was expected to move it
  and nothing did.
* **F2 now blocks two things.** All three refusals still unreachable — BEN-003
  (code-mixed), BEN-010 (Odia script) and PLN-022 (Odia transliterated) — are out of
  the retrieval window for the same reason the Odia-script recall rows are: the index
  has no surface in the officer's register (§2.3). The one refusal that was English,
  BEN-001, is fixed. So the SME reading unblocks the refusal defect as well as the
  recall one, and every remaining refusal failure is a register failure.
* **The 19 refusal rows have never been in the recall measurement at all** —
  `RECALL_EXCLUDED_CASES` drops `unanswerable`, so `recall@30 = 95.4%` says nothing
  about whether a documented refusal can be retrieved. That is the measurement gap
  that let finding B hide. Recommendation in §7.4.

---

## 7. Decisions wanted, and the threshold call

### 7.1 T6 — thresholds: NOT WARRANTED, on evidence

No threshold was changed. `config.py` is byte-identical to `7184d5e`.

The brief authorises a change only on evidence of **systematic mis-zoning**. There
is none:

* **The zone gate is not where the failures are.** Of 27 confirmed failures, 15 are
  Odia-script/transliterated rows whose gold entry is outside the top-30 *by
  cosine* — lowering `NO_MATCH_LOWER_THRESHOLD` or widening `CLARIFY_SCORE_MARGIN`
  does not put a rank-129 entry into a 30-candidate window. `VECTOR_TOP_K` would
  have to roughly double to reach the median miss (rank 65), which would raise the
  rerank token bill — already 74% of spend (3.4) — by the same factor, to fix rows
  whose phrasing the SME has not ratified. That is tuning against unratified
  input, which WP-4a section 5.2 forbids by name.
* **Consistency is 4.7% against ~3%** (3.3). A 1.7-point gap on 211 questions is
  about 3.6 questions. Tuning a threshold against that is tuning against noise.
* **The one number that did move is not a threshold's business.** Accuracy went
  from 58-64% to 86-87% with `config.py` untouched.

If a threshold change is ever argued for, the evidence to bring is a
distribution of gold-entry retrieval ranks **for ratified phrasing only**. That
does not exist until the SME reads the Odia rows.

### 7.2 DEFERRED BY THE OPERATOR — a relative period in a follow-up fragment (finding C)

**Operator ruling: revisit later.** No change made; the defect stands as described and
this section is the record of it, not an open ask. Everything below is the material a
later ruling will need.

**The defect:** *"what about last year?"* keeps the frame's year and states it as
the answer's year. 3/3 stable, one gold row (#1016), and it is the
confidently-wrong class — the officer sees a plausible table under a sentence
naming the wrong year.

**Why it is not already fixed:** it changes documented follow-up behaviour for every
time fragment, no ruling covers it (D28.3-5 cover the tier collision, the bound-tier
replacement and the three declines), and D28.6 explicitly reserved these two rows
for a decision after re-measurement. WP-4 declined the analogous bound-tier change
for the same reason and the PM ratified that judgement in D28.4; consistency says
propose rather than implement.

**What the ruling actually has to settle — and a correction to my own first
proposal.** I first wrote that the fix is to resolve the phrase with
`resolve_fiscal_years(message, validator.fiscal_years())`. **That would not fix it**,
and checking is what showed why:

```
loaded years: 2020-2021 … 2025-2026
resolve_fiscal_years("what about last year?", known)  ->  '2024-2025'
```

The reader resolves a relative phrase against **the data** — "last year" means the
year before the most recent loaded year. The frame in #1016 is already on 2024-2025,
so a data-relative reading returns the year it is already showing, which is exactly
the wrong value the bug produces today. The gold row expects 2023-2024, i.e. **the
year before the FRAME's**.

So the decision is not "apply the existing reader"; it is:

**In a follow-up, is a relative period relative to the CONVERSATION or to the DATA?**

D9 and D11.1 settle it for a standalone question — data-relative, and
`_elicitation_defaults` uses the most recent loaded year. Nothing settles it for a
follow-up, and the two readings differ by a year whenever the frame is not on the
latest year.

* **Conversation-relative** (what #1016's gold expects, and what a person means):
  "last year" = one step back from the frame's `$date_range`. Deterministic, needs
  the frame's year as the anchor rather than the registry's last entry.
* **Data-relative** (consistent with the standalone rule): "last year" always means
  the same year regardless of what is on screen — defensible, but it makes the
  follow-up a no-op whenever the frame is already there, which is the current
  behaviour and reads as the system ignoring the question.

A third option, and the conservative one: **clarify instead of resolving.** D9
already makes an unstated year ask rather than guess, so "which year did you mean?"
with year chips is in keeping and cannot be wrong. It costs a round trip on a common
follow-up.

Whichever is chosen, the reader's vocabulary is narrow and worth knowing: "last
year" and "this year" resolve, **"the year before" does not** (returns nothing). Pin
with #1016 (relative) and #1624 (explicit — it works today and must not regress).

### 7.3 Ruling wanted: PLN-022 is answered with a table of zeros

PLN-022 ("which blocks consistently experience delays in GPDP approvals") is a
documented unanswerable. In 3 of 3 replays it is answered with **PLN-020**. This is
what the officer actually sees, verbatim from the run:

```
Which Blocks have the highest number of pending GPDP approvals in 2025-2026 (10)?

Note: pending_approvals is 0 everywhere because approval_date is always populated.

block_name    pending_approvals   gps_with_plan
Bhubaneswar                   0               3
Barpali                       0               2
Rangeilunda                   0               2
```

**The caveat IS rendered** — D3 is doing its job, and this is less bad than "a table
of zeros served as an answer". An earlier draft of this report said there was "no
indication"; that was wrong, and the correction matters for how the ruling should
weigh it.

What remains wrong is narrower but real: the note explains why the COLUMN is zero,
not that the question the officer asked ("consistently delayed") cannot be answered
at all for want of a deadline and a business rule. A reader who takes the table at
face value concludes no block has a delay problem. The workbook's own answer —
PLN-022's documented reason, plus PLN-010 with a user-supplied `$deadline` as the
closest answerable form — is never offered.

The refusal-precedence rule (2.3) cannot fire: PLN-022 is at retrieval rank 46, far
outside the window, because its gold question is Odia-transliterated. So this is F2
in its consequences but it is worse than the other F2 rows, because the others
decline while this one *answers*.

**Operator ruling: (a) — treat it as F2.** Settled by a measurement the operator
asked for, which shows the refusal logic is not what is broken. The same question in
three registers:

| phrasing | PLN-022 retrieval rank | served |
|---|--:|---|
| the gold row, Odia transliterated | **46** of 376 — outside the window | **PLN-020**, the zeros table |
| the same question in English | **0** | **PLN-022** — the reranker picks the refusal |
| English, loose paraphrase (*"which blocks are repeatedly late in approving GPDPs?"*) | **0** | **PLN-022** — via the near-miss rule |

In English it works twice over, through two independent mechanisms — and the third
case is the near-miss rule (2.3) earning its keep on a phrasing nobody wrote a
paraphrase for: the reranker returned `no_match` but named PLN-022 among the closest
candidates, and the refusal was served anyway.

So this is F2 and nothing else, and whatever fixes the Odia registers fixes it.

**The alternative was NOT taken, and the reason is now quantified.** A
catalogue-level rule ("a template whose caveat declares its own measure uniformly
zero never wins a rerank") would apply to exactly **two** templates — PLN-020 and
PLN-021, the only two in the catalogue whose caveat says so. The ~30 SBM templates
carrying "partial data" caveats are a different family: they return real rows, just
incomplete ones. A mechanism for two rows is not worth its blast radius, so
**PLN-020/PLN-021 go on the statewide-arrival checklist instead**, to be re-profiled
when `approval_date` behaves differently in the full drop.

### 7.4 Recommendation: put the refusals in the recall measurement

`RECALL_EXCLUDED_CASES` drops every `unanswerable` row, so `recall@30 = 95.4%` says
nothing about whether a documented refusal can be retrieved — and finding B is
exactly the defect that gap hid for a whole work package. The 19 refusal rows have
never been measured for retrieval at all.

Not changed here, because it moves the recall denominator mid-comparison and the
brief asks for a per-language table against WP-4's. Recommended as a WP-5 gate item:
report refusal recall as its own line rather than folding it into the headline.

### 7.5 The smaller items, for the next package

1. **Widen the categorical gold coverage** before reopening the D30.1 retry — 42
   expectations is too few to rule on (4.2).
2. **The superlative flip** (5.2) — an `inverse_of` field from the generator makes it
   deterministic.
3. **#1524's gold row and the grader**: a `tier_collision` clarification is the
   ratified D18.P3 outcome and should grade as a pass on a collision row, instead of
   the ratified behaviour costing an accuracy point (3.2).
4. **D30.4's prefill** (4.3) — first task, with a 3x replay.
5. **The `.jsonl` write path** — this package hardened the reader and made the
   writer rewrite from memory (3.5), but the root cause is streaming a flush-per-line
   file into a Drive-synced folder. WP-5 should write eval artefacts to a local path
   and copy them in.

---

## 8. SME package delta

Which WP-4a section 4 items now have eval evidence attached:

| item | status after WP-4c |
|---|---|
| **4.3 — 34 Odia/transliterated phrasing rows** | **Still the top SME priority, and now blocking more than recall.** Odia script retrieves at 52.9% against 100% for every other register (3.1) — unchanged, because nothing here touched it. What is new: **15 of 27 confirmed failures are Odia-script or transliterated rows**, and **three of them are documented refusals that cannot be reached** (BEN-003 code-mixed, BEN-010 Odia script, PLN-022 Odia transliterated). One of those, PLN-022, is *answered* with a zero-filled near-miss rather than declined (7.3). The SME reading now unblocks a wrong-answer class, not only a recall number |
| **4.2 B1-B3, B7-B8** (clarify-or-default) | **Evidence now exists, because F1 no longer dominates.** These are the 6 `ambiguity` rows among the confirmed failures — #1036 "GPDP status?", #1411 "SFC vs CFC comparison", #1521 "expenditure Andhrua?", #1613, #1614, and #1524. All six clarify stably (3/3 or 2/3); the gold says answer. The disagreement is now a clean behavioural question with a stable measurement behind it, which is what the ruling was waiting for |
| **4.2 B4-B6** (tier collisions) | **CLOSED on the implementation side.** The `tier_collision` clarification now fires on both fragment paths (2.2): G1524 raised it in 2 of 3 replays against 0 of 3 in WP-4, and G1044 continues to hit 3/3. What remains is the scoring question in 7.5 item 3, not the behaviour |
| **4.2 B9** (Odia numerals) | **CLOSED** — unchanged from WP-4; G1008 hits 3/3 |
| **4.2 B10-B11** (judgement thresholds) | Unchanged, still pinned in tests |
| **4.1 M1-M7** (metric definitions) | **Now obtainable, and this is the change.** WP-4 said these "need a stable accuracy number to argue over" and none was available. There is one now: 85.8 / 87.2 / 87.2% with 4.7% consistency, and 27 confirmed failures of which 6 rows are the residue after F2 and the SME behaviour calls. The metric-definition discussion can proceed |
| **0 P4** (duplicate workbook rows) | Unchanged — measured crowding impact is still mean 0.02 siblings in top-30 (3.1). "Don't bother" stands |
| **0 P6** (SBM under-weighting) | Unchanged |

**One new SME-adjacent item.** The gold set has 528 date expectations and 42
categorical ones (4.2). That imbalance is why F1 was measurable and the categorical
all-None rate is not. Widening it is authoring work, not a ruling — but it is the
prerequisite for the D30.1 retry decision, so it belongs on the same list.

---

## 9. Compliance with the brief

| constraint | status |
|---|---|
| Repo-only, Ask-side paths only (D14) | Yes — every commit touches `Chatbot/`, `eval/`, `handoffs/WP4c*` and the recall CSV only. Discover's files were dirty throughout and were not touched or staged |
| Drive `.duckdb` read-only | Yes — `open_analytical_db` throughout |
| `.env` untouched and unprinted | Yes — presence of `OPENAI_API_KEY` checked as a boolean, never printed |
| §3a cache deletion at T0 | Yes — `__pycache__` + `.pytest_cache` deleted before the baseline run |
| §3a clean-tree check at T0 | **Partial, and reported** — the tree again held the concurrent Discover workstream's uncommitted work, plus an operator rename of the data-dictionary docx. Per D14 none of it was touched or staged |
| Baseline 461 passed / 16 skipped at T0 | Yes — verified exactly, before any change |
| LLM spend only in T4's runs and the T5 A/B | Yes, with one disclosure: the diagnostics in §2.3 and the pre-sweep smoke checks were part of preparing and triaging T4's runs and are itemised in §3.4. They are what found findings B and D |
| Call estimate printed before each paid run | Yes — and `recall_eval`'s estimate was **wrong** (it printed ~1 call and 10 were made, because it tested whether the cache file existed rather than whether it would be used). Fixed in `0637e04` |
| Edit the generator, never the generated files | Yes — `unanswerable_catalog.py` regenerated only, via `tools/build_catalog.py` |
| Thresholds move only in T6, on post-re-run evidence | **No change made** — §7.1, "not warranted", with the distribution evidence |
| Every reported failure replay-confirmed | Yes — `triage_replays.py`, ≥ 2 of 3 |
| Commit before and after the run | Yes for Ask-side paths |
