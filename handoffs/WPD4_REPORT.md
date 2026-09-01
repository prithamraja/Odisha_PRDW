# WP-D4 report — prose trial v2 (context-driven writer + safety net)

**Workstream:** Discover. **Nature: TRIAL.** No published artifact changed.
**Run:** 2026-08-31, against `master` at `586ce40`, candidate set
`a7f991c1df3771f9`. **Deliverable:** `Insights/prose_trial/REVIEW.md`.

**The one-line result.** The design works, and the thing that failed is the
safety net, not the writer. A writer given no rules at all — only the context
brief and deterministically computed figures — invented nothing across 15
findings and 181 numerals. The mechanical checks fired twice, both on a
fiscal year written `2024-25` instead of `2024-2025`. The AI verifier caught
three real drifts no mechanical check could see, and produced seven false
positives from a single flaw in its own prompt, which is what drove 8 of 15 to
fall back.

---

## §0 Gate table

| # | Gate | Status | Evidence |
|---|---|---|---|
| 1 | All 15 final renderings check-green or explicit fallbacks | **MET** | 7 check-green (2 first-pass + 5 regenerated), 8 explicit `FELL BACK`; §2 |
| 2 | Verifier verdicts logged with claim mappings/quotes, no vague verdicts | **MET** | 36 verdicts logged; 0 fail-to-verify; every pass carries a 4–13 entry claim map, every fail quotes the claim |
| 3 | Usage recorded, under cap | **MET** | 50 calls of 60; every call's `usage` in `logs/calls.jsonl`; §4 |
| 4 | `git status` shows exactly the writable set | **MET** | `?? Insights/prose_trial/` and this report; §7 |
| 5 | Operator labels each of the 15 | **OPEN — yours** | `Insights/prose_trial/REVIEW.md` has a label line per finding |

**Read gate 1 with §3 in hand.** It is met as written, but 7 of the 8 fallbacks
were caused by a defect in the verifier's prompt rather than by anything wrong
with the prose. The review document therefore shows, for every fallback, both
the fallback and the rendering that was produced, so the labelling exercise is
still about the writing.

---

## §1 What ran

**Preconditions.** 1 **failed at first**: the tree was dirty (`.gitignore`,
`deploy/RAILWAY.md`, `handoffs/PROJECT_PLAN.md` modified, the brief untracked —
all unrelated to WP-D4 and all outside the writable set). Per the escalation
protocol this was a STOP; it was escalated rather than worked around, the
operator committed (`586ce40`), and the run started from a clean tree.
2 (local-mirror execution) held throughout — see below. 3 **passed**: SHA-256 of
all six files in `Insights/metainsights/` match WPD3b §4 exactly, re-verified
after the commit. 4 **passed**: `Insights/.env` provides the key.

**Execution location (D6).** All Python ran in a local mirror,
`C:\dev\odisha-prose-trial`, never against the Drive path. Recipe step 1 was
re-run there to produce the parquet views the figure computation needs
(12,704 / 1,440 / 120 rows, 0 failed checks) — deliberately in the mirror,
because `Insights/views_prdw/` is **not** in this WP's writable set. `.env` was
**not** copied into the mirror; the key is loaded in place from the Drive path
at runtime (`llm.py:DRIVE_ENV`), which is also the direct guard against WPD3
§4.4's first bug.

**Models.**

| role | id | how chosen |
|---|---|---|
| writer | `gpt-5.6-sol` | the D17 pin, read from `discover_config.DISCOVER_PROSE_MODEL`, not hard-coded |
| verifier | `gpt-5.5` | a different model generation. Same vendor — a disclosed limitation: `Insights/.env` serves one vendor's key, and the brief permits same-vendor if disclosed |

Both ids were verified against the **live** model list before use, per D17.

**D17 budget check — evidence.** Run on the real 15-finding prompt rather than
a toy one, because reasoning cost scales with the prompt:

```
finish_reason  : stop
prompt_tokens  : 10,545      (est. 10,539; cap 16,000)
completion     : 2,971 of 8,000     visible text 8,455 chars
reasoning      : 1,024
headroom       : 5,029 of 8,000
```

Non-empty prose, `stop`, and wide headroom — so the T2 truncation trap never
triggered and **the batch was never split**. All 50 calls in the run returned
`finish_reason: stop`; no call approached the 16,000-token input ceiling
(max observed 10,539).

**Batch structure.** One writer call carrying Appendix A verbatim, a delimiting
instruction, and all 15 packets; 15 first-pass verifier calls; 13 single-finding
regenerations; 13 second-pass verifier calls; then 8 measurement calls (§3).

**T1 packets.** Built by reusing `phase5b_report.enrich_candidates_with_stats`
rather than reinventing the arithmetic, so every figure is the same number the
executive path would print, already rendered as a display string
(`Rs 42.61 lakh`, `62.1%`) — which is what makes the T3 substring matching
sound. Each figure carries a provenance string. Two packets are **thin**: ranks
2 and 9 have `breakdown = "(varies)"`, and the existing enrichment refuses to
aggregate across members measured on different scales. Per T1 they were marked
thin and no figures were improvised.

One deliberate exclusion: the enrichment also attaches `evenness_framing`,
`linkage_framing`, `earmark_framing` and `reporting_caveat`, which are
**imperative prompt rules** ("Lead with the magnitude from `stats.total`"). This
design forbids rules reaching the writer, so those keys are stripped. The
packets were scanned to confirm no rule text survived.

---

## §2 Results

| rank | packet | first-pass checks | final checks | verifier v1 | verifier v2 | status |
|---|---|---|---|---|---|---|
| 1 | | pass | pass | fail | pass | fell back |
| 2 | thin | pass | pass | pass | — | regenerated |
| 3 | | **FAIL (a)** | pass | fail | pass | fell back |
| 4 | | pass | pass | pass | — | regenerated |
| 5 | | pass | pass | pass | — | **first-pass** |
| 6 | | **FAIL (a)** | pass | fail | pass | fell back |
| 7 | | pass | pass | pass | — | regenerated |
| 8 | | pass | pass | fail | pass | fell back |
| 9 | thin | pass | pass | fail | **fail** | fell back |
| 10 | | pass | pass | fail | pass | fell back |
| 11 | | pass | pass | pass | — | regenerated |
| 12 | | pass | pass | pass | — | regenerated |
| 13 | | pass | pass | fail | pass | fell back |
| 14 | | pass | pass | pass | — | **first-pass** |
| 15 | | pass | pass | fail | pass | fell back |

First-pass rate 2/15; check-green after one regeneration 7/15; fell back 8/15.
Every fallback was driven by the verifier, never by the code checks — the code
checks passed on all 15 final renderings.

---

## §3 What each safety layer caught — the core question

The brief asks whether the verifier catches real drift the code checks miss.
**It does, and the drift is exactly the kind no mechanical check could reach.**
It also over-fires in one specific, fixable way.

### The code checks caught 2 of 28 renderings, both the same class

Both were a fiscal year written naturally instead of verbatim: finding 3 wrote
`2020-21` and `2025-26`, finding 6 wrote `2024-25`, where the packets carry
`2020-2021`, `2025-2026`, `2024-2025`. The numbers were **correct**; they were
not **identical**. Appendix A itself writes `2023-24`, so the writer was
following the context it was given.

Nothing else ever tripped them. Across 181 numerals in 28 renderings the writer
invented no figure, named no place outside its own finding, and emitted no
database token — no `overspend_vs_plan`, no `(varies)`, no `PERIOD_12`, no
pattern enum. The tight normalization held against its stated trap: `5,196`
does not match `51.96`, and `893` does not match inside `6,893`, because
numerals are compared as whole tokens, not substrings.

**Read that as a result about the packets, not about the model.** Handing the
writer display-formatted strings it can only copy removes the invention failure
mode almost entirely — which is why the layer that mattered was the other one.

### The verifier caught three real drifts the code could not see

None of the three changes a digit, so no numeral check could ever fire on them.

1. **Finding 3 — a limitation quietly narrowed.** The writer turned the
   background's *"sanction records exist for only about one **work** in six"*
   into *"sanction records exist for only about one **activity** in six"*.
   Verifier: *"The background says: 'Sanction records exist for only about one
   work in six'; it does not say one activity in six."* Same digits, different
   denominator — and works and activities are not the same population here.

2. **Finding 8 — a sample-wide total attached to a subset, and a lost scope.**
   The writer wrote *"Activities still marked 'Activity Approved' account for
   Rs 41.61 crore of the gap ... in 18 of the 20 sampled Gram Panchayats"*.
   Verifier: *"It does not say the Rs 41.61 crore figure is specifically for
   those 18 Gram Panchayats"*, and separately *"The source limits the finding to
   'Records covered: is_costless = Costed'. The writing does not state that the
   figure applies only to costed records."* Both numerals were legitimate; the
   attribution and the scope were not.

3. **Finding 9 — a claim about the analysis itself.** The writer asserted
   *"this analysis did not assess geographic differences"*. Nothing in the
   packet or background says that. This is the one verifier catch that survived
   the correction below, and it is a genuine catch.

### The verifier's own defect, measured rather than asserted

Under the brief's literal T4 wording the verifier failed 8 of 15. Reading the
flags, 7 of the 8 were **one repeated false positive**: it flagged the
*"what to check at the next review"* sentence as an unsupported claim — the very
sentence Appendix A instructs the writer to produce. Representative flags:

- finding 6: *"reviews should check whether staffing and reconciliation
  arrangements are adequate"* → *"it does not mention staffing or reconciliation
  arrangements or recommend..."*
- finding 10: *"Reviews should test whether work statuses are being updated
  promptly"* → *"it does not state that status updates may be delayed or that
  reviews should test prompt updating."*
- finding 13: *"Reviews should ask Boipariguda to complete theme mapping"* →
  *"It does not say reviews should ask Boipariguda to complete mapping."*

The cause is structural, not random. T4 specifies the verifier's inputs as the
packet plus *Appendix A's background*, so it sees the nine background bullets
but never the instruction that a recommendation is wanted. Background bullets
never "state" a recommendation, so every suggestion looked invented.

To measure the size of the class rather than argue about it, the 8 fallbacks
were re-verified with **one sentence added** to the verifier prompt, separating
a suggested action from a factual claim — while still failing any suggestion
that smuggles in a fact ("payments are missing"), and still failing any lost
limitation. Everything else was held identical: same model, same inputs, same
output shape, same no-rubber-stamp rule.

**Result: 7 of 8 passed. Only finding 9 — the genuine catch — still failed.**

That is the trial's most useful number. The verifier's *judgment* is sound; its
*brief* was wrong. `Insights/prose_trial/verify_v2.py` carries the corrected
wording and the reasoning, run as a measurement and **not** substituted for the
specified v1 run, whose verdicts stand in the record.

### The rubber-stamp guard held

T4's trap is a verifier that passes without doing the work. Passes here carry
4–13 mapped claims each, every one pointing at a specific packet line or
background bullet, and a pass with an empty or partial map is downgraded to
fail-to-verify in code (`verify.parse_verdict`). Across 36 verdicts there were
**0** fail-to-verify outcomes — the verifier never returned an unparseable or
vague answer.

---

## §4 Cost and usage

| purpose | calls | model |
|---|---:|---|
| writer batch (all 15) | 1 | `gpt-5.6-sol` |
| verifier (T4, both attempts) | 28 | `gpt-5.5` |
| regeneration (T5) | 13 | `gpt-5.6-sol` |
| verifier v2 (measurement, §3) | 8 | `gpt-5.5` |
| **total** | **50** | cap **60** |

Prompt tokens **81,471** · completion **47,503** (of which reasoning **33,550**)
· total **128,974**. Wall time ≈ 615 s across all calls.

Well inside the worst case the brief budgeted (~1.44M tokens): the actual run
used under 9% of it. No cap was reached, so no shortfall to report. The repo
records no token price anywhere, so cost is reported in tokens rather than
guessed in currency. Every call's full request, response, `finish_reason` and
`usage` is in `Insights/prose_trial/logs/calls.jsonl` (50 lines, 408 KB, scanned
clean of credentials).

---

## §5 Defects found in existing code — logged, not fixed

1. **`status_label` in view1 is contaminated with an asset category.** It holds
   six values, one of which is **`Buildings`** (13 rows), alongside
   `Activity Approved`, `WORK ONGOING`, `WORK ABANDONED`, `UNDER APPROVAL`,
   `WORK COMPLETED`. `Buildings` is an `asset_category_label` value. This means
   findings 8, 10 and 12 — all broken down by `status_label` — are computed over
   a dimension that mixes a status with an asset type, and the published feed
   sentences inherit it. Found because the verifier objected to the writer
   calling `Buildings` a status; the writer was reading the packet correctly and
   the packet was reading the view correctly. **Not fixed** (outside the
   writable set). Recommend tracing it in the view SQL before this feed is used
   for anything operational.

2. **Feed sentence 3 says "and 1 others".** `global_feed.json` rank 3 ends
   *"Ganjam (no clear pattern) and 1 others"* — ungrammatical, and it hides
   Rayagada's name behind a count. The packet carries the full exception list, so
   the trial's own renderings name all four; but the current feed text an officer
   sees today does not.

3. **`enrich_candidates_with_stats` returns instructions inside its data.**
   `stats` mixes computed figures with imperative prompt rules
   (`evenness_framing`, `linkage_framing`, `earmark_framing`,
   `reporting_caveat`). Any consumer that treats `stats` as facts — as this WP
   needed to — must know to strip them by name, and nothing marks them. Not a
   bug in the executive path, which wants both; a trap for every other caller.

4. **Two of the top 15 findings can carry no figures at all.** Ranks 2 and 9
   have `breakdown = "(varies)"`, so the enrichment declines to aggregate and
   the findings reach any reader — this trial or the executive report — with no
   numbers of their own. Correct behaviour, but worth knowing that 13% of the
   feed is structurally figure-less.

---

## §6 Decision journal

| # | Decision | Why |
|---|---|---|
| 1 | Dirty tree → **STOPPED and escalated** rather than working around it | Precondition 1 is an explicit STOP. The dirt was unrelated and benign, but "commit it myself" is a git write this WP is denied, and "proceed anyway" would have made gate 4 uncheckable. Operator committed `586ce40`; hashes re-verified after |
| 2 | Verifier = `gpt-5.5` | A different model generation from the writer. Same vendor, disclosed: the available key serves one vendor |
| 3 | Numerals compared as whole **tokens**, exact match | The stated trap. Substring matching would let `893` match inside `6,893`; comma-stripping would let `5,196` match `51.96` |
| 4 | The only normalization allowed: a trailing `.0` dropped (`100.0`→`100`) | Formatting-only, no digit changes. Rounding (`48.3`→`48`) is a different claim and is rejected |
| 5 | **Rejected** fiscal-year equivalence (`2024-25` ≡ `2024-2025`) | Loosening is what the trap warns against. It fired twice; §3 recommends adding it as the one normalization the evidence supports, but the run was not re-scored to make itself look better |
| 6 | Name check (b) via a **roster** built from the views' name columns | Generic proper-noun detection false-positives on "March", "Gram Panchayat", "Odisha". The roster asks the precise question: of the 217 real entity names, did any appear in a finding whose packet does not contain it |
| 7 | Detail-length tolerance 220 words for the brief's "~200" | "~" is approximate; the raw count is recorded either way. Max observed was 81, so the tolerance never mattered |
| 8 | `*_framing` / `*_caveat` keys stripped from packets | They are imperative writing rules, and this design's whole premise is that no rule constrains the writer |
| 9 | Verifier runs even when the code checks already failed | The trial's stated purpose is measuring what each layer catches; short-circuiting would have hidden the overlap |
| 10 | Verifier v2 run on the **8 fallbacks only**, not all 15 | 8 calls instead of 15+ answers §3's core question inside the remaining budget, and leaves the specified v1 run intact as the record |
| 11 | Mirror at `C:\dev\odisha-prose-trial`; views rebuilt there | D6 forbids running against the Drive path, and `Insights/views_prdw/` is outside this WP's writable set — the mirror satisfies both |
| 12 | `.env` never copied; key loaded in place from the Drive path | The brief forbids copying it, and WPD3 §4.4's first bug was exactly a wrong `.env` path failing silently |
| 13 | Batch not split | The budget check showed 5,029 tokens of headroom and `finish_reason: stop`; splitting would have spent calls to fix a problem that did not exist |

---

## §7 Self-audit

**Files written — matches the allowlist exactly, nothing else:**

```
Insights/prose_trial/          REVIEW.md, packets.json, results.json,
                               results_v2.json, entity_roster.json,
                               build_packets.py, prompts.py, checks.py,
                               llm.py, verify.py, verify_v2.py,
                               run_trial.py, run_v2.py, make_review.py,
                               logs/calls.jsonl
handoffs/WPD4_REPORT.md        this file
```

`git status` at handover shows `?? Insights/prose_trial/` plus this report and
nothing more.

**Not touched, as required:** `Insights/src/`, `Insights/metainsights/`
(hash-verified identical before and after), `Insights/reports_prdw/`, the domain
packs, `Data/`, `Ask/`, `eval/`, every other file in `handoffs/`,
`PROJECT_PLAN.md`. `global_feed.json` is byte-identical — D16's freeze holds.
The parquet views and reports the rebuild produced were written **in the mirror
only**; no `Insights/views_prdw/` exists in the repo.

**Git:** read-only throughout — `status`, `log`, `rev-parse`, `diff` only. The
one commit in this session (`586ce40`) was made by the operator, not by this
agent.

**Secrets:** `Insights/.env` was never printed, copied, or written. Its value is
loaded into process memory from the Drive path at call time. All 50 logged calls
and every trial artefact were scanned for credential patterns — clean.

**Known limitations of this trial.** The verifier shares a vendor with the
writer (§1). The v2 measurement re-verified only the 8 fallbacks, not all 15, so
"7 of 8 were false positives" is measured on the failures, not on the whole set.
The first-pass rate of 2/15 is a measurement of the verifier's prompt as
specified, not of the writing — §3 is the number to carry forward.
