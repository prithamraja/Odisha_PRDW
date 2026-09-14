# Eval_1 full replay after WP-6 (PM-run, 2026-09-14)

**What:** every non-blank row of `Eval_1.xlsx` (314 questions, 28 question groups) posted once to the live `/query` endpoint from the `C:\dev\odisha-wp6` mirror at HEAD `8a93ced`, one fresh session per question. Harness: `Ask/run_custom_eval.py`. Inputs and raw results: `handoffs/WP6_eval1_questions.json`, `handoffs/WP6_eval1_replay.jsonl`.

**How graded:** each row range has an accepted set of template ids (the 2026-09-12 matching table, updated for WP-6's folds). A row is a **hit** if the served id is in the set; a **clarification** if the bot asked; **wrong** otherwise. Hits were then spot-checked on the bound filters, which moved one whole group (see finding 1). The "sector" group (rows 280-290) is expected to clarify by operator ruling and is graded as a hit when it does.

## Headline

| outcome | rows | share |
|---|--:|--:|
| correct answer | 213 | 68% |
| asked a clarifying question | 73 | 23% |
| of which the right template was among the chips | 58 | |
| wrong answer or answer that lost the question | 28 | 9% |

Compared with WP-6's own T7 replay (96-98% on 52 chosen rows), this is the same system on all 314 phrasings, with a clarification counted as a miss rather than as correct behaviour, and with hits checked on their filters, not only on their template id.

## By question group

| group | n | correct | clarify | wrong |
|---|--:|--:|--:|--:|
| total planned budget, main GPDPs | 14 | 12 | 2 | 0 |
| GPs with zero-cost activities | 18 | 9 | 9 | 0 |
| Swachh Bharat sanitation completed | 18 | 10 | 8 | 0 |
| total unspent statewide | 6 | 6 | 0 | 0 |
| tied spend, water vs sanitation | 12 | 9 | 0 | 3 |
| allocation to Sankalp themes | 12 | 12 | 0 | 0 |
| GPs with nothing under Sankalp themes | 12 | 10 | 2 | 0 |
| GPs uploaded main GPDP (defective rows, two years named) | 12 | 12 | 0 | 0 |
| GPs not uploaded GPDP | 12 | 12 | 0 | 0 |
| supplementary plans approved | 12 | 0 | 10 | 2 |
| GPs with a supplementary plan in Ganjam | 12 | 12 | 0 | 0 |
| total activities in main GPDPs | 12 | 9 | 3 | 0 |
| GP with most planned activities | 12 | 0 | 12 | 0 |
| total estimated cost statewide | 12 | 0 | 8 | 4 |
| planned activities by theme | 12 | 8 | 0 | 4 |
| activities under sanitation | 12 | 12 | 0 | 0 |
| GP with most piped-water activities | 12 | 9 | 3 | 0 |
| GPs pending GPDP approval | 12 | 12 | 0 | 0 |
| completed activities statewide | 11 | 7 | 1 | 3 |
| activities in progress | 11 | 11 | 0 | 0 |
| sector with best completion rate (expected: ask) | 11 | 10 | 0 | 1 |
| road works in progress | 11 | 0 | 1 | 10 |
| districts behind on GPDP submission | 11 | 9 | 1 | 1 |
| GPs with spend but no physical progress | 11 | 11 | 0 | 0 |
| district-wise asset creation | 11 | 4 | 7 | 0 |
| five-year fund utilisation | 13 | 7 | 6 | 0 |

## Findings, in order of harm

1. **"Road construction" is not recognised as the Roads focus area, and the bot answers anyway.** All ten served rows in the road-works group bound only the status. The answer is the count of every ongoing activity (400 for 2024-25) presented as road works. The echo does not say "Roads", so a careful reader can see the filter is missing, but the number is wrong for the question asked. The fix is an alias, the way "piped water" already resolves to Drinking water. The larger point: when a question names a subject the extractor did not bind, answering silently is the confidently-wrong class. Ten rows, all wrong, all stable.
2. **Two list-valued filters at once lose the comparison.** Row 44, "sector-wise expenditure of tied funds for water and sanitation for 2024 to 2026", bound both a two-year list and a two-focus-area list. The automatic breakdown chose the year, so the answer is two rows, one per year, with water and sanitation summed inside each. The question asked for the opposite. Rule needed: when a non-year dimension carries a list, it wins the breakdown; the year list becomes a second grouping or a stated combination.
3. **Zero counts render as "No records matched".** Row 19, completed sanitation activities for 2025-26, and rows 246 and 257, GPs pending approval across two years, all returned no rows instead of a row saying 0. WP-6 fixed this for three templates with the grouping-sets change; the fix did not reach STS-003 with a focus-area filter, or PLN-014 with a year breakdown. A count question must never answer "nothing was found".
4. **Swachh Bharat still goes to the SBM entries.** The alias binds Sanitation correctly when STS-003 is chosen (10 of 18). The other 8 times the reranker asks, and 7 of those 8 offer only SBM soak-pit and toilet entries, not the template that would have answered. This is row #2005 from the WP-6 report, at full scale.
5. **Four groups clarify almost every time even though the right template is on the chips.** "GP with most planned activities" (12 of 12 ask, PLN-031 offered 11 times), "supplementary plans approved" (10 of 12 ask, PLU-004 offered every time), "district-wise asset creation" (7 of 11 ask), "five-year fund utilisation" (6 of 13 ask). These are reranker confidence problems, not retrieval problems, and each is one disambiguation note away from answering.
6. **Total estimated cost never lands on the expected template.** BUD-006 with the total breakdown answers "total planned budget" (group 1) reliably but not "total estimated cost" (group 21). Two rows went to SCH-003 with no scheme bound, which is actually the right number; two went to BUD-001, per-GP funding recorded, which is not.
7. **Minor.** PLN-072 "are activities balanced across themes" answers "distribution across themes" 4 times; it returns per-theme counts so the reader gets what they asked for under the wrong echo. PLN-023, a refusal about consistent delays, answered "districts with delayed submissions" once; defensible. TRD-002 was chosen once with both years set to the same year.

## What this says about WP-6

The structural gaps the package targeted are closed. Plan type, breakdowns, totals, lists of years, the Ganjam district filter, the new physical-progress template and the Sankalp reading all work on every phrasing. The remaining losses are in three places that were outside WP-6's scope: entity aliases for subjects officers name (roads), the reranker's confidence on templates it has correctly retrieved, and presentation of zero counts. Finding 2 is WP-6's own and should be fixed in WP-6b.

## For WP-6b

Add to the brief: the Roads alias and a guard for unbound subjects (finding 1); the two-list breakdown rule (finding 2); zero-count rendering on every counting template (finding 3); disambiguation notes for the four groups in finding 5 and the SBM confusion in finding 4, measured by re-running this file.
