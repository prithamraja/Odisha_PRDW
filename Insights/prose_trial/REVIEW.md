# WP-D4 prose trial — review document

**What this is.** A trial, not a shipped change. The fifteen findings at the top
of the Discover feed were rewritten by a writer that received **no writing rules
at all** — only the context brief and, per finding, a packet of deterministically
computed reference figures and variable definitions. All safety sits *after* the
writer: mechanical nothing-invented checks, then a different-model verifier.
Nothing here is wired to the feed, the reports or the frontend; `global_feed.json`
is untouched and the feed sentences below are its current text.

**Your job at the gate.** Label each of the fifteen **adopt** / **adopt-with-edits**
/ **reject**, judging the new text against the current feed text shown beside it.
That labelling — not anything in this document — decides whether the design goes to
production and what the context brief needs changed.

- **Candidate set:** `a7f991c1df3771f9` (six pinned files in `Insights/metainsights/` verified against WP-D3b §4 before the run; feed `global_feed.json` sha256 `3da40edae324f917…`)
- **Writer:** `gpt-5.6-sol` — pinned by D17 through `discover_config`. One batch call, all 15 findings, no rules in the prompt.
- **Verifier:** `gpt-5.5` — a different model generation; same vendor (disclosed limitation: one completion key on file).
- **Context:** the instantiated Appendix A, reproduced in full at the end of this document. It carries **no list of domain facts** and no caution layer; the writer worked from the packets alone.

## Totals

| | count |
|---|---:|
| Findings | 15 |
| Clean on the first pass (checks **and** verifier) | **11** |
| Passed after one regeneration | **3** |
| Fell back to the current feed sentence | **1** |
| Renderings put through the safety net | 19 |
| Numerals machine-checked across them | 128 |
| Renderings the code checks failed | **0** |
| Renderings the verifier failed | **4** |
| Verifier calls that returned nothing to parse | 1 |
| API calls | 26 of 60 allowed |

**What the code checks caught: nothing.** Across 19 renderings and 128 numerals,
every figure traced to its own packet or to the context, no rendering named a place
or category outside its own finding, no rendering emitted a database token, and every
lead and detail was inside the length bounds. The layer is not idle — it is the layer
that makes "the writer invented no figure" a measured statement rather than an
impression — but on this run it found nothing to reject. Round 1's only two catches
were fiscal years written `2020-21` against a packet that said `2020-2021`; this
round's packets carry both forms of every year, and that class is gone.

**What the verifier caught that the code could not.** 4 drifts, none of which changes
a digit and none of which any mechanical check could see:

1. **Finding 4, attempt 1** — "officials should reconcile unspent sanctions and missing sanction records"
   *The source says:* The sources say the figures cover only activities that have a sanction record on file, and that this is about one in six activities; they do not establish that sanction records are missing or that the remaining activities should have sanction records.
2. **Finding 4, attempt 2** — "Cuttack was closest to its sanctioned amount at 92.0% utilisation."
   *The source says:* The source supports only that Cuttack's utilisation was 92.0%: "utilization_companion / utilization_pct / Cuttack: 92.0%". It does not state that Cuttack was the closest district overall; utilisation figures for all 9 districts are not provided, and by absolute overspend_vs_sanction Rayagada is closer to zero than Cuttack (Rayagada Rs -17.43 lakh; Cuttack Rs -18.73 lakh).
3. **Finding 7, attempt 1** — "with Govindapur’s different classification practice reviewed for lessons that could be applied elsewhere."
   *The source says:* The source says only: “Govindapur: different pattern -- the engine found a different kind of pattern here.” It does not establish that Govindapur has a different classification practice, or that the pattern reflects a practice that could provide lessons for elsewhere.
4. **Finding 9, attempt 1** — "creating predictable periods of higher transaction workload and control risk"
   *The source says:* The source supports a seasonal pattern in payment_count for month and quarter, but it does not state that this creates higher control risk.

All four are the same species: the numbers were right and the *attribution*,
*inference* or *implied fact* was not. A pattern read as a practice; a seasonal
shape read as a control risk; a partial coverage figure read as evidence of missing
records; a single quoted percentage read as a rank across nine districts. This is the
class of error the trial exists to test for, and code checks cannot reach it.

**The verifier's own failure, measured.** One verifier call — finding 1, first
attempt — returned an empty string: the model spent all 4,000 of its completion
budget on internal reasoning and stopped for length. Under the brief an
unparseable verdict is a fail-to-verify, never a pass, so that finding was
regenerated and its recorded status is *regenerated*. Re-running that same call
afterwards at the same ceiling returned **pass** on 1537 reasoning tokens, so the
starvation was a one-off, not a property of that prompt. **Finding 1's first
rendering was sound; it was regenerated because the judge fell over, not
because the writing did.** Both versions are shown below.

**Cost.** 26 calls: 1 budget check, 1 writer batch all15, 19 verifier, 4 regenerate, 1 verifier remeasure. Token usage in full:

| call type | model | calls | prompt tokens | completion tokens | of which reasoning |
|---|---|---:|---:|---:|---:|
| budget check | `gpt-5.6-sol` | 1 | 1,848 | 578 | 348 |
| writer batch all15 | `gpt-5.6-sol` | 1 | 14,397 | 3,237 | 1,238 |
| verifier | `gpt-5.5` | 19 | 38,028 | 36,695 | 28,410 |
| regenerate | `gpt-5.6-sol` | 4 | 5,923 | 2,259 | 1,445 |
| verifier remeasure | `gpt-5.5` | 1 | 2,500 | 2,020 | 1,537 |
| **total** | | **26** | **62,696** | **44,789** | **32,978** |

The repository holds no per-token price list for these model ids, so the cost is
stated in tokens rather than in an invented currency figure. Worst case allowed by
the brief was about 1.44M tokens; this run used 107,485.

---

## Finding 1 — Activity Lifecycle

**Status: REGENERATED.**

**Current feed text (what production says today)**

> Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends

**Final rendering**

> **Recorded expenditure across the 20-GP sample was Rs 51.96 crore below planned cost, and the gap is spread across all 16 blocks rather than being driven by one block. Rangeilunda and Kalimela warrant first review because they show the largest shortfalls.**
>
> Across 5,630 costed activities from 2020-21 to 2025-26, Rangeilunda spent Rs 2.73 crore of Rs 11.84 crore planned—a Rs 9.11 crore gap and 23.1% utilisation—while Kalimela spent Rs 1.76 crore of Rs 7.65 crore, a Rs 5.90 crore gap and 23.0% utilisation. The broad block-level spread appears in 27 of 28 category groupings; Banking Facilities is the only grouping where no clear pattern was found. At the next review, ask blocks to reconcile planned costs with work status and recorded payments, particularly in Rangeilunda and Kalimela; these figures show lower recorded spending than planned, but do not establish whether this reflects delays, cancelled works or incomplete records.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 9 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

<details><summary>Attempts</summary>

**Attempt 1** — checks PASS, verifier fail_to_verify

> **Costed activities show a combined spending shortfall of Rs 51.96 crore against plans, and the gap is spread across blocks rather than being confined to one location.**
>
> The broad spread appears in 27 of 28 asset categories; Banking Facilities shows no clear pattern. Rangeilunda has the largest recorded gap at Rs 9.11 crore, with Rs 2.73 crore spent against Rs 11.84 crore planned, while Kalimela spent Rs 1.76 crore of Rs 7.65 crore. Blocks should review ageing activities and reconcile whether these gaps reflect works yet to start, incomplete expenditure records or plans that are no longer active; the sample does not by itself establish the cause.

- Flagged: "(none quoted)"
  Source says: verifier returned no parseable JSON: 

**Attempt 2** — checks PASS, verifier pass

> **Recorded expenditure across the 20-GP sample was Rs 51.96 crore below planned cost, and the gap is spread across all 16 blocks rather than being driven by one block. Rangeilunda and Kalimela warrant first review because they show the largest shortfalls.**
>
> Across 5,630 costed activities from 2020-21 to 2025-26, Rangeilunda spent Rs 2.73 crore of Rs 11.84 crore planned—a Rs 9.11 crore gap and 23.1% utilisation—while Kalimela spent Rs 1.76 crore of Rs 7.65 crore, a Rs 5.90 crore gap and 23.0% utilisation. The broad block-level spread appears in 27 of 28 category groupings; Banking Facilities is the only grouping where no clear pattern was found. At the next review, ask blocks to reconcile planned costs with work status and recorded payments, particularly in Rangeilunda and Kalimela; these figures show lower recorded spending than planned, but do not establish whether this reflects delays, cancelled works or incomplete records.

*Reason fed back to the writer for the regeneration:* A reviewer flagged this claim: "(none quoted)". The source says: verifier returned no parseable JSON:

*Re-measurement of attempt 1's verdict, run after the trial and not counted
in it:* the same verifier, same ceiling, same rendering returned **pass**
(finish `stop`, 1537 reasoning tokens, 8 factual claims mapped to source lines).

</details>

---

## Finding 2 — Geo-Month Cash Cube

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)

**Final rendering**

> **Payments linked to planned activities are trending upward, reaching a sample high of Rs 5.92 crore in 2025-26.**
>
> The upward pattern appears in the monthly, quarterly and fiscal-year views, although individual years fluctuate: annual expenditure fell to Rs 3.66 crore in 2023-24 before rising to Rs 5.06 crore in 2024-25 and Rs 5.92 crore in 2025-26. Reviews should check whether this reflects faster implementation, improved linking of payments to activities, or both.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 10 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 3 — GP Performance

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others

**Final rendering**

> **Recorded sanctions are declining in five of the nine sampled districts, with the sample total falling from Rs 6.13 crore in 2020-21 to Rs 3.57 crore in 2025-26.**
>
> The declining pattern appears in Bargarh, Koraput, Cuttack, Sundargarh and Malkangiri. Kandhamal moves in the opposite direction, while Khordha, Ganjam and Rayagada show no clear trend. Districts with declines should be asked whether fewer proposals, delayed approvals, changes in funding or incomplete entries explain the pattern; these records alone cannot distinguish among them.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 8 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 4 — Activity Lifecycle

**Status: FELL BACK.**

**Current feed text (what production says today)**

> Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends

**Final rendering**

*The safety net rejected both attempts, so the final rendering is the current
feed sentence above, marked* `FELL BACK`. *The text the writer actually
produced is shown under "attempts" below, because you cannot judge the design
from a fallback.*

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **fail** — 1 drifted claim(s)

- Flagged: "Cuttack was closest to its sanctioned amount at 92.0% utilisation."
  Source says: The source supports only that Cuttack's utilisation was 92.0%: "utilization_companion / utilization_pct / Cuttack: 92.0%". It does not state that Cuttack was the closest district overall; utilisation figures for all 9 districts are not provided, and by absolute overspend_vs_sanction Rayagada is closer to zero than Cuttack (Rayagada Rs -17.43 lakh; Cuttack Rs -18.73 lakh).

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

<details><summary>Attempts</summary>

**Attempt 1** — checks PASS, verifier fail

> **For activities with sanction records, spending is Rs 5.02 crore below the sanctioned amount, and the shortfall is broadly distributed across districts and asset categories.**
>
> No single district dominates the gap across 27 of 28 categories; Banking Facilities has no clear pattern. Ganjam has the largest recorded shortfall at Rs 1.68 crore, spending Rs 4.61 crore of Rs 6.30 crore sanctioned, followed by Khordha at Rs 73.70 lakh. These figures cover only activities with sanctions on file—about one in six—so officials should reconcile unspent sanctions and missing sanction records rather than treat this as a programme-wide utilisation rate.

- Flagged: "officials should reconcile unspent sanctions and missing sanction records"
  Source says: The sources say the figures cover only activities that have a sanction record on file, and that this is about one in six activities; they do not establish that sanction records are missing or that the remaining activities should have sanction records.

**Attempt 2** — checks PASS, verifier fail

> **In activities with a sanction record, spending was Rs 5.02 crore below the sanctioned amount across the 20-GP sample. The gap extends across districts and 27 of 28 asset categories, rather than being confined to one place or type of work.**
>
> Ganjam shows the largest reported gap—Rs 1.68 crore, with Rs 4.61 crore spent against Rs 6.30 crore sanctioned—followed by Khordha at Rs 73.70 lakh; Cuttack was closest to its sanctioned amount at 92.0% utilisation. Banking Facilities was the only category without a clear district pattern. At the next review, ask districts, particularly Ganjam and Khordha, whether these balances reflect ongoing work, delays, savings or expenditure not yet entered, and check the relevant sanction and payment entries. These figures cover only activities that have a sanction record on file—about one in six activities—so they are not a programme-wide utilisation rate and do not show whether other activities should have sanction records.

- Flagged: "Cuttack was closest to its sanctioned amount at 92.0% utilisation."
  Source says: The source supports only that Cuttack's utilisation was 92.0%: "utilization_companion / utilization_pct / Cuttack: 92.0%". It does not state that Cuttack was the closest district overall; utilisation figures for all 9 districts are not provided, and by absolute overspend_vs_sanction Rayagada is closer to zero than Cuttack (Rayagada Rs -17.43 lakh; Cuttack Rs -18.73 lakh).

*Reason fed back to the writer for the regeneration:* A reviewer flagged this claim: "officials should reconcile unspent sanctions and missing sanction records". The source says: The sources say the figures cover only activities that have a sanction record on file, and that this is about one in six activities; they do not establish that sanction records are missing or that the remaining activities should have sanction records.

</details>

---

## Finding 5 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern)

**Final rendering**

> **Two undocumented output codes dominate planned untied funding for public works: Code 101 accounts for Rs 34.88 crore and Code 105 for Rs 16.90 crore.**
>
> Code 101 represents 62.1% and Code 105 another 30.1% of the Rs 56.20 crore total, and they lead in 19 of the 20 sampled Gram Panchayats. Haldikudar follows a different pattern. Because no descriptions are recorded for these codes, officials cannot tell what outputs receive most discretionary funding; the code definitions and Haldikudar’s classification should be checked before drawing a policy conclusion.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 11 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 6 — Geo-Month Cash Cube

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern)

**Final rendering**

> **Bhubaneswar block recorded one-quarter of all payment vouchers in the sample and had the highest count in five of the six years.**
>
> Bhubaneswar recorded 2,135 of 8,529 vouchers, compared with 945 in Rangeilunda and 885 in Bheden; 2024-25 was the only year without a clear leader. Voucher counts indicate transaction volume, not spending or performance, so the next review should check whether Bhubaneswar’s concentration reflects workload, payment fragmentation or differences in recording practice.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 7 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 7 — Activity Lifecycle

**Status: REGENERATED.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern)

**Final rendering**

> **More than half of the public works reviewed—5,181 of 9,418 activities, or 55%—have no asset category recorded. “Uncategorised” is the largest group in 19 of the 20 sampled Gram Panchayats, limiting oversight of what assets were planned.**
>
> Govindapur is the only GP that does not follow this pattern, though the data does not explain why. Officials should ask the other 19 GPs to check whether asset categories were omitted during data entry or are also missing from source records, and review Govindapur separately to understand its different pattern; by comparison, the largest named category, Buildings, accounts for 688 activities or 7.3%.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 8 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

<details><summary>Attempts</summary>

**Attempt 1** — checks PASS, verifier fail

> **Asset classification is missing for 5,181 public works—55.0% of all public works activities in the sample.**
>
> “Uncategorised” is the largest group in 19 of the 20 Gram Panchayats; only Govindapur follows a different pattern. This limits any assessment of whether plans are balanced across buildings, sanitation, water, roads and other assets. Gram Panchayats should complete or correct asset categories, with Govindapur’s different classification practice reviewed for lessons that could be applied elsewhere.

- Flagged: "with Govindapur’s different classification practice reviewed for lessons that could be applied elsewhere."
  Source says: The source says only: “Govindapur: different pattern -- the engine found a different kind of pattern here.” It does not establish that Govindapur has a different classification practice, or that the pattern reflects a practice that could provide lessons for elsewhere.

**Attempt 2** — checks PASS, verifier pass

> **More than half of the public works reviewed—5,181 of 9,418 activities, or 55%—have no asset category recorded. “Uncategorised” is the largest group in 19 of the 20 sampled Gram Panchayats, limiting oversight of what assets were planned.**
>
> Govindapur is the only GP that does not follow this pattern, though the data does not explain why. Officials should ask the other 19 GPs to check whether asset categories were omitted during data entry or are also missing from source records, and review Govindapur separately to understand its different pattern; by comparison, the largest named category, Buildings, accounts for 688 activities or 7.3%.

*Reason fed back to the writer for the regeneration:* A reviewer flagged this claim: "with Govindapur’s different classification practice reviewed for lessons that could be applied elsewhere.". The source says: The source says only: “Govindapur: different pattern -- the engine found a different kind of pattern here.” It does not establish that Govindapur has a different classification practice, or that the pattern reflects a practice that could provide lessons for elsewhere.

</details>

---

## Finding 8 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering**

> **Activities still recorded as “Activity Approved” account for Rs 41.61 crore of the Rs 51.96 crore gap between planned cost and expenditure.**
>
> Only Rs 14.00 lakh is recorded as spent against Rs 41.75 crore planned for this status, and it has the largest shortfall in 18 of the 20 Gram Panchayats; Boipariguda and Laxmipur show no clear pattern. Officials should identify how long these activities have remained approved and check for stalled starts, outdated statuses or missing payments. The data shows a recorded gap, not why the activities have not progressed.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 7 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 9 — Geo-Month Cash Cube

**Status: REGENERATED.**

**Current feed text (what production says today)**

> Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern)

**Final rendering**

> **Payment activity in the 20-Gram-Panchayat sample follows a recurring pattern by month and quarter, so officials should identify the busiest periods and plan reviews accordingly. This pattern alone does not indicate irregularity.**
>
> The pattern appears at monthly and quarterly levels across April 2020 to March 2026, but not across fiscal years. Annual totals varied without a clear recurring pattern: 2025-26 was highest at 1,985 vouchers, or 23.3% of the sample’s 8,529 vouchers, while 2023-24 was lowest at 1,003. At the next review, ask which months and quarters repeatedly see higher voucher volumes and whether this timing reflects work cycles, payment deadlines or local recording practices.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 8 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

<details><summary>Attempts</summary>

**Attempt 1** — checks PASS, verifier fail

> **Payment-voucher activity follows a recurring annual cycle, creating predictable periods of higher transaction workload and control risk.**
>
> The seasonal pattern is visible in both monthly and quarterly data, while annual totals show no clear pattern; the six-year sample contains 8,529 vouchers. Officials should identify the recurring peak months and quarters and plan staffing, verification and cashbook scrutiny accordingly. The pattern does not establish whether peaks arise from work schedules, fund releases or year-end processing.

- Flagged: "creating predictable periods of higher transaction workload and control risk"
  Source says: The source supports a seasonal pattern in payment_count for month and quarter, but it does not state that this creates higher control risk.

**Attempt 2** — checks PASS, verifier pass

> **Payment activity in the 20-Gram-Panchayat sample follows a recurring pattern by month and quarter, so officials should identify the busiest periods and plan reviews accordingly. This pattern alone does not indicate irregularity.**
>
> The pattern appears at monthly and quarterly levels across April 2020 to March 2026, but not across fiscal years. Annual totals varied without a clear recurring pattern: 2025-26 was highest at 1,985 vouchers, or 23.3% of the sample’s 8,529 vouchers, while 2023-24 was lowest at 1,003. At the next review, ask which months and quarters repeatedly see higher voucher volumes and whether this timing reflects work cycles, payment deadlines or local recording practices.

*Reason fed back to the writer for the regeneration:* A reviewer flagged this claim: "creating predictable periods of higher transaction workload and control risk". The source says: The source supports a seasonal pattern in payment_count for month and quarter, but it does not state that this creates higher control risk.

</details>

---

## Finding 10 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering**

> **Works marked “WORK ONGOING” account for Rs 28.59 crore, or 93.9%, of all recorded spending from the General social-category component.**
>
> This concentration appears in 18 of the 20 Gram Panchayats, while Boipariguda and Laxmipur show no clear pattern. Ongoing works make up 37.5% of the costed activities but dominate this component of spending, so reviews should check whether heavily spent works remain correctly classified as ongoing and whether completion statuses are being updated. This finding covers the General component, not total spending from all social-category components.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 6 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 11 — Geo-Month Cash Cube

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)

**Final rendering**

> **Activity-linked expenditure is rising over time in six of the nine sampled districts, with Rs 1.99 crore recorded in 2026-Q1—the highest quarter in the sample.**
>
> The upward pattern appears in Khordha, Ganjam, Kandhamal, Sundargarh, Malkangiri and Rayagada. Bargarh, Koraput and Cuttack follow different, unspecified patterns and should be compared with the other districts to check for implementation delays, irregular payment linking or distinct release schedules. The trend concerns only cashbook payments linked to planned activities.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 6 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 12 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering**

> **Almost all recorded expected beneficiaries—2,03,534 people, or 98.4%—are attached to activities that remain at “Activity Approved” status.**
>
> Ongoing works record only 2,759 expected beneficiaries, while completed works record none; the same dominance of approved activities appears in 18 Gram Panchayats, with no clear pattern in Boipariguda and Laxmipur. Beneficiary information exists for only 763 activities and represents expectations, not people actually reached. Officials should check whether beneficiary fields and activity statuses are updated as works move into implementation and completion.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 7 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 13 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values); Kalimela (Theme 4 - Water Sufficient Village has the highest fund_untied_total among theme values)

**Final rendering**

> **Half of planned untied funding—Rs 30.07 crore—is directed to Theme 6, “Self-sufficient Infrastructure in Village,” which leads in 18 of the 20 Gram Panchayats.**
>
> Kalimela differs, with Theme 4, “Water Sufficient Village,” receiving the most untied funding; in Boipariguda, the largest amount is under “Unmapped theme.” Officials should confirm that the concentration on infrastructure reflects approved local priorities and correct Boipariguda’s missing theme mapping before assessing its funding mix. The finding describes planned discretionary funding, not expenditure or results.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 7 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 14 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern)

**Final rendering**

> **Among new works with sanction records, Code 101 has the largest spending gap: Rs 14.94 crore spent against Rs 17.43 crore sanctioned.**
>
> The Rs 2.49 crore shortfall is the largest by output code in 19 of the 20 Gram Panchayats; Chikilli shows no clear pattern. Code 101’s utilisation is 85.7%, so its large absolute gap may partly reflect its scale rather than especially weak performance. Since output-code descriptions are missing and sanction-based figures cover only activities with sanctions on file, officials should first obtain the code definitions and then review ageing unspent sanctions.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 10 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 15 — Activity Lifecycle

**Status: FIRST-PASS.**

**Current feed text (what production says today)**

> Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern)

**Final rendering**

> **All 6,893 geotagged photo uploads recorded for new works are attached to Code 101, while every other output code has none.**
>
> This concentration appears across 19 Gram Panchayats, with no clear pattern in Chikilli, even though Code 101 represents only 32.8% of new-work activities. Officials should check whether the photo-evidence workflow is enabled only for Code 101, whether other works are mis-coded, or whether their evidence is missing. The records establish an upload gap, not that physical work or other forms of evidence are absent.

**Checks (final attempt):** PASS numerals; PASS names; PASS no database wording; PASS shape

**Verifier verdict (final attempt):** **pass** — 7 factual claims mapped to source lines

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Appendix — the context every rendering was written from

Reproduced verbatim, so this document reads without opening another file. It is the
instantiated Appendix A of the WP-D4 brief: the operator's template with the four
PR&DW slot values filled in. Note what is *not* in it — no list of domain facts, no
caution library, no writing rules, no phrasing suggestions.

> You are writing for a decision-aid system used by government officials in Odisha's Department of Panchayati Raj & Drinking Water. The system automatically analyses village-level planning and spending records — development plans, sanctions, payments, works and photo evidence from Gram Panchayats, blocks, and districts — and surfaces patterns worth an official's attention. The current data is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
>
> Your readers are busy block-, district- and state-level officials, not data analysts. They read these insights to decide where to direct attention: which districts to question, which records to reconcile, which local practices to check at the next review.
>
> Below are findings from the analysis engine, each written in the engine's internal style — accurate but full of database language — along with reference figures for each. Rewrite each finding as an insight a senior officer would find clear and actionable:
>
> - a one-to-two-sentence lead the officer sees first. This should be interesting enough to catch a reader's attention and easy enough to understand that the officer doesn't need to read the subsequent paragraph simply to understand it. Lead with what the officer would act on — usually the size and direction of the issue — rather than with the statistical pattern.
> - a short detail paragraph explaining what was found, which places are exceptions and in what way, and what is worth checking or asking at the next review.
>
> Write naturally, in plain English. Use the reference figures where they strengthen the point; use no number that is not provided. Be direct about what the data can and cannot establish — an insight that overstates certainty could send an official after the wrong problem.

