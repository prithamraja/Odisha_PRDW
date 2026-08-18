# WP-5 — Gates and pre-pilot hardening: REPORT

> ## Where everything is
>
> ```
> Ask/prdw_gates.py                             gate-green, as one command (T3)
> Ask/refusal_recall.py                         the D31.4 refusal-recall line (T3.8, T4c)
> Ask/eval_artefacts.py                         the local-then-copy write path (T4d)
> Ask/query_router/router.py                    the $date_range PREFILL (T1)
> Ask/query_router/operations.py                the truncated-table guard (T2a)
> Ask/query_router/echo.py                      the operations echo (T2b)
> Ask/main.py                                   the echo wired + the served-echo assertion
> Ask/tools/build_catalog.py                    the code-mixed refusal surface (T4c)
> Ask/tests/test_operations.py                  T2c, against a stub re-query hook
> Ask/tests/test_truncated_table_endpoint.py    T2c, against the real endpoint and SQL
> Ask/grade_full_eval.py, triage_replays.py     `clarify_as_ratified` (T4a)
> eval/gold/*.jsonl, coverage.json, README.md   +12 categorical rows, 3 `acc` corrections,
>                                               derived coverage (T4b)
> handoffs/WP5_REPORT.md                        this file
> ```
>
> **`Ask/pmkisan_gates.py` is deleted** — it was AP's, and `prdw_gates.py`
> replaces it.
>
> **Nothing is committed.** Per the operator's ruling of 2026-08-18 the working
> tree is left as it stands: this package's changes sit alongside the operator's
> own in-flight `Chatbot/` → `Ask/` reorganisation and the Discover/frontend
> edits. §8.1 lists exactly which files are this package's.
>
> Re-run anything:
> ```
> cd Ask && python prdw_gates.py                          # THE gate — exit 0 is green
> cd Ask && python prdw_gates.py --no-spend               # …with no API call at all
> cd Ask && python refusal_recall.py --yes                # the refusal ranks, measured
> python eval/gold/build_eval_questions.py --check        # gold set + coverage drift
> cd Ask && python run_consistency_eval.py --runs 3 --tag wp5 --yes
> cd Ask && python triage_replays.py eval_full_graded_wp5_run{1,2,3}.json
> ```
> Run from a local mirror, not the Drive path (bootstrap §6); the mirror needs
> `--repo <the Drive repo>` so the gates find the workbook and `eval/gold`.

---

## 0. For the PM — what this package did, in five lines

1. **Gate-green is a command.** `python prdw_gates.py` exits 0 with nine checks,
   one line each. It makes exactly one API call and that call is a model *list*.
2. **The one pre-pilot fix is closed, and closed live.** "Which focus area has
   the highest…?" → "and the lowest?" used to answer with the *highest*. It now
   re-queries the whole population, returns the real lowest, and prints an echo
   above it saying what it computed and over what.
3. **The `$date_range` reader is a prefill.** The slot leaves the extractor's job
   whenever the reader can read it — measured at 179–180 questions
   per replay — and the paired-year re-ordering it made unnecessary is deleted.
4. **The measurement gaps D31 named are closed.** Refusal retrieval has its own
   asserted line; categorical gold expectations went 10 → 22; a ratified
   `tier_collision` clarification no longer costs an accuracy point.
5. **The numbers held.** **87.7 / 88.2 / 88.6%** on the 211 rows WP-4c ran, against its 85.8 / 87.2 / 87.2% — up on every replay, `wrong_direction` still 0, and the confidently-wrong rate down from 3.3–3.8% to 1.8–3.1%.

---

## 1. Gate (definition of done)

| # | gate item | status |
|---|---|---|
| 1 | `python prdw_gates.py` exits 0, covering every T3 item | **PASS** — §4, output verbatim |
| 2 | T1's 3× replay at or above WP-4c's numbers, `wrong_direction` 0, no new confirmed failures | **PASS** — **87.7 / 88.2 / 88.6%** on WP-4c's own 211 rows against 85.8 / 87.2 / 87.2%; `wrong_direction` **0/0/0**; 27 confirmed failures, none of them new engineering. §6 |
| 3 | #1404/#1042 re-query or reject with echo; `query_description` never `None` on a served answer | **PASS** — §3 |
| 4 | `--check` green with the new gold rows; BEN-003 in-window or the residual honestly reported | **PASS** — §5.2, §5.3 |
| 5 | `pmkisan_gates.py` deleted; suite green; zero threshold changes | **PASS** — suite 594 passed / 22 skipped from a 568/22 baseline; `git diff 7184d5e -- config.py` still empty |

---

## 2. T1 — the `$date_range` reader, promoted to a prefill (D30.4)

### 2.1 What changed

`_fiscal_year_from_text` used to run in `_fill_slots_or_clarify`, on the branch
where the extractor had returned nothing. It now runs in `_extract_slot_values`,
beside `amount_from_text`, **before** the extractor is called — so a slot the
reader resolves is never in `askable` and is never sent.

Three consequences, all of them the ones WP-4c §4.3 predicted:

* **The slot leaves the extractor's job** on the great majority of questions.
* **The extractor stays the fallback for it.** The reader's vocabulary is narrow
  — it resolves "last year" and "this year" but not "the year before" — so a
  phrase it cannot read is still sent, and a year the model recovers from one is
  still bound. Reader-first-then-extractor is strictly safer than either order.
* **`_order_paired_fiscal_years` is deleted.** It existed because the extraction
  prompt orders a year pair by *mention* and the catalogue orders it
  *chronologically*; the reader splits one two-year phrase by entity type, and
  that split **is** the catalogue's convention. It fills both paired slots or
  neither, so a mixed pair cannot arise.

**No default year was introduced, and this was checked rather than assumed.**
`_DEFAULT_ENTITY_VALUES` still holds `top_n` alone, `$date_range` is required on
324 templates and optional on two, and the reader returns `None` when the
question names no year — so a yearless question still clarifies.
`test_a_question_with_no_year_still_clarifies_normally` pins it, and the replay
measured 2 / 3 / 2 (0.9–1.3%) "For which date range?" clarifications, in line with
WP-4c's ~2%.

### 2.2 What the tests measure now

The fiscal-year tests used to call `_fill_slots_or_clarify` directly, which after
this change is a path the router no longer takes for this slot. They now run
`_extract_slot_values` first, with a stub extractor, and record **which slots
were actually asked for** — the property the promotion is worth anything for:

```python
self.assertNotIn("date_range", self.asked,
                 "the reader resolved it, so it must not be sent")
self.assertIn("district_name", self.asked,
              "the slots with no deterministic reader still go out")
```

Two tests were added: one that the extractor is still the fallback (proved on
"the year before last", which the reader cannot read), and one that the reader
fills **both** paired slots or neither — the property that made deleting the
re-ordering safe.

### 2.3 The residual, named

The deleted re-ordering has one path it used to cover and nothing now does: a
**paired-year question the reader cannot read at all**, so that both slots come
back from the extractor and may arrive in mention order. It did not occur in any
of the six replays this project has run — every paired-year disagreement WP-4c
logged was a question the reader read correctly — but it is not impossible, and
the direction is now guarded by three things that do not depend on the deleted
function: `tests/test_paired_year_direction.py` (executed against the sample
database, and gate check 7), the convention stated beside the SQL in
`_validate_fiscal_year`, and `grade_full_eval`'s `wrong_direction` bucket, which
reads the served **values** on every replay.

### 2.4 The disagreement log

Kept, and staying quiet is now its *result* rather than its input: with the
reader running first, a disagreement is structurally unreachable, so a line in
that log means some new path has started supplying the slot from elsewhere. A
second log line was added for the case that *is* now informative — every
`$date_range` the reader could not read and the extractor rescued — which is the
measurement of whether keeping the extractor as the slot's fallback still earns
its place. Replay counts in §6.3.

---

## 3. T2 — the truncated-table guard, and the echo (§5.2, D31.2)

### 3.1 The defect, and what closes it

```
#1403 "Which focus area has the highest planned expenditure in 2024-25?"
      -> BUD-022, $top_n = 1 (a bare superlative binds it, by design)
      -> the displayed table is ONE ROW: the highest
#1404 "and the lowest?"
      -> read as an OPERATION on that table
      -> the minimum of a one-row table is that row
```

`frame.bound_params` carried `top_n: '1'` the whole time and nothing consulted
it. The guard sits in `run_operation`, **above every implementation**, so a new
operation cannot be added past it:

* `truncating_limit(frame, rows)` returns the `$top_n` that actually **cut** the
  table. It returns `None` when the limit never bound — `top_n = 10` over a
  seven-row population returns seven rows, the LIMIT did not bite, and the table
  *is* the population. Refusing there would decline a question with a correct
  answer.
* If the operation is population-dependent, the frame is re-queried through the
  same template with `$top_n` re-bound to the ceiling (**1,000**, the
  operator-ruled maximum — not "unlimited", because `LIMIT NULL` is unbounded),
  and the operation is recomputed on the full result. Mode `REQUERY`.
* If re-query is unavailable, raises, or returns nothing: `REJECTED`, with a
  reason that **names the truncation** — a generic refusal would leave the
  officer believing the table is the population, which is the belief that made
  the defect dangerous.

**Which operations are guarded** is enumerated in `operations.py`, one decision
per entry in `OPERATIONS`. Guarded: everything whose answer is a claim about a
*population* — `sum, average, share_of_total, min, max, top_n, bottom_n,
percent_change, median, stdev, percentile, range, mode, count_distinct`. Not
guarded, deliberately: `count` (its whole answer is "the table has N rows"),
`sort` and `filter_rows` (they return the rows on screen), `compare` (re-queries
by construction). The test suite asserts the unguarded set is exactly those four,
so it stays a decision rather than a leftover.

### 3.2 Before and after, on the recorded shapes

Read off the replay record, not reconstructed:

| | WP-4c (before) | WP-5 (after) |
|---|---|---|
| **#1404** "and the lowest?" over BUD-022 `top_n=1` | `Lowest planned_cost: 42,118,474 (focus area name: **Drinking water**)` — which is the **highest** | mode `requery`; `Bottom 1 rows by planned_cost. **Khadi** leads with 0. (Recomputed over all 25 rows: the table on screen was the top 1.)` |
| **#1042** "aur sabse kam?" (Hinglish) over PLN-052 | `Bottom 1 rows by planned_cost. Poverty allevation programme leads with 3,581,500.` — the top of a top-1 table | mode `requery`; `Bottom 1 rows by planned_cost. **Rural housing** leads with 0. (Recomputed over all 25 rows: the table on screen was the top 1.)` |
| `query_description` on both | `None` | `Lowest planned cost among all focus area name, 2024-2025:` |

### 3.3 The echo, and the assertion

`echo.operation_description` builds a deterministic sentence from the operation,
the column, the **scope** and the frame's period. The scope clause is the
load-bearing half: `among all …` is only ever written after the guard has
re-queried over the full population; a client-side computation says `among the …
shown`. So the sentence distinguishes the two cases the defect conflated.

`echo.operation_answer` puts the echo above the computed sentence and appends the
frame's caveat — which the `/query` operation path was not doing at all, and
which qualifies a recomputation exactly as much as the count it came from. A
`REJECTED` result gets no echo: restating a question above a sentence explaining
why it was not answered reads as though it had been.

`main._echoed` **raises** on a served answer with no `query_description`:

> Substituting a placeholder here would restore the silence in a form that reads
> like an answer; raising makes a missing echo a failure of the run, visible to
> the eval harness and to the suite, on the first replay rather than the
> fiftieth.

Measured across the three replays: **0 / 0 / 0 served answers with no echo**,
against WP-4c's 1 / 4 / 3 per replay.

### 3.4 Tests

Two files, at two levels, because the defect was never a logic error:

* `tests/test_operations.py` — 16 new tests against a stub re-query hook:
  both recorded shapes, the rejection path, a failing re-query (which must reject
  rather than fall back to the truncated table — that would be the defect again
  with an excuse attached), the limit-that-never-bound case, and the closed
  unguarded set.
* `tests/test_truncated_table_endpoint.py` — 8 tests through the **real
  `/operation` endpoint against the real sample database**: real template, real
  binder, real SQL, real validator. It asserts first that the displayed row *is*
  the population maximum (the premise, rather than an assumption), then that the
  minimum never returns it, then that the re-query reaches every focus area the
  sample holds. It blanks `OPENAI_API_KEY` for its own lifetime so that entering
  a `TestClient` cannot build the vector index — an always-on test that drives
  the app is the WP-2 spend trap one layer up.

---

## 4. T3 — `prdw_gates.py`

```
$ cd Ask && python prdw_gates.py

══ PR&DW gates ══  9 checks, from C:\dev\odisha-prdw-backend

  [PASS] 1. Full test suite, fresh caches
          594 tests across 30 modules, 22 skipped, 4 caches cleared
  [PASS] 2. Catalogue executes (346 templates, row counts)
          theme registry: 1 value(s) carry stray whitespace in the SOURCE and are bound verbatim …
          status registry: excluded ['Buildings'] — … a decoder defect in the SOURCE …
  [PASS] 3. Catalogue in step with the workbook
          in step with the workbook
  [PASS] 4. Gold set + harness format
            categorical expectations (theme/scheme/status — the slot families with no
            deterministic reader): 22 across theme 6, scheme 9, scheme_2 1, status 6
          OK — 223 records, invariants hold
          hard checks: PASS
          soft failures: none

── prdw_gates (model identity): estimated API spend ──
  provider model list (one catalogue read, no completion)  1 calls
  TOTAL                                                    ~1 calls
  confirmed — running

  [PASS] 5. Model identity (config + live model list)
          config: abstraction=gpt-5.4-mini, embedding=text-embedding-3-large,
                  extraction=gpt-5.4-mini, rerank=gpt-5.4-mini
          all four ids present on the live model list (124 models)
  [PASS] 6. Served-refusal invariant (result is None, never [])
          10 assertions
  [PASS] 7. Paired-year direction pins (executed)
          6 assertions
  [PASS] 8. Refusal recall (documented refusals retrieve)
          ── Refusal recall@30 (19 documented refusals, 376-entry index) ──
            en             15/15 in window   [asserted]
            code_mixed     2/2 in window   [asserted]
            odia           0/1 in window   [reported, NOT asserted (deferred)]
            odia_translit  1/1 in window   [reported, NOT asserted (deferred)]
            BEN-001 pin: rank 4 (was 51 before WP-4c, 4 after) — OK
          PASS  every refusal in a ratified register retrieves in window
  [PASS] 9. Static invariants
          date_filter unset on all 346 templates
          no $tag$ dollar quoting in any sql_template
          all 251 Partial templates carry a caveat
          extraction sentinel distinguishes failure from empty
          spend guard present on 3 paid harnesses
          pmkisan_gates.py deleted

GATE GREEN — 9/9 checks passed.

$ echo $?
0
```

Run from the `C:\dev` mirror with `--repo <the Drive repo>`, because DuckDB
cannot create temp files inside the Drive folder (bootstrap §6). Nine checks,
one line each; a failure names the check and prints its detail underneath.

### 4.1 Notes on three of the checks

**Check 5 — model identity.** Both halves, because checking config against
itself proves nothing: the four pinned ids are compared to what this gate
expects, *and* to the provider's live model list. One call, and it is
`models.list()` — a catalogue read, not a completion. On any mismatch it fails
with the bootstrap's own reminder quoted in full: *"on any model swap, check the
completion-token budget first"* — the failure mode where a reasoning model spent
a 2,000-token budget entirely on reasoning and returned empty strings, which is
the same signature as F1 in this project. `--no-spend` drops the call and says
so, rather than reporting a config-only check as if it had verified anything.

**Check 8 — refusal recall (D31.4).** Run `--cached-only`, because this file
makes exactly one paid call and it is check 5's. A cold cache reports
**UNMEASURED** and names the one command that fills it: an unverifiable invariant
is not a passing one.

**Check 9 — static invariants.** Five contracts that hold by construction and
are invisible until an answer is already wrong: no `date_filter` on any template,
no `$tag$` dollar quoting, every Partial carries a caveat, the extraction
sentinel distinguishes an API failure from an honestly empty extraction, and all
three paid harnesses go through `confirm_spend`. The Partial check refuses to
pass **vacuously**: if no template reports `answerable='Partial'` it fails,
because "all 0 Partial templates carry a caveat" is the worst possible thing for
a caveat check to print. (It printed exactly that on the first run — the field is
`answerable`, not `answerability`.)

---

## 5. T4 — gold and grader alignment

### 5.1 A ratified clarification is a pass (D31.3)

G1524 — "what about Laxmipur?" over a state-wide expenditure answer — is a
fragment × tier collision, and D18.P3 ruled that the router must **ask**, with the
tier question rather than the generic one. WP-4c made it do exactly that, in 2 of
3 replays against 0 of 3 in WP-4 — and the grader scored every one a `clarify`,
so the project paid an accuracy point for shipping behaviour it had ratified.

The rule is **general**, not a special case for one row. A gold row may declare
`expected_clarification`, naming the clarification reason(s) that are its ratified
outcome; a clarification with that reason lands in a new `clarify_as_ratified`
bucket, which `triage_replays.py` counts as passing. A clarification for any
*other* reason still lands in `clarify` — the row is pinned to the reason, not
excused generally. `build_eval_questions.py --check` validates the declared reason
against the router's own closed vocabulary, so a typo cannot quietly make a row
unpassable.

Re-graded against WP-4c's own recorded replays, without re-running them:

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| G1524 verdict, old grader | `clarify` | `clarify` | `partial` |
| G1524 verdict, new grader | **`clarify_as_ratified`** | **`clarify_as_ratified`** | `partial` |
| clarification reason recorded | `tier_collision` | `tier_collision` | `broad_question` |
| WP-4c behaving-correctly, re-graded | 85.8% → **86.3%** | 87.2% → **87.7%** | 87.2% → 87.2% |

Run 3 is unchanged and should be: the router asked a *different* question there,
and the rule is pinned to the reason.

### 5.2 +12 categorical gold rows (D31.6)

WP-4c §4.2 could measure the extractor's date behaviour precisely and could say
almost nothing about its categorical behaviour, which is why D30.1's retry
decision was deferred. The three slot families with **no deterministic reader**
— `theme`, `scheme`, `status` — stood at 10 expectations between them.
`$date_range` now has a reader (T1) and `$amount_threshold` has
`amount_from_text`, so both measure a regex as much as a model; these three can
only come from the extractor.

**10 → 22.** Twelve rows: 5 theme (PLN-031, PLN-032, AST-008), 5 scheme (SCH-002,
SCH-003, SCH-006, SCH-009, SCH-011), 2 status (STS-003, completing the status
registry — `UNDER APPROVAL` and `Activity Approved` were the two values nothing
measured, and they differ by one word and mean different things).

Every value was checked against the live registry before authoring, so each row
measures the extractor rather than a missing alias. The surfaces chosen are the
ones most likely to fail: a scheme whose name is two ordinary words (`Own Funds`),
an alias whose distinguishing token is a numeral where the stored value spells
the word (`14th` → `Fourteen Finance Commission`), a value stored in upper
case and asked in title case, the longest theme name in the registry, and a
theme named by number alone.

**Register is deliberately not the variable.** Every row is English or code-mixed,
both of which retrieve at 100%. An Odia-script row would fail for a reason that
has nothing to do with reading a scheme name.

Set is now **223 rows**; recall CSV **185**. `--check` and the harness-format gate
are green.

**`coverage.json` is now derived rather than remembered.** It was a hand-written
snapshot of the 205-row authoring set and still said 205 after WP-4c added six
rows — a coverage table that drifts is read as the answer to "is this set still
balanced?" and answers about a set that no longer exists. It is recomputed by
`--install`, `--check` fails on drift, and it now carries the categorical count
as a first-class figure. README §8 is rewritten around it; the WP-4a tables are
kept and labelled as the authoring snapshot.

### 5.3 BEN-003's register — and a correction to WP-4c §2.3

**The finding first, because it changes what the task was.** WP-4c §2.3 reported
BEN-003 at rank **64** and PLN-022 at rank **46**, both outside the 30-candidate
window. Measured against the shipped retriever, on the shipped index, with the
gold questions as queries — which is what `refusal_recall.py` now does on every
gate run — they were at rank **28** and **18**. Both were already *inside* the
window before this package touched anything.

I cannot reconcile the two from the record. WP-4c's own generator comment gives a
third set of numbers again ("measured after: BEN-001 rank 1, BEN-003 rank 12,
PLN-022 rank 0"), which suggests those were self-retrieval — the entry against
its own question — rather than against the gold row. The number to trust is the
one a script reproduces on demand, and that script now exists and runs in the
gate. **BEN-003 was not out of window; it was two places from the edge.**

The code-mixed surface was authored anyway, and it does what it was meant to:

| entry | register | before | after | in window (k=30)? |
|---|---|--:|--:|---|
| **BEN-003** | code-mixed | 28 | **24** | yes — margin 2 → 6 |
| BEN-010 | Odia script | 367 | 358 | no — deferred register, reported not asserted |
| BEN-001 | English | 4 | 4 | yes (pinned; was 51 before WP-4c) |
| PLN-022 | Odia transliterated | 18 | 18 | yes |
| the other 14 English rows | English | 0–1 | 0–1 | yes |

**How it is built.** Nothing translates. An officer typing code-mixed keeps the
domain nouns in English — scheme, pension scheme, beneficiary, village, cash,
purpose — and switches the *interrogative frame* around them. So the generator
rewrites the frame from an ordered table of eleven patterns and leaves every
content word exactly as the workbook wrote it. It runs on the **scope-free** form,
so place and year are already gone. A sentence no frame matches gets no
code-mixed line at all, rather than a half-converted one that would embed as
neither register.

**It is gated to the Dropped sheet**, which is the scope D31.5 rules on. The
frame table would fire on most of the 17 "No" rows too, on several of them
producing a line that differs from the English by one word — index weight for no
retrieval gain, added days before a pilot. Widening the gate is a one-line change
and should be made the way this one was: on a rank measurement, not on the
argument that more surface cannot hurt.

### 5.4 Three `acc` corrections the replay earned

A follow-up's acceptable set must cover **every reading that answers the question
correctly**, not only the one the author had in mind. WP-4c made this same
correction to G1003; the run found three more, and two of them are consequences
of WP-4c's own re-diagnosis.

| row | was | now `acc` admits | why |
|---|---|---|---|
| **G1404** "and the lowest?" | gold `BUD-023` only | `BUD-022` | WP-4c §5.2 corrected its first reading of this row: the verdict is `tier=operation`, not a template re-serve, and the catalogue carries no relation expressing the hop. Under the D31.2 guard the fragment now re-queries BUD-022 without its `$top_n = 1` and returns the true lowest focus area with an echo saying so. **Grading only BUD-023 scores the fix as a failure.** |
| **G1042** "aur sabse kam?" | gold `PLN-053` only | `PLN-052` | The same thing in Hinglish, for the same reason |
| **G1625** "…are under approval…" | gold `STS-003` only | `STS-010` | **My authoring error, found by the run.** STS-010 is a purpose-built template for exactly this question ("…are stuck in Under Approval status…"), so routing there is at least as good a reading as STS-003 with `$status` bound. The consequence is stated rather than hidden: on the STS-010 route there is no `$status` slot, so this row's categorical expectation is vacuous and G1626 is the row that measures the status slot |

The gold set wins over the copy `run_full_eval` writes onto each record, so these
corrections apply to replays already on disk rather than requiring 223 questions
to be re-run. **This is a judgement call and it is reversible**: if the PM wants
"and the lowest?" to be required to hop to the sibling template, remove the two
`acc` entries and the rows go back to failing — but then the catalogue needs the
`inverse_of` relation WP-4c §7.5 item 2 proposed, because nothing in it expresses
that hop today.

### 5.5 The `.jsonl` write path (D31.7)

`Ask/eval_artefacts.py`: stream to a **local** temporary file, copy the finished
artefact into the repo in one operation. WP-4c hardened the *reader* and made the
writer rewrite from memory at the end; both were right and neither was the fix —
the reader was repairing damage that should never have been written, and the
rewrite only helps a run that reaches its own last line.

Applied to the results `.jsonl`, the router log (appended to on every routing
decision, which is the same shape), the usage sidecar, the graded JSON, and the
append-only consistency file (which needs its existing copy as *input*, so it is
copied out to scratch first and back at the end). `PRDW_EVAL_SCRATCH` overrides
the scratch directory; the default is the platform temp directory.

This package's three replays were streamed through it. **All three published files parsed clean on the first read — 223 lines, 223 records, zero rejoins and zero orphans, against WP-4c's one split record plus a duplicate in replay 1 and four lost questions in replay 2.**

---

## 6. The runs

### 6.1 The headline, and the comparison WP-4c asked for

Three replays of the full gold set, `--tag wp5`, so WP-4c's artefacts are
untouched and the before/after has two intact halves.

**The set grew by 12 rows this package, so the honest comparison is the 211-row
subset WP-4c actually ran.** Both are given; the full set is the number that
carries forward.

| behaving correctly | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| **the 211 rows WP-4c ran** | **87.7%** | **88.2%** | **88.6%** |
| WP-4c, same rows, same grader | 86.3% | 87.7% | 87.2% |
| WP-4c, as reported at the time | 85.8% | 87.2% | 87.2% |
| **the full 223-row WP-5 set** | **88.3%** | **88.8%** | **89.2%** |
| full set, Odia script excluded | 93.6% | 94.1% | 94.6% |
| full set, Odia script + transliterated excluded | 94.7% | 94.7% | **95.8%** |

Against WP-4c's own Odia-excluded 91.1 / 92.7 / 92.7%, and within touching
distance of the 96–97% benchmark on the registers the project has ratified.

**Gate item 2, item by item:**

| | required | measured |
|---|---|---|
| at or above WP-4c's numbers | 85.8 / 87.2 / 87.2 | **87.7 / 88.2 / 88.6** on the same rows — up on every replay |
| `wrong_direction` still zero | 0 | **0 / 0 / 0** |
| disagreement log quiet | quiet | **0 / 0 / 0** lines |
| the ~12% extractor all-None rate irrelevant to `$date_range` | — | **179 / 180 / 179** prefills; the extractor supplied the slot **0 / 0 / 1** times |
| no new confirmed failures | — | 27 confirmed, none of them new engineering; §6.5 |

### 6.2 The confidently-wrong rate

The number WP-4c argued the pilot decision on — how often the system asserts
something untrue, as against asking:

| | correct | asked / declined | **confidently WRONG** |
|---|--:|--:|--:|
| all rows, WP-5 | 88.3 / 88.8 / 89.2% | 9.9 / 8.1 / 8.1% | **1.8 / 3.1 / 2.7%** |
| all rows, WP-4c | 85.8 / 87.2 / 87.2% | 10.9 / 9.0 / 9.5% | 3.3 / 3.8 / 3.3% |
| Odia excluded, WP-5 | 93.6 / 94.1 / 94.6% | 4.4 / 2.9 / 3.4% | **2.0 / 2.9 / 2.0%** |
| Odia excluded, WP-4c | 91.1 / 92.7 / 92.7% | 5.7 / 4.2 / 4.2% | 3.1 / 3.1 / 3.1% |

Down on every line, and the failure mode is still overwhelmingly "it asked"
rather than "it lied", which is the right way round for a v1. (The WP-4c rows
divide by 211 and the WP-5 rows by 223 — these are rates, and §6.1 gives the
like-for-like comparison on identical rows.)

### 6.3 T1 — the prefill, measured

| | run 1 | run 2 | run 3 |
|---|--:|--:|--:|
| `$date_range` supplied by the READER (prefill) | 179 | 180 | 179 |
| `$date_range` supplied by the EXTRACTOR (fallback) | 0 | 0 | 1 |
| disagreements logged | 0 | 0 | 0 |
| paired-year re-orderings | n/a — the function is deleted | | |
| "For which date range?" clarifications | 2 (0.9%) | 3 (1.3%) | 2 (0.9%) |
| extraction calls | 197 | 198 | 198 |

**Two things worth the PM's attention.**

*The prefill saves SLOTS, not calls.* Extraction calls are essentially unchanged
(197–198 against WP-4c's 186 over a smaller set) because only **2** of the gold
templates have a fiscal year as their *only* slot — every other question still
needs an extraction call for its geography. What changed is that ~180 slots per
replay no longer depend on a model measured at a 12% all-None rate. WP-4c §4.3
said "about 160 fewer slots per replay" and that is exactly what happened.

*The extractor fallback earned its keep once, in three replays.* One question in
669 needed it. That is not an argument for removing it — a fallback that fires
rarely is doing the job a fallback is for, and the phrases the reader cannot
handle ("the year before") are real — but it is the measurement the next package
would want before deciding either way. The clarification rate for a stated-but-
unreadable year is **0.9–1.3%**, against WP-4c's ~2%: the prefill halved it.

### 6.4 T4b — the first measurement of categorical extraction

All twelve new rows are `hit` in **3 of 3** replays, and the categorical slot is
bound to the gold value on **11 of 12** in every replay:

| family | rows | categorical slot bound correctly |
|---|--:|---|
| theme | 5 | 5 / 5, all three replays |
| scheme | 5 | 5 / 5, all three replays |
| status | 2 | 1 / 2, all three replays — #1625 routes to STS-010, which has no `$status` slot (§5.4) |

**This is the evidence D30.1 was waiting for, and it argues against the retry.**
Twenty-two categorical expectations, stable across three replays, with no
all-None failure on any of them: `Own Funds` (two ordinary words), `Fourteen
Finance Commission` (asked as "14th"), `4TH STATE FINANCE SCHEME` (asked in title
case), `Theme 1 - Poverty Free and Enhanced Livelihoods Village` (seven words),
`Theme 8` (a number alone) and `Activity Approved` (one word from `UNDER
APPROVAL`) all bound correctly, three times each. The ruling is the PM's; the
measurement now exists.

### 6.5 Triage — 27 confirmed failures, and what they are

`triage_replays.py`, majority rule 2 of 3. **Replay noise: 0** — every failure
here is stable, which is itself a change from WP-4c.

| class | rows | state |
|---|--:|---|
| **Odia script** | 12 | Operator-deferred. Every one clarifies rather than answering |
| **Odia transliterated** | 2 | Operator-deferred — #1415, #1860 |
| **SME behaviour calls** | 5 | #1036, #1411, #1521, #1613, #1614 — all clarify stably; the gold says answer. Open for the pilot |
| **Finding C (fragment year)** | 2 | #1016, #1624 — operator-deferred; both print the year they answered |
| **Documented refusals not reached** | 3 | #1039 (PLN-022, Odia transliterated), #1972 (BEN-003, code-mixed), #1974 (BEN-010, Odia script) — see below |
| **Fragments that lose the frame** | 3 | #1202, #1503, and #1026 — the unstable code-mixed row WP-4c named |

By register: 13 Odia script, 3 Odia transliterated, 2 code-mixed, 9 English.
**Sixteen of the 19 refusal rows serve their documented reason 3/3**, unchanged
from WP-4c.

**Verdict flips: 10 of 223 = 4.5%** (WP-4c: 4.7%). Route flips: 9 of 223 = 4.0%.
Still the ~3% standing risk, unchanged and unchased.

**The residual worth naming: in-window is not the same as served.** BEN-003 now
retrieves at rank 24 of 376 — comfortably inside the 30-candidate window — and
still comes back `declined_generically` in all three replays: the router declines,
correctly, but without the workbook's own reason for declining.

So the index gap D31.5 named is closed, and closing it made a *second*, downstream
gap visible behind it — the reranker has the candidate now and does not pick it.
That is a selection question rather than a retrieval one; it is one row; and the
outcome is still a refusal rather than a wrong answer. Reported, not fixed, and
the honest reading of D31.5's target: **BEN-003 is in-window as asked, and still
not served.** Whether that is worth a package is the PM's call — the measurement
to argue it from is now a gate line that runs on every commit.

### 6.6 Spend

| | run 1 | run 2 | run 3 | total |
|---|--:|--:|--:|--:|
| calls | 624 | 623 | 623 | **1,870** |
| total tokens | 1,592,532 | 1,589,278 | 1,585,804 | **4,767,614** |
| embed / rerank / extraction / follow-up | 213/201/197/13 | 212/200/198/13 | 212/200/198/13 | |

Plus **~11 embedding calls** for the refusal-rank before/after (§5.3) and **one
`models.list()`** per full gate run. Every one went through `eval_spend.confirm_spend`.

---

## 7. Pilot go/no-go checklist

### 7.1 The blocking item, closed

| | |
|---|---|
| **D31.2 — the §5.2 truncated-table guard** | **DONE.** Guarded in the operations layer above every implementation; re-queries to the ruled 1,000 ceiling or rejects naming the truncation; both recorded shapes verified live in the replay (§3.2); echo added and asserted; 24 tests across a stub hook and the real endpoint. |

### 7.2 The three disclosures — pilot-ready, and to be carried verbatim

1. **Odia-script questions reach the right answer about half the time** (52.9%
   recall, unchanged — nothing in this package touched it). Either keep
   Odia-typing officers out of the pilot, or tell them to type in English or in
   transliterated Odia, which retrieves at 100%. One documented refusal (BEN-010)
   sits at rank 358 of 376 in Odia script and cannot be reached at all.
2. **Every percentage divides by the 20 loaded GPs**, not the official roster
   (standing risk, PROJECT_PLAN §6). On a 20-GP sample that is the difference
   between a statistic and an anecdote. Say it before anyone quotes a figure.
3. **Follow-up fragments are the weak surface.** A relative period in a fragment
   ("what about last year?") may answer about the year already on screen — finding
   C, root-caused and **operator-deferred**, not fixed. The standalone-question
   surface is close to clean; the fragments are where the remaining
   confidently-wrong rows live.

### 7.3 Open items for the pilot's operators

| # | item | state |
|---|---|---|
| 1 | **The six SME behaviour calls** (WP-4c §5.5) — #1036 "GPDP status?", #1411 SFC vs CFC, #1521 "expenditure Andhrua?", #1613, #1614, #1524 | Open. All six clarify stably; the gold says answer. A pilot is exactly the evidence D9 and D18.P3 said to revisit them from. #1524 is now *scored* as a pass (§5.1) — the behaviour question is still open. |
| 2 | **Finding C** — a relative period in a follow-up fragment | **Operator-deferred.** Diagnosis and the design question are in WP-4c §7.2. Disclosure 3 above is the mitigation. |
| 3 | **F2 / Odia** | **Operator-deferred.** Odia script and transliterated Odia remain out of scope; `refusal_recall.py` reports their ranks on every gate run without asserting them, so deferring stays a visible choice. **BEN-003 (D31.5) is half-closed and says so:** in-window at rank 24 after the code-mixed surface, still `declined_generically` 3/3 — a reranker-selection gap the retrieval fix uncovered (§6.5). |
| 4 | **The D30.1 categorical retry** | **Now rulable, and the evidence argues against it.** 22 categorical expectations against 10; all twelve new rows `hit` 3/3, the categorical slot bound to the gold value on 11 of 12 in every replay, and no all-None failure on any of them (§6.4). |
| 5 | **The `$top_n` ceiling of 1,000** | Standing operator ruling. The truncation guard re-queries *to* the ceiling rather than past it, so a population above 1,000 rows would still be a truncated view — statewide, that is a real case and it clarifies rather than answers, as ruled. |
| 6 | **`refusal_recall.py`'s caches** | The gate runs it `--cached-only`. On a fresh machine the first gate run reports check 8 UNMEASURED until `python refusal_recall.py --yes` is run once (~1 API call). Documented in the check's own failure text. |

---

## 8. Things the operator should know

### 8.1 The tree was reorganised mid-run

`Chatbot/` became `Ask/`, the root `.md` files moved into `handoffs/`, and
`Other_analysis/` appeared, while this package was executing. The tree was
verified **clean** at T0, as the brief requires; the change arrived afterwards.
All WP-5 work survived into `Ask/` and was verified there.

**The rename silently broke three things, all repaired here:**

| what | how it broke | repair |
|---|---|---|
| `eval/gold/build_eval_questions.py`, `check_harness_format.py` | both hard-coded `REPO / "Chatbot"`. The catalogue cross-check does not *fail* when it cannot import — it reports SKIPPED, so the gold set would have validated against nothing | `_backend_dir()` resolves `Ask/` then `Chatbot/`, and names the path it could not find |
| `.gitignore` | ignored `Chatbot/eval_full_results*.jsonl`; after the rename ~200 MB of replay artefacts were no longer ignored | both spellings listed |
| `prdw_gates.py` (new) | would have looked for the workbook and `eval/gold` beside the backend | `PRDW_REPO` / `--repo`, the same override `build_eval_questions.py` already takes |

Files this package changed, for when you separate the commits:

```
Ask/query_router/router.py          Ask/prdw_gates.py            (new)
Ask/query_router/operations.py      Ask/refusal_recall.py        (new)
Ask/query_router/echo.py            Ask/eval_artefacts.py        (new)
Ask/main.py                         Ask/pmkisan_gates.py         (DELETED)
Ask/tools/build_catalog.py          Ask/tests/test_truncated_table_endpoint.py (new)
Ask/query_router/unanswerable_catalog.py   (regenerated — the only generated file whose CONTENT changed)
Ask/grade_full_eval.py              Ask/tests/test_operations.py
Ask/run_full_eval.py                Ask/tests/test_fiscal_year_fallback.py
Ask/run_consistency_eval.py         Ask/triage_replays.py
eval/gold/{planning,assets,budgeting_funding,expenditure,implementation_progress}.jsonl
eval/gold/{build_eval_questions.py,check_harness_format.py,coverage.json,README.md}
.gitignore
```

`template_catalog.py`, `rerank_context.py` and `tests/data/workbook_test_report.json`
were rewritten by the generator but are **byte-identical to HEAD modulo line
endings** (`core.autocrlf=true`, so git normalises them back).

### 8.2 `refusal_recall.py` made the mistake WP-4c had just fixed

Its first version tested `_CACHE_PATH.exists()` for the spend estimate, printed
"0 (cached)", and then spent nine embedding calls — because regenerating the
unanswerable catalogue changed the index signature and the retriever correctly
rejected the stale cache a moment later. This is the identical defect WP-4c found
in `recall_eval` (§9, "the estimate was wrong"). It is fixed the same way: the
signature is recomputed and compared, and staleness counts as cold. Reported
because an estimate wrong by an order of magnitude is worse than no estimate, and
because the pattern has now appeared twice.

### 8.3 Data oddities

Nothing new. The running list in PROJECT_PLAN §3a is unchanged; `validate_catalog`
still reports the `Theme 5 - Clean and Green Village ` trailing space and the
`'Buildings'` mis-decode on every run, and both remain logged, not fixed.

---

## 9. Compliance with the brief

| constraint | status |
|---|---|
| Ask-side paths only (D14) | Yes — `Ask/`, `eval/gold/`, `.gitignore`, `handoffs/WP5_REPORT.md`. Discover's files and the frontend's were dirty throughout and were not touched or staged |
| Drive `.duckdb` read-only | Yes — `open_analytical_db`/`get_adapter` throughout; every execution ran from the `C:\dev` mirror |
| `.env` untouched and unprinted | Yes — read as a boolean for key presence, never printed. The new endpoint test *blanks* `OPENAI_API_KEY` for its own lifetime and restores it |
| §3a: fresh caches before trusting a run | Yes — at T0, and gate check 1 now does it on every run |
| §3a: clean-tree check at T0 | Yes, and it **passed** — the tree was clean. The reorganisation arrived mid-run; §8.1 |
| Baseline before any change | Yes — 568 passed / 22 skipped, `validate_catalog` all-clear, `--check` and the harness gate green |
| LLM spend only in T1's replay proof, through `eval_spend.py` | **Yes, with two disclosures, both itemised.** (a) `refusal_recall.py`'s before/after measurement — ~11 embedding calls, which the brief's T4c sanctions ("the embedding call is part of index build"), guarded by `confirm_spend`; one of those runs spent 9 calls against an estimate of 0, §8.2. (b) One `models.list()` call per full gate run — check 5, guarded, and a catalogue read rather than a completion |
| Call estimate printed before each paid run | Yes, and the one that was wrong is reported and fixed |
| Thresholds untouched | Yes — `git diff 7184d5e -- Ask/query_router/config.py` is empty. No threshold changed |
| Edit the generator, never the generated files | Yes — `unanswerable_catalog.py` regenerated via `tools/build_catalog.py` only |
| Not in scope, and not done | F2/Odia beyond BEN-003; thresholds; finding C |
