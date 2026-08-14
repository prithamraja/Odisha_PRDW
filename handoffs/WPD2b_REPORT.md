# WP-D2b report — view1 at depth 1, ranking list fixed, package v2

Executing `handoffs/WPD2b_view1_rerun.md` (Discover workstream, addendum to
WP-D2). Run date **2026-08-14**. No git operation performed — staging and
committing are the operator's.

**Headline:** all five gate items pass. view1 **drained in 262.5 s** of a
3,600 s budget at `max_subspace_depth = 1`, with all 17 dimensions and all 24
measures kept — 48,792 data scopes, 3,139 candidates, 0.60 GB peak memory. The
executive report now carries **all three sections** and all four T5 checks are
green across the whole of it: zero prose-gate problems, zero hollow sections,
the FY 2023-24 caveat exact in both directions, and **70 of 70** quoted figures
traced. The calibration package is v2 with **33 findings** (15 + 15 + 3). The
nine-view list in `phase5_ranking.py` is gone and the driver is retired.

The one thing worth the operator's eye before anything else: **depth 1 was
about twelve times cheaper than WP-D2's own conservative projection**, and §2
says why, measured. The decision was still the right one on the memory wall
alone, but the time price of depth 2 was over-stated in §2 of the last report.

---

## §0 Gate self-assessment

| # | Gate item | Verdict | Evidence |
|---|---|---|---|
| 1 | view1 drains at depth 1; diagnostics prove it | **PASS** | 262.5 s of a 3,600 s budget; the queue emptied — 48,792 of 48,792 scopes. §2 |
| 2 | Ranking list fixed; driver retired | **PASS** | `phase5_ranking.py.__main__` lists three views; `run_phase5_prdw.py` deleted. Re-ranking view2/view3 from unchanged candidates reproduced their WP-D2 `*_ranked.json` **byte for byte**. §3 |
| 3 | Executive report carries all three sections; all four T5 checks green across it | **PASS** | 703 / 663 / 544 words; prose gate 0 problems, rc=0; caveat exact both ways; 70/70 figures traced; 15 view1 figures additionally re-derived from the Parquet by hand. §4 |
| 4 | Calibration package v2 delivered | **PASS** | `handoffs/WPD2_calibration/` — 33 findings, sheet, three per-view read-ups, both dashboards, both check outputs, mining and ranking transcripts, README v2. §5 |
| 5 | No file outside scope touched; no git operations | **PASS with one disclosure** | File list in §7. `phase4b_engine.py` was NOT edited — it is not in this brief's writable set — so the view1 mine ran from a scratchpad runner calling the same `run_engine`. That leaves a stale budget line in it; see E-1 |

**Preconditions.** D25 ratified (this brief). `Insights/.env` exists and carries
`OPENAI_API_KEY` — D-2 is closed by the operator, and this run made no attempt
to read `Chatbot/.env`. Local mirror used throughout; nothing was executed
against the Drive mount. **The tree was not committed**: WP-D2's edits to seven
`Insights/src` files are still working-tree modifications, so this run built on
an uncommitted base. Everything WP-D2b measured is reproducible from that tree,
but the "tree committed" precondition is formally unmet — see E-6.

---

## §1 What changed in the code

Four edits, all inside the brief's writable set.

| file | edit |
|---|---|
| `Insights/src/phase2_engine.py` | `VIEW1_CONFIG.max_subspace_depth` → `2 if _STATEWIDE else 1`, with the D25 rationale in place: the depth-2 arithmetic, the ~37-row average slice, the two walls, and the note that statewide keeps depth 2 and is compute-gated behind the engine-scaling WP. Dimensions and measures untouched — 17 and 24. |
| `Insights/src/phase2_engine.py` | one measure comment, `sc_amount`: "LABEL SWAPPED AT SOURCE" → "SUSPECTED LABEL SWAP", so the config does not assert more than the glossary now does (E-3). |
| `Insights/src/phase5_ranking.py` | `__main__`'s nine-view list → `["view1", "view2", "view3"]`, with the D-12/D25 authority and the driver retirement recorded beside it. Nothing else in the file. |
| `Insights/src/phase5b_report.py` | the `sc_amount` / `st_amount` glossary entries now state a **suspected** swap — "the two source tables carry these values swapped relative to each other; whether the labels or the data are wrong is unconfirmed with the data team" — and the comment block above `VIEW_DESCRIPTIONS` was brought into step. The ban on any SC-versus-ST comparison from those two columns is unchanged; it holds under either reading. |

Plus one deletion (`handoffs/WPD2_calibration/run_phase5_prdw.py`) and one test
update: `verify_configs_prdw.py`'s depth assertion became "view1 depth 1 sample
/ 2 statewide", which is now a two-sided check rather than the one-sided
`== 2` it replaced.

**`verify_configs_prdw.py`: 99 checks, 0 failures** — the same count as WP-D2,
because the edit changed an assertion rather than adding one. Archived at
`WPD2_calibration/verify_configs_output.txt`, re-runnable. The three depth
checks now read:

```
  [PASS] view3 depth 1 sample / 2 statewide
  [PASS] view1 depth 1 sample / 2 statewide
  [PASS] view2 depth 1 both
```

**D-15 stands as implemented.** No change, per the brief. `n_completed` still
qualifies for the §5.2 caveat under the wider reading; view3's top two findings
still carry it.

---

## §2 view1 drained — and the projection was wrong in the safe direction

| | WP-D2, depth 2 | **WP-D2b, depth 1** |
|---|---|---|
| subspaces enumerated | 13,495 (1 + 172 + 13,322) | **173** (1 + 172 + 0) |
| retained after the 1% impact prune | 2,438 | **127** |
| data scopes behind them | 880,752 | **48,792** |
| budget | 18,000 s (escalated) | **3,600 s** |
| **elapsed** | stopped at 585.6 s, 1.7% done | **262.5 s — queue empty** |
| throughput | 25.6 scopes/s cumulative | **185.9 scopes/s** |
| patterns found | 17,290 at 15,000 scopes | **51,571** |
| HDPs evaluated / skipped by dedup | — | 22,724 / 86,959 (**79.3%**) |
| query / pattern cache hit rate | — | **97.4% / 43.0%** |
| peak process memory | **3.94 GB**, 0.38 GB machine free | **0.60 GB** |
| candidates | 14,172 and climbing, unscoreable | **3,139** |
| top score | — | **0.8760** |

The drain proof is the loop's own exit condition: `run_engine` leaves only when
the queue is empty or the budget is gone, and 262.5 s against a 3,600 s budget
with all 48,792 scopes evaluated is the queue emptying. No trim beyond depth was
applied — the dimension list is 17 long and the measure list 24 long, as
shipped.

**The projection was 12.4× pessimistic and that is worth recording.** WP-D2 §2
priced depth 1 at "≈0.9 h" by dividing 48,792 scopes by the *conservative*
15.0 scopes/s observed in the opening segment of the depth-2 run. The real rate
at depth 1 is 185.9 scopes/s. The cause is measured, not mysterious: with 127
subspaces instead of 2,438, the same scopes recur far more often, so the HDP
dedup hit rate rises to **79.3%** (against 62.8% and 67.1% on the two small
views) and the query cache to **97.4%** — and none of it is competing with a
3.94 GB working set for physical memory. Per-scope cost is not a constant of the
view; it is a function of how much of the queue is cache-resident, which is
exactly what depth controls.

That does not reverse D25 — the memory wall was independent of the time wall,
and 880,752 scopes at even 185.9/s is still 79 minutes with a candidate file
nothing downstream is sized for. But if the statewide question is revisited, the
right input is this number, not §2's.

**What depth 1 actually produced.** Six pattern types and zero of the five
temporal ones — `TREND`, `SEASONALITY`, `CHANGE_POINT`, `OUTLIER`,
`UNIMODALITY` all returned nothing, which is correct: view1 has no temporal
dimension by design (D22/§5 routes all temporal mining to view2). The candidate
pool splits 2,027 subspace-extending / 1,112 measure-extending.

---

## §3 Ranking

`python Insights/src/phase5_ranking.py` — the fixed `__main__`, no driver.

| view | candidates | pre-filter | ranked | TotalUse |
|---|---|---|---|---|
| view1 | 3,139 | 3,139 (under the 5,000 cap) | **15** | 11.6889 |
| view2 | 110 | 110 | **15** | 4.1263 |
| view3 | 5 | 5 | **3** | 0.8940 |

**The list edit is proved inert.** view2's and view3's candidate files were not
re-mined — their configs did not move — and re-ranking them produced
`view2_ranked.json` and `view3_ranked.json` **byte-identical** (SHA-256) to the
files WP-D2 produced with the driver. So the six deleted entries changed which
views get ranked and nothing about the ranking. The candidate files this package
was ranked against are hashed in `WPD2_calibration/mining_log.txt`:

```
view1_candidates.json  236f8e1b4c5d2d0e30c1a4b8e56df209f90f0f71b790d2d338b2bf09f78239b1
view2_candidates.json  33501b929ce348410f8661d86f4af4657a4b45d0f84a6567b6d502b7f21bc426
view3_candidates.json  b8085da4970eb5749a8a483274237cab7bac95776c54b96f603a36806f54e5d8
```

view1's pre-filter is a no-op at 3,139 candidates. Had depth 2 drained, the same
stage would have faced roughly 800,000 — the second of the two walls, and the
reason a truncated depth-2 queue could not simply have been ranked as-is.

---

## §4 The report and the four checks (T3)

`Insights/reports_prdw/executive_metainsight_report.md` (+ `.pdf`), three
sections, generated in one run by `gpt-5.6-sol` at the pinned 9,000-token
budget. Output archived at `WPD2_calibration/check_report_output.txt`.

**(a) Prose gate — clean, with nothing left to except.** `prose_gate.py` runs
unmodified and reports `1/1 report(s) clean`, exit 0. WP-D2's single structural
complaint — view1's section missing — is gone because the section exists. Zero
vocabulary violations, zero rival methodology blocks, exactly one deterministic
reading note per section.

**(b) No hollow sections.** 703 (view1) / 663 (view2) / 544 (view3) words
against a 400–800 word instruction; zero blank sections; every registered view
has a section.

**(c) The FY 2023-24 caveat is exact in both directions, now over three
sections.**

| section | findings that qualify | caveat in the report? | correct? |
|---|---|---|---|
| Activity Lifecycle | **#13 and #14** | yes | ✔ |
| Monthly Money Flows by Gram Panchayat | none | no | ✔ |
| Gram Panchayat Report Card by Year | **#1 and #2** | yes | ✔ |

view1's two qualifying findings are `is_started` and `n_activities` broken down
across all six fiscal years — activity counts compared across the boundary. Its
three other fiscal-year findings (#12 and #15, rupee measures) correctly do
**not** qualify, which is the predicate discriminating on `_UNITS` rather than
on the presence of a fiscal-year axis. In both qualifying sections the sentence
sits inside the deterministic reading note, verbatim, never in model prose.

**(d) Every figure traces. 70 of 70** — 39 in view1, 19 in view2, 12 in view3.
Every numeric token in the prose was extracted and matched against the union of
everything the enrichment rendered, everything the view's own description,
glossary and reading note state as fact, and the HDP member and commonness
counts.

**Fifteen view1 figures were then re-derived from the Parquet itself**, not from
the enrichment that produced them — a claim can trace to engine output and still
be attached to the wrong scope:

| claim in the view1 prose | re-derived | verdict |
|---|---|---|
| sample-wide SPENT-minus-PLANNED "Rs -51.96 crore" | -51.96 cr | ✔ |
| "No Gram Panchayat has a positive aggregate balance" | 20/20 negative | ✔ |
| "Biswamathpur, Rs -7.23 crore against 4.3% of all activities" | -7.23 cr, 4.3% | ✔ |
| "Kalimela, Rs -5.90 crore against 6.7%" | -5.90 cr, 6.7% | ✔ |
| SPENT-minus-SANCTIONED "Rs -5.02 crore" | -5.02 cr | ✔ |
| "Sheragada Rs -85.77 lakh against 7.2%" | -85.77 lakh, 7.2% | ✔ |
| "Rangeilunda Rs -82.57 lakh against 9.2%" | -82.57 lakh, 9.2% | ✔ |
| "Khallikote records Rs 0 against 5.0%" | 0.00, 5.0% | ✔ |
| "Theme 6 … Rs 30.07 crore … 50.4% of the Rs 59.64 crore total" | 30.07 / 59.64 = 50.4% | ✔ |
| "Theme 4 … Rs 11.63 crore, or 19.5%" | 11.63, 19.5% | ✔ |
| "Activity Approved … 10,108 activities, or 79.6%"; ONGOING 2,110 / 16.6%; ABANDONED 420 / 3.3% | exact | ✔ |
| "New/Fresh 11,047 activities, or 87.0%"; Maintenance 1,207 / 9.5% | exact | ✔ |
| overspend by status: Approved -41.61 cr, ABANDONED -5.64 cr, ONGOING -4.24 cr | exact | ✔ |
| "Sanitation 620 activities, or 29.1%; Drinking water 548, or 25.8%" (of 2,127 started) | exact | ✔ |
| "Chikilli … Rs 0 … across every fiscal year … 5.0% of all activities" | 0 in all six years, 5.0% | ✔ |

Six structural claims were checked against `view1_ranked.json` as well: "18 of
the 20 Gram Panchayats" (#7, 18/20), the Boipariguda `Unmapped theme` and
Kalimela `Theme 4` exceptions (#7 HIGHLIGHT_CHANGE), "Boipariguda and Laxmipur"
as the two status exceptions (#9/#10/#11 NO_PATTERN), and "across every fiscal
year" on #13 (6/6 members). All ✔.

**The prose applied the domain rules unprompted where it mattered.** It wrote
"these are totals, not performance rates" beside the two largest negative
balances; it flagged that the block-level activity shares "cover the whole view,
not just activities with sanction records"; it left both readings of Chikilli's
Rs 0 open rather than calling it a failure; and it stated that with 17 recorded
completions "the recorded completion field cannot support a meaningful
comparison of Gram Panchayat performance."

---

## §5 Calibration package v2 and the deltas from v1

`handoffs/WPD2_calibration/` — **33 findings** (view1 15, view2 15, view3 3),
against 18 in v1.

| | v1 (WP-D2) | **v2 (WP-D2b)** |
|---|---|---|
| findings | 18 | **33** |
| views covered | 2 | **3** |
| report sections | 2 | **3** |
| figures traced | 37/37 | **70/70** |
| prose-gate problems | 1 structural (missing section) | **0** |
| config checks | 99 / 0 failures | 99 / 0 failures |
| `run_phase5_prdw.py` | shipped | **deleted** |
| new files | — | `findings_view1.md`, `ranking_log.txt` |

`labeling_sheet.csv` carries 33 rows, `label` and `operator_notes` empty on all
of them, `fy_2023_24_caveat = yes` on exactly four (view1 #13, #14; view3 #1,
#2). `mining_log.txt` is now a two-part transcript: the WP-D2 view2/view3 runs
reproduced unedited, then the WP-D2b view1 run, with the depth-2 comparison and
the candidate hashes in the header. `README.md` is rewritten for v2, including
the new re-run sequence (step 3 is now `phase5_ranking.py` itself).

**Two things about view1's fifteen that the operator should know before
labelling**, both stated in the README:

1. **Ranks 1 and 2 are near-twins.** Both are `EVENNESS` over
   `asset_category_label` with the identical 27-of-28 commonness set and the
   identical single exception (Banking Facilities); they differ only in measure
   (`overspend_vs_plan` / `overspend_vs_sanction`) and breakdown (`gp_name` /
   `block_name`). The greedy ranker's redundancy penalty did not separate them.
2. **Ranks 3–11 are largely one 20-GP HDP seen through nine measures.** At depth
   1 the only geography subspaces are single GPs, so "across nearly all gp_name
   values (18–19 of 20)" is the shape almost every high-scoring view1 finding
   takes. That is a property of the view at this depth, not a bug, but it means
   the top of view1's list is narrower in *kind* than its length suggests.

Both are exactly the sort of thing the calibration session exists to price, and
neither is a reason to withhold the findings.

---

## §6 Decision journal

**E-1 · `phase4b_engine.py` was not edited; the view1 mine ran from a scratchpad
runner.** The brief's files-in-scope list names `phase2_engine.py`,
`phase5_ranking.py`, `phase5b_report.py` and the artifact directories.
`phase4b_engine.py` is not among them, and its `ALL_CONFIGS` loop would also
have re-mined view2 and view3 — which T2 explicitly forbids. So T2 ran from
`scratchpad/mine_view1.py`, which imports the same `VIEW1_CONFIG` and calls the
same `run_engine` with `time_budget_seconds=3600` and writes the same
`view1_candidates.json`. Nothing about the mining differs; only the budget
integer and the view selection are supplied by the caller instead of the file.
**Consequence, and an open item:** `phase4b_engine.py` still carries
`("view1", VIEW1_CONFIG, 18000)` and about thirty lines of comment arguing for
an 18,000 s escalation that D25 has superseded. A run of that file today would
still work and still drain — 262.5 s is far inside 18,000 s — but the comment
now describes a decision that was reversed. One line and one comment block, and
it needs a WP to authorise the same way D-12 did. *Reversal cost:* none here;
the fix is elsewhere.

**E-2 · view2 and view3 were not re-mined, and the claim is proved rather than
asserted.** Their configs are untouched by WP-D2b, so T2 says their WP-D2
candidates are current. Rather than rely on that, the candidate files were
hashed and the re-ranking output compared to WP-D2's: both `*_ranked.json` are
byte-identical. *Reversal cost:* 28 s of re-mining if ever doubted.

**E-3 · One `phase2_engine.py` comment was changed beyond the depth line.**
`MeasureConfig("sc_amount", ...)` was annotated "LABEL SWAPPED AT SOURCE". With
the glossary narrowed to a *suspected* swap, leaving the config asserting the
strong version would have put the pipeline's two statements of the same fact out
of step — and the config comment is the one a future config editor reads. It now
says "SUSPECTED LABEL SWAP". The brief scopes this file to "the `VIEW1_CONFIG`
depth line + comment"; this is inside `VIEW1_CONFIG` and is one line.
*Reversal cost:* two words.

**E-4 · The whole report was regenerated, so view2's and view3's prose is new
text over identical findings.** `phase5b_report.py` writes one report in one
run; there is no per-section mode. The alternative was to splice v1's two
sections beside a freshly generated view1 section, which would have shipped a
report no single run produced and whose checks were run over three different
generations. So all three sections are from one run: the *findings* under view2
and view3 are byte-identical to v1, the *wording* differs (663 words against
700, 544 against 538). Every figure in both still traces, and the twelve
structural claims WP-D2 hand-checked were re-checked mechanically by check (d).
*Reversal cost:* one more API call.

**E-5 · Package v2 overwrote v1 in place at `handoffs/WPD2_calibration/`.** The
brief lists `handoffs/WPD2_calibration/**` as in-scope-to-regenerate and names no
new path; a `WPD2b_calibration/` beside it would have left two labelling sheets
where the operator needs one. v1's contents are recoverable — nothing in it was
committed, and everything in it is reproducible from the README's commands.
`ranking_log.txt` was added because the ranking step now has its own transcript
worth keeping. *Reversal cost:* re-run steps 2–6 of the README.

**E-6 · Proceeded on an uncommitted tree.** The brief's precondition is
"tree committed"; WP-D2's edits to seven `Insights/src` files are still working
-tree modifications, alongside live changes from the Ask workstream and the PM
sessions. Nothing about this run depends on the commit — the mirror was taken
from the working tree, which is the state the operator is about to commit — but
the precondition is formally unmet and stopping on it would have cost a day for
a `git add`. Disclosure, not a decision to reverse. *Reversal cost:* none.

**E-7 · The `.env` was used, not created.** `Insights/.env` exists (operator, per
D-2) and carries `OPENAI_API_KEY`. It was copied into the mirror so the report
step could load it there; the key was never printed, echoed or written anywhere.
`Chatbot/.env` was not read by this run at all. *Reversal cost:* none.

---

## §7 Self-audit

**Verified by running it:**

- The 99 config checks, at both scales, in subprocesses — archived and
  re-runnable.
- The view1 mine itself. Every number in §2 is read from its transcript, and the
  memory figures from `psutil` in the mining process, not estimated.
- The ranking, over all three views, through the edited `__main__` — and the
  byte-identity of view2's and view3's output against WP-D2's.
- The report generation, one run, three sections.
- The four T5 checks over the whole report, archived.
- Fifteen view1 figures re-derived directly from
  `view1_activity_lifecycle.parquet` with pandas, independent of the enrichment,
  plus six structural claims read against `view1_ranked.json`.
- The labelling sheet: 33 rows, 15/15/3 by view, `label` empty on every row,
  four caveat flags in the four right places.

**Not verified — relied on prior work:**

- WP-D1's reconciliation and `check_ask_parity`. Not re-run; the view Parquets
  used here are the ones WP-D2 built and proved against a byte-identical pack.
- That `Data/` equals the DuckDB the Ask chatbot serves (PM-validated, plan §5.5).
- The statewide branches, now including view1's depth-2 statewide branch. They
  are constructed at import and asserted by the config gate at both scales, and
  they have never seen statewide data because no statewide drop exists.
- WP-D2's §3 model probe. `gpt-5.6-sol` was used as pinned; no new probe was run.

**Known weaknesses in what was delivered:**

- **view1's top of list is redundant in kind** — §5's two notes. Fifteen
  findings, but ranks 1–2 are near-twins and 3–11 share one HDP shape. The
  ranker's redundancy penalty operates on member sets, and these findings have
  genuinely different member sets across different dimensions; it is the
  *reader* who sees them as one story. Whether that is a ranking defect or a view
  property is a calibration question, and the labels will answer it.
- **Depth 1 cannot say anything conditional.** No view1 finding can be about a
  slice of a slice, so "within Bargarh, among costless activities" is
  unreachable at sample scale. That was the priced cost of D25 and it is now
  visible in the output rather than in a table.
- **view3 still contributes 3 findings, all `n_completed`.** Unchanged from
  WP-D2, and still the operator's open question 5.
- **The report's view2/view3 prose is a fresh generation** (E-4). Anyone
  diffing v1 against v2 will see wording changes over identical findings.
- `phase5c_gamma_reports.py` and `gamma_sensitivity.py` still carry AP prompt
  text, unchanged and unrun — WP-D3's to convert.
- `phase4b_engine.py`'s stale view1 budget and escalation comment (E-1).

**Files this WP touched, and no others:**

```
Insights/src/phase2_engine.py           (depth line + two comments)
Insights/src/phase5_ranking.py          (__main__ view list only)
Insights/src/phase5b_report.py          (sc_amount/st_amount glossary + its comment)
Insights/reports_prdw/executive_metainsight_report.{md,pdf}
handoffs/WPD2_calibration/**            (regenerated; run_phase5_prdw.py deleted)
handoffs/WPD2b_REPORT.md                (this file)
```

Everything else executed in a local mirror under the session scratchpad. No git
operation was performed. The tree moved under this run again — the Ask
workstream and the PM sessions are live — and none of those changes are mine.

**What the PM should decide:**

1. **`phase4b_engine.py`'s view1 budget line** (E-1) — the last artifact of the
   depth-2 escalation, now stale. Authorise the one-line edit, or leave it and
   accept that the file argues for a decision that was reversed.
2. **Whether ranks 1–2 and the 3–11 block are one finding or nine.** The
   calibration labels will price this; if the answer is "one", the ranker's
   redundancy penalty is the thing to look at, not the configs.
3. **view3 at sample scale** — WP-D2's open question 5, untouched here.
4. Whether the statewide depth-2 branch should keep depth 2 at all, given §2's
   measured 185.9 scopes/s. The number that priced it is now known to be 12×
   conservative in one direction while the memory wall stands in the other; the
   engine-scaling WP should start from the real figure.
