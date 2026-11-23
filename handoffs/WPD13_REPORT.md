# WP-D13 report — Insight report fixes

**For:** the PM and the operator. **Executed:** Fix 1 on 2026-11-21; Fix 1b
and Fix 6 on 2026-11-22; Fix 9 and Fix 10 on 2026-11-23. Fix 10 is frontend
only, built in the frontend mirror `C:\dev\ab-dashboard-odisha`. Mirror `C:\dev\odisha-d13`
(refreshed from HEAD `925511e` on 2026-11-22, and on 2026-11-23 brought up to
the Drive copy's model settings, as the standing rules ask). One section per fix. Fix 2 moved to its own brief
(`handoffs/WPD13b_headline_trial.md`, reported in `handoffs/WPD13b_REPORT.md`).
Fix 7 is reported in `handoffs/WPD12_REPORT.md`.

---

# Fix 1 — Direction in words, and a check that catches a reversed direction

## Outcome in one paragraph

T1 and T2 are built and green. The writer is now handed "Rs 51.96 crore below
plan" instead of "Rs -51.96 crore", and in the live trial it **never wrote a
minus sign or "above plan" in 46 attempts**. The direction check works on the
brief's cases, but live it fired only on correct sentences: the writer names a
shortfall once and then lists its parts ("Sharagada accounts for Rs 3.36 crore
of the gap") without repeating "below plan". Under `block`, 2 of 12 answers fell
back because of that — over the brief's limit of 1. **So the default shipped is
`log`, and Fix 1 STOPS here** for the PM's ruling on a looser R1. Every failing
sentence is listed in §5 so the operator can overrule my calls.

## 1. Commits (current branch, not pushed)

| Commit | Task |
|---|---|
| `6faea99` | T1: signed figures state their direction in words (+ the brief) |
| `e3f4f30` | T2: the direction check, tests, gate additions |
| T3 commit | T3: the live trial, its results, the default (`log`) and this report |

## 2. Gates and tests, baseline vs final

| | Baseline (HEAD `477350e`) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 34/34 green | **35/35 green** |
| `python -m pytest DiscoverChat/tests -q` | 92 passed, 1 failed | **111 passed, 1 failed** |

The one failure is the same test in both runs and predates this work:
`test_citations.py::WriterPromptTests::test_the_prompt_is_the_operators_text`
looks for the line "Do not make causal claims ever", which the operator's
2026-09-11 edit to `context_brief.py` replaced. Not touched: that file is the
operator's.

Gate changes: new check `signed-direction-in-words` (the corpus sweep), and a
reversed-direction case added to `citation-checks-fire` (now 7 seeded
violations, all caught).

## 3. T1 — direction in words

- `glossary.signed_money(text, measure)` rewrites every `Rs -N[ lakh| crore]`
  as `Rs N[ lakh| crore] below plan` (or `below sanction`). It works on a bare
  value too: `signed_money("Rs -51.96 crore", "overspend_vs_plan")` →
  `"Rs 51.96 crore below plan"`, for WP-D12's cards and charts.
- `glossary.direction_in_words(...)` applies it and drops the "This measure is
  signed: …" sentence when `signs == "all_negative"`; kept for `mixed` and
  `all_positive`.
- `Finding.display_sentence()` calls it after the column translation, for
  decompositions only. The glossary docstring is updated.
- The "below" and "above" words are imported from
  `phase5f_decompose._SIGNED_DIRECTION`. The builder does not export the
  sign-convention sentence itself, so `glossary.signed_note()` rebuilds its
  frame around those words. The sweep asserts it is found verbatim in all
  5,717 records, so a wording change in the builder fails the gate loudly.

**Corpus sweep (test and gate, all records of both corpora):**

| | Count |
|---|---|
| Signed decompositions | 5,717 (5,420 all negative, 281 mixed, 16 all positive) — matches the brief |
| `Rs -` figures in the stored sentences | 18,984 — matches the brief |
| "below" phrases added | 18,984 |
| Display sentences still showing `Rs -` | 0 |
| Records whose digits changed | 0 |
| Sign sentence present exactly when not all-negative | 5,717 of 5,717 |
| Other records, display sentence unchanged | 65,466 of 65,466 |

Example, `d1-00248`: "…spending measured against plan totals Rs 51.96 crore
below plan across 4 tied or untied grant values. It is concentrated: (not
recorded) accounts for 90.3% of it (Rs 46.90 crore below plan). …"

## 4. T2 — the direction check (`5_direction`)

Built as briefed: same sentence split and same `bind_numerals` bindings as
step 2; R1, R2, R3; one "below plan" covers the sentence; a sentence with
shares or counts only is not checked. Mode `DISCOVERCHAT_DIRECTION_CHECK`
(`block` | `log` | `off`), read at call time. `check_citations` also takes
`direction_mode=` for one call (the tests and the gate pin `block` with it).
In `log` mode the step is recorded but neither counts towards `all_pass` nor
goes into the retry reason, so the writer's behaviour is unchanged.

The retry reason quotes the failing sentences and gives the figure as the
finding has it, for example: *These sentences do not give the direction of a
spending figure as the finding gives it: "Recorded spending is Rs 51.96 crore
above plan.". Write each figure's direction exactly as the finding gives it --
"Rs 51.96 crore below plan" -- not with a minus sign and not in other words.*

**The five sentences of §1.1, now (block mode):**

| Prose | `all_pass` | Failed on |
|---|---|---|
| "…totals Rs -51.96 crore" | False | R2 (and R1) |
| "…Rs 51.96 crore below plan" | **True** | — |
| "…Rs 51.96 crore above plan" | False | R1, R3 |
| "Spending exceeded the plan by Rs 51.96 crore" | False | R1 |
| "…Rs 61.96 crore below plan" | False | step 2 |

**Calls I made where the brief was open:**

- *Ambiguous tokens.* I read the brief literally: a figure is skipped if the
  stored sentence shows it with a minus **and anywhere without one**, as money,
  a share or a count. That gives 50 records / 50 tokens. The brief's 49 counts
  money only; the one extra is a figure that also appears as a non-money
  number, which the writer could be quoting. Skipped in the trial: **0**.
- *R3's exception* counts a positive money figure only when it is bound to a
  signed record. "Above plan" means nothing for other measures.
- *R2* treats a hyphen, Unicode minus or en dash as a minus sign when it comes
  straight before a digit and not after a letter or digit, or after "Rs". So
  "2023-24", "d1-00248" and "Code-101" pass.

## 5. T3 — the live trial

**Design.** `DiscoverChat/experiments/run_direction_trial.py`, output
`direction_trial_results.json`. Retrieval and the judge once per question,
then the production `writer.consolidate`, unmodified, twice on the same
findings: once in `log`, once in `block`, in parallel within each arm. For
Cuttack only, a third run with the pre-fix display sentences and the step off.

**How the 12 questions were chosen.** The recorded answers in
`experiments/` predate the current corpus: only 7 of 38 recorded questions had
cited a signed record. So I ranked all 38, plus the Cuttack question, by how
many signed records sit in the top 20 of their retrieval pool. This used
query embeddings only, no chat model. I took the top ones, skipping "why"
questions (they get a reframe, not a written answer) and "What about the other
blocks?" (it needs a previous turn). In the event, **11 of 12 answers cited a
signed record**; Q7, "Who is driving the shortfall?", got three pattern
findings and no signed record.

**Results per answer:**

| # | Question | Findings (signed) | log: attempts, fell back on | block: attempts, fell back on |
|---|---|---|---|---|
| 1 | Is spending on track? | 5 (4) | 1 (pass) - answered | 2 (5_direction; pass) - answered |
| 2 | What makes up the underspend? | 6 (6) | 2 (3_causal,5_direction; 3_causal,5_direction) - **fell back** on 3_causal | 2 (3_causal; pass) - answered |
| 3 | What should I raise at the next review meeting? | 8 (7) | 2 (3_causal,5_direction; 2_numerals_cited,3_causal,5_direction) - **fell back** on 2_numerals_cited, 3_causal | 2 (3_causal,5_direction; pass) - answered |
| 4 | Where does the gap sit? | 3 (3) | 2 (3_causal,5_direction; 3_causal) - **fell back** on 3_causal | 2 (3_causal; 5_direction) - **fell back** on 5_direction |
| 5 | Which blocks account for the shortfall? | 1 (1) | 1 (pass) - answered | 2 (3_causal; pass) - answered |
| 6 | Which places are behaving differently from the rest? | 11 (1) | 1 (pass) - answered | 1 (pass) - answered |
| 7 | Who is driving the shortfall? | 3 (0) | 2 (3_causal; pass) - answered | 1 (pass) - answered |
| 8 | Where is money planned but not spent? | 12 (11) | 1 (5_direction) - answered | 2 (5_direction; pass) - answered |
| 9 | Anything worth my attention this quarter? | 8 (5) | 2 (3_causal; 5_direction) - answered | 2 (3_causal,5_direction; pass) - answered |
| 10 | How is Barpali block doing? | 8 (1) | 2 (3_causal; pass) - answered | 1 (pass) - answered |
| 11 | Anything I should be looking at in Ganjam? | 7 (1) | 2 (3_causal; pass) - answered | 2 (4_all_findings_cited; 5_direction) - **fell back** on 5_direction |
| 12 | What should I know about Cuttack? | 13 (1) | 1 (pass) - answered | 2 (3_causal; 3_causal) - **fell back** on 3_causal |

Step names: 2 = figure not in the cited finding, 3 = cause-and-effect wording, 4 = a finding left out, 5 = direction. In the log arm step 5 is recorded but does not count, so it appears in the list without causing a retry.

**Totals.**

| | log arm | block arm |
|---|---|---|
| Writer attempts | 19 (1.58 per answer) | 21 (1.75 per answer) |
| Sentences the step checked | 63 | 75 |
| Sentences failing the step | 30 (all R1) | 13 (all R1) |
| R2 (minus sign) / R3 ("above") failures | 0 / 0 | 0 / 0 |
| Answers that fell back | 3 — Q2, Q3, Q4, all on cause-and-effect wording (Q3 also on a figure) | 3 — **Q4 and Q11 on direction**, Q12 on cause-and-effect wording |
| Accepted answers whose final text fails step 5 | Q8, Q9 (shown, since the step only logs) | none |

**My classification.** All 43 failing sentences (13 in block, 30 in log) are
**false alarms**. None was wrong and none showed a minus sign. Each lists
parts of a shortfall that the sentence, or the text around it, calls a "gap",
"underspend" or "shortfall", without repeating "below plan". Under `block`,
2 answers (Q4, Q11) fell back because of them. **The rule allows at most 1,
so the default is `log` and Fix 1 stops here.** I have not loosened R1 or
added a synonym list.

Pattern, for the PM's ruling (description only): the failing sentences fall
into three shapes. (a) A figure called "the gap" or "the underspend"; (b) a
part of a gap named in the sentence before ("Sharagada accounts for 16.7% (Rs
3.36 crore)"); (c) a list of parts with no direction word at all ("Rural
housing accounts for Rs 2.13 crore, or 44.9%").

**Every failing sentence** (verbatim, tags kept; R1 = no "below plan" / "below
sanction" in the sentence):

**block arm**

1. Q1 attempt 1 - R1: no 'below plan' for d1-36141; R1: no 'below plan' for d1-44064. The finding gives: Rs 7.23 crore below plan, Rs 6.74 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Biswamathpur has the largest gap in both views—Rs 7.23 crore for costed activities [d1-36141] and Rs 6.74 crore for approved activities [d1-44064]—followed by Kalimela at Rs 5.90 crore [d1-36141] and Rs 5.46 crore [d1-44064], respectively.
2. Q1 attempt 1 - R1: no 'below plan' for d1-46759. The finding gives: Rs 3.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > This gap is also dispersed, led by Sharagada at Rs 3.36 crore and Biswamathpur at Rs 2.66 crore [d1-46759].
3. Q3 attempt 1 - R1: no 'below plan' for d1-46828. The finding gives: Rs 7.12 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Maintenance of community systems accounts for 35.4% (Rs 7.12 crore) and roads for 23.5% (Rs 4.74 crore), while the other six focus areas account for Rs 8.27 crore. [d1-46828]
4. Q4 attempt 2 - R1: no 'below plan' for d4-00049. The finding gives: Rs 7.23 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Biswamathpur has the largest share at 13.9% (Rs 7.23 crore), followed by Kalimela at 11.3% (Rs 5.90 crore); the other 18 account for Rs 38.84 crore. [d4-00049]
5. Q4 attempt 2 - R1: no 'below plan' for d1-49758. The finding gives: Rs 34.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > The same locations stand out when New/Fresh works are examined: the gap is Rs 34.36 crore, led by Biswamathpur at 15.8% (Rs 5.43 crore) and Kalimela at 11.5% (Rs 3.95 crore), while the remaining 18 account for Rs 24.98 crore. [d1-49758]
6. Q4 attempt 2 - R1: no 'below plan' for d1-46759. The finding gives: Rs 20.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > For Theme 6—Self-sufficient Infrastructure in Village—the gap is Rs 20.13 crore and is again dispersed across the sample. [d1-46759]
7. Q4 attempt 2 - R1: no 'below plan' for d1-46759. The finding gives: Rs 3.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Sharagada is the main location to examine under this theme, with 16.7% of the gap (Rs 3.36 crore) against 5.2% of activities, followed by Biswamathpur at 13.2% (Rs 2.66 crore); the other 18 account for Rs 14.12 crore. [d1-46759]
8. Q8 attempt 1 - R1: no 'below plan' for d1-39534. The finding gives: Rs 37.82 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Among 14 Gram Panchayats classified as near a bus stop, the total gap is Rs 37.82 crore; Kalimela accounts for 15.6% (Rs 5.90 crore) and Bheden for 14.8% (Rs 5.60 crore), while the remaining 12 account for Rs 26.33 crore. [d1-39534]
9. Q8 attempt 1 - R1: no 'below plan' for d1-27660; R1: no 'below plan' for d1-30622. The finding gives: Rs 51.17 lakh below plan, Rs 75.10 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > The main exceptions are Andhrua, where Uncategorised accounts for 50.1% (Rs 51.17 lakh) of the Rs 1.02 crore gap, and Hirlipali, where it accounts for 59.0% (Rs 75.10 lakh) of the Rs 1.27 crore gap. [d1-27660] [d1-30622]
10. Q8 attempt 1 - R1: no 'below plan' for d1-28703; R1: no 'below plan' for d1-28967; R1: no 'below plan' for d1-29842; R1: no 'below plan' for d1-27925; R1: no 'below plan' for d1-28178. The finding gives: Rs 2.09 crore below plan, Rs 1.70 crore below plan, Rs 91.35 lakh below plan, Rs 34.71 lakh below plan, Rs 22.81 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Uncategorised records are also the largest component in several other GPs, including Bheden at Rs 2.09 crore, Biswamathpur at Rs 1.70 crore, Dutimendi at Rs 91.35 lakh, Bandhpali at Rs 34.71 lakh and Barimunda at Rs 22.81 lakh, making these records a practical starting point for reconciliation. [d1-28703] [d1-28967] [d1-29842] [d1-27925] [d1-28178]
11. Q8 attempt 1 - R1: no 'below plan' for d1-29024; R1: no 'below plan' for d1-32203; R1: no 'below plan' for d1-30370. The finding gives: Rs 2.13 crore below plan, Rs 31.04 lakh below plan, Rs 21.81 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Category-specific review should also note Rural housing at Rs 2.13 crore and Drinking water at Rs 1.26 crore in Boipariguda, Buildings at Rs 31.04 lakh and Irrigation Sources at Rs 30.00 lakh in Mendarajpur, and Water Sources & Structures at Rs 21.81 lakh in Haldikudar. [d1-29024] [d1-32203] [d1-30370]
12. Q9 attempt 1 - R1: no 'below plan' for d1-29024. The finding gives: Rs 2.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Rural housing accounts for Rs 2.13 crore, or 44.9%, despite representing 0.9% of the 647 activities, while drinking water accounts for Rs 1.26 crore, or 26.5%. [d1-29024]
13. Q11 attempt 2 - R1: no 'below plan' for d4-02688. The finding gives: Rs 7.23 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > The gap is distributed across all four, led by Biswamathpur at 40.5% (Rs 7.23 crore) and Sharagada at 25.9% (Rs 4.63 crore) [d4-02688]; costless activities are led by Sharagada at 40.8% (722 activities) and Mendarajpur at 23.8% (421 activities) [d4-02684].

**log arm**

14. Q2 attempt 1 - R1: no 'below plan' for d1-47028. The finding gives: Rs 18.51 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Records without a fund component account for 91.9% [d1-47028], or Rs 18.51 crore [d1-47028], across 4,036 rows [d1-47028]; the remaining recorded components account for Rs 1.62 crore [d1-47028].
15. Q2 attempt 2 - R1: no 'below plan' for d1-47028. The finding gives: Rs 18.51 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 6—Self-sufficient Infrastructure in Village, Rs 18.51 crore of the Rs 20.13 crore underspend, or 91.9%, sits in 4,036 rows without a fund component; the five recorded components account for Rs 1.62 crore. [d1-47028]
16. Q2 attempt 2 - R1: no 'below plan' for d1-46072. The finding gives: Rs 11.69 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 4—Water Sufficient Village, unclassified records account for Rs 11.69 crore of the Rs 13.11 crore gap, or 89.2%, across 1,002 rows; the five recorded components account for Rs 1.42 crore. [d1-46072]
17. Q2 attempt 2 - R1: no 'below plan' for d1-46554. The finding gives: Rs 7.24 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 5—Clean and Green Village, 1,507 unclassified rows account for Rs 7.24 crore of the Rs 8.62 crore gap, or 84.1%, while the three recorded components account for Rs 1.37 crore. [d1-46554]
18. Q2 attempt 2 - R1: no 'below plan' for d1-45609. The finding gives: Rs 2.51 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 3—Child Friendly Village, 996 unclassified rows account for Rs 2.51 crore of the Rs 2.67 crore underspend, or 93.9%; the four recorded components account for Rs 16.41 lakh. [d1-45609]
19. Q2 attempt 2 - R1: no 'below plan' for d1-47492. The finding gives: Rs 2.20 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 8—Village with Good Governance, 1,681 such rows account for Rs 2.20 crore of the Rs 2.41 crore gap, or 91.3%; the six recorded components account for Rs 21.03 lakh. [d1-47492]
20. Q2 attempt 2 - R1: no 'below plan' for d1-45225. The finding gives: Rs 68.61 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 1—Poverty Free and Enhanced Livelihoods Village, 528 unclassified rows account for Rs 68.61 lakh of the Rs 69.31 lakh gap, or 99.0%; the two recorded components account for Rs 70,788. [d1-45225]
21. Q3 attempt 1 - R1: no 'below plan' for d1-46759; R1: no 'below plan' for d1-45790; R1: no 'below plan' for d1-46285. The finding gives: Rs 20.13 crore below plan, Rs 13.11 crore below plan, Rs 8.62 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > The largest plan-to-spending gaps warrant attention in Theme 6 – Self-sufficient Infrastructure in Village at Rs 20.13 crore, Theme 4 – Water Sufficient Village at Rs 13.11 crore, and Theme 5 – Clean and Green Village at Rs 8.62 crore across the 20-Gram-Panchayat sample. [d1-46759] [d1-45790] [d1-46285]
22. Q3 attempt 1 - R1: no 'below plan' for d1-46828. The finding gives: Rs 7.12 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 6, maintenance of community systems accounts for 35.4% (Rs 7.12 crore) of the gap and roads for 23.5% (Rs 4.74 crore), while the remaining 6 focus areas account for Rs 8.27 crore. [d1-46828]
23. Q3 attempt 1 - R1: no 'below plan' for d1-47007. The finding gives: Rs 18.51 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Scheme details require particular reconciliation: 4,036 Theme 6 rows have no scheme recorded and account for 91.9% (Rs 18.51 crore) of its gap. [d1-47007]
24. Q3 attempt 1 - R1: no 'below plan' for d1-46759. The finding gives: Rs 3.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 6, Sharagada accounts for 16.7% (Rs 3.36 crore) and Biswamathpur for 13.2% (Rs 2.66 crore) of the Rs 20.13 crore gap. [d1-46759]
25. Q3 attempt 1 - R1: no 'below plan' for d1-46285. The finding gives: Rs 2.15 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 5, Biswamathpur alone accounts for 25.0% (Rs 2.15 crore) of the Rs 8.62 crore gap despite holding 3.1% of the activities, with a recorded spending-to-plan ratio of 11.1%. [d1-46285]
26. Q3 attempt 1 - R1: no 'below plan' for d1-45790. The finding gives: Rs 3.34 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 4, Kalimela accounts for 25.5% (Rs 3.34 crore) of the Rs 13.11 crore gap and has a recorded spending-to-plan ratio of 16.3%. [d1-45790]
27. Q3 attempt 1 - R1: no 'below plan' for d1-24173. The finding gives: Rs 2.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Rural housing is the clearest concentrated exception: Boipariguda accounts for 95.7% (Rs 2.13 crore) of the Rs 2.23 crore gap, while holding 2.0% of the activities and showing a recorded spending-to-plan ratio of 0.0%. [d1-24173]
28. Q3 attempt 2 - R1: no 'below plan' for d1-46759; R1: no 'below plan' for d1-45790; R1: no 'below plan' for d1-46285. The finding gives: Rs 20.13 crore below plan, Rs 13.11 crore below plan, Rs 8.62 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Raise the sizeable gaps between planned and recorded spending: Rs 20.13 crore in Theme 6—Self-sufficient Infrastructure in Village [d1-46759], Rs 13.11 crore in Theme 4—Water Sufficient Village [d1-45790], and Rs 8.62 crore in Theme 5—Clean and Green Village [d1-46285].
29. Q3 attempt 2 - R1: no 'below plan' for d1-47007. The finding gives: Rs 20.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Of its Rs 20.13 crore gap, 91.9%—Rs 18.51 crore—is attached to 4,036 rows with no scheme recorded [d1-47007].
30. Q3 attempt 2 - R1: no 'below plan' for d1-46828. The finding gives: Rs 7.12 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > By focus area, maintenance of community systems accounts for 35.4%—Rs 7.12 crore—while roads account for 23.5%—Rs 4.74 crore [d1-46828].
31. Q3 attempt 2 - R1: no 'below plan' for d1-46759. The finding gives: Rs 3.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > By Gram Panchayat, Sharagada accounts for 16.7%—Rs 3.36 crore—and Biswamathpur for 13.2%—Rs 2.66 crore [d1-46759].
32. Q3 attempt 2 - R1: no 'below plan' for d1-24173. The finding gives: Rs 2.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Boipariguda accounts for 95.7%—Rs 2.13 crore—of the Rs 2.23 crore rural-housing gap, despite holding 2.0% of the 305 activities; its recorded ratio is 0.0% [d1-24173].
33. Q3 attempt 2 - R1: no 'below plan' for d1-46285. The finding gives: Rs 2.15 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 5, Biswamathpur accounts for 25.0%—Rs 2.15 crore—of the gap while holding 3.1% of the 2,127 activities [d1-46285].
34. Q3 attempt 2 - R1: no 'below plan' for d1-45790. The finding gives: Rs 3.34 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > In Theme 4, Kalimela accounts for 25.5%—Rs 3.34 crore—while holding 11.0% of the 1,575 activities [d1-45790].
35. Q4 attempt 1 - R1: no 'below plan' for d4-00049. The finding gives: Rs 7.23 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Biswamathpur has the largest share at 13.9% (Rs 7.23 crore), followed by Kalimela at 11.3% (Rs 5.90 crore); the other 18 GPs account for Rs 38.84 crore. [d4-00049]
36. Q4 attempt 1 - R1: no 'below plan' for d1-49758. The finding gives: Rs 5.43 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Biswamathpur again has the largest share at 15.8% (Rs 5.43 crore), followed by Kalimela at 11.5% (Rs 3.95 crore), while the remaining 18 GPs account for Rs 24.98 crore. [d1-49758]
37. Q4 attempt 1 - R1: no 'below plan' for d1-46759. The finding gives: Rs 20.13 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Within Theme 6—Self-sufficient Infrastructure in Village—the gap is Rs 20.13 crore and is also widely distributed. [d1-46759]
38. Q4 attempt 1 - R1: no 'below plan' for d1-46759. The finding gives: Rs 3.36 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Here, Sharagada leads with 16.7% (Rs 3.36 crore), followed by Biswamathpur with 13.2% (Rs 2.66 crore); the other 18 GPs account for Rs 14.12 crore. [d1-46759]
39. Q8 attempt 1 - R1: no 'below plan' for d1-39534. The finding gives: Rs 37.82 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Among 14 Gram Panchayats near a bus stop, the combined gap is Rs 37.82 crore; Kalimela accounts for Rs 5.90 crore and Bheden for Rs 5.60 crore, while the other 12 account for Rs 26.33 crore. [d1-39534]
40. Q8 attempt 1 - R1: no 'below plan' for d1-28703; R1: no 'below plan' for d1-28967; R1: no 'below plan' for d1-29842; R1: no 'below plan' for d1-30622; R1: no 'below plan' for d1-27660. The finding gives: Rs 2.09 crore below plan, Rs 1.70 crore below plan, Rs 91.35 lakh below plan, Rs 75.10 lakh below plan, Rs 51.17 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > A substantial part of the gap is recorded as “Uncategorised” in several Gram Panchayats: Rs 2.09 crore in Bheden, Rs 1.70 crore in Biswamathpur, Rs 91.35 lakh in Dutimendi, Rs 75.10 lakh in Hirlipali and Rs 51.17 lakh in Andhrua. [d1-28703] [d1-28967] [d1-29842] [d1-30622] [d1-27660]
41. Q8 attempt 1 - R1: no 'below plan' for d1-30622; R1: no 'below plan' for d1-27660. The finding gives: Rs 1.27 crore below plan, Rs 1.02 crore below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > It accounts for 59.0% of Hirlipali’s Rs 1.27 crore gap and 50.1% of Andhrua’s Rs 1.02 crore gap, making these classification records particularly relevant for reconciliation. [d1-30622] [d1-27660]
42. Q8 attempt 1 - R1: no 'below plan' for d1-27925; R1: no 'below plan' for d1-28178. The finding gives: Rs 34.71 lakh below plan, Rs 22.81 lakh below plan. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Smaller but still notable uncategorised gaps appear in Bandhpali at Rs 34.71 lakh and Barimunda at Rs 22.81 lakh. [d1-27925] [d1-28178]
43. Q9 attempt 2 - R1: no 'below sanction' for d1-45395. The finding gives: Rs 6.81 lakh below sanction. **My call: false alarm** (no minus sign, no 'above'; the figure is part of a shortfall that the sentence or the text around it calls a gap, underspend or shortfall).  
   > Mendarajpur accounts for Rs 6.81 lakh [d1-45395] and Dadhapatna for Rs 3.07 lakh [d1-45395] of this gap.

## 6. The Cuttack answer, before and after, in full

**Before Fix 1** (pre-fix display sentences, no direction step; answered on
attempt 2):

> Across the 2 sampled Gram Panchayats, Cuttack records 1,104 planned activities, planned cost of Rs 5.35 crore and spending of Rs 2.17 crore. The signed spending-against-plan measure is Rs -3.18 crore, where a negative value denotes spending below plan.
>
> Planning and spending are distributed differently between the two Gram Panchayats. Govindapur holds 48.8% of activities and 56.2% of planned cost (Rs 3.00 crore), but 42.9% of spending (Rs 92.85 lakh). Dadhapatna holds 51.2% of activities (565 activities), 43.8% of planned cost (Rs 2.34 crore) and 57.1% of spending (Rs 1.24 crore). The spending-against-plan measure is Rs -2.07 crore for Govindapur (65.3%, with a stated ratio of 30.9%) and Rs -1.10 crore for Dadhapatna (34.7%). Of 181 ongoing activities, Dadhapatna has 112 (61.9%) and Govindapur has 69 (38.1%).
>
> The composition of the plan differs by activity count and planned value. Sanitation leads activity volume with 343 activities (31.1%), followed by maintenance of community system with 162 (14.7%). Roads lead planned cost with Rs 1.53 crore (28.7%) despite representing 5.9% of activities, while drinking water accounts for Rs 92.11 lakh (17.2%). Untied grant planning is concentrated in Theme 6—Self-sufficient Infrastructure in Village, with Rs 3.11 crore (84.3%) and 43.6% of activities. Tied grant planning is split mainly between drinking water at Rs 85.61 lakh (51.8%) and sanitation at Rs 79.71 lakh (48.2%); the other 23 focus areas together account for Rs 1,000. Public works account for 977 activities (88.5%), compared with 127 beneficiary-oriented programmes, while 639 activities (57.9%) are costed and 465 (42.1%) are costless.
>
> Sanctions and payment links merit record-level reconciliation. Sanction records cover only about one in six activities, with Rs 2.33 crore recorded as sanctioned. Roads account for Rs 57.60 lakh (24.7%) of sanctions and drinking water for Rs 52.82 lakh (22.7%). Spending linked to planned activities totals Rs 2.07 crore across 6 fiscal years, and the linked share moved from 2.7% to 53.2% across those years. This movement indicates greater recording completeness only if the cashbook total does not rise alongside it, so linked payments should be checked against cashbook records before drawing conclusions about spending.

**After Fix 1** (the shipped `log` mode; answered on attempt 1):

> Cuttack’s sample covers 2 Gram Panchayats with 1,104 planned activities: Dadhapatna has 565 activities and Govindapur 539 activities. Planned cost is Rs 5.35 crore, while recorded spending is Rs 2.17 crore, leaving spending Rs 3.18 crore below plan. Govindapur accounts for Rs 3.00 crore of planned cost and Rs 2.07 crore of the amount below plan; its spending-to-plan ratio is 30.9%. Dadhapatna records the larger spending total at Rs 1.24 crore and has 112 of the district’s 181 ongoing activities. 
>
> The portfolio is predominantly Public Works, covering 88.5% or 977 activities, while Beneficiary Oriented Programmes account for 127 activities. Sanitation is the largest focus area by activity count at 31.1% or 343 activities, but Roads is largest by planned cost at 28.7% or Rs 1.53 crore despite representing 5.9% of activities. Untied-grant planning is concentrated in Theme 6—Self-sufficient Infrastructure in Village—which accounts for 84.3% or Rs 3.11 crore of the Rs 3.69 crore planned. Tied-grant planning is almost entirely divided between Drinking water at 51.8% or Rs 85.61 lakh and Sanitation at 48.2% or Rs 79.71 lakh. Of all planned activities, 639 are costed and 465 are costless. 
>
> Record completeness needs attention when interpreting progress. Spending linked to planned activities totals Rs 2.07 crore across 6 fiscal years, and the linked share went from 2.7% to 53.2%; this rise indicates improved linkage unless the cashbook total also rose. Sanction records cover only about one in six activities, with Rs 2.33 crore recorded as sanctioned; Roads accounts for Rs 57.60 lakh and Drinking water for Rs 52.82 lakh. These limitations make reconciliation of plans, sanctions, cashbook spending and activity records important before drawing conclusions about implementation.

The `block` arm's Cuttack answer fell back on both attempts on
cause-and-effect wording, not on direction.

## 7. Model calls and cost

| | Calls | Cost |
|---|---|---|
| T3 trial: judge | 12 | |
| T3 trial: writer (log 19, block 21, Cuttack-before 2) | 42 | |
| **T3 total** (gpt-5.6-sol, $4 / $20 per 1M tokens in / out) | **54** (cap 80) | **$2.32** |
| Query embeddings (OpenRouter qwen3-embedding-8b): 39 for choosing questions, 12 in the trial | 51 | under $0.01 |

The sol price used is the promotional one, which was recorded as running
"through at least 2026-11-21", the day of this run. Per-call tokens, timings
and costs are in `direction_trial_results.json` → `calls.log`.

## 8. Things worth knowing

- **T1 alone fixed what the officer reads.** Before the fix the Cuttack
  answer said "The signed spending-against-plan measure is Rs -3.18 crore,
  where a negative value denotes spending below plan"; after it, "leaving
  spending Rs 3.18 crore below plan". Across 46 live attempts with the new
  display sentences, the writer wrote no minus sign and no "above plan".
- **Cause-and-effect fall-backs are the bigger loss.** In the `log` arm, 3 of
  12 answers fell back on the causal scan, and 17 of 40 attempts across both
  arms failed it (10 of 19 in log, 7 of 21 in block). This is separate from Fix 1 and is already known (2026-09-14
  latency note). Recorded here because it dwarfs the direction effect.
- §1.4 test 2 expects the raw-minus sentence to fail on R2. It does, and it
  also fails R1 because it has no "below" words. The test asserts R2 is among
  the reasons.

---

# Fix 1b — A direction rule that fits how the writer writes

## Outcome in one paragraph

Built and green, with no model call. R1 ("below plan" must be in every
sentence that carries a figure) is gone. In its place R1′ fails a sentence
only if it uses one of the operator's wrong-direction words ("exceeded",
"overspent", "surplus", "more than the plan", …). Replayed over all 77
recorded attempts of the two WP-D13 trials, the step now **fails no correct
sentence**: 0 failures in 203 checked sentences. All 43 of Fix 1's false
alarms pass. So, by the brief's rule, **the direction check now ships as
`block`**. The one old test failure is fixed, so the suite has no failures.

## 1. Commits (current branch `master`, not pushed)

| Commit | Task |
|---|---|
| `17b2327` | T1: R1′ in place of R1; the retry reason names the offending word |
| `49302fd` | T2: tests (five sentences, each word family, the 43, the replay) |
| `f6b5107` | T3: default `block` (`config.py`, only the direction-check lines) |
| T4 commit | T4: the old prompt test follows the operator's text; this section |

## 2. Gate and tests, baseline vs final

| | Baseline (HEAD `925511e`) | Final |
|---|---|---|
| `python -m DiscoverChat.gates` | 36/36 green | **36/36 green** |
| `python -m pytest DiscoverChat/tests -q` | 150 passed, 1 failed | **157 passed, 0 failed** |

No gate change was needed. The seeded reversed-direction case in
`citation-checks-fire` ("…Rs 51.96 crore above plan") is still caught (now on
R3 alone), and its reason still contains "below plan".

## 3. T1 — the rule as built

- **R1′.** `checks.OPPOSITE_DIRECTION_WORDS` is the one list. It sits beside
  step 5 and is matched as whole words, ignoring case: exceed, exceeds,
  exceeded, exceeding; overspend, overspent, overspending; overshoot,
  overshoots, overshooting, overshot; overrun, overran; surplus; in excess;
  over [the] plan, over [the] sanction; more / higher / greater than [the]
  plan or sanction. I read "overshoot…" as its four forms. Every other entry is
  exactly the approved word, so "overruns", "overspends" and "excess" on its
  own are **not** on the list.
- **R2 and R3 are unchanged.** R1 is removed. A sentence that cites a signed
  record with only shares or counts is still not checked.
- **The retry reason** quotes each failing sentence, names what is wrong in
  it, and gives the figure as the finding has it. For example: *These
  sentences describe a spending figure in a way that says the opposite of the
  finding: "Spending exceeded the plan by Rs 51.96 crore." (it uses
  "exceeded"). The finding gives the figure as "Rs 51.96 crore below plan".
  Write its direction that way -- not with a minus sign, and not with a word
  that says the opposite.*

**The five sentences of §1.1, now (block):**

| Prose | `all_pass` | Failed on |
|---|---|---|
| "…totals Rs -51.96 crore" | False | R2 |
| "…Rs 51.96 crore below plan" | **True** | — |
| "…Rs 51.96 crore above plan" | False | R3 |
| "Spending exceeded the plan by Rs 51.96 crore" | False | R1′ ("exceeded") |
| "…Rs 61.96 crore below plan" | False | step 2 |

## 4. T2 — tests (`test_direction.py`)

- The five sentences above. "Above plan" now fails on R3 only, and "exceeded"
  on R1′ only.
- **The 43 sentences of §5 above**, read from the recorded trial file
  (`direction_trial_results.json`, every recorded R1 failure). Each is still
  checked, and each passes. The test also asserts there are exactly 43.
- **Each word family fails once.** There are eight sentences, one per family,
  each true in its figure and wrong in its words. Each fails R1′ alone, and its
  word appears in the reason. Every listed form matches. Near-misses do not
  match: "exceedingly", "overrunning", "higher than the planned cost", "below
  plan", "shortfall".
- A share-only sentence is still not checked, even when it uses "exceed".
- Fix 1's "a follow-on sentence without below words fails" test is reversed.
  Such a sentence now passes. A follow-on sentence with "surplus" fails, and
  the reason names it.
- **The T3 replay is also a test**, so the result is kept: all 77 attempts
  pass step 5, and the two pre-Fix-1 Cuttack attempts fail on R2 only.

## 5. T3 — offline replay, no model calls

Step 5 in `block` was run over every recorded attempt. I used the same
sentence split and bindings as production. For the headline trial I first
stripped the markers, as that trial's own check did.

| Source | Attempts | Sentences | Checked by step 5 | R1′ | R2 | R3 |
|---|---|---|---|---|---|---|
| Direction trial (log + block arms) | 40 | 317 | 138 | 0 | 0 | 0 |
| Headline trial (baseline + headline arms) | 37 | 295 | 65 | 0 | 0 | 0 |
| **Total, written on today's display sentences** | **77** | **612** | **203** | **0** | **0** | **0** |
| Direction trial, Cuttack on the **pre-Fix-1** sentences | 2 | 32 | 3 | 0 | 3 | 0 |

No figure was skipped as ambiguous. (The brief counts 697 sentences. My 612
is the step's own split, which moves a leading tag back onto the sentence
before it. I could not reproduce 697 with any split I tried.)

**Every failure, verbatim.** All three are **true catches**: each shows a
minus sign. They come from the two Cuttack attempts written on the old
display sentences ("Rs -3.18 crore"), which production no longer hands the
writer.

1. Cuttack before Fix 1, attempt 1 — R2. The finding gives: Rs 3.18 crore below plan.
   > The signed spending-against-plan measure is Rs -3.18 crore, indicating spending below plan; Govindapur accounts for 65.3% (Rs -2.07 crore), compared with Dadhapatna’s 34.7% (Rs -1.10 crore), and Govindapur’s measure is 30.9% when expressed as a ratio. [d3-01105]
2. Cuttack before Fix 1, attempt 2 — R2. The finding gives: Rs 3.18 crore below plan.
   > The signed spending-against-plan measure is Rs -3.18 crore, where a negative value denotes spending below plan [d3-01105].
3. Cuttack before Fix 1, attempt 2 — R2. The finding gives: Rs 2.07 crore below plan.
   > The spending-against-plan measure is Rs -2.07 crore for Govindapur (65.3%, with a stated ratio of 30.9%) and Rs -1.10 crore for Dadhapatna (34.7%) [d3-01105].

**Default shipped: `block`.** No failure fell on a correct sentence.
Reversal without a code change: `DISCOVERCHAT_DIRECTION_CHECK=log`.

## 6. T4 — the one old test failure

`test_citations.py::WriterPromptTests::test_the_prompt_is_the_operators_text`
now looks for the operator's current line in `context_brief.py`: "It is very
important that you do not make causal claims - none of our data can be used
to determine causality." That line came in with commit `cc72e71`. The
operator's file was not touched.

## 7. Things worth knowing

- **R1′ has no "positive figure" exception, while R3 has one.** I built it as
  written. The cost is that a true sentence about a mixed-sign record fails if
  it uses a list word for the positive part. For example: "One focus area
  exceeded its sanction by Rs 1.73 lakh, while Sanitation was Rs 1.33 crore
  below sanction". The same sentence with "above sanction" passes R3. This
  touches only the 281 mixed records, and no recorded sentence did it. If the
  PM wants R3's exception on R1′, it is a one-line change.
- **The writer now gets direction feedback again.** Under `block`, a
  wrong-direction word triggers one retry and then the bare sentences. The
  Fix 6 live run below ran with this default.
- **The Drive working copy had model edits that are not mine.** They appeared
  at 19:11–19:12 on 2026-11-22, during this run, in `DiscoverChat/config.py`
  (classifier, verifier and judge ids) and `Insights/src/discover_config.py`
  (writer `gpt-6.2-sol`). They are left uncommitted and untouched.
  `f6b5107` was staged from a patch, so it holds only the direction-check
  lines.

---

# Fix 6 — The cause-and-effect check stops blocking answers; a caution line is added

## Outcome in one paragraph

Built and green. The cause-and-effect check is now a switch,
`DISCOVERCHAT_CAUSAL_CHECK`, set to `log`. It still scans every answer and
records what it finds, but it no longer causes a retry or a fall-back. No code
was deleted, and the writer's instructions are unchanged. Every Insight report
now ends with the operator's caution line, and Copy carries it. Live, on the
15 WP-D13b questions with the same findings: **no answer lost its narrative
(0 of 15; the baseline lost 2 of 15, both to this check)**, and the writer
needed **16 attempts against 20**. The scan flagged 9 sentences in 5
attempts. They are all listed in §6 for the operator to read.

## 1. Commits (current branch `master`, not pushed)

| Commit | Task |
|---|---|
| `9097653` | T1: the switch (`config.py`, `checks.py` at both call sites, the log line in `writer.py`) |
| `e972251` | T2: the gate and the tests follow the mode |
| `14940b2` | T3: the caution line (frontend), tests, screenshots |
| T4 commit | T4: the live trial, its results, this section |

`9097653` was staged from a patch so that it holds only the Fix 6 lines of
`config.py`. The operator's uncommitted model edits in that file are still
there and still uncommitted.

## 2. Checks, before vs after

| | Before (HEAD `4c40b90`, after Fix 1b) | After |
|---|---|---|
| `python -m DiscoverChat.gates` (default `log`) | 36/36 green | **36/36 green** |
| same, pinned `DISCOVERCHAT_CAUSAL_CHECK=block` | — | **36/36 green** |
| same, `DISCOVERCHAT_CAUSAL_CHECK=off` | — | **36/36 green** |
| `python -m pytest DiscoverChat/tests -q` | 157 passed, 0 failed | **173 passed, 0 failed** |
| `npm test` (vitest) | 146 passed, 10 files | **151 passed, 10 files** |
| `npm run lint` | 3 errors, 7 warnings | **the same 3 errors and 7 warnings** (pre-existing, as in WP-D12) |
| `npm run build` | green | **green** |

## 3. T1 — the switch

- **`DISCOVERCHAT_CAUSAL_CHECK` = `block` | `log` | `off`, default `log`.**
  It is read and checked in `config.py` exactly like the direction switch. An
  unknown value stops the service at start-up. Both the causal and the
  direction modes are now in the settings dump (`/health` → `knobs`).
- **Both places the chat service runs the scan use the same helper:** step
  `3_causal` of `check_citations` (the live path) and `e_causal` of
  `check_prose` (the path behind `DISCOVERCHAT_CONSOLIDATE=0`). Like the
  direction check, both functions accept a one-call override (`causal_mode=`).
  - `block`: the scan's result, byte for byte as before. It counts towards
    `all_pass` and goes into the retry reason. A test checks this.
  - `log`: the scan's result under the same key, plus `counts: false` and the
    flagged sentences. It does not count towards `all_pass`, causes no retry
    and no fall-back, and adds nothing to the retry reason.
  - `off`: no scan, and no key.
- **The log line.** In `log` mode, when an answer that is **shown** has
  flagged words, the writer adds one line to `logs/citation_failures.jsonl`:
  `kind: "causal_words_shown"`, `fell_back: false`, the question, the turn id,
  the attempt, the words, and each flagged sentence with its words. Fall-back
  lines carry no `kind`, so the two kinds cannot be confused. The line is
  written on both writer paths. In the live run, 4 lines were written, one for
  each of the 4 shown answers that had flagged words.
- **The flagged-sentence list** scans each sentence on its own. The
  whole-text scan reports each word only once, at its first place, so it
  cannot list every sentence. The pass/fail verdict is still the whole-text
  scan's.
- **Nothing deleted or edited in** `causal_gate.py`,
  `Insights/src/prose_gate.py`, `context_brief.py` or `classifier.py`.

## 4. T2 — the gate and the tests

- `causal-gate-catches`: unchanged. The scanner still has to fire.
- `causal-scan` and the three live lines that assert `e_causal` passes: they
  gate under `block`. Under `log` or `off` they report the count and do not
  fail. Today that reads "27 answers scanned, 0 with cause-and-effect words
  (mode log: reported, not gated)".
- **One check outside the brief's list had to follow:** `citation-checks-fire`
  seeds a causal claim and expects it to be caught. Under `log` it would no
  longer be caught, and the gate would go red. I pinned its seeded calls to
  `causal_mode="block"`, as it already pins direction to `block`. It still
  proves the step fires, whatever the default.
- The existing causal-rejection test (`test_a_causal_claim_fails`) pins
  `block` and keeps its assertions, plus `all_pass` is False. The other causal
  tests (`CausalGateTests`, `test_no_answer_asserts_a_cause`) test the scanner
  and the code-written answers, not the writer's check, so they did not
  change.
- **New `tests/test_causal_mode.py`, 16 tests:**
  - `log`: prose with "because" and "therefore" gives `all_pass` true, with
    `3_causal` failing and `counts` false. The reason is empty.
  - `log`, with a stub writer that writes "because": `consolidate` keeps the
    narrative on attempt 1, makes no second call, and writes one log line with
    the words and sentences.
  - `log`, with a real failure of another step (an untagged figure): it still
    retries and still falls back. The retry prompt carries that step's reason
    and not the causal one.
  - `block`: the retry, the fall-back and the reason are as before.
  - `off`: the key is absent, and nothing is logged.
  - The connective path (`check_prose`) in all three modes.
  - An unknown value raises at start-up (checked in a subprocess). An unknown
    one-call override raises too. The default is `log`, and the mode is in the
    dump.

## 5. T3 — the caution line

- **The text, exactly:** "Produced with AI, so it may contain mistakes. It
  shows patterns in the records and cannot tell what caused them. Please check
  the source records before acting."
- **One constant, one line:** `REPORT_CAUTION` near the top of
  `frontend/…/insights/ReportFooter.tsx`. It is not exported, so lint gets no
  new warning. The tests read the text from the page, so changing the words
  breaks no test.
- **Where and how it looks:** the footer, on its own full-width line directly
  above the "as of … / Copy" row, on every report. It is 12px,
  `report-ink-muted`, plain text, with no icon and no box. It is marked
  `data-report-chrome=""` (and `data-report-caution=""` for the tests), and the
  "no layout renders as before" text comparison still passes unchanged.
- **Copy** now copies the question, the answer and the caution, each separated
  by a blank line. The existing Copy test was updated to expect that.
- **Tests (+5):** the line is shown on Cuttack (with a layout), on Cuttack
  with `{}`, on the Ask decline (`{}`), and on Kalimela (a fall-back). It sits
  directly above the stamp/Copy row inside the footer and has none of the box
  classes. It is the same text on all six saved payloads, and it has no
  nowrap or fixed width.
- **No horizontal scroll at 360px.** I checked in the browser (Vite and
  Chromium) on Cuttack, Cuttack with no layout, the decline and Kalimela: the
  page scrolls 0px sideways, and no element goes past the right edge.
- **Screenshots** (`handoffs/WPD13_shots/`): `f6_1_cuttack_desktop.png`,
  `f6_2_cuttack_390.png`, and footer close-ups `f6_3_footer_desktop.png` and
  `f6_4_footer_390.png`. At desktop width the line sits under the "Needs
  checking" box in muted grey, and it does not compete with it.

## 6. T4 — measured live

**Design.** `DiscoverChat/experiments/run_causal_log_trial.py`, output
`causal_log_trial_results.json`. It uses the 15 WP-D13b questions, each with
the findings the judge picked for it in the WP-D13b **baseline** arm. The
writer is the production `writer.consolidate` with today's wording, all 15 in
parallel. So the only differences from that baseline arm are the two check
modes: causal `log` (Fix 6) and direction `block` (Fix 1b; the baseline ran
direction in `log`). I reused the findings rather than re-running the judge
because it makes the comparison cleaner and needs no judge calls.

**Writer model: `gpt-5.6-sol`**, the committed default, which the baseline
also used. See §7 on the operator's uncommitted switch to `gpt-6.2-sol`.

| | WP-D13b baseline arm | This run (causal `log`) |
|---|---|---|
| Answers that lost their narrative | 2 of 15 — Q2 Chikilli and Q10 "Who is driving the shortfall?", **both on the cause-and-effect step** | **0 of 15** |
| Lost to the cause-and-effect step | 2 | **0 — pass mark met** |
| Writer attempts | 20 | **16** |
| Retries, and why (the first attempt's failing step) | 5: cause-and-effect 3, a finding left out 1, a figure not tagged 1 | 1: Q14, a finding left out (step 4) |
| Direction step (now `block`) | — (ran in `log`) | checked on 8 answers, **0 failures** |
| Attempts with words the scan flagged | 5 of 20 (each one rejected) | 5 of 16 (none rejected for it) |
| Shown answers with flagged words (one log line each) | — | 4 (Q1, Q6, Q10, Q14) |

**Every sentence the scan flagged, verbatim.** There is no pass mark on
these; the operator's reading is now the safeguard.

1. Q1 "Is spending on track?", attempt 1 (shown). Words: "because".
   > Biswamathpur warrants early reconciliation because it has the largest recorded gap in both views: Rs 7.23 crore, or 13.9%, for costed activities and Rs 6.74 crore, or 16.2%, for approved activities.
2. Q1 "Is spending on track?", attempt 1 (shown). Words: "therefore".
   > Review should therefore combine reconciliation of Biswamathpur and Kalimela’s approved and costed records with thematic follow-up in Sheragada, Rangeilunda and Ganjam; the remaining gaps are distributed across many other Gram Panchayats, blocks and districts rather than being confined to these locations.
3. Q6 "Which blocks account for the shortfall?", attempt 1 (shown). Words: "because".
   > It holds 9.2% of the 12,704 activities but 17.5% of the spending shortfall, making it the clearest block for initial review, while reconciliation should still cover all 16 blocks because most of the shortfall is distributed among the others.
4. Q10 "Who is driving the shortfall?", attempt 1 (shown). Words: "driving".
   > No single Gram Panchayat is driving the spending shortfall: the 20 sampled Gram Panchayats are collectively Rs 51.96 crore below their costed plan totals, with the gap spread across all 20.
5. Q10 "Who is driving the shortfall?", attempt 1 (shown). Words: "therefore", "because".
   > Attention should therefore cover reconciliation across the full sample, while beginning with Biswamathpur and Kalimela because they have the largest recorded gaps.
6. Q14 "Anything I should be looking at in Ganjam?", attempt 1 (not shown: this attempt failed step 4 and was retried). Words: "because".
   > The sanction-based picture is incomplete because only about one in six activities has a sanction record on file.
7. Q14 "Anything I should be looking at in Ganjam?", attempt 1 (not shown: this attempt failed step 4 and was retried). Words: "because".
   > Recorded linkage between spending and planned activities rose from 2.7% to 53.2% over six years; this should be checked against cashbook totals because a rise may reflect more complete recording unless the cashbook total also rises.
8. Q14 "Anything I should be looking at in Ganjam?", attempt 2 (shown). Words: "therefore".
   > Sharagada should therefore be specifically reviewed for costless plans, abandoned works and sanction documentation.
9. Q14 "Anything I should be looking at in Ganjam?", attempt 2 (shown). Words: "therefore".
   > The linked share rose from 2.7% to 53.2% across six years, but this indicates greater recording completeness unless the cashbook total rose alongside it; the plan-to-payment linkage should therefore be reconciled with cashbooks before interpreting the increase as higher spending.

Sentence 4 is the kind §6.2 predicted: a denial that starts with "No". The
scan's list of denial words has no "no", and that list was not touched.

**Model calls and cost.** 16 calls, all writer, against a cap of 45. They cost
$0.37 at the price used for the earlier WP-D13 trials (`gpt-5.6-sol`, $4 / $20
per 1M tokens in / out — the promotional price, recorded as running through
at least 2026-11-21; I did not re-check it for 2026-11-22). There were no
judge calls, no classifier calls and no query embeddings. Per-call tokens and
times are in the results file. Turns took 4.7–26.9 s, run in parallel.

## 7. Things worth knowing

- **The operator is switching models in the Drive working copy.** At
  19:11–19:12 on 2026-11-22 (during this run, uncommitted),
  `Insights/src/discover_config.py` set the writer to `gpt-6.2-sol`, and
  `DiscoverChat/config.py` set the judge to `gpt-6.2-sol` and the classifier
  and verifier to `gpt-6-luna`. I ran T4 on the committed model
  (`gpt-5.6-sol`), because the brief's numbers and the baseline arm use it,
  and the writer model is not yet chosen (D67). To repeat T4 on another
  writer, with no code change:
  `DISCOVER_PROSE_MODEL=<id> python DiscoverChat/experiments/run_causal_log_trial.py`.
  The script prices only `gpt-5.6-sol`, so it would show $0 for another model.
- **What the officer gets is unchanged where it matters.** The API payload
  (`prose.citation_checks`) already left out `3_causal`, and still does. The
  flagged words reach only the log, not the answer.
- **One comment in `writer.py` is now out of date.** Its D7.3 note says the
  citation check is "Blocking, all four". The brief limits `writer.py` to the
  log line, so I left the comment. The true picture is in `checks.py` and
  `config.py`.
- **Not deployed.** Nothing was pushed, Railway was not touched, and the
  operator's `:8080` mirror (`C:\dev\ab-dashboard-main`) was not updated. To
  see the caution line locally, copy `src/components/insights/ReportFooter.tsx`
  into that mirror.

---

# Fix 9 — Small repairs from the review of Fixes 1b, 6 and 7

## Outcome in one paragraph

All four tasks are built, with no model call and no prompt or frontend
change.
- **T1:** the wrong-word rule now has the same exception as the "above plan"
  rule. A true sentence about a mixed-sign record ("One focus area exceeded
  its sanction by Rs 1.73 lakh, while Sanitation was Rs 1.33 crore below
  sanction") passes. The same words with no positive figure still fail.
- **T2:** the out-of-date comment in `writer.py` is corrected.
- **T3:** the two experiment scripts no longer crash when the cause-and-effect
  check is `off`.
- **T4:** the two trial scripts named in the brief no longer report $0 for a
  model with no price; they report the tokens and "price not set for <id>".

The gate is green apart from the two model-evidence checks the standing rules
name, and the service tests have no failures.

## 1. Commits (current branch `master`, not pushed)

| Commit | Task |
|---|---|
| `ab6f909` | T1: R1′ takes R3's exception (`checks.py`), tests |
| `58a8740` | T2: the D7.3 comment in `writer.py` |
| `5b1fb58` | T3: `run_answer_compare.py`, `measure_prose.py` read the causal result safely |
| `6a85494` | T4: no $0 for an unpriced model (`run_causal_log_trial.py`, `run_headline_trial.py`), tests |
| report commit | this section |

## 2. Gate and tests, before vs after

The mirror now carries the operator's model settings from the Drive copy
(writer and judge `gpt-6.2-sol`, classifier and verifier `gpt-6-luna`).
Those two files were copied in unchanged; they are not in any Fix 9 commit.

| | Before (HEAD `e853475`) | After |
|---|---|---|
| `python -m DiscoverChat.gates` | 34/36 — red: `judge-model-evidenced`, `classifier-model-evidenced` (the operator's decision, D69) | **34/36 — the same two red, and no other** |
| `python -m pytest DiscoverChat/tests -q` | 182 passed, 0 failed | **188 passed, 0 failed** |

No model was called. No price was put in for the new models.

## 3. T1 — the wrong-word rule gets the "above plan" rule's exception

- **The change:** in `checks.check_direction`, an R1′ word no longer fails
  a sentence when `positive_bound` is true. That is the condition R3 already
  uses, read from the same variable; no second condition was written. The
  comment beside the rule no longer says "No exception".
- **Tests** (`test_direction.py`, +2), on `d1-00108` (mixed sign: "1 of them
  add Rs 1.73 lakh", "Sanitation at Rs -1.33 crore", measured against
  sanction):
  - The brief's sentence, with both figures bound, passes.
  - The same words with no positive figure ("One focus area exceeded its
    sanction, while Sanitation was Rs 1.33 crore below sanction") still fail
    on R1′ ("exceeded").
  - "Spending exceeded the plan by Rs 51.96 crore" still fails. This test
    already existed.
  - The five sentences and the 77-attempt replay are unchanged: 0 failures.
    These tests already existed and still pass.
- **The word list is unchanged.** `OPPOSITE_DIRECTION_WORDS` is exactly as
  built; the extra forms were dropped by the operator.

## 4. T2 — the comment in `writer.py`

The D7.3 note said the citation check is "Blocking, all four". It now says
that steps 1, 2 and 4 always block, step 3 (the causal scan) blocks only under
`DISCOVERCHAT_CAUSAL_CHECK=block`, and step 5 follows
`DISCOVERCHAT_DIRECTION_CHECK`. Comment only; no code change.

## 5. T3 — two experiment scripts and the `off` setting

`run_answer_compare.py` (`3_causal`) and `measure_prose.py` (`e_causal`) now
read the causal result safely, and record `"not run"` when the key is absent.
I checked the new lines on all three settings. Under `block` and `log` they
record exactly what they did before (`False` and `['because of']` on a test
sentence); under `off` they record `"not run"`. Both scripts compile. I did
not run them end to end, because they call models.

## 6. T4 — no $0 for a model with no price

- **Each trial script has its own price table.** There is no shared one. So,
  as the brief says, I fixed `run_causal_log_trial.py` and
  `run_headline_trial.py`.
- **Left unchanged, as the brief says:** `run_direction_trial.py` has the same
  pattern (`PRICES = {"gpt-5.6-sol": …}`, other models costed at $0). No other
  script in `DiscoverChat/experiments/` prices calls.
- **What the two scripts do now:**
  - A call to a model with no price records `"usd": null` in the results file,
    not 0.
  - The totals record the input and output tokens and a `price_not_set` list.
    If any model is unpriced, `usd` is null.
  - The printed line reads, for example, "2,000 tokens in, 1,000 out; price
    not set for gpt-6-luna; price not set for gpt-6.2-sol".
  - A run that mixes priced and unpriced models adds "$… for the N priced
    calls", and never prints a dollar total.
  - A priced model is costed exactly as before.
- **No price was put in** for `gpt-6.2-sol` or `gpt-6-luna`. A test checks
  this.
- **Tests** (`test_trial_costs.py`, new, 4): each script is loaded in its own
  process, because loading one replaces the model-call function, and is
  handed a fake model call. The tests cover unpriced, priced and mixed runs.
  No model is called.

## 7. Things worth knowing

- **Fix 6 report §7 is out of date on one point.** It said the trial script
  "would show $0 for another model". That is fixed by T4.
- `run_direction_trial.py` still costs an unpriced model at $0, as the brief
  left it. It is a one-function change if wanted.

---

# Fix 10 — Download the report as a PDF; the Copy button goes

## Outcome in one paragraph

Built and green. Every finished Insight report now has a **"Download PDF"**
button where Copy was. It opens the browser's own print box on the report as
it is on screen; the officer saves it from there. There is no PDF library, no
call to the service, and no model call. Only the report prints, from the top
of page 1, on A4, in colour, with nothing cut in half and nothing added by
us. Ctrl+P anywhere else prints exactly as before; I checked this against the
build from before the fix. **One thing the brief did not expect:** Chrome and
Edge tick their own "Headers and footers" option by default, so a saved PDF
also carries the browser's date line, page title, web address and page
number in the margins unless the officer unticks it (§8). We add none of
those. Removing them would be a design change, so I have left it for the PM.

## 1. Commits (current branch `master`, not pushed)

| Commit | Task |
|---|---|
| `2dea7df` | T1: "Download PDF" replaces Copy (`ReportFooter.tsx`, the card marker in `InsightReport.tsx`), tests |
| `2512903` | T2: the print rules (`index.css`), the "do not print" markers (`InsightReport.tsx`), tests |
| `1765cfc` | T3: the three PDFs (`handoffs/WPD13_fix10_pdf/`) and screenshots (`handoffs/WPD13_shots/f10_*`) |
| report commit | this section |

## 2. Tests and build, before vs after

No service file changed, so the gate and the service tests were not run (as
the brief says).

| | Before (HEAD `bce10e5`) | After |
|---|---|---|
| `npm test` | 152 passed (10 files) | **162 passed (10 files)** |
| `npm run build` | green | **green** |
| `npm run lint` | 10 problems (3 errors, 7 warnings) | **the same 10**, all in `src/components/ui/*` and `tailwind.config.ts`; none in a changed file |
| `tsc --noEmit` (app) | clean | **clean** |

## 3. T1 — the button

- **Where and what:** in the footer, in Copy's place, with the same size and
  style, a download icon, and the label "Download PDF". It is marked
  `data-report-chrome` as Copy was. It shows on every finished report: with a
  layout, with `{}`, on a fall-back, and on the decline that routes to Ask.
- **What a click does:**
  1. Marks the page as "printing a report" (`data-report-printing` on
     `<html>`) and marks this report card (`data-print-target`).
  2. Sets the page title to the file name.
  3. Calls `window.print()` once.
  4. On `afterprint`, which Chrome and Edge fire when the print box closes,
     puts back the old title and removes both marks. The marks stay until
     then, so a browser whose `print()` returns at once still prints
     correctly.
- **The file name:** "Insight report - <the question, first 60 characters,
  file-safe> - YYYY-MM-DD". "File-safe" means `\ / : * ? " < > |` and
  control characters become spaces, then runs of spaces collapse. The date is
  the day of download, on the officer's clock.
  - Example: "Insight report - What should I know about Cuttack -
    2026-11-23".
  - A question made only of unsafe characters gives "Insight report -
    2026-11-23".
- **Copy is gone:** the button, the clipboard code and its timer. The caution
  line and the stamp stay where they were. The footer's comment and the
  comment in `ReportLayout.test.tsx` now describe Download.
- **Tests** (`ReportLayout.test.tsx` §5, replacing the Copy test; +5 net):
  - The button is on all four kinds of report.
  - There is no Copy button, and a click never touches the clipboard.
  - A click calls `window.print` exactly once, under the file-name title,
    with both marks set. After printing, the old title is back and both
    marks are gone.
  - File-safe naming works, including the all-unsafe question.
  - A second click before the box reports closing still restores the
    original title.

## 4. T2 — the print rules (`index.css`)

All of them apply only while `html[data-report-printing]` is set.

- **Only the report prints.** Any element that neither contains the report
  card nor sits inside it is taken out of the layout. That covers the app
  header and tabs, the question box, the feed below, toasts and the hover
  box. Because they are removed rather than hidden, they leave no empty
  space.
- **The whole report prints, however long.** The boxes the card sits in lose
  their fixed height (`h-screen overflow-hidden` in `pages/Index.tsx`), their
  inner scroll (`overflow-y-auto` in `AnomaliesView.tsx`), their padding and
  their width cap. No marker was needed in either file.
- **Page:** A4 portrait with 15 mm margins. This is a *named* page
  (`@page report`), which only the marked page selects, so plain Ctrl+P keeps
  the browser's own page.
- **Colours print** without "Background graphics" being ticked
  (`print-color-adjust: exact` on the card).
- **Left out (marked `data-print-hide`):**
  - the dismiss button;
  - the Download button;
  - the "point at / tap any number" hint;
  - "Put this question to Ask".
  - "Open record" links stay, and work as links in the PDF.
- **Nothing cut in half:** each of these stays on one page:
  - a card;
  - a chart;
  - the "Needs checking" box, when it fits on a page (a longer one may break
    between items but never inside one, and its heading stays with its first
    item);
  - a bare finding on a fall-back;
  - the footer.

  Prose paragraphs flow across pages as normal text does.
- **A hover box open at the moment of Download** is not printed. The PDF is
  pixel-identical to one made with no box open.
- **Tests** (`ReportLayout.test.tsx` §7–8, +6):
  - Exactly the four controls are marked. The caution line, stamp, cards,
    charts, warning box, figures and every "Open record" link are not.
  - Every selector inside `@media print` starts at
    `html[data-report-printing]`, and the only `@page` rule is the named one.
    I checked that this test fails when an unscoped print rule or a plain
    `@page` rule is added.

## 5. T3 — three real PDFs (`handoffs/WPD13_fix10_pdf/`)

**How they were made.** Each PDF was made from the built page, served with
`vite preview`, with `/chat` answered from the saved payloads
(`discover-layout.fixtures.json`):
1. The real "Download PDF" button was pressed. `window.print` was replaced by
   a recorder, because a headless browser has no print box.
2. Chrome's own print-to-PDF (Chromium 147) then printed the page in the
   state the button left it in.
3. "Background graphics" was **off**, as in the print box's default, so any
   colour in the PDF is there because of our rule.

The scripts that made and checked them are not committed.

| PDF | Report | Pages | Only the report | Colours | Nothing cut in half | Nothing added |
|---|---|---|---|---|---|---|
| `1_cuttack_with_layout.pdf` | Cuttack, with cards, three charts and a "Needs checking" box | **3**, A4 | yes | yes: bar blues, the warning card and box tint (`#E8F4F7`) | yes | yes |
| `2_kalimela_fallback.pdf` | Kalimela, fall-back to bare sentences, with layout | **4**, A4 | yes | yes | yes: each bare finding moves whole | yes |
| `3_chikilli_long.pdf` | Chikilli, narrative with three charts | **3**, A4 | yes | yes | yes: the pair of charts moves whole to page 2 | yes |

How each column was checked:
- **Page size and margins:** read from the PDF, at 210 × 297 mm. The report
  card's border sits 15 mm from every page edge.
- **Nothing cut in half:** I looked at every page.
- **Nothing added:** I compared the PDF's words with the words of the report
  on screen, minus the controls. The only differences are:
  - a word broken across a line end on the narrower page ("Self-sufficient",
    "2024-2025", "activities—550");
  - the "1." of the "Needs checking" list, which is on screen too but is drawn
    by the browser rather than held as text.

  No other word was added or lost.
- **The file name:** each PDF's stored title is the file-name title (for
  example "Insight report - How is Chikilli doing - 2026-11-23"). The old
  title was back after printing.

**Before vs after:** to check the parts that must not change, I built the
frontend from `bce10e5` in a separate folder:
- **The screen:** the report at 1280px and at 390px differs only in a 44px
  strip where the button is. Nothing else on the screen moved.
- **Ctrl+P elsewhere:** Ctrl+P on the Discover page with a report showing
  (button not pressed), and Ctrl+P on the Ask page, give page-for-page
  identical PDFs before and after. Both are one page, the browser's
  default, as before.

## 6. What the print box shows, in Chrome and in Edge

I checked this in the installed browsers, **Chrome 157** and **Edge 158**,
each with a fresh profile. I pressed the real button and read the print box
itself; screenshots are `handoffs/WPD13_shots/f10_1`–`f10_4`.

**Both browsers:**
- **The preview** is the report alone, from the top of page 1, in colour.
- **Page count:** Chrome says "3 sheets of paper" and Edge "Total: 3 sheets of
  paper" for Cuttack, the same as the PDF.
- **Destination:** the box opens on the computer's default printer, here
  "Microsoft Print to PDF". "Save as PDF" is in the list; the officer picks
  it once, and the browser remembers it next time.
- **With "Save as PDF":**
  - The page is A4 and the paper-size choice is not offered (Chrome hides
    "Paper size", Edge hides "Layout"), because the page sets them. It shows
    3 pages.
  - "Background graphics" is unticked, and the colours still print.
- **With a printer destination,** including "Microsoft Print to PDF", the
  browser uses that printer's own paper: Letter on this computer. The report
  is still 3 sheets. A4 is guaranteed only on "Save as PDF".
- **"Headers and footers" is ticked by default.** The preview shows the date
  and time top left, the page title (the file name) top centre, the web
  address bottom left and "1/3" bottom right. See §8.
- **The file name:** both browsers suggest the page title as the file name.
  The title at the moment the box opened was the file-name title, which the
  box itself shows in its header line. I did not click through to the Windows
  save dialog, and I did not watch the title come back as the box closed: the
  browsers were closed by the script. That step is covered by the unit test
  and the headless runs.

## 7. Phone-sized window

- **On screen at 390px wide:** the button is 143 × 44 px, inside the report
  card, on its own line under the stamp (where Copy sat). The page has no
  sideways scroll, before or after. The only inner box that scrolls sideways
  is the question input showing its own long text, as before.
- **Printing from a 390px window:** the PDF is identical, page for page, to
  the one from a 1280px window (Cuttack 3 pages, Kalimela 4). The print
  layout follows the paper, not the window.
- **A real phone is not tested.** Phones handle `window.print()` in their
  own way. On Android Chrome the call returns at once. The code keeps the
  title and the print marks until the browser reports the print finished, so
  this should be safe, but it has not been seen on a device. iOS has not been
  tried at all.

## 8. Things worth knowing

- **The browser's own header and footer — PM's call.**
  - **What happens:** Chrome and Edge tick "Headers and footers" by default,
    so unless the officer unticks it under "More settings", the PDF carries
    the date and time, the page title, the web address and page numbers in
    the margins. Our code adds none of it. The brief asks for nothing
    added, but this is the browser's own default, so I logged it rather than
    work around it.
  - **One option, tested but not shipped:** an empty "page margin box" rule
    in the print CSS (`@top-left { content: "" }` inside the named page)
    removed the **top** line (date and title) in Chrome 157; the bottom line
    stayed (`f10_7_…NOT_SHIPPED.png`). Adding the same rule for the bottom
    would very likely remove the bottom line too, but I have not tried it,
    and I have not tried either rule in Edge.
- **A4 only on "Save as PDF".** A printer destination uses the printer's
  paper size (above).
- **Some pages end with white space.** When a chart or a bare finding does
  not fit in the space left, it moves whole to the next page. On Chikilli
  page 1, about 40% of the page is left empty. This is the price of
  "nothing cut in half".
- **Older browsers.** The rules rely on `:has()` (Chrome and Edge 105+,
  Firefox 121+, Safari 15.4+). In an older browser the button would print
  what Ctrl+P prints today: one page, cut off.
- **Where the links point.** "Open record" links in the PDF point to the
  service address the page was built with. In these test PDFs that is
  `http://localhost:8100`; on the deployed site it is the deployed address.
- **The comparison folder.** The "before" build was a scratch copy at
  `C:\dev\ab-dashboard-odisha-before`, removed afterwards.
