# WP-D2 report — mining configs, prose model, first Discover run

Executing `handoffs/WPD2_mining_calibration.md` (Discover workstream).
Run date **2026-08-14**. No git operation performed — staging and committing are
the operator's.

**Headline:** T1, T2 and T4 are complete and verified. T3 drained two of the
three views and **view1 did not drain — it cannot, at its shipped width, on this
machine.** That is the brief's own escalation condition, it is measured rather
than estimated, and §2 gives the operator the numbers to decide what to do about
it. T5 and T6 were delivered over the views that did drain: the executive report
is written, its determinism checks are green on every section it contains, and
the calibration package is ready for 18 findings instead of the ~45 the brief
anticipated.

---

## §0 Gate self-assessment

| # | Gate item | Verdict | Evidence |
|---|---|---|---|
| 1 | Three configs live; imports clean; `DISCOVER_SCALE` works; AP configs gone | **PASS** | `verify_configs_prdw.py`: **99 checks, 0 failures** (`WPD2_calibration/verify_configs_output.txt`). Nine modules import; every registry holds exactly three views; no `VIEW4..9_CONFIG` survives anywhere |
| 2 | Mining drains on all three views; drain times reported | **FAIL (view1)** | view2 **21.6 s** of a 300 s budget; view3 **6.2 s** of 120 s — both drained. view1 reached 15,000 of **880,752** scopes in 585.6 s and was stopped. §2 |
| 3 | Model pinned to the verified GPT-5.6 id; budget probe evidence recorded | **PASS** | §3. Pinned `gpt-5.6-sol`, verified against the live model list; probe evidence for all three 5.6 ids in `model_probe_results.json` |
| 4 | Executive report: prose gate green, zero hollow sections, caveat check green, spot-checked claims trace | **PASS on what was written; FAIL structurally** | §4. Zero prose-gate problems in either section written; zero hollow sections; the FY 2023-24 caveat scope is exact in both directions; **37/37** quoted figures and 12 hand-checked structural claims trace. The gate's only complaint is that view1's section is missing — which is item 2, not a prose defect |
| 5 | Calibration package delivered | **PASS (reduced scope)** | `handoffs/WPD2_calibration/` — 18 findings across two views, with a labelling sheet, per-view read-ups, the report, the dashboard and the run transcript |

The **workstream** gate ("no nonsense findings in top ranks") is untouched by
this report: it closes on the operator's labels, not here.

**Preconditions.** All five hold. `Insights/domain_pack_prdw/` was committed as
`62ea264` ("WP-D1 done… gate green (D23)") at 11:30 today, and the pack the build
actually read is **byte-identical to HEAD** (SHA-256 across all ten pack files, 0
differing). The `--strict` build was replayed from that pack on a local mirror:
**exit 0, 0 failed checks, 51.3 s, 12,704 / 1,440 / 120 rows**. Every
`⟦PENDING-WPD1⟧` slot in the brief is filled. No `.env` exists where Discover
looks for one — see D-2. No other agent was live on the *engine* tree, though the
tree did move under this run (§7).

---

## §1 Configs and the scale switch

### The three configs

| | view1 `Activity Lifecycle` | view2 `Geo-Month Cash Cube` | view3 `GP Performance` |
|---|---|---|---|
| rows × cols | 12,704 × 70 | 1,440 × 17 | 120 × 26 |
| dimensions (sample) | 17 | 4 | 3 |
| temporal dimensions | **0** | 3 (month, quarter, fiscal_year) | 1 (fiscal_year) |
| measures | 24, all SUM | 7, all SUM | 18, all SUM |
| impact measures | n_activities, total_cost | payment_amount, payment_count | n_activities, expenditure_total |
| depth | 2 | 1 | 1 sample / 2 statewide |
| `extremum_ratio` | 0.67 (default) | 0.67 | 0.67 |

Written exactly as the brief's T1 table specifies. Four properties were checked
mechanically rather than by eye, because each is a silent-failure risk:

- **Every named column exists verbatim** in the built Parquets — 41 for view1, 13
  for view2, 22 for view3, **0 missing**. WP-D1 §8's "there are no renames" is
  confirmed against the files, not taken on trust.
- **No LGD code column is a dimension.** The views carry six of them for the
  frontend contract; a code and its name are the same dimension, so mining both
  would find every geographic pattern twice and rank the duplicate beside the
  original.
- **Every measure is SUM** and `extremum_ratio` is left at the 0.67 default. AP
  raised every view to 0.80 because its findings were proportional; every PR&DW
  measure in v1 is volumetric, so the looser bar would buy nothing and would
  lower the evidence standard.
- **Every dimension and measure has a glossary entry and a unit** — see §4.

`VIEW4..9_CONFIG` are deleted. Import sites fixed: `phase4a_engine`,
`phase4b_engine`, `phase5b_report`, `phase5b_dual_reports`, `phase5c_global_feed`.
`phase5c_gamma_reports` discovers configs by reflection and picked up the change
with no edit.

### The switch

One module-level flag, defined next to `VIEW1_CONFIG` in `phase2_engine.py` and
imported by `phase4a_engine`, in the `_DB_SOURCES` shape the Ask adapter uses:

```python
DISCOVER_SCALE = os.getenv("DISCOVER_SCALE", "sample")
_STATEWIDE = DISCOVER_SCALE == "statewide"
```

`DISCOVER_SCALE=statewide python src/phase4b_engine.py` changes **only** the
dimension lists and view3's depth:

| | sample | statewide | §6 reason |
|---|---|---|---|
| view1 dims | gp, block, district + 14 categoricals | **district** + the same 14 | 6,800 GP and 314 block values put every depth-2 GP subspace below the 1% impact prune |
| view2 dims | gp, block, district, fiscal_year | **district, block**, fiscal_year | GP stays the grain; exceptions still name GPs |
| view3 dims | gp, block, district | **district, block** | as view2 |
| view3 depth | 1 | **2** | ~41k rows across 30 districts make a two-filter subspace both populated and specific |

Verified by running both scales in subprocesses and diffing every field:
temporal dimensions, measures, impact measures, `tau`, `min_impact`,
`min_hdp_size` and `extremum_ratio` are **identical** under both, so a finding
that survives the switch is the same kind of finding. The statewide branches
ship untested — no statewide drop exists — and each carries its §6 rationale in
place.

---

## §2 Mining diagnostics — and the view1 escalation

### The two views that drained

| | view2 | view3 |
|---|---|---|
| budget | 300 s | 120 s |
| **drain time** | **21.6 s** | **6.2 s** |
| subspaces enumerated → kept after the 1% prune | 52 → 52 | 46 → 46 |
| data scopes evaluated | 2,149 | 2,502 |
| patterns found | 1,613 | 618 |
| HDPs evaluated / skipped by dedup | 1,845 / 3,116 (62.8%) | 430 / 876 (67.1%) |
| **candidates** | **110** | **5** |
| query / pattern cache hit rate | 96.8% / 48.0% | 96.5% / 23.1% |
| top score | 0.7211 | 0.6598 |
| ranked (top-15) | **15** | **3** |

Both drained well inside budget, so both are scoreable. `run_engine` leaves its
loop only when the queue is empty or the budget is gone; an elapsed time far
under the budget **is** the drain proof.

**view3 returning 5 candidates is a result, not a fault.** 120 rows, three
geography dimensions at depth 1 and one temporal breakdown do not offer many
HDPs of at least three members, and the greedy ranker then drops two of the five
as redundant. Statewide — depth 2 over ~41k rows — is a different view
arithmetically. Worth the operator's eye at calibration: **view3 as configured
for the sample can only ever say a few things, and all three of the things it
says are about `n_completed`**, the most degenerate measure in the drop (17
completions sample-wide).

### view1 — the escalation

view1 **did not drain and cannot**, and the brief's ceiling is not close.

| | measured |
|---|---|
| subspaces enumerated | **13,495** (1 + 172 depth-1 + 13,322 depth-2) |
| surviving the 1% impact prune | **2,438** |
| **data scopes behind them** | **880,752** |
| evaluated before the run was stopped | 15,000 (**1.7%**), in 585.6 s |
| throughput, first 5,000 scopes | 15.0 scopes/s |
| throughput, scopes 5,000–10,000 | 68.0 scopes/s |
| throughput, scopes 10,000–15,000 | 28.1 scopes/s |
| **cumulative throughput** | **25.6 scopes/s** |
| implied full drain | **≈ 34,400 s ≈ 9.6 hours** (16.4 h at the opening rate) |
| what the brief's 1,800 s ceiling buys | ≈ 46,000 scopes — **5% of the queue** |
| what the raised 18,000 s budget buys | ≈ 460,000 scopes — **52% of the queue** |
| process memory at 1.7% of the queue | **3.94 GB** private, with **0.38 GB** of the machine's 15.7 GB free |

Two independent walls, not one:

1. **Time.** Even at the best rate observed, the queue is a working day long.
2. **Memory.** `QueryCache` and `PatternCache` never evict — by design, and it is
   why the cache hit rates are 96%+ — so memory grows with scopes evaluated. At
   **1.7%** of the queue the machine was already out of free physical memory. The
   run would thrash long before it finished, and the 14,172 candidates it had
   already accumulated at that point project to a candidate file nothing
   downstream is sized for.

**What was NOT done, deliberately.** The configs were not trimmed. The brief is
explicit that which dimensions or measures view1 can afford to lose is a
calibration decision (T1 trap, escalation protocol), and trimming to force a
drain is exactly how a view quietly stops being able to find things. The budget
was raised from 900 s to 18,000 s **to measure rather than guess**, and the run
was then stopped on the measurement rather than left to burn nine hours to a
predictable end. No `view1_candidates.json` exists, because a truncated queue is
the one unscoreable failure.

### Input for the operator's trim decision

Measured against the same Parquet, at the run's own **conservative** 15.0
scopes/s. Nothing below is a recommendation; each row is a price tag.

| variant | dims | meas | depth | subspaces kept | data scopes | implied drain |
|---|---|---|---|---|---|---|
| **as shipped** | 17 | 24 | 2 | 2,438 | 880,752 | 16.4 h |
| **depth 1 only** | 17 | 24 | **1** | **127** | **48,792** | **0.9 h** |
| drop gp_name | 16 | 24 | 2 | 1,928 | 650,400 | 12.1 h |
| drop gp_name + block_name (= the statewide list) | 15 | 24 | 2 | 1,467 | 459,912 | 8.5 h |
| drop focus_area_name (30 values) | 16 | 24 | 2 | 2,016 | 680,016 | 12.6 h |
| drop asset_category_label (28 values) | 16 | 24 | 2 | 2,074 | 699,552 | 13.0 h |
| drop the 4 sanction-subset dims | 13 | 24 | 2 | 1,960 | 520,224 | 9.7 h |
| drop the 8 status flags | 17 | 16 | 2 | 2,438 | 587,168 | 10.9 h |
| drop the 5 thin measures | 17 | 19 | 2 | 2,438 | 697,262 | 13.0 h |
| gp + block out **and** depth 1 | 15 | 24 | 1 | 91 | 30,600 | 0.6 h |
| gp + block out **and** the 8 flags out | 15 | 16 | 2 | 1,467 | 306,608 | 5.7 h |
| gp out, flags out, thin out | 16 | 11 | 2 | 1,928 | 298,100 | 5.5 h |

The shape of that table is the finding: **depth is the only knob with an order
of magnitude in it.** Dropping a whole dimension buys 20–25%; dropping a third of
the measures buys a third; dropping the subspace depth from 2 to 1 buys **18×**,
because depth-2 subspaces are 13,322 of the 13,495 enumerated. What depth 1
costs is the ability to say "within Bargarh district, among costless
activities…" — every two-filter slice. That is a real loss and it is the
operator's to price, not mine.

A second observation the session may want: the 1% impact prune keeps 2,438 of
13,495 subspaces. A higher `min_impact` would cut the queue further while
changing what counts as a finding rather than what the engine looks at — a
different kind of decision from trimming, and one this brief does not authorise
either.

---

## §3 Model pin and budget probe (T4)

**The live model list had a surprise in it.** Verified against
`client.models.list()` on 2026-08-14: **there is no `gpt-5.6`.** GPT-5.6 ships as
three ids — `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra` — created within
eleven minutes of each other and carrying no distinguishing metadata beyond the
name (`owned_by: system`, no `shutdown_date`). The brief expects one id; the API
offers three; so the pin was made on the probe rather than on the name.

One representative phase5b prompt (view2, 15 ranked findings, **9,049 prompt
tokens**), sent once to each id at `DISCOVER_MAX_COMPLETION_TOKENS = 9000`:

| model | finish_reason | reasoning tokens | visible tokens | headroom | words | empty? |
|---|---|---|---|---|---|---|
| `gpt-5.6-luna` | `stop` | 1,024 | 987 | 6,989 | 650 | no |
| **`gpt-5.6-sol`** | `stop` | 1,565 | 1,057 | **6,378** | 677 | no |
| `gpt-5.6-terra` | `stop` | 512 | 1,007 | 7,481 | 685 | no |

**The budget is re-verified and NOT raised.** The worst case of the three left
6,378 of 9,000 tokens unspent. The gpt-5.5 incident — 2,000 tokens of budget, all
of it reasoning, `finish_reason='length'`, empty string, nine blank sections —
cannot recur at this margin, and `_require_content` would crash loudly if it
somehow did.

**Why `sol`.** Budget safety does not separate them, so the prose did. All three
were read in full against the section's own rules:

- `terra` **misattributed the headline figure**: "across those five years, it
  recorded 2,135 vouchers" — 2,135 is the six-year total, and the enrichment's
  `top_values` are computed over the finding's base subspace, which is the whole
  view. A number that is right attached to a scope that is wrong is the failure
  mode this deployment's number-formatting discipline exists to prevent.
- `sol` scoped that same figure correctly **and** was the only one of the three to
  apply the recorded-zero rule unprompted: *"the data cannot establish whether no
  linked expenditure occurred or whether it was not entered as linked
  expenditure."*
- `luna` was correct but thinner, and did not make the zero distinction.

`DISCOVER_PROSE_MODEL` defaults to `gpt-5.6-sol`; the operator can flip to either
sibling with the env var, with no code change and nothing upstream to re-run. The
full evidence is in `WPD2_calibration/model_probe_results.json`, and the reasoning
is written into `discover_config.py` beside the pin so the next model swap starts
from it.

**No API call was made before this point.** T1–T3 make none.

---

## §4 Report checks (T5)

Report: `Insights/reports_prdw/executive_metainsight_report.md` (+ `.pdf`).
Checks: `WPD2_calibration/check_report_prdw.py`, output archived beside it.

**(a) Prose gate — zero prose problems.** `src/prose_gate.py` runs unmodified.
It reports exactly one problem, and it is not about prose: *"[Activity
Lifecycle …] section is missing from the report, so its reading note is missing
too."* That is the gate correctly noticing §2's escalation. In both sections that
were written there are **no** vocabulary violations and **no** rival
methodology blocks, and each carries exactly one deterministic reading note.

Vocabulary was given real content for this deployment rather than inherited. The
distinction that matters here is money basis: view2's `payment_amount` is Rs
68.58 crore of cashbook outflow, view1's `total_expenditure` is Rs 25.35 crore of
voucher-linked spending on planned activities, and describing the first as
spending on works overstates work spending nearly threefold. So view2 may not
borrow view1's words (`work completed`, `abandoned`, `geotagged`, `overspend`,
`action plan`, `planned cost`, `costless`), view1 may not borrow view2's
(`receipts`, `cashbook`, `inflows`, `monthly`, `seasonality`), and view3 — which
legitimately holds both cash and activity measures — is denied only the month
axis it does not have.

**(b) No hollow sections.** Both sections carry real prose: **700 words**
(view2) and **538 words** (view3), against a 400–800 word instruction. Zero
blank sections. view1 has no section at all, which is loud rather than silent:
the generator prints a banner naming the omitted view, and the gate flags it.

**(c) The FY 2023-24 caveat is exact in both directions.**

| section | findings that qualify | caveat in the report? | correct? |
|---|---|---|---|
| Monthly Money Flows by Gram Panchayat | **none** | no | ✔ |
| Gram Panchayat Report Card by Year | **#1 and #2** | yes | ✔ |

The test is deterministic, runs before the model sees anything, and requires all
three of: a view whose counts are activity counts (view1, view3 — view2 counts
vouchers and sanctions and is artifact-free); a measure whose UNIT is
`activities`, read off `_UNITS` rather than listed again, so a new measure cannot
be added to a config and silently escape it; and fiscal years actually being
**compared** across the boundary — a fiscal_year *filter* pins one year and makes
no comparison, so it does not qualify. Fourteen predicate cases are asserted in
`verify_configs_prdw.py`, including the four near-misses (rupee measure across
the boundary; activity count entirely after it; photo uploads, which are counted
on uploads not activities; fiscal_year as a filter).

Where it fires, the §5.2 sentence joins the section's existing reading note
rather than becoming a second blockquote — the prose gate expects exactly one
marker per section, and two callouts would read as two separate sets of
conditions where there is one. It is emitted verbatim and never written by the
model; the prompt separately tells the writer, on qualifying findings only, not
to present the jump as growth.

**(d) Every figure traces. 37 of 37.** Not a spot check: every numeric token in
both sections was extracted and matched against the union of every string the
enrichment rendered, every number the view's own description, glossary and
reading note state as fact, and the HDP member and commonness counts. Nothing
untraced.

Twelve structural claims were then checked by hand against
`layer3p_ranked_dashboard.txt`, because a figure can be real and its sentence
still wrong:

| claim in the prose | finding | verdict |
|---|---|---|
| "17 of the 20 Gram Panchayats" | view3 #1, 17/20 | ✔ |
| "Dutimendi, Andhrua and Kalimela" | view3 #1 exceptions | ✔ |
| "13 of the 16 blocks" | view3 #2, 13/16 | ✔ |
| "Khajuripada, Bhubaneswar and Kalimela" | view3 #2 exceptions | ✔ |
| "10 of the 18 report-card measures … within Bargarh" | view3 #3, 10/18, subspace `district_name:Bargarh` | ✔ |
| "n_plans, sanctioned amount and completed activities show no clear pattern" | view3 #3 NO_PATTERN exceptions | ✔ |
| "2,135 vouchers, or 25.0% of the total 8,529" | view2 #2 stats; re-derived from the Parquet | ✔ |
| "Rangeilunda 945, 11.1%; Bheden 885, 10.4%" | view2 #2 `top_values` | ✔ |
| "leader in five of the six fiscal years; 2024-2025 the exception" | view2 #2, 5/6 | ✔ |
| "increased in Khordha, Sundargarh, Malkangiri, Rayagada, Ganjam, Kandhamal; Bargarh, Cuttack, Koraput differ" | view2 #4, 6/9 + 3 TYPE_CHANGE | ✔ |
| "9 blocks increasing; Barpali, Bheden, Baranga, Attabira, Rangeilunda, Boipariguda, Tangi Choudwar differ" | view2 #11, 9/16 + 7 exceptions | ✔ |
| "Ganjam shifts at August 2020; sanctions October 2020; activity-linked expenditure November 2020" | view2 #13, CHANGE_POINT 2020-08 with two HIGHLIGHT_CHANGE exceptions | ✔ |

**One expected-by-design entry showed up on its own.** The brief listed
completion-measure degeneracy as something the calibration session should test;
view3's top two findings are both `n_completed` trends, and the report leads with
them — while stating unprompted that "only 17 activities were recorded as
completed", that "these are absolute counts, not completion rates", and that a
recorded zero leaves two readings open. The March year-end spike also surfaced,
in the view2 section and in its reading note. Both are for the operator to label
`already-known`.

---

## §5 Calibration package

`handoffs/WPD2_calibration/` — **18 findings** (view2 15, view3 3).

| file | what it is |
|---|---|
| `labeling_sheet.csv` | the sheet to fill in: one row per finding, with summary, figures, commonness, exceptions, score components and an `fy_2023_24_caveat` flag. `label` and `operator_notes` are empty |
| `findings_view2.md`, `findings_view3.md` | the same findings laid out to read |
| `layer3p_ranked_dashboard.txt`, `layer2p_raw_explorer.txt` | the engine's own dashboards — the audit trail behind every row, and the pool the ranker rejected |
| `mining_log.txt` | the run transcript, including the view1 escalation as it happened |
| `verify_configs_prdw.py` + output | the 99-check T1/T2 gate, re-runnable |
| `check_report_prdw.py` + output | the four T5 checks, re-runnable |
| `run_phase5_prdw.py` | the ranking driver (see D-12) |
| `build_labeling_sheet.py` | rebuilds the sheet after any re-run |
| `model_probe_results.json` | §3's probe evidence |
| `README.md` | how to use it, what to expect, and every re-run command |

The report itself is at `Insights/reports_prdw/executive_metainsight_report.md`,
beside WP-D1's validation reports, where `phase5b_report.py` now writes it.

Labelling needs no code: open the CSV, read the summary, type `real`,
`already-known` or `spurious`. The README names the three known-by-design
patterns to expect and the one spurious class to watch for (a total broken down
by place ranks places by size — the enrichment now sends each place's share of
the view's volume alongside the total, and the prompt carries a rule against
writing those as delivery gaps, but the finding is still in the sheet and
whether it earns a slot is the operator's call).

---

## §6 Decision journal

Everything here was decide-and-document unless marked otherwise.

**D-1 · Proceeded on a precondition that became true mid-run.**
At the start of this run the WP-D1 pack was uncommitted, which the brief's first
precondition requires. It was committed as `62ea264` at 11:30 while this work was
in progress, and the pack the build read is byte-identical to HEAD across all ten
files. Rather than rely on either fact, the `--strict` build was replayed from
the pack and produced 12,704 / 1,440 / 120 with 0 failed checks. *Reversal cost:*
none; this is a disclosure.

**D-2 · The OpenAI key was read from `Chatbot/.env`, and no `.env` was written.**
`phase5b_report` loads `Insights/.env`; `phase5b_dual_reports` loads the repo
root's. **Neither exists.** The repo's only OpenAI key is `Chatbot/.env`, which
belongs to the Ask workstream and is on the brief's DO-NOT-TOUCH list. Creating
`Insights/.env` would have meant creating a `.env`, also out of scope. So T4 and
T5 loaded that file's key into the process environment at run time and wrote
nothing; the key was never printed, echoed or copied. **This is an open item for
the operator:** either place an `.env` at `Insights/` or accept that the Discover
entry points do not find a key on their own. *Reversal cost:* one file.

**D-3 · The phase5b edit widened from "VIEW_DESCRIPTIONS + VIEW_CONFIGS" to the
whole prompt path.**
The brief scopes `phase5b_report.py` to those two objects, but T2's done-when is
"no AP string survives anywhere in the prompt path" — and the AP strings were in
the prompt bodies, the unit formatters, the reading notes, the vocabulary rules
and the report header, not in `VIEW_DESCRIPTIONS`. The narrow reading cannot
satisfy the stated gate. The wider reading was taken and is verified by check 6
of `verify_configs_prdw.py`, which greps the file *and* a built prompt for
seventeen AP/UP tokens. *Reversal cost:* the file's previous state is one `git
checkout` away.

**D-4 · The `sc_amount` / `st_amount` glossary was corrected, against
"transcribe verbatim".**
The brief says Appendix A's five measured-content patches from WP-D1 §8 are
already applied. WP-D1 §8 lists **six**, numbered 0–5, and it is item **0** that
is missing: `sc_amount` and `st_amount` are **swapped at source** on all 21
affected activities, verified there against three corroborating tables. Appendix
A says only that the components are near-empty and that "a near-zero here is data
coverage, not a finding" — which is not enough, because it is the *non-zero*
values that are on the wrong label. WP-D1 called this "the one glossary line
where the current wording could produce a confidently wrong equity statement".
Transcribing it verbatim would have shipped that risk knowingly, so the entry now
states the swap and forbids any SC-versus-ST comparison from those two columns.
Everything else in Appendix A is transcribed as written. *Reversal cost:* two
glossary entries.

**D-5 · Appendix A's grouped glossary keys were split, one key per column.**
Appendix A groups siblings under one heading (`gp_name / block_name /
district_name`). Each column now has its own key sharing a constant, so "every
config column has a glossary entry" is a check a script runs rather than a claim
a reader trusts. No wording changed beyond naming the column each sentence is
about. *Reversal cost:* cosmetic.

**D-6 · The AP roster-share machinery was re-pointed, not deleted.**
`POPULATION_SHARE_RULE` is imported by `phase5c_gamma_reports`, and its own
comment says a rule naming a key the enrichment does not emit is worse than no
rule. The AP block computed each social category's share of the PM-KISAN roster;
PR&DW has no roster and no demographic dimension, so it would have been dead
weight injecting PM-KISAN prose into every prompt. It now computes the same
shape — each place's share of the view's own volume (`n_activities` for view1 and
view3, `payment_count` for view2) for a **geography** breakdown of a SUM — under
`stats.size_share`, with rule 2b rewritten as "size is not performance". Same
mechanism, same failure it guards against, this domain's denominator. *Reversal
cost:* one function and one rule string.

**D-7 · The §5.2 caveat joins the existing reading note rather than becoming a
second blockquote.**
`prose_gate.check_reading_note` expects exactly one `READING_NOTE_MARKER` per
section and `prose_gate.py` is DO-NOT-TOUCH, so a second deterministic callout
would fail the gate. All three views now carry a static reading note (each has
something the reader must be told), and the caveat sentence is appended to the
view's note when any finding in that section qualifies. *Reversal cost:* one
branch in `reading_note_block`.

**D-8 · view1's budget was raised to 18,000 s to measure, then the run was
stopped on the measurement.**
The brief's starting budget is 900 s and its escalation ceiling 1,800 s. A
pre-flight said the queue was 880,752 scopes, which 900 s could not touch — but
the pre-flight measured pattern detection only (150 scopes/s) and the real loop
was ten times slower once HDP evaluation was included. Raising the budget was the
only way to measure the real rate rather than argue about a projection. Once
three segments of real throughput existed and memory had reached 3.94 GB at 1.7%
of the queue, the run was stopped: nine more hours would have produced a number
already known. §2 has everything. *Reversal cost:* one integer; the file records
the measurement as the reason.

**D-9 · The run list runs the cheap views first.**
`ALL_CONFIGS` is ordered view2, view3, view1. The two small views drain in under
half a minute between them, which proves the ranking and the report's prompt path
on real candidates before hours are committed to the wide one — and their
candidate files survive an interrupted run. *Reversal cost:* reorder three
tuples.

**D-10 · `phase5b_report` tolerates a view with no ranked findings — loudly.**
It previously assumed every registered view had a ranked file and would have
crashed with `FileNotFoundError`. It now skips such a view, prints a banner
naming it, and leaves the prose gate to flag the missing section. Silence was the
alternative and silence is what the hollow-report incident was made of. *Reversal
cost:* two guards.

**D-11 · `gpt-5.6-sol` pinned among three ids.** §3. *Reversal cost:* an env var.

**D-12 · `phase5_ranking.py` was not edited; a driver ships instead.**
Its `__main__` still lists nine views. The file is in the brief's DO-NOT-TOUCH
list ("ranking in phase5") and not in the writable set, so
`WPD2_calibration/run_phase5_prdw.py` calls the same `prefilter_candidates`,
`rank_metainsights` and report generators over the three views that exist.
Nothing about the ranking differs. **This is the last stale nine-view list in the
pipeline** and the fix is deleting six entries from one list; it needs a WP to
authorise it. *Reversal cost:* delete the driver once the list is fixed.

**D-13 · `phase5c_global_feed.LINEAGE` was emptied rather than left as AP's.**
That file is WP-D3's. Its two view registries were updated as the brief allows,
but its lineage map named AP columns (`cropnameeng`, `ekyc_status`,
`benefit_amount`), none of which exists in a PR&DW view. A stale entry that
happened to collide with a PR&DW column name would merge two unrelated findings;
an empty map makes `_lineage` return each column unchanged, so dedup can only
miss a merge, which is the safe failure. The coverage-weight block is untouched
and marked: it weights views by distinct PM-KISAN farmers over CSVs this
deployment does not have, PR&DW has no beneficiary identity anywhere in its drop
(§4.4), so its weighting must be **designed** by WP-D3, not translated. Until
then no global feed is produced and `phase5b_report` writes the per-view sections
only, which is its documented no-feed path. *Reversal cost:* `git checkout`.

**D-14 · The calibration package lives at `handoffs/WPD2_calibration/`.**
T6 requires the artifact and the brief names no path. It sits beside this report,
is self-contained, and can be deleted in one move. *Reversal cost:* none.

**D-15 · `n_completed` qualifies for the §5.2 caveat — faithful to the spec, and
arguably wider than the artifact.**
The mapping doc says "a count-based measure" and the brief says "activity-count
measure"; `n_completed` is both, so it qualifies, and view3's top two findings
carry the caveat. But the artifact itself is that **costless** activities begin
being recorded in 2023-24, and a costless training or campaign is not a work that
gets marked WORK COMPLETED — so the completion series is affected by the
denominator changing, not by inflation of the count. The narrower reading would
restrict the caveat to `n_activities`, `n_costed` and `n_costless`. The spec's
reading is implemented; the narrower one is a one-line change to
`activity_count_measures`. **Flagged for the operator, not decided.**

---

## §7 Self-audit

**Verified by running it:**

- The `--strict` pack build on the local mirror: exit 0, 0 failed checks, 51.3 s,
  12,704 / 1,440 / 120 — and the pack was proved byte-identical to the committed
  one first (SHA-256, ten files, 0 differing).
- Every column named by every config, against the built Parquets: 0 missing
  across all three views.
- The 99 T1/T2 checks, archived as output, re-runnable by the operator.
- Both scales of `DISCOVER_SCALE`, in separate processes, field by field.
- The mining run itself, and every number in §2 read from its transcript.
- The view1 sensitivity table — twelve hypothetical configs, each enumerated,
  pruned and counted against the real Parquet. **No config was changed to produce
  it.**
- All three GPT-5.6 ids, one real prompt each, usage figures recorded from the
  API response.
- The four T5 checks, plus twelve structural claims read by hand against the
  ranked dashboard, plus `2,135 / 8,529 / 25.0%` and `Rs 24.00 crore` re-derived
  directly from the Parquet rather than from the enrichment that produced them.

**Not verified — relied on prior work:**

- WP-D1's reconciliation and its `check_ask_parity` result. This WP re-ran the
  build, not the parity check.
- That `Data/` equals the DuckDB the Ask chatbot serves (PM-validated, plan §5.5).
- The statewide branches of the scale switch. No statewide drop exists; they are
  written, type-checked by being constructed at import, and untested against data.

**Known weaknesses in what was delivered:**

- **view1 is absent.** Two thirds of the mining the brief scoped did happen; the
  view carrying 12,704 activities and 24 measures did not. Everything downstream
  of it — its share of the calibration package, its report section, its
  contribution to whatever WP-D3's feed becomes — is deferred behind one decision
  that is not mine to take.
- **view3 contributes 3 findings, all about the same degenerate measure.** The
  package is thinner than "top-15 per view" implies, and honestly so.
- The FY 2023-24 caveat is applied at **section** granularity, because the report
  is prose and there is no per-paragraph anchor to attach a deterministic note
  to. The per-*finding* determination is exact and is carried into the prompt and
  into the labelling sheet; what the reader sees is one sentence in the section's
  note. D-15 is the related open question.
- `phase5c_gamma_reports.py` and `gamma_sensitivity.py` still contain AP prompt
  text. Neither is in this WP's writable set beyond registries, neither was run,
  and both are WP-D3's to convert. Anyone running a gamma edition before that
  happens will get Andhra Pradesh framing over Odisha findings.

**The tree moved under this run, again.** Besides `62ea264`, the working tree now
carries changes to `PROJECT_PLAN.md` and `handoffs/WP4_eval_run.md` and a new
`handoffs/WPD3_feed_editions.md`, none of them mine — the PM sessions are live.
Files this WP touched, and no others:
`Insights/src/{discover_config,phase2_engine,phase4a_engine,phase4b_engine,phase5b_report,phase5b_dual_reports,phase5c_global_feed}.py`,
`Insights/reports_prdw/executive_metainsight_report.{md,pdf}`,
`handoffs/WPD2_REPORT.md` and `handoffs/WPD2_calibration/**`.

**What the PM should decide:**

1. **view1's trim** — §2's table is the input. Depth is the only knob with an
   order of magnitude in it, and depth 1 costs every two-filter slice.
2. **D-15** — does the FY 2023-24 caveat belong on `n_completed`?
3. **D-2** — where the Discover workstream's `.env` should live.
4. **D-12** — authorising the six-line deletion in `phase5_ranking.py`'s
   `__main__` so the driver can be retired.
5. Whether **view3 at sample scale** earns its place in the calibration session
   at all, given that all three of its findings are about a measure with 17
   non-zero events in the entire drop.
