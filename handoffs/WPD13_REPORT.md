# WP-D13 report — Insight report fixes

**For:** the PM and the operator. **Executed:** Fix 1 on 2026-11-21; Fix 1b
and Fix 6 on 2026-11-22. Mirror `C:\dev\odisha-d13` (refreshed from HEAD
`925511e` on 2026-11-22). One section per fix. Fix 2 moved to its own brief
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
