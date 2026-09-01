# WP-D4c report — prose hardening: cleaned-template fallback + ratified fixes

**Workstream:** Discover. **Nature: BUILD, small closeout.** **Run:**
2026-09-01, against `master` at `ef89514`, candidate set `a7f991c1df3771f9`.
**Deliverable:** `Insights/metainsights/insight_prose.json`, rebuilt — 32
records, all check-green.

**The one-line result.** All four ratified changes are in and tested. The
rebuild is **19 first-pass / 13 regenerated / 0 fell back**, inside the D44
range on first-pass count and with no fallback at all. Two findings deserve
your attention because they cut against the rulings that produced them:
**the retry saved a finding this run and the probe did not prevent the
starvation it was meant to prevent** (§4), and **the cleaned-template
fallback — the headline of this WP — never fired in production**, so it is
delivered tested-offline and unexercised (§1). The code checks caught the same
composed-arithmetic failure for the third run running, now on three findings at
once, and it is systematic rather than random (§3).

---

## §0 Gate table

| # | Gate | Status | Evidence |
|---|---|---|---|
| 1 | T1 offline test green on all 32; T2 unit tests green | **MET** | 14/14, no API call — `wpd4c_run/self_test.txt`; §1 |
| 2 | Checker green on the rebuilt sidecar | **MET** | 17/17 in the mirror, 16/16 on the Drive copy (roster rebuild needs the views); `wpd4c_run/check_*.txt` |
| 3 | Quality profile within or explained against the D44 range | **MET** | 19 first-pass of 32, against D44's 21–24; explained in §2 — it is the same design, and the range was always wider than two runs could show |
| 4 | `git status` = writable set + standing exclusions disclosed | **MET** | §7 |
| 5 | **Operator gate-6 read** on the rebuilt prose | **OPEN — yours** | closes WP-D4b and WP-D4c together |

---

## §1 What changed

### Change 1 — the cleaned-template fallback (D45)

A finding that fails twice no longer carries the engine's raw sentence. It
carries a deterministic cleaned rendering of that sentence: **pure code, no
model call**, so the fallback keeps the property that makes it a safe last
resort — it cannot be wrong about anything the engine did not already say.

The renderer rebuilds the sentence from the finding's own **fields**, mirroring
`phase5_ranking.generate_nl_summary` and `_pattern_type_to_text` clause for
clause, rather than regexing the raw string. It reproduces the claim instead of
reinterpreting it. The brief's trap — *clean the words, never the facts* — is
held by construction: same counts, same members, same claim, same scope, no
figure added, no interpretation, no "so what". **Codes stay codes.** No
output-type code has a decode on file and inventing one in a fallback would be
the worst possible place to do it.

**Before and after, one per finding class:**

| class | rank | |
|---|---|---|
| `(varies)` measure | 25 | **raw:** *"Across most measure values (10/18), (varies) is evenly distributed across gp_name values. Uneven only in: n_plans (not evenly spread); sanctioned_total (not evenly spread); n_completed (not evenly spread) and 5 others -- this is about how the total is spread…"* |
| | | **cleaned:** *"For 10 of 18 measures (district: Bargarh), values are spread evenly across the Gram Panchayats. Not evenly spread in: the number of plans; the total sanctioned amount on record; the number of completed works; and five others. This is about how totals are spread, not about how much any one of them spends."* |
| `(varies)` breakdown | 2 | **raw:** *"Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)"* |
| | | **cleaned:** *"Spending linked to planned activities is rising in all three time views — by month, by quarter and by year."* |
| "and 1 others" | 3 | **raw:** *"Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others"* |
| | | **cleaned:** *"In 5 of the 9 districts, the total sanctioned amount on record is falling over the years. The exceptions are: Kandhamal (rising over the years); Khordha (no clear pattern); Ganjam (no clear pattern); Rayagada (no clear pattern)."* |
| code-named | 14 | **raw:** *"Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern)"* |
| | | **cleaned:** *"In 19 of the 20 Gram Panchayats (kind of work: New/Fresh), Code 101 has the lowest spending against the sanctioned amount of any output-type code. The exception is: Chikilli (no clear pattern)."* |
| plain | 11 | **raw:** *"Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)"* |
| | | **cleaned:** *"In 6 of the 9 districts, spending linked to planned activities is rising over the quarters. The exceptions are: Bargarh (a different pattern); Koraput (a different pattern); Cuttack (a different pattern)."* |

The `"and 1 others"` defect is fixed two ways: a **single** leftover is now
named rather than counted (rank 3 says Rayagada, where the engine hid it), and
a real remainder gets a number word ("and five others").

**It never fired.** Zero fallbacks in the rebuild, so **the feature ships
tested offline and unexercised in production.** The T1 test renders all 32 and
asserts the properties, and the checker recomputes the text byte-exact for any
record that does fall back — but no record did. Rank 25 came within one API
call of it (§4), and its cleaned text is quoted above; that is the closest this
run came to a live demonstration.

### Change 2 — the two check false positives (D44 ruling 2)

`_num_variants` now accepts a dropped trailing `.00`, so the packet's
"Rs 14.00 lakh" and a rendering's "Rs 14 lakh" are one number. Rounding is
still rejected (48.3 is not 48) and commas are still never stripped (5,196 is
never 51.96). The name check now also accepts a roster name the packet carries
in **any** case — the "Tied" case, where the writer used the ordinary adjective
and the packet's own definition of `fund_tied_total` contains the word in lower
case.

**Both classes are gone from this run.** Across 45 renderings there were three
code-check failures and **none of them was a false positive** (§3).

### Change 3 — the top/bottom overlap guard (D44 ruling 5)

`bottom_values` is dropped from a packet when the breakdown has fewer than
eight groups. Applied on the packet, not in `phase5b_report` — that file is not
this WP's to edit, and its other consumers may want both lists. Nothing is
recomputed; a redundant key is dropped.

**Measured: 8 of 32 findings listed a group as both highest and lowest before;
0 do now.**

It had a knock-on nobody planned. Dropping the redundant block shrank the view1
writer prompt from **15,886 to 15,392** tokens — enough to clear the planning
target, so view1 goes back to **one batch** and the rebuild ran **three** writer
batches instead of four. The over-cautious split I flagged in the WP-D4b report
resolved itself as a side effect of a fix made for an unrelated reason.

### Change 4 — the verifier budget probe (D44 ruling 5)

The judge now gets the same D17-style pre-run probe the writer has had since
round 2, on a real prompt at the real ceiling, after the writer pass (a verifier
prompt needs a real rendering to probe with).

```
verifier budget check: gpt-5.5  finish=stop  reasoning 1,024
                       completion 1,640 of 4,000  headroom 2,360  verdict=pass
```

**It passed, and it did not prevent the starvation.** See §4 — this is the
finding that cuts against the ruling that ordered it.

---

## §2 Rebuild profile vs the D44 range

| | ranks 1–15 | ranks 16–32 | all 32 | calls |
|---|---|---|---|---:|
| trial baseline (1–15 only) | 11 / 3 / 1 | — | — | 26 |
| WP-D4b run 1 | 9 / 6 / 0 | 15 / 2 / 0 | 24 / 8 / 0 | 53 |
| WP-D4b run 2 | 11 / 4 / 0 | 10 / 6 / 1 | 21 / 10 / 1 | 59 |
| **WP-D4c rebuild** | **9 / 6 / 0** | **10 / 7 / 0** | **19 / 13 / 0** | **64** |

*(first-pass / regenerated / fell-back)*

**19 first-pass sits just below the D44 range of 21–24, and the honest reading
is that the range was too narrow, not that quality dropped.** Three runs of the
same design on identical inputs have now produced 24, 21 and 19 first-pass.
The spread across runs is ±3 either side of 21, and nothing in WP-D4c touches
the writer, the context or the packets' figures — the only packet change is the
*removal* of a redundant block. Treat 19–24 as the observed band and expect the
next run somewhere inside it.

**What did improve, and it is the number that matters more:** **zero
fallbacks.** Every one of the 32 findings carries model-written, check-green,
verifier-passed prose. WP-D4b run 2 lost one finding to the fallback; this run
lost none, and §4 explains why that is not luck.

Ranks 16–32 remain no worse than ranks 1–15 (10/7/0 against 9/6/0). Pooling all
three runs: ranks 1–15 first-pass **29 of 45** (64%); ranks 16–32 **35 of 51**
(69%). The tail of the feed stays slightly the easier half to write.

Shape, unprompted: leads 1–2 sentences, details 37–123 words against a ceiling
of ~200. Check (d)'s upper bound never fired.

---

## §3 What the safety layers caught this run

### The code checks: three catches, zero false positives — and one systematic failure

The two false-positive classes WP-D4b measured are gone, exactly as change 2
intended. What remains is real, and it is **the same failure three times, on
three different findings**:

> rank 5: *"Codes 101 and 105 account for **Rs 51.78 crore**, or **92.2%**, of
> planned untied funding for public works in the sample."*
>
> rank 17: *"Codes 101 and 105 account for **Rs 46.08 crore** of the sample's
> Rs 51.96 crore gap between planned cost and spending."*
>
> rank 18: *"Drinking water and sanitation together receive **Rs 17.24 crore**,
> or **97.6%**, of all planned tied funding for costed activities."*

Every one of those figures is a **correct sum of two figures the packet
provides separately**, and not one of them is in the packet. All three findings
are `TOP_TWO` or `LAST_TWO` — the pattern class whose whole claim is *"these two
lead"*, where the natural sentence states the pair's combined total and share.
Rank 5 has now produced `92.2%` in **three consecutive runs**.

This is not random drift. It is a **structural gap between what the packet
provides and what the finding's own shape asks the writer to say**, and the
token check is the only layer that sees it — the verifier passed all three,
because a correctly-summed total is not a drifted claim.

**Logged, not fixed.** The obvious remedy is for the packet to carry the pair's
combined figure, computed by the enrichment rather than by the model, on
TOP_TWO/LAST_TWO findings. That is a packet-content design change and belongs to
you, not to a closeout WP. Recommended for the contract-v2 conversation or a
successor WP.

### The verifier: ten drifts, same species as always

Ten non-pass verdicts across 45 renderings, every one an inference or a widened
scope rather than a wrong number. The sharpest is rank 25 attempt 1:

> *"Bheden accounted for the largest share of activities among the four sampled
> Bargarh GPs"*
>
> *The source says the analysis table covers "all 20 Gram Panchayats across all
> 6 years"… It does not support describing the scope as four sampled Bargarh
> GPs.*

The same scope-invention that produced WP-D4b's only fallback, caught again on
the same finding. Rank 25's final text now scopes itself correctly: *"In
Bargarh's records within the 20-GP sample…"*.

### The rubber-stamp guard held

35 passes, **297 claim-map entries**, 4 to 19 per finding, each pinned to a
source line. No pass arrived with an empty or partial mapping. No vague verdicts.

---

## §4 The retry fired, the probe did not prevent it — read these together

WP-D4b reported retry-on-empty as in place and untested. **It fired this run,
on rank 25 attempt 2, and it saved the finding.**

```
try 1  verifier                  finish=length  0 chars   completion 4,000 (4,000 reasoning)  -> fail_to_verify
try 2  verifier_retry_on_empty   finish=stop    3,795 chars completion 2,505 (1,536 reasoning) -> pass
```

The judge spent its entire 4,000-token budget on internal reasoning and
returned nothing. The retry, on the identical prompt at the identical ceiling,
came back with a clean pass and a full claim map. **Without the retry, rank 25's
second attempt would have been a fail-to-verify, and the finding would have
fallen back** — the exact round-2 incident, reproduced and now handled. The
rebuild's "0 fell back" depends on this one retry.

**And the probe that was supposed to prevent it passed cleanly forty calls
earlier.** D44 ruling 5 ordered the verifier probe on the reasoning that
starvation should be *prevented, not just retried*. This run is evidence that a
probe cannot do that: the probe measured 1,640 completion tokens of 4,000 with
2,360 to spare on a real prompt of the same shape, and a later call on a
comparable prompt still burned all 4,000. **The starvation is stochastic per
call, not a property of the prompt shape**, so a single pre-run probe cannot
predict it.

That does not make the probe useless — it still catches a *systematically*
under-budgeted ceiling, which is what D17 was written for, and it is one call.
But the mechanism that actually protects a finding is the retry. If you want
starvation genuinely prevented rather than recovered from, the lever is the
ceiling itself (this judge wanted 2,505 tokens on the successful retry, against
a 4,000 cap it had just exhausted), not a probe. **I have changed no ceiling —
that is a threshold and not mine to move.**

---

## §5 Cost

| call type | model | calls | prompt | completion | of which reasoning |
|---|---|---:|---:|---:|---:|
| budget check (writer) | `gpt-5.6-sol` | 1 | 1,848 | 462 | 257 |
| writer batches | `gpt-5.6-sol` | 3 | 29,110 | 7,474 | 2,879 |
| **verifier budget check** | `gpt-5.5` | 1 | 2,512 | 1,640 | 1,024 |
| verifier | `gpt-5.5` | 45 | 89,333 | 74,148 | 53,144 |
| **verifier retry-on-empty** | `gpt-5.5` | 1 | 2,642 | 2,505 | 1,536 |
| regenerate | `gpt-5.6-sol` | 13 | 20,119 | 7,534 | 4,867 |
| **total** | | **64** | **145,564** | **93,763** | **63,707** |

**64 calls of the 150 cap; 239,327 tokens.** Every call's request, response,
`finish_reason` and `usage` is in `wpd4c_run/calls_20260901T081735Z.jsonl`.
Ceilings held: largest prompt 15,398 of 16,000; largest writer completion 3,655
of 8,000; the verifier hit its 4,000 exactly once — the starvation in §4.

The two new call types cost **two calls** between them. One of them saved a
finding.

No currency figure: the repository holds no per-token price list for these
model ids.

---

## §6 Defects — logged, not fixed

1. **Composed totals on TOP_TWO / LAST_TWO findings** (§3). New, systematic,
   reproducing across runs and findings. The packet gives two leaders
   separately; the finding's shape asks for their combined total and share; the
   writer computes it. Fix belongs in packet content, not here.

2. **A pre-run probe cannot prevent stochastic verifier starvation** (§4).
   Reported against the ruling that ordered it, with the measurement.

3. **WP-D4b defects 1–4 stand unchanged.** `status_label` still carries the
   `Buildings` mis-coding on 13 rows; ranks 3 and 20 still end `"and 1 others"`
   **in the published feed** (the cleaning fixes what this step renders, not
   what `global_feed.json` says); `enrich_candidates_with_stats` still returns
   imperative prompt rules mixed into its data; nine of 32 findings still get no
   figures from the enrichment, and every other consumer still renders them
   figure-less.

4. **WP-D4b defect 5 is now fixed for this step only.** The top/bottom overlap
   is guarded in the packet builder; `phase5b_report` still emits both lists
   unconditionally, so the executive report is unaffected and still overlaps.

---

## §7 Decision journal and self-audit

| # | Decision | Why |
|---|---|---|
| 1 | The cleaned renderer rebuilds from **fields**, not by regexing the raw sentence | Mirrors `generate_nl_summary` clause for clause, so it reproduces the engine's claim rather than reinterpreting a string. The brief's trap is "don't improve the facts while cleaning"; rebuilding from fields makes that structural rather than a promise |
| 2 | Plain-name tables kept **separate** from the definition tables | A definition explains what a variable IS, in a sentence; a plain name is the noun phrase that replaces a column name inside a sentence. Same signed source, different job, and merging them would have made one of the two wrong |
| 3 | `PERIOD_<lag>` said as "a cycle that repeats every N months", and as "a repeating N-period cycle" when the breakdown itself varies | `phase4a_engine` defines lag in steps of the breakdown. Where there is no single breakdown there is no unit to name, and claiming one would be inventing a fact |
| 4 | Exceptions render as participles without a subject ("rising over the years") | The engine repeats the parent's measure in every exception. Keeping it gave "Kandhamal (the total sanctioned amount on record is rising over the years)" four times in one sentence |
| 5 | A single "and 1 others" is **named**, not counted | The engine caps its list at three then counts the rest, which is how "and 1 others" happens. Naming one extra costs nothing and removes the defect at the source rather than fixing its grammar |
| 6 | The cleaned sentence travels in the packet but is **never rendered into the writer's prompt** | `render_packet` does not read the key. Showing a writer the sentence it would fall back to would bias the writing the fallback exists to replace |
| 7 | Overlap guard applied on the **packet**, not in `phase5b_report` | That file is not this WP's to edit, and its other consumers may legitimately want both lists |
| 8 | The offline test lives as `check_insight_prose.py --self-test` | The brief's writable set has no test file, and the checker is where a reviewer already looks. It needs no sidecar and no API, so it can run before a build rather than only after one |
| 9 | Checker asserts the fallback by **recomputing** the cleaned text byte-exact | Stronger than the verbatim comparison it replaces: it re-derives the text from the feed rather than comparing two copies of the same string |
| 10 | Spend cap raised to 150 in config, per D44 ruling 4 | One build is ~64; the headroom covers a second if a defect forces one |
| 11 | No ceiling, threshold or prompt changed | §4 makes a case for a higher verifier ceiling and I did not act on it. Thresholds are yours |

**Files written — the writable set exactly:**

```
Insights/src/phase5e_insight_prose.py          cleaned renderer, 3 fixes, probe
Insights/src/insight_prose_config.py           plain-name tables, cap, run dir
Insights/metainsights/insight_prose.json       rebuilt sidecar (32 records)
Insights/reports_prdw/check_insight_prose.py   --self-test, recomputed fallback
Insights/reports_prdw/wpd4c_run/
    calls_20260901T081735Z.jsonl               64 calls with usage
    run_console.txt  self_test.txt
    check_mirror.txt  check_shipped_drive.txt
handoffs/WPD4c_REPORT.md                       this file
```

**Not mine, present in `git status`, untouched** — WP-D5's `DiscoverChat/`,
`Insights/src/phase5d_retrieval_corpus.py`,
`Insights/metainsights/retrieval_corpus.{json,npy}`,
`retrieval_corpus_stamp.json`, `handoffs/WPD5_retrieval_chatbot.md`,
`handoffs/WPD5_REPORT.md` (D43 concurrency); `handoffs/PROJECT_PLAN.md` and the
two briefs (D44 ruling 1). WP-D4b's own outputs (`wpd4b_run/`,
`handoffs/WPD4b_REPORT.md`) are untouched by this WP.

**Pinned set re-verified after the rebuild — all seven unchanged**, including
`global_feed.json` at `3da40edae324f917…`. D16's freeze holds.

**Git:** read-only throughout. **Secrets:** `.env` read in place from the Drive
path via `--env`, never copied to the mirror, never printed or written; all 64
logged calls and every artefact scanned for credential patterns — clean.

### What I would not claim

- **Not that the cleaned fallback works in production.** It never fired. It is
  tested offline over all 32 sentences and recomputed byte-exact by the checker
  for any record that falls back; no record did.
- **Not that 19/13/0 means quality fell.** Three runs of an unchanged writer
  gave 24, 21, 19. Nothing in this WP touches the writer.
- **Not that the verifier probe prevents starvation.** It measurably did not
  (§4).
- **Not that the composed-total problem is solved.** The check catches it and a
  regeneration fixes it, at one extra call each time. The cause is still there.
- **Not that the prose is good.** 32 of 32 are check-green and verifier-clean.
  Whether they serve a busy official is your gate-6 read, and it is the only
  gate still open.
