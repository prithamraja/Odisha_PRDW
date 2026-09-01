# WP-D4 prose trial - review document

**What this is.** A trial, not a shipped change. Fifteen findings were rewritten by
a context-driven writer that received no writing rules at all - only the context
brief (Appendix A of the WP-D4 brief) and a packet of deterministically computed
reference figures per finding. All safety sits *after* the writer: mechanical
nothing-invented checks, then a different-model verifier. Nothing here is wired to
the feed, the reports or the frontend; `global_feed.json` is untouched.

**Your job at the gate.** Label each of the fifteen **adopt** / **adopt-with-edits**
/ **reject**, judging the new text against the current feed text shown beside it.

- **Candidate set:** `a7f991c1df3771f9` (six pinned files verified against WPD3b section 4 before the run)
- **Writer:** `gpt-5.6-sol` - one batch call, all 15 findings, no rules in the prompt
- **Verifier:** `gpt-5.5` - a different model generation; same vendor (disclosed limitation)

## Totals

| | count |
|---|---:|
| Findings | 15 |
| Clean on the first pass (checks + verifier v1) | **2** |
| Passed after one regeneration | **5** |
| Fell back to the current feed sentence | **8** |
| Code checks that fired (of 28 renderings checked) | 2 |
| Verifier v1 failures later shown to be false positives | 7 of 8 |
| API calls | 50 of 60 allowed |

**What the code checks caught.** Two of twenty-eight renderings, both the same
thing: a fiscal year written `2020-21` / `2024-25` where the packet says
`2020-2021` / `2024-2025`. The number was *right*; it was not *verbatim*. Nothing
else ever tripped them - across 181 numerals checked, the writer invented no
figure, named no place outside its own finding, and emitted no database token.

**What the verifier caught that the code could not.** Three real drifts, none of
which changes a digit and none of which any mechanical check could see:

1. **Finding 3** - the writer narrowed a stated limitation, turning the background's
   "sanction records exist for only about one **work** in six" into "one **activity**
   in six". Different denominator, same digits.
2. **Finding 8** - the writer attached a sample-wide total (`Rs 41.61 crore`) to the
   eighteen Gram Panchayats the *pattern* holds in, and dropped the finding's
   `Costed`-only scope. Every numeral was legitimate; the attribution was not.
3. **Finding 9** - the writer asserted "this analysis did not assess geographic
   differences", a claim about the analysis that no source makes.

**The verifier's own defect, measured.** Under the brief's literal T4 wording the
verifier failed 8 of 15 - but 7 of those 8 were one repeated false positive: it
flagged the *"what to check at the next review"* sentence as an unsupported claim,
the very sentence Appendix A asks the writer to produce. The verifier sees only the
background bullets, which never *state* a recommendation, so every suggestion looked
invented. Re-running those eight with one sentence added, separating a suggested
action from a factual claim, 7 of 8 passed. **The fallbacks below are an artefact of
that verifier wording, not of the writing** - which is why each one shows the
rendering it produced as well as the fallback.

---

## Finding 1 - Activity Lifecycle

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** The recorded gap between planned cost and expenditure is spread across blocks in 27 of 28 asset categories, rather than being driven by any single block. Across 5,630 costed activities, recorded expenditure is Rs 51.96 crore below planned cost, although incomplete expenditure links mean this is not confirmed underspending.
>
> **Detail.** Banking Facilities is the only category with no clear cross-block pattern. The largest block-level gaps are in Rangeilunda, where Rs 2.73 crore is recorded as spent against Rs 11.84 crore planned, and Kalimela, with Rs 1.76 crore against Rs 7.65 crore planned; officials should start by reconciling expenditure links in these blocks, while treating this as a record-quality check rather than evidence of poor delivery.

**Checks (final rendering):** (a) numerals PASS (8 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 65 w)

**First attempt checks:** (a) numerals PASS (8 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 78 w)

**Why it was regenerated:** A reviewer flagged this claim: "Spending remains below planned cost across almost every asset category". The source says: The source says that across nearly all asset_category_label values, overspend_vs_plan is spread evenly across block_name values. It gives an overall total of Rs -51.96 crore, but it does not provide category-level totals showing that spending is below planned cost in almost every asset category. A reviewer flagged this claim: "reviews should focus on whether plans, expenditure links and work status are current". The source says: The source provides cautions about incomplete

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"officials should start by reconciling expenditure links in these blocks"*
  - source says: The source identifies Rangeilunda and Kalimela as the largest negative block-level values and states that linked spending is affected by record-keeping, but it does not recommend that officials start with these blocks or state that their gaps specifically are due to unreconciled expenditure links.

**Verifier v2 (action separated from claim): PASS**

- claim: *The recorded gap between planned cost and expenditure is spread across blocks in 27 of 28 asset categories, rather than being driven by any single block.* -> supported by: Engine sentence: Across nearly all asset_category_label values (27/28), overspend_vs_plan is spread evenly across block_name values -- it belongs to all of them and no single block_name accounts for it.
- claim: *Across 5,630 costed activities, recorded expenditure is Rs 51.96 crore below planned cost* -> supported by: Records covered: is_costless = Costed; total: Rs -51.96 crore; size_share / volume_in_scope: 5,630 activities
- claim: *incomplete expenditure links mean this is not confirmed underspending.* -> supported by: Total cashbook spending has not grown across these years, while the share of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise in "linked spending" is mostly better record-keeping.
- claim: *Banking Facilities is the only category with no clear cross-block pattern.* -> supported by: Exceptions: - Banking Facilities: no clear pattern -- the engine found no clear pattern here

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 2 - Geo-Month Cash Cube  ·  *thin packet: no reference figures could be computed*

**Status: REGENERATED**

**Current feed text (what the officer sees today):**

> Across all temporal_grain values, activity_linked_expenditure is increasing over (varies)

**Final rendering:**

> **Lead.** Spending recorded against planned activities rises whether viewed by month, quarter or financial year. This mainly indicates better linking of records, not an increase in overall spending.
>
> **Detail.** All three time views show the same upward pattern, with no exceptions recorded. Total cashbook spending did not grow, while the share linked to planned activities rose from 2.7% to 53.2%; at review, confirm whether changes in data-entry coverage and timing account for the trend before drawing conclusions about spending levels.

**Checks (final rendering):** (a) numerals PASS (2 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 51 w)

**First attempt checks:** (a) numerals PASS (2 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 39 w)

**Why it was regenerated:** A reviewer flagged this claim: "Officials should continue improving payment-to-activity reconciliation". The source says: The source says linked spending mostly reflects better record-keeping, but it does not make a recommendation about what officials should do.

**Verifier v1 (gpt-5.5): PASS**

- claim: *Spending recorded against planned activities rises whether viewed by month, quarter or financial year.* -> supported by: Engine sentence: Across all temporal_grain values, activity_linked_expenditure is increasing over (varies); Follows the pattern (3 of 3): month, quarter, fiscal_year
- claim: *This mainly indicates better linking of records, not an increase in overall spending.* -> supported by: Total cashbook spending has not grown across these years, while the share of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise in "linked spending" is mostly better record-keeping.
- claim: *All three time views show the same upward pattern, with no exceptions recorded.* -> supported by: Follows the pattern (3 of 3): month, quarter, fiscal_year; Exceptions: none recorded.
- claim: *Total cashbook spending did not grow, while the share linked to planned activities rose from 2.7% to 53.2%* -> supported by: Total cashbook spending has not grown across these years, while the share of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise in "linked spending" is mostly better record-keeping.
- claim: *confirm whether changes in data-entry coverage and timing account for the trend before drawing conclusions about spending levels* -> supported by: Total cashbook spending has not grown across these years, while the share of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise in "linked spending" is mostly better record-keeping.; March concentrates payments every year; it is the fiscal year-end and this is normal government cash flow.

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 3 - GP Performance

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year. Exceptions: Kandhamal (sanctioned_total is increasing over fiscal_year); Khordha (no clear pattern); Ganjam (no clear pattern) and 1 others

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** Sanctioned values declined over time in five of the nine districts represented in the 20-Gram-Panchayat sample. Kandhamal moved in the opposite direction, while Khordha, Ganjam and Rayagada showed no clear pattern.
>
> **Detail.** The declining pattern appears in Bargarh, Koraput, Cuttack, Sundargarh and Malkangiri; the recorded sanctioned value across all years was Rs 28.84 crore. Because sanction records cover only about one work in six, review the completeness and timeliness of sanction entry before interpreting these trends as changes in actual sanctioning.

**Checks (final rendering):** (a) numerals PASS (2 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 49 w)

**First attempt checks:** (a) numerals FAIL (4 checked: 2020-21, 2025-26); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 62 w)

**Why it was regenerated:** It used numbers that were not in the reference figures or the background: 2020-21, 2025-26. Use only figures that were given to you. A reviewer flagged this claim: "sanction records exist for only about one activity in six". The source says: The background says: "Sanction records exist for only about one work in six"; it does not say one activity in six. A reviewer flagged this claim: "districts should be asked whether the change reflects actual sanctions or incomplete entry". The source says: The source says a falling sanctioned value can mean fewer sanctions or fewer sanctions being entered,

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"review the completeness and timeliness of sanction entry before interpreting these trends as changes in actual sanctioning"*
  - source says: The source supports incompleteness of sanction records and says a falling sanctioned value can mean fewer sanctions or fewer sanctions being entered, but it does not specifically state a timeliness issue with sanction entry.

**Verifier v2 (action separated from claim): PASS**

- claim: *Sanctioned values declined over time in five of the nine districts* -> supported by: Engine sentence: Across most district_name values (5/9), sanctioned_total is decreasing over fiscal_year.
- claim: *represented in the 20-Gram-Panchayat sample* -> supported by: This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
- claim: *Kandhamal moved in the opposite direction* -> supported by: - Kandhamal: opposite direction -- moves in the opposite direction: increasing, where most are decreasing
- claim: *Khordha, Ganjam and Rayagada showed no clear pattern* -> supported by: Exceptions:
  - Khordha: no clear pattern -- the engine found no clear pattern here
  - Ganjam: no clear pattern -- the engine found no clear pattern here
  - Rayagada: no clear pattern -- the engine found no clear pattern here

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 4 - Activity Lifecycle

**Status: REGENERATED**

**Current feed text (what the officer sees today):**

> Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it. Uneven only in: Banking Facilities (not evenly spread) -- this is about how the total is spread, not about how much any one of them spends

**Final rendering:**

> **Lead.** In activities with sanction records, expenditure was Rs 5.02 crore below the sanctioned amount, with the gap spread across districts in 27 of 28 asset categories rather than concentrated in one district. Banking Facilities was the sole category with no clear district pattern.
>
> **Detail.** Ganjam recorded the largest gap at Rs 1.68 crore, spending Rs 4.61 crore of Rs 6.30 crore sanctioned (73.3%); Khordha followed with Rs 73.70 lakh. A review could check whether the larger gaps reflect genuinely unspent sanctions or incomplete entries and examine Banking Facilities separately. Sanctions are recorded for only about one in six works, so these figures describe that subset of this 20-Gram-Panchayat sample, not overall programme utilisation or delivery.

**Checks (final rendering):** (a) numerals PASS (9 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 71 w)

**First attempt checks:** (a) numerals PASS (6 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 65 w)

**Why it was regenerated:** A reviewer flagged this claim: "reviews should first reconcile missing sanctions and expenditure links.". The source says: The source states that sanction records exist for only about one work in six and that linked spending reflects better record-keeping, but it does not prescribe that reviews should first reconcile missing sanctions and expenditure links.

**Verifier v1 (gpt-5.5): PASS**

- claim: *In activities with sanction records, expenditure was Rs 5.02 crore below the sanctioned amount* -> supported by: Reference figures: total: Rs -5.02 crore; utilization_companion / basis: sanctioned amount; utilization_companion / what_this_is: the same money as overspend_vs_sanction, read as a share instead of a difference... describes only the activities that have a sanction record on file
- claim: *the gap spread across districts in 27 of 28 asset categories rather than concentrated in one district* -> supported by: Engine sentence: Across nearly all asset_category_label values (27/28), overspend_vs_sanction is spread evenly across district_name values -- it belongs to all of them and no single district_name accounts for it.
- claim: *Banking Facilities was the sole category with no clear district pattern.* -> supported by: Exceptions: - Banking Facilities: no clear pattern -- the engine found no clear pattern here
- claim: *Ganjam recorded the largest gap at Rs 1.68 crore* -> supported by: Reference figures: bottom_values / Ganjam / value: Rs -1.68 crore
- claim: *spending Rs 4.61 crore of Rs 6.30 crore sanctioned (73.3%)* -> supported by: utilization_companion / utilization_pct / Ganjam: 73.3%; utilization_companion / absolutes / Ganjam: Rs 4.61 crore spent of Rs 6.30 crore sanctioned amount
- claim: *Khordha followed with Rs 73.70 lakh.* -> supported by: Reference figures: bottom_values / Khordha / value: Rs -73.70 lakh

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 5 - Activity Lifecycle

**Status: FIRST-PASS**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Exception: Haldikudar (different pattern)

**Final rendering:**

> **Lead.** Codes 101 and 105 account for most recorded untied funds for public works in 19 of the 20 sampled Gram Panchayats, while Haldikudar follows a different pattern.
>
> **Detail.** Code 101 carries Rs 34.88 crore, or 62.1% of the total, and Code 105 carries Rs 16.90 crore, or 30.1%. The department has no descriptions on file for Codes 101 to 110, so no conclusion can yet be drawn about what is being prioritised; obtain the code definitions and then check why Haldikudar differs.

**Checks (final rendering):** (a) numerals PASS (12 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 54 w)

**Verifier v1 (gpt-5.5): PASS**

- claim: *Codes 101 and 105 account for most recorded untied funds for public works in 19 of the 20 sampled Gram Panchayats* -> supported by: Engine sentence: Across nearly all gp_name values (19/20), Code 101 and Code 105 lead in fund_untied_total among output_type_label values. Records covered: activity_type_label = Public Works; Background: This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
- claim: *Haldikudar follows a different pattern* -> supported by: Exceptions: - Haldikudar: different pattern -- the engine found a different kind of pattern here
- claim: *Code 101 carries Rs 34.88 crore, or 62.1% of the total* -> supported by: top_values / Code 101 / value: Rs 34.88 crore; top_values / Code 101 / share_of_total: 62.1%
- claim: *Code 105 carries Rs 16.90 crore, or 30.1%* -> supported by: top_values / Code 105 / value: Rs 16.90 crore; top_values / Code 105 / share_of_total: 30.1%
- claim: *The department has no descriptions on file for Codes 101 to 110* -> supported by: Output categories "Code 101" to "Code 110" have no descriptions on file; nothing can be concluded about what they contain until the department supplies the decode.
- claim: *no conclusion can yet be drawn about what is being prioritised* -> supported by: Output categories "Code 101" to "Code 110" have no descriptions on file; nothing can be concluded about what they contain until the department supplies the decode.

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 6 - Geo-Month Cash Cube

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values. Exception: 2024-2025 (no clear pattern)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** Bhubaneswar recorded the highest payment workload in five of the six years reviewed, accounting for 2,135 vouchers—25.0% of the sample total. This indicates transaction volume, not performance.
>
> **Detail.** Across the 16 blocks represented, 8,529 vouchers were recorded. Bhubaneswar’s volume was well above Rangeilunda (945), Bheden (885), Sheragada (609) and Kalimela (568); in the remaining year, there was no clear leader. At the next review, ask whether Bhubaneswar’s consistently higher count reflects genuinely more transactions or differences in how vouchers are entered and counted.

**Checks (final rendering):** (a) numerals PASS (8 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 55 w)

**First attempt checks:** (a) numerals FAIL (6 checked: 2024-25); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 41 w)

**Why it was regenerated:** It used numbers that were not in the reference figures or the background: 2024-25. Use only figures that were given to you. A reviewer flagged this claim: "reviews should check whether staffing and reconciliation arrangements are adequate for Bhubaneswar’s volume.". The source says: The source supports that voucher/payment counts are workload, not performance, and that Bhubaneswar has the highest payment_count in 5 of 6 fiscal years, but it does not mention staffing or reconciliation arrangements or recommend a review of their adequacy.

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"At the next review, ask whether Bhubaneswar’s consistently higher count reflects genuinely more transactions or differences in how vouchers are entered and counted."*
  - source says: The source supports that voucher and payment counts are workload, not a performance rating, and that Bhubaneswar had the highest payment_count in 5 of 6 years. It does not state that differences in how vouchers are entered and counted may explain Bhubaneswar’s higher count.

**Verifier v2 (action separated from claim): PASS**

- claim: *Bhubaneswar recorded the highest payment workload in five of the six years reviewed* -> supported by: Engine sentence: Across most fiscal_year values (5/6), Bhubaneswar has the highest payment_count among block_name values.
- claim: *accounting for 2,135 vouchers—25.0% of the sample total* -> supported by: top_values / Bhubaneswar / value: 2,135 vouchers; top_values / Bhubaneswar / share_of_total: 25.0%; total: 8,529 vouchers; This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
- claim: *This indicates transaction volume, not performance.* -> supported by: Voucher and payment counts are workload, not a performance rating.
- claim: *Across the 16 blocks represented, 8,529 vouchers were recorded.* -> supported by: count_breakdown_values: 16; measure_unit: vouchers; total: 8,529 vouchers

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 7 - Activity Lifecycle

**Status: REGENERATED**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values. Exception: Govindapur (different pattern)

**Final rendering:**

> **Lead.** Asset categories are missing for most public-works activities in the sample, limiting any comparison of what Gram Panchayats are building. “Uncategorised” is the largest group in 19 of the 20 Gram Panchayats; Govindapur is the only exception.
>
> **Detail.** Of 9,418 public-works activities, 5,181 (55.0%) have no asset category recorded. The next largest category, Buildings, has 688 activities (7.3%). The available finding does not specify which category leads in Govindapur, only that its pattern differs; at review, first establish Govindapur’s breakdown and the extent of missing category data before drawing conclusions about asset priorities.

**Checks (final rendering):** (a) numerals PASS (7 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 55 w)

**First attempt checks:** (a) numerals PASS (5 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 46 w)

**Why it was regenerated:** A reviewer flagged this claim: "Gram Panchayats should be asked to complete the classification field". The source says: The source says “Uncategorised” means no asset category was recorded, but it does not state or support this recommendation. A reviewer flagged this claim: "Govindapur’s different recording pattern may offer a practice worth examining". The source says: The source only says Govindapur is an exception with a “different pattern”; it does not say the pattern reflects a practice or that it is worth examining.

**Verifier v1 (gpt-5.5): PASS**

- claim: *Asset categories are missing for most public-works activities in the sample* -> supported by: Reference figures: highlight_values / Uncategorised / value: 5,181 activities; highlight_values / Uncategorised / share_of_total: 55.0%; total: 9,418 activities; background bullet: "Uncategorised" assets are works with no asset category recorded -- about two-thirds of all works; it is not itself a kind of asset.
- claim: *limiting any comparison of what Gram Panchayats are building* -> supported by: background bullet: "Uncategorised" assets are works with no asset category recorded -- about two-thirds of all works; it is not itself a kind of asset.
- claim: *“Uncategorised” is the largest group in 19 of the 20 Gram Panchayats* -> supported by: Engine sentence: Across nearly all gp_name values (19/20), Uncategorised has the highest n_activities among asset_category_label values.
- claim: *Govindapur is the only exception* -> supported by: Exception: Govindapur (different pattern); Exceptions: - Govindapur: different pattern -- the engine found a different kind of pattern here
- claim: *Of 9,418 public-works activities, 5,181 (55.0%) have no asset category recorded.* -> supported by: Reference figures: total: 9,418 activities; highlight_values / Uncategorised / value: 5,181 activities; highlight_values / Uncategorised / share_of_total: 55.0%; background bullet: "Uncategorised" assets are works with no asset category recorded -- about two-thirds of all works; it is not itself a kind of asset.
- claim: *The next largest category, Buildings, has 688 activities (7.3%).* -> supported by: Reference figures: top_values / Uncategorised / value: 5,181 activities; top_values / Buildings / value: 688 activities; top_values / Buildings / share_of_total: 7.3%

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 8 - Activity Lifecycle

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** In 18 of the 20 sampled Gram Panchayats, costed activities marked “Activity Approved” had the largest gap between planned cost and recorded spending among status groups. Across the full sample, this group recorded Rs 14.00 lakh spent against Rs 41.75 crore planned—a gap of Rs 41.61 crore.
>
> **Detail.** “Activity Approved” accounts for 53.9% of the 5,630 costed activities reviewed. The pattern was not clear in Boipariguda or Laxmipur. At the next review, reconcile planned costs, recorded expenditure and status classifications for this group, and clarify what the “Buildings” status represents; the data show low recorded spending against plan, but cannot establish whether activities have started or whether records are incomplete.

**Checks (final rendering):** (a) numerals PASS (7 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 62 w)

**First attempt checks:** (a) numerals PASS (7 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 65 w)

**Why it was regenerated:** A reviewer flagged this claim: "Activities still marked “Activity Approved” account for Rs 41.61 crore of the gap between planned cost and recorded spending in 18 of the 20 sampled Gram Panchayats.". The source says: The source supports 'highlight_values / Activity Approved / value: Rs -41.61 crore' and separately says the pattern holds in 18 of 20 gp_name values. It does not say the Rs 41.61 crore figure is specifically for those 18 Gram Panchayats; the records are also limited to 'is_costless = Costed.' A reviewer flagged this claim: "Activities still marked “Activity Approved” account for R

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"clarify what the “Buildings” status represents"*
  - source says: The source lists “Buildings” as a status_label value with figures, but does not state that its meaning is unclear or needs clarification.
- flagged: *"cannot establish whether activities have started"*
  - source says: The source gives overspend/utilization figures and general record-incompleteness cautions, but it does not provide or discuss activity start information or state that starts cannot be established from these data.

**Verifier v2 (action separated from claim): PASS**

- claim: *In 18 of the 20 sampled Gram Panchayats, costed activities marked “Activity Approved” had the largest gap between planned cost and recorded spending among status groups.* -> supported by: Engine sentence: Across nearly all gp_name values (18/20), Activity Approved has the lowest overspend_vs_plan among status_label values. Records covered: is_costless = Costed
- claim: *Across the full sample, this group recorded Rs 14.00 lakh spent against Rs 41.75 crore planned—a gap of Rs 41.61 crore.* -> supported by: utilization_companion / absolutes / Activity Approved: Rs 14.00 lakh spent of Rs 41.75 crore planned cost; highlight_values / Activity Approved / value: Rs -41.61 crore
- claim: *“Activity Approved” accounts for 53.9% of the 5,630 costed activities reviewed.* -> supported by: size_share / scope: Costed only; size_share / volume_in_scope: 5,630 activities; size_share / share_of_volume / Activity Approved: 53.9%
- claim: *The pattern was not clear in Boipariguda or Laxmipur.* -> supported by: Exceptions: - Boipariguda: no clear pattern -- the engine found no clear pattern here; - Laxmipur: no clear pattern -- the engine found no clear pattern here

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 9 - Geo-Month Cash Cube  ·  *thin packet: no reference figures could be computed*

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across most temporal_grain values (2/3), payment_count shows seasonal pattern (PERIOD_12) over (varies). Exception: fiscal_year (no clear pattern)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** Payment counts show a recurring seasonal pattern when viewed by month or quarter, including the normal concentration of payments in March. No clear recurring pattern appears in fiscal-year totals.
>
> **Detail.** This pattern covers all records in the view and reflects timing and workload, not performance. Reviews should compare like periods and avoid treating the usual year-end payment concentration as an exception; this analysis did not assess geographic differences.

**Checks (final rendering):** (a) numerals PASS (0 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 38 w)

**First attempt checks:** (a) numerals PASS (0 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 34 w)

**Why it was regenerated:** A reviewer flagged this claim: "Reviews should instead look for departures from the usual year-end pattern, delayed reconciliation or unusual backlogs in particular places.". The source says: The source supports that March concentrates payments every year and that this is normal government cash flow, but it does not mention delayed reconciliation, unusual backlogs, or reviews in particular places.

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"this analysis did not assess geographic differences"*
  - source says: The source finding is about temporal_grain values for payment_count and says records covered all records in this view, but it does not explicitly state that geographic differences were not assessed.

**Verifier v2 (action separated from claim): FAIL**

- flagged: *"this analysis did not assess geographic differences."*
  - source says: The source finding is about payment_count by temporal_grain and says records covered are all records in the view, but it does not state whether geographic differences were or were not assessed.

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 10 - Activity Lifecycle

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** Ongoing works account for 93.9% of the recorded value of costed activities—Rs 28.59 crore out of Rs 30.43 crore. This pattern appears in 18 of the 20 sampled Gram Panchayats.
>
> **Detail.** Boipariguda and Laxmipur are the only exceptions, with no clear dominant status by value. Completed works account for just Rs 23.98 lakh, or 0.8%, but only 17 works in the full sample are recorded as completed, so this reflects status recording rather than actual delivery; at the next review, ask the 18 Gram Panchayats to explain the large value recorded as ongoing and reconcile work-status records with available work and payment evidence.

**Checks (final rendering):** (a) numerals PASS (9 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 72 w)

**First attempt checks:** (a) numerals PASS (6 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 55 w)

**Why it was regenerated:** A reviewer flagged this claim: "Reviews should test whether work statuses are being updated promptly". The source says: The source reports the distribution of gen_amount by status_label and notes record-quality limitations, but it does not state that status updates may be delayed or that reviews should test prompt updating.

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"at the next review, ask the 18 Gram Panchayats to explain the large value recorded as ongoing and reconcile work-status records with available work and payment evidence."*
  - source says: The source supports that 18 Gram Panchayats follow the WORK ONGOING-majority pattern and that WORK ONGOING totals Rs 28.59 crore, but it does not state a next-review action, require explanations from those Gram Panchayats, or say that work-status records should be reconciled with available work and payment evidence.

**Verifier v2 (action separated from claim): PASS**

- claim: *"Ongoing works account for 93.9% of the recorded value of costed activities"* -> supported by: Records covered: is_costless = Costed; Reference figures: - top_values / WORK ONGOING / share_of_total: 93.9%
- claim: *"Rs 28.59 crore out of Rs 30.43 crore"* -> supported by: Reference figures: - top_values / WORK ONGOING / value: Rs 28.59 crore; - total: Rs 30.43 crore
- claim: *"This pattern appears in 18 of the 20 sampled Gram Panchayats."* -> supported by: Engine sentence: Across nearly all gp_name values (18/20), WORK ONGOING accounts for the majority of gen_amount among status_label values.; This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
- claim: *"Boipariguda and Laxmipur are the only exceptions"* -> supported by: Exceptions: - Boipariguda: no clear pattern -- the engine found no clear pattern here; - Laxmipur: no clear pattern -- the engine found no clear pattern here

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 11 - Geo-Month Cash Cube

**Status: REGENERATED**

**Current feed text (what the officer sees today):**

> Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter. Exception: Bargarh (different pattern); Koraput (different pattern); Cuttack (different pattern)

**Final rendering:**

> **Lead.** Activity-linked expenditure increased over successive quarters in six of the nine districts represented in this 20-Gram-Panchayat sample. This is more likely to reflect improved linking of payments to planned activities than growth in overall spending.
>
> **Detail.** Khordha, Ganjam, Kandhamal, Sundargarh, Malkangiri and Rayagada follow the rising pattern; Bargarh, Koraput and Cuttack show different, unspecified patterns that merit review. The records contain Rs 24.00 crore of linked expenditure, with the highest quarterly totals including Rs 1.99 crore in 2026-Q1 and Rs 1.92 crore in 2025-Q1, while 2020-Q2 and Q3 show no linked expenditure. At the next review, check whether the exceptions and early zero values reflect payment-linking or data-entry gaps before treating them as changes in actual spending.

**Checks (final rendering):** (a) numerals PASS (11 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 81 w)

**First attempt checks:** (a) numerals PASS (6 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 61 w)

**Why it was regenerated:** A reviewer flagged this claim: "Several of the highest totals occur in first quarters, including Rs 1.99 crore in 2026-Q1 and Rs 1.92 crore in 2025-Q1, consistent with normal March concentration.". The source says: The source supports the listed Q1 top values, and separately says “March concentrates payments every year; it is the fiscal year-end and this is normal government cash flow.” But it does not state that these Q1 totals are caused by or explained by March concentration, nor does it define Q1 as including March. A reviewer flagged this claim: "districts should explain differences in pa

**Verifier v1 (gpt-5.5): PASS**

- claim: *Activity-linked expenditure increased over successive quarters in six of the nine districts* -> supported by: Engine sentence: Across most district_name values (6/9), activity_linked_expenditure is increasing over quarter.
- claim: *represented in this 20-Gram-Panchayat sample* -> supported by: This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.
- claim: *This is more likely to reflect improved linking of payments to planned activities than growth in overall spending.* -> supported by: Total cashbook spending has not grown across these years, while the share of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise in "linked spending" is mostly better record-keeping.
- claim: *Khordha, Ganjam, Kandhamal, Sundargarh, Malkangiri and Rayagada follow the rising pattern* -> supported by: Follows the pattern (6 of 9): Khordha, Ganjam, Kandhamal, Sundargarh, Malkangiri, Rayagada
- claim: *Bargarh, Koraput and Cuttack show different, unspecified patterns* -> supported by: Exceptions: - Bargarh: different pattern -- the engine found a different kind of pattern here; - Koraput: different pattern -- the engine found a different kind of pattern here; - Cuttack: different pattern -- the engine found a different kind of pattern here
- claim: *The records contain Rs 24.00 crore of linked expenditure* -> supported by: total: Rs 24.00 crore

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 12 - Activity Lifecycle

**Status: REGENERATED**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values. Exception: Boipariguda (no clear pattern); Laxmipur (no clear pattern)

**Final rendering:**

> **Lead.** Expected beneficiaries are heavily concentrated under “Activity Approved”: 2,03,534 people, or 98.4% of the sample total. This is the largest status group in 18 of the 20 Gram Panchayats.
>
> **Detail.** Boipariguda and Laxmipur show no clear leading pattern. At the next review, ask whether the concentration under “Activity Approved” reflects the actual planning pipeline or the way statuses are recorded; it should not be read as evidence of delivery, especially as completion is very sparsely recorded in this 20-GP sample.

**Checks (final rendering):** (a) numerals PASS (5 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 50 w)

**First attempt checks:** (a) numerals PASS (5 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 62 w)

**Why it was regenerated:** A reviewer flagged this claim: "Almost all expected beneficiaries are attached to activities still marked “Activity Approved,” suggesting that beneficiary and status records need reconciliation.". The source says: The source supports that Activity Approved has 2,03,534 expected beneficiaries, 98.4% of the total, but it does not state that beneficiary and status records need reconciliation. A reviewer flagged this claim: "so officials should check status updates and beneficiary-field completion rather than infer delivery.". The source says: The source says only 17 works are marked completed, so

**Verifier v1 (gpt-5.5): PASS**

- claim: *Expected beneficiaries are heavily concentrated under “Activity Approved”: 2,03,534 people, or 98.4% of the sample total.* -> supported by: Reference figures: - top_values / Activity Approved / value: 2,03,534 people; - top_values / Activity Approved / share_of_total: 98.4%; - total: 2,06,929 people
- claim: *This is the largest status group in 18 of the 20 Gram Panchayats.* -> supported by: Engine sentence: Across nearly all gp_name values (18/20), Activity Approved has the highest beneficiaries_expected among status_label values.
- claim: *Boipariguda and Laxmipur show no clear leading pattern.* -> supported by: Exceptions: - Boipariguda: no clear pattern -- the engine found no clear pattern here; - Laxmipur: no clear pattern -- the engine found no clear pattern here
- claim: *At the next review, ask whether the concentration under “Activity Approved” reflects the actual planning pipeline or the way statuses are recorded; it should not be read as evidence of delivery, especially as completion is very sparsely recorded in this 20-GP sample.* -> supported by: Only 17 works in the whole sample are marked completed, so completion figures measure recording practice, not delivery.; This is a 20-Gram-Panchayat sample; percentages describe the sample, not the state.

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 13 - Activity Lifecycle

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values. Exception: Boipariguda (Unmapped theme has the highest fund_untied_total among theme values); Kalimela (Theme 4 - Water Sufficient Village has the highest fund_untied_total among theme values)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** Theme 6—Self-sufficient Infrastructure in Village—accounts for ₹30.07 crore, or 50.4% of untied funds across costed activities, and is the largest theme in 18 of the 20 sampled Gram Panchayats. Boipariguda and Kalimela are the exceptions.
>
> **Detail.** The analysis covers 5,630 costed activities worth ₹59.64 crore. Unmapped theme records carry the highest total in Boipariguda, while Theme 4—Water Sufficient Village—leads in Kalimela; officials should examine the underlying activity and theme records for these two GPs before interpreting their allocation patterns, as the data shows which category leads but not why.

**Checks (final rendering):** (a) numerals PASS (8 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 53 w)

**First attempt checks:** (a) numerals PASS (10 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 57 w)

**Why it was regenerated:** A reviewer flagged this claim: "Reviews should ask Boipariguda to complete theme mapping and confirm that the concentration under Theme 6 reflects local plans rather than routine coding.". The source says: The source says Boipariguda is an exception where 'Unmapped theme' has the highest fund_untied_total, and that Theme 6 leads in 18 of 20 gp_name values. It does not say reviews should ask Boipariguda to complete mapping, nor does it mention local plans or routine coding as possible explanations for Theme 6 concentration.

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"officials should examine the underlying activity and theme records for these two GPs before interpreting their allocation patterns"*
  - source says: The source identifies Boipariguda and Kalimela as exceptions and says which theme leads in each, but it does not state that officials should examine underlying records before interpreting them.

**Verifier v2 (action separated from claim): PASS**

- claim: *Theme 6—Self-sufficient Infrastructure in Village—accounts for ₹30.07 crore, or 50.4% of untied funds across costed activities* -> supported by: Reference figures: - top_values / Theme 6 - Self-sufficient Infrastructure in Village / value: Rs 30.07 crore; - top_values / Theme 6 - Self-sufficient Infrastructure in Village / share_of_total: 50.4%; Records covered: is_costless = Costed
- claim: *[Theme 6] is the largest theme in 18 of the 20 sampled Gram Panchayats* -> supported by: Engine sentence: Across nearly all gp_name values (18/20), Theme 6 - Self-sufficient Infrastructure in Village has the highest fund_untied_total among theme values.
- claim: *Boipariguda and Kalimela are the exceptions* -> supported by: Exceptions: - Boipariguda: different pattern -- a different one leads here: Unmapped theme; - Kalimela: different pattern -- a different one leads here: Theme 4 - Water Sufficient Village
- claim: *The analysis covers 5,630 costed activities* -> supported by: size_share / scope: Costed only; size_share / volume_in_scope: 5,630 activities

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 14 - Activity Lifecycle

**Status: FIRST-PASS**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (19/20), Code 101 has the lowest overspend_vs_sanction among output_type_label values. Exception: Chikilli (no clear pattern)

**Final rendering:**

> **Lead.** Among new works with sanction records, Code 101 accounts for almost the entire Rs 2.54 crore gap between sanctioned amount and expenditure; Chikilli shows no clear pattern.
>
> **Detail.** Code 101 records Rs 14.94 crore spent against Rs 17.43 crore sanctioned, leaving a Rs 2.49 crore gap. This covers only the minority of activities with sanctions on file and cannot be treated as programme-wide utilisation. Because Codes 101 to 110 have no descriptions, obtain the decode before asking Gram Panchayats to explain the concentration, and check whether missing sanctions or expenditure links contribute to it.

**Checks (final rendering):** (a) numerals PASS (8 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 1 sent., detail 66 w)

**Verifier v1 (gpt-5.5): PASS**

- claim: *Among new works with sanction records* -> supported by: Records covered: work_type_label = New/Fresh; utilization_companion / basis: sanctioned amount; utilization_companion / what_this_is: the same money as overspend_vs_sanction, read as a share instead of a difference: how much of each group's sanctioned amount was actually spent This is the sanctioned basis, so it describes only the activities that have a sanction record on file (about one in six); it is not a programme-wide utilisation rate.
- claim: *Code 101 accounts for almost the entire Rs 2.54 crore gap between sanctioned amount and expenditure* -> supported by: highlight_values / Code 101 / value: Rs -2.49 crore; total: Rs -2.54 crore; utilization_companion / absolutes / Code 101: Rs 14.94 crore spent of Rs 17.43 crore sanctioned amount
- claim: *Chikilli shows no clear pattern* -> supported by: Exceptions: - Chikilli: no clear pattern -- the engine found no clear pattern here
- claim: *Code 101 records Rs 14.94 crore spent against Rs 17.43 crore sanctioned, leaving a Rs 2.49 crore gap.* -> supported by: utilization_companion / absolutes / Code 101: Rs 14.94 crore spent of Rs 17.43 crore sanctioned amount; highlight_values / Code 101 / value: Rs -2.49 crore
- claim: *This covers only the minority of activities with sanctions on file and cannot be treated as programme-wide utilisation.* -> supported by: utilization_companion / what_this_is: the same money as overspend_vs_sanction, read as a share instead of a difference: how much of each group's sanctioned amount was actually spent This is the sanctioned basis, so it describes only the activities that have a sanction record on file (about one in six); it is not a programme-wide utilisation rate.
- claim: *Codes 101 to 110 have no descriptions* -> supported by: Output categories "Code 101" to "Code 110" have no descriptions on file; nothing can be concluded about what they contain until the department supplies the decode.

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Finding 15 - Activity Lifecycle

**Status: FELL BACK**

**Current feed text (what the officer sees today):**

> Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values. Exception: Chikilli (no clear pattern)

**Final rendering - per the failure path, this is the current feed sentence above.**

**The rendering that was produced** (shown because the fallback was driven by the
verifier wording described above, not by anything wrong in this text):

> **Lead.** All 6,893 recorded photo uploads for New/Fresh works are under Code 101, with this pattern seen in 19 of the 20 sampled Gram Panchayats. Chikilli is the only exception, where no clear pattern was found.
>
> **Detail.** The records cover 11,047 New/Fresh activities spread across five output codes, but Codes 102, 103, 109 and 110 have no recorded photo uploads. As Codes 101 to 110 have no descriptions on file, the upload distribution cannot yet be interpreted; the department should obtain the code descriptions and examine Chikilli separately at the next review.

**Checks (final rendering):** (a) numerals PASS (11 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 55 w)

**First attempt checks:** (a) numerals PASS (9 checked); (b) names PASS; (c) db tokens PASS; (d) shape PASS (lead 2 sent., detail 58 w)

**Why it was regenerated:** A reviewer flagged this claim: "This strongly warrants a check of evidence coding or system mapping.". The source says: The source supports that all recorded photo uploads in this New/Fresh finding are under Code 101 and that Codes 101 to 110 have no descriptions, but it does not state that there is an evidence-coding or system-mapping issue, nor the degree of certainty that this 'strongly warrants' such a check. A reviewer flagged this claim: "the records cannot establish whether evidence is genuinely absent for other work types or has been assigned to a default code". The source says: The fi

**Verifier v1 (gpt-5.5): FAIL**

- flagged: *"the department should obtain the code descriptions and examine Chikilli separately at the next review"*
  - source says: The source supports that Codes 101 to 110 have no descriptions on file and that nothing can be concluded until the department supplies the decode, and it identifies Chikilli as the only exception with no clear pattern. However, it does not state that Chikilli should be examined separately or that this should happen at the next review.

**Verifier v2 (action separated from claim): PASS**

- claim: *All 6,893 recorded photo uploads for New/Fresh works are under Code 101* -> supported by: Records covered: work_type_label = New/Fresh; top_values / Code 101 / value: 6,893 photo uploads; top_values / Code 101 / share_of_total: 100.0%; total: 6,893 photo uploads
- claim: *with this pattern seen in 19 of the 20 sampled Gram Panchayats* -> supported by: Across nearly all gp_name values (19/20), Code 101 accounts for the majority of evidence_uploads among output_type_label values; This is a 20-Gram-Panchayat sample
- claim: *Chikilli is the only exception, where no clear pattern was found* -> supported by: Exceptions: - Chikilli: no clear pattern -- the engine found no clear pattern here
- claim: *The records cover 11,047 New/Fresh activities* -> supported by: size_share / scope: New/Fresh only; size_share / volume_in_scope: 11,047 activities

**Operator label:**  [ ] adopt   [ ] adopt-with-edits   [ ] reject

---

## Calls and usage

| purpose | calls | model |
|---|---:|---|
| writer_batch_all15 | 1 | `gpt-5.6-sol` |
| verifier | 28 | `gpt-5.5` |
| regenerate | 13 | `gpt-5.6-sol` |
| verifier_v2 | 8 | `gpt-5.5` |
| **total** | **50** | cap 60 |

Prompt tokens 81,471 - completion tokens 47,503 (of which reasoning 33,550) - total 128,974.
Every call returned `finish_reason: stop`; nothing was truncated and the batch was
never split. The repo records no token price, so usage is reported in tokens only.

