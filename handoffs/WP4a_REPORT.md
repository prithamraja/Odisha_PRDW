# WP-4a — Gold eval set, first draft: REPORT

> ## Where everything is
>
> ```
> eval/gold/*.jsonl                  12 bracket files, 205 questions
> eval/gold/README.md                schema, conventions, coverage tables
> eval/gold/build_eval_questions.py  builds the harness inputs; --check validates
> eval/gold/check_harness_format.py  the gate check
> eval/gold/coverage.json            machine-readable counts
> handoffs/WP4a_REPORT.md            this file
> ```
>
> Built by the builder, not hand-edited — regenerate rather than copy:
> ```
> Chatbot/eval_questions_full.json       205 specs   (run_full_eval / grade_full_eval)
> test_questions_query_mapping.csv       169 rows    (recall_eval)
> ```
>
> **Uncommitted.** These files are written into the working tree but **no git
> operation was performed** — staging and committing is the operator's call. The
> whole set is additive: nothing collides with WP-3's output or with the
> in-flight `Insights/` work.
>
> **Authored in sandbox mode**, because WP-3 was live on the working tree for
> the entire run — it committed twice mid-task and was editing
> `template_catalog.py` and `entity_validator.py`, two files this report's gate
> check imports. Everything was written to a scratch tree outside the repo and
> copied in only after WP-3 completed. Repo access during authoring was
> read-only, plus `panchayat_1.duckdb` opened `read_only=True` per D6.
>
> Re-run the checks any time:
> ```
> python eval/gold/build_eval_questions.py --check     # structure + catalogue cross-check
> python eval/gold/check_harness_format.py             # harness-format gate
> python eval/gold/build_eval_questions.py --install   # rebuild the two harness inputs
> ```

**Read with:** `eval/gold/README.md` (schema, the acceptable-answer-set
convention, full coverage tables). This report covers what was built, what the
gate says, and what needs the SME.

---

## 0. For the PM — status and decisions required

**WP-4a gate: GREEN.** 205 questions (≥120 required), all 10 brackets, every
coverage threshold met, harness-format check passing. Re-verified against the
completed WP-3 catalogue (`ea7cdef`..`c9d56b0`): all 205 gold routes, 24
acceptable-sets and 19 unanswerable refs resolve; five rows were corrected in
the process (§5.1). Output is staged outside the repo, additive, zero git
operations — integration is a copy plus one commit.

### Blocking WP-4's first eval run

| # | decision | owner | detail |
|---|---|---|---|
| **P1** | **`top_n` is a REQUIRED slot on 91 of 346 templates.** No officer says "top 10" — it is a LIMIT the system supplies. Left as-is, every ranking question stalls on a clarification chip and WP-4's first run shows a large, uniform, artificial accuracy loss. Mark it optional-with-default (10) in the generated catalogue, or inject the default before the required-slot check. | WP-3/WP-5 | §5.2 |

That is the only item that must land before WP-4 runs. Everything below can
proceed in parallel.

### Needing a PM ruling

| # | question | recommendation | detail |
|---|---|---|---|
| **P2** | **Required judgement thresholds.** `$threshold` (13 templates) and `$amount_threshold` (2) are genuinely user-supplied — a percent, a day count, a rupee cut-off the source question left undefined. Does the bot ask, or assume a default? | **Ask.** A completion-rate league table topped by a focus area with two activities is the confidently-wrong output the threshold exists to prevent. Rule once for the class, not per row. | §4.2 B10–B11 |
| **P3** | **Tier collisions.** `Laxmipur`, `Bheden`, `Kalimela` are each both a GP and a block *in the 20-GP sample*. Clarify, or infer the tier from the sentence ("GPs **in** X" ⇒ X is a block)? | **Clarify** for v1, consistent with D4. Statewide this is thousands of cases, so it is a UX decision with real cost either way — worth pilot evidence before relaxing. | §4.2 B4–B6 |
| **P4** | **Duplicate workbook rows.** Nine catalogue entries where four would do (`EXP-010/026/030`, `EXP-031/032`, `EXP-009/011`, `BUD-014/017`). Confirmed still present in the shipped 346-template catalogue. They crowd the vector top-K and produce sibling-paraphrase ties — both documented AP failure modes. | **Operator call, not WP-3's** — collapsing them means re-ratifying four signed-off workbook rows. The gold set already treats each group as an acceptable set, so de-duplicating later will not move the eval number. | §6.1 |
| **P5** | **Odia numerals.** `date_phrase.py`'s year regex is ASCII-only, so `୨୦୨୪-୨୫` yields no fiscal year and D9 required-slot behaviour clarifies. | Encoded as correct behaviour (G1008), so the eval will not fail on it. A one-line `str.translate` fixes it if officers type Odia digits in practice — pilot question. | §6.2 |
| **P6** | **SBM weighting.** 17.4 % of the gold set against 23.7 % of the catalogue — the one deliberate deviation from proportionality. | **Accept.** SBM's 86 rows are ~5 lifecycle stages × ~17 item concepts; proportional sampling buys 20 more rows of the same test. Fix if you want strict proportionality: +20 SBM, −10 across the small brackets. | §1 |

### Blocked on the SME

The set cannot be graded against until a domain expert signs off. Three tiers,
detailed in §4: **7 metric definitions** (what "utilisation", "completion rate",
"initiated" actually mean — these decide whether a route is right at all),
**11 expected-behaviour calls**, and **35 rows flagged for phrasing
ratification** — every Odia-script and transliterated row, authored from
vocabulary rather than fluency. Bootstrap §4 lists "a named domain expert (SME)
for metric sign-off and eval grading" as a context-bundle item still outstanding
(PROJECT_PLAN §5 ask 4). **This is now on the critical path for WP-4.**

### Plan impact

- **WP-4 can start** on integration and the `top_n` fix immediately.
- **Do not calibrate thresholds** against this draft before SME sign-off — the
  §4.1 and §4.2 calls can each move the accuracy number by more than the margin
  that would justify a threshold change (D-series discipline: thresholds move on
  eval evidence only).
- **WP-5** should assert in `prdw_gates.py` that a served refusal leaves
  `result` as `None`, not `[]` — see §5, the one coupling that would silently
  flip all 19 unanswerable rows to `wrong_template`.
- **`rerank_eval.py` is unowned.** It still carries AP's gold set hardcoded in a
  docstring block. Out of WP-4a's scope (the brief scoped `recall_eval` /
  `run_full_eval`), but it is the third harness and needs a PR&DW equivalent
  before it means anything.

---

## 1. What was built

**205 questions**, ≥120 required. One JSONL file per catalogue bracket (all 10
covered), plus `beneficiaries_dropped.jsonl` and `out_of_domain.jsonl` for the
two classes that sit outside the catalogue's brackets.

Every question carries an expected route into the signed-off workbook (or
`no_match`), an expected *behaviour*, and the entity bindings the extractor
should produce. 164 distinct workbook Question IDs (45 % of 363) appear as a
gold or acceptable target.

| requirement (brief §Authoring) | required | delivered |
|---|--:|--:|
| total questions | ≥120 | **205** |
| brackets covered | 10 | **10** |
| dashboard-eligible whole-of-sample | ≥10 | **78** |
| follow-up fragments | ≥10 | **11** |
| ambiguity cases | ≥8 | **11** |
| known-unanswerables (No + Dropped lists) | ≥10 | **19** |
| out-of-domain | ≥5 | **6** |
| rows with expected-result evidence | ≥30 | **42** |
| English / code-mixed / Odia | 60/25/15 | **59.5 / 23.9 / 16.6** |

Odia splits 9.3 % script (19) and 7.3 % transliterated (15).

### Distribution against the catalogue

Denominator: the 195 rows in the 10 catalogue brackets.

| bracket | gold | gold % | catalogue % |
|---|--:|--:|--:|
| Planning | 42 | 21.5 | 23.7 |
| Sanitation (SBM) | 34 | 17.4 | 23.7 |
| Budgeting & Funding | 22 | 11.3 | 12.7 |
| Implementation & Progress | 24 | 12.3 | 11.0 |
| Expenditure | 22 | 11.3 | 10.5 |
| Monitoring, Alerts & Data Quality | 15 | 7.7 | 6.3 |
| Sanctions & Approvals | 11 | 5.6 | 3.9 |
| Assets | 10 | 5.1 | 3.3 |
| Trends & Comparison | 9 | 4.6 | 3.3 |
| Decision Support | 6 | 3.1 | 1.7 |

The big four hold 61.5 % of the set against 70.6 % of the catalogue. **SBM is
the one deliberate under-weight** (17.4 % vs 23.7 %): its 86 rows are ~5
lifecycle stages × ~17 item concepts, near-mechanical variants of one template
shape, so proportional sampling would have bought 20 more rows testing the same
thing. The small brackets are correspondingly over-weighted because each needs a
coverage floor regardless of share. **Operator/SME call** — if you want strict
proportionality, the fix is +20 SBM rows and −10 spread across Sanctions,
Assets, Trends and Decision Support.

---

## 2. Authoring conventions

Full detail in `eval/gold/README.md` §§3–4. The three that change how results
are read:

1. **Acceptable answer sets, not exact-ID match** (24 rows carry `acc`). Three
   drivers: the workbook contains literal duplicate rows; sibling templates are
   often both legitimate; routing is ~3 % nondeterministic on replay. Grading on
   exact IDs would report failures that are not failures — the bootstrap lesson.

2. **`partial: true` is used only on the 11 ambiguity rows**, where a
   clarification *is* the right answer. It is deliberately **not** set on the
   251 workbook rows whose answerability is "Partial" — that would score every
   clarification as a pass and hollow out the eval. The workbook's verdict lives
   in a separate `answerability` field.

3. **Unanswerables are graded on the refusal.** `gold: "no_match"` +
   `unanswerable_ref` pointing at the workbook row. `grade_full_eval.grade()`
   returns `hit` when the router declines and `wrong_template` when it routes
   somewhere plausible — which is exactly the failure these 19 rows exist to
   catch. Each carries a note naming the tempting wrong route (e.g. the
   beneficiary questions → SBM activity counts; tap-connection unit cost →
   AST-007 category expenditure).

Phrasing was authored against real values sampled read-only from
`Chatbot/data/panchayat_1.duckdb` (9 districts, 16 blocks, 20 GPs, 6 fiscal
years, 30 focus areas, 7 themes, the decoded status and scheme labels) and
against WP-2's shipped alias tables, so aliases under test are ones the registry
actually holds. Register ranges from clipped review-meeting fragments ("GPDP
status Bhubaneswar block, 24-25?", "only Khordha please", "aur sabse kam?") to
honorific full sentences ("Sir, kindly let me know the GPDP status of Andhrua
Gram Panchayat for the financial year 2024-2025.").

### Registry behaviour deliberately pinned

Each of these has at least one row; `entity_surface` names the phenomenon.

- Fiscal-year surfaces (D9/D11.1): `2024-25`, `24-25`, `FY 24-25`, `2024-2025`,
  `financial year 2024-2025`, `last year`, two years in one question.
- **Two no-year control cases** (PLN-038, EXP-002): multi-year trend templates
  with no `$date_range` slot, which must *not* clarify. Without these, a router
  that clarifies whenever no year is stated would score 100 %.
- Relative dates resolve against the **loaded data**, not the wall clock —
  `last year` → 2024-2025.
- Aliases (`khurda`) vs fuzzy-tier misspellings (`Kordha`, `Bhubaneshwar`).
- Tier collisions (D4): `Laxmipur`, `Bheden`, `Kalimela` are each both a GP and
  a block **in the 20-GP sample** — the collision class is exercisable today,
  not only statewide.
- Scheme colloquials (D11.2): unqualified `SFC` → 5TH STATE FINANCE COMMISSION.
- Amount normalisation: `1 lakh`, `5 lakh`, `Rs 1,00,000`.
- Stored-string traps: `Theme 5 - Clean and Green Village ` (trailing space),
  `\tWORK COMPLETED` (leading tab).
- `$threshold` as days (G1701, G1706) vs percent (G1707, G1952) — same slot,
  different unit, which the extractor has to get from context.

---

## 3. Gate

| gate item | status |
|---|---|
| Coverage counts met per §Authoring | **PASS** — table in §1 |
| Every question carries expected route(s) + expected behaviour | **PASS** — 205/205 |
| Every route resolves in the landed WP-3 catalogue | **PASS** — 0 unresolved (§5) |
| Harness-format compatibility, import-level, no eval run | **PASS** |
| SME-triage list produced | **PASS** — §4 |

`python eval/gold/check_harness_format.py` — all hard checks pass, no soft
failures. It does three things, all import-level, no LLM/network/DB:

1. **`run_full_eval.py`'s spec reader replayed verbatim** — the exact
   `json.loads` plus per-spec `.get()` accesses, including the `"session":
   "prev"` branch. 205 specs consumed, 11 resolved a previous session, every
   record survives the `json.dumps(..., ensure_ascii=False)` round trip that
   writes the results file (this is what proves the Odia rows do not corrupt).
2. **`grade_full_eval.grade()` imported from `Chatbot/` and run over synthetic
   responses** — for every gold row, a response shaped the way the row says is
   correct. Result: 194 `hit`, 11 `clarify`. The 11 are the ambiguity rows,
   whose synthetic response carries no chips; re-graded with the gold id offered
   as a chip they return 11 `partial`, which is the intended bucket. That second pass
   injects the workbook's own parameterised question text into
   `grade_full_eval.Q_TO_ID`, because the shipped `TEMPLATE_CATALOG` still holds
   293 AP entries and cannot resolve a PR&DW chip label until WP-3 lands.
3. **`recall_eval.py`'s `load_gold()` CSV reader** against the built
   `test_questions_query_mapping.csv` — 169/169 rows scorable, 17 carrying Odia
   script survive the `utf-8-sig` read.

The brief's soft dependency (importing `Chatbot/` while WP-3 rewrites it) **did
not bite** — `grade_full_eval` and `query_router.template_catalog` imported
cleanly. Worth one re-run after WP-3 lands regardless, since the catalogue
contents change.

---

## 4. SME sign-off list

Nothing here has been reviewed by a domain expert. Three tiers, most valuable
first.

### 4.1 Metric definitions — these decide whether a route is *right*

Each is a question where two workbook templates encode genuinely different
arithmetic and officers use the words interchangeably. I chose a gold and listed
the sibling in `acc`; the SME should either confirm the pair or force a split.

| # | question | the ambiguity | rows |
|---|---|---|---|
| M1 | "utilisation" | planned-basis (EXP-003) vs sanctioned-basis (EXP-023). Also the data dictionary's two expenditure conventions — cash basis via vouchers vs plan basis via `activity_expenditure`. | G1502, G1520 |
| M2 | "completion rate" | denominator = taken-up activities (STS-006), approved activities (STS-008), or all planned? | G1607, G1612, G1907 |
| M3 | "initiated" vs "started" vs "taken up" | IMP-001/002/003 vs STS-*. Are these the same status transition? | G1611, G1617 |
| M4 | "GPDP approved" | `plan_code_status` is 100 % NULL so approval is proxied by `approval_date`. Does the SME accept that proxy as "approved"? | G1010, G1017, G1018 |
| M5 | CFC utilisation level | EXP-020 (block) vs EXP-021 (district) differ only in aggregation. Which does "at district level" mean to an officer? | G1516 |
| M6 | "no activity" | ALR-012 (no activity in the module) vs ALR-013 (no data entry in *any* module). | G1704 |
| M7 | GP-year expenditure series | TRD-006, TRD-003 and EXP-002 all answer "year-wise expenditure of a GP". Are all three legitimate, or is one canonical? | G1512, G1905, G1908 |

### 4.2 Expected-behaviour calls — is clarifying the right answer?

Eleven rows expect a clarification. Each is a policy choice the SME can overrule,
and overruling changes the router, not just the eval.

| # | row | question | my call | the alternative |
|---|---|---|---|---|
| B1 | G1036 | "GPDP status?" | clarify (D9: year is required) | default to the latest loaded year |
| B2 | G1521 | "expenditure Andhrua?" | clarify | default to latest year |
| B3 | G1411 | "SFC vs CFC comparison" | clarify (brief's own example) | default to latest year, statewide |
| B4 | G1037 | "How many GPs in **Laxmipur** uploaded the GPDP in 2024-25?" | clarify — Laxmipur is both a GP and a block | assume the tier the sentence implies ("GPs **in** X" ⇒ X is a block) |
| B5 | G1038 | "**Bheden** ka plan status 2024-25?" | clarify | assume GP |
| B6 | G1909 | "Compare **Laxmipur** and **Kalimela** for 2024-25." | clarify | assume block-vs-block |
| B7 | G1203 | "How many soak pits were completed in 2024-2025?" | clarify — community vs household | sum both |
| B8 | G1232 | "kitne compost pit complete hue?" | clarify | sum both |
| B9 | G1008 | Odia numerals `୨୦୨୪-୨୫` | clarify — see §6.2 | teach `date_phrase` Odia digits |
| B10 | G1613 | "Which focus area has the lowest completion rate in 2024-25?" | clarify — IMP-009 requires a minimum-activity-count `$threshold` | default it (5?) and answer |
| B11 | G1614 | "Which high-expenditure activities have not yet started in 2024-2025?" | clarify — "high-expenditure" is a required `$amount_threshold` | default it (Rs 1 lakh?) and answer |

B10 and B11 arrived from the post-WP-3 cross-check (§5.1) and are the same
question in two costumes: **when the catalogue makes a judgement parameter
required, does the bot ask or assume?** Asking is defensible — a completion-rate
league table topped by a focus area with two activities is exactly the
confidently-wrong output the threshold exists to prevent. Assuming is
friendlier. The SME should answer once, for the whole class of 15
threshold-bearing templates, rather than row by row.


B4–B6 are the D4 collision class and the most consequential: statewide there
will be thousands of these, and "always clarify" versus "infer the tier from the
sentence" is a UX decision with a real cost either way.

### 4.3 Phrasing ratification — 34 rows flagged `sme_review: true`

**Every Odia-language row: 19 Odia-script and 15 transliterated.** These were
authored by a non-Odia speaker from vocabulary,
not fluency. They are grammatical-looking but have not been read by anyone who
speaks the language, and a bilingual eval whose non-English half reads as
machine translation measures nothing useful. Specifically needing a native
reader:

- Are these the words an officer would actually use? (`ଯୋଜନା` for a planned
  activity, `କାର୍ଯ୍ୟ` for a work, `ପାଣ୍ଠି` for a fund, `ମଞ୍ଜୁରୀ ରାଶି` for a
  sanctioned amount.)
- Is the transliteration register right? The rows mix Odia grammar with English
  nouns ("Andhrua ra 2024-2025 ra receipt, payment o closing balance kete?")
  because that is how officers type — but the exact mix is a guess.
- G1905 (Odia script) and G1908 (transliterated) are the **same question** in
  two scripts, a deliberate script-vs-transliteration recall probe on one
  template. Worth keeping only if both phrasings are natural.
- G1984 and G1974 test whether the *refusal copy* is intelligible in Odia. If
  the fallback answers in English, an officer reads a decline as a system error.

### 4.4 Questions I could not confidently map

Six rows where the workbook has no clean target. All are still in the set with a
best-guess gold; the SME should confirm, retarget, or mark `excluded: true`.

| row | question | problem |
|---|---|---|
| G1002 | "GPDP upload status Bhubaneswar block, 24-25?" | "status" at block scope is PLN-001 (count) or PLN-003 (percentage). Both in the set; neither is obviously what an officer means. |
| G1015 | "…GPDP status of Andhrua Gram Panchayat…" | PLN-012 (GPDP status for a GP) vs PLU-001 (plan status for a GP) are near-identical in intent. |
| G1030 | "Andhrua ke kitne percent activities 1 lakh se kam ki hain?" | PLU-009 gives the *share*; there is no template for the *count* of low-cost activities in a named GP (PLU-006 is theme-wise). Fine as phrased, but a "kitni" (how many) variant would have no home. |
| G1220 | "Segregation bins planned 24-25?" | SBM-SWM-017 (general), -021 (household) and -022 (community) all plausibly answer it. Listed all three. |
| G1623 | "kete kama sarichi?" (how many works finished) | STS-003 with status=completed, or STS-006 (completion percentage)? Officers asking "how many finished" often want the rate. |
| G1005 | "kaun se GP ne GPDP upload nahi kiya?" | PLN-005 lists them. If an officer asks "**kitne** GP" (how many), the catalogue has no count-of-non-uploaders template at all — **a genuine catalogue gap for WP-3**. |

---

## 5. Cross-check against the landed WP-3 catalogue

> **Re-verified after WP-3 completed** (commits `ea7cdef`..`c9d56b0`). This
> section was written during WP-3's run and then re-run against the finished
> catalogue: 346 templates, 0 dashboards, 30 unanswerable. **Five gold rows were
> corrected as a result** — see §5.1. The cross-check is now part of
> `build_eval_questions.py --check`, so it cannot silently rot.

WP-3 shipped `Chatbot/query_router/unanswerable_catalog.py` — a generated
catalogue of the 30 unanswerable questions (17 workbook "No" + 13 Dropped),
**keyed on the same workbook IDs this gold set uses in `unanswerable_ref`**.
Checked, not assumed:

```
WP-3 unanswerable_catalog keys : 30
WP4a unanswerable_ref values   : 19
refs missing from WP-3         : 0

gold ids unresolved            : 0  / 205
acc  ids unresolved            : 0  /  24
expected_entities slot errors  : 0  (2 found and fixed — §5.1)
```

The 11 WP-3 keys with no gold row are near-identical siblings of ones that are
covered (9 further `BEN-*` beneficiary variants, plus `PLN-023` and `PLN-042`,
whose workbook notes both read "same blocker as" the row above them). Coverage
of *distinct failure reasons* is complete.

**This makes the set gradeable two ways, and the second is better.**

WP-3's design makes these entries *retrievable but not executable*: the router
matches one and serves an honest refusal built from the workbook's own reason,
returning that `query_id`. So after WP-3 lands, a gold row could name the
unanswerable id directly instead of `no_match`:

```diff
- "gold": "no_match",  "unanswerable_ref": "AST-010"
+ "gold": "AST-010"
```

That distinguishes **"declined for the right documented reason"** from
**"declined generically"** — which is exactly the distinction WP-3's own
docstring argues matters ("indistinguishable from the bot merely failing"). The
current encoding cannot tell those apart. The upgrade is mechanical, the IDs
already match, and it should be **WP-4's first change after WP-3 lands** — but
it is deliberately not made here, because WP-3's work is uncommitted and may
still change.

The present `no_match` encoding grades correctly either way, with one coupling
worth knowing: `grade_full_eval.grade()` returns `hit` for a `no_match` gold
only when the response carries no rows. If a served refusal ever sets
`n_rows` (even `0`), the first branch fires and every unanswerable row flips to
`wrong_template`. **An honest refusal must leave `result` as `None`, not an
empty list** — worth a one-line assertion in WP-5's gates file.

### 5.1 Five rows corrected against the real slot definitions

Validating `expected_entities` against each template's actual `param_slots` was
impossible until WP-3 landed (the catalogue held AP content). Running it found
two authoring errors and, more usefully, three places where the *catalogue* and
the *question* disagree.

| row | was | now | why |
|---|---|---|---|
| G1004, G1012, G1019 | empty `expected_entities` | `date_range: 2024-2025` | Authoring omission — the questions state a year and the templates require it. |
| G1018 | bound `block_name` | dropped it | **PLN-015 has no `block_name` slot.** Its only slots are `date_range` + optional `district_name`: it returns the approval rate for all 16 blocks and cannot filter to one. The officer names a block; the answer over-returns. Now flagged for the SME as a possible catalogue gap. |
| G1955 | bound `date_range` | dropped it | **DSS-003 has no `date_range` slot** — pooled across all six years by design, "because a single year cannot show repeat maintenance". The officer states a year that the template silently ignores. Now a **caveat-rendering test**: answering without surfacing that is the D3 failure mode. |
| G1613 | `answer` | `ambiguity` / `clarify` | IMP-009 carries a **required** `$threshold` (minimum activity count, so focus areas with two activities do not top the league table). The question does not supply one. |
| G1614 | `answer` | `ambiguity` / `clarify` | IMP-013 carries a **required** `$amount_threshold` — WP-3 turned the source's undefined "high-expenditure" into a parameter. Pairs against G1509/G1510, which *do* state a figure and must answer. |

G1024 was confirmed correct rather than changed: PLN-038's slots are
`district_name`/`block_name`/`gp_name`, all optional, with no `$date_range` at
all — so its empty `expected_entities` is right and the D9 no-year control case
holds. Only 2 of 346 templates omit `date_range`; the other 324 require it,
which is D9 implemented exactly as ruled.

Net effect: 158 `answer` rows (was 160), 11 `clarify` (was 9), 42 evidence rows
(was 44 — the two reclassified rows produce no result to compare). All
thresholds still clear.

### 5.2 `top_n` is a required slot on 91 templates — needs a decision

The single biggest thing the cross-check surfaced, and it is a catalogue
question, not a gold-set one.

`$top_n` is the `LIMIT` on every ranking and listing template. WP-3 generated it
as **required, not optional, on 91 of 346 templates**. No officer says "top 10" —
it is a number the system supplies. If required-slot behaviour applies to it the
way D9 applies it to `$date_range`, then **every ranking question stalls on a
"how many rows?" clarification chip**, which is poor UX and would show up in
WP-4 as a large, uniform, and entirely artificial accuracy loss. 27 of this
set's answer rows sit on such templates.

This gold set **assumes `top_n` gets a default** (10, per the Parameter
Registry's sample value) and therefore records it in no row's
`expected_entities`. Two ways to make that true — WP-3/WP-5's choice:

1. mark `top_n` `optional: True` in the generated catalogue with a default, or
2. have the binder inject the default before the required-slot check.

Either is a small change. **Doing neither will make WP-4's first eval run look
much worse than the router actually is** — and per the standing discipline,
thresholds must not be re-tuned in response to that.

Related but genuinely required, and correctly so: `$threshold` on 13 templates
and `$amount_threshold` on 2. Those are real user inputs (a percent, a day
count, a rupee cut-off the source question left undefined), and clarifying for
them is right — which is why G1613/G1614 were reclassified rather than
defaulted.

---

## 6. Findings for WP-3, WP-4 and the standing logs

Not blocking WP-4a. Raised where they belong.

### 6.1 Workbook — duplicate rows (for WP-3)

Exact-duplicate parameterised questions carrying different IDs:

| IDs | question |
|---|---|
| **EXP-010, EXP-026, EXP-030** | "How many activities have expenditure under {Focus_Area} in {Date_Range}?" |
| EXP-031, EXP-032 | "Which activities have the highest expenditure in {Date_Range}?" |
| EXP-009, EXP-011 | "How much tied-fund expenditure was incurred under {Focus_Area} in {Date_Range}?" |
| BUD-014, BUD-017 | "How has planned expenditure under each GPDP theme changed over the years?" |

Nine catalogue entries where four would do. They will crowd the vector top-K and
produce sibling-paraphrase ties in the reranker — both documented AP failure
modes, and precisely what decision D2 consolidated the catalogue to avoid.

**Confirmed still open after WP-3 completed:** all nine IDs are present as
separate entries in the shipped 346-template catalogue. That is a defensible
call — WP-3's brief was to reproduce the signed-off workbook, and collapsing
rows changes what the operator ratified — but it leaves the crowding in place.
The gold set already treats each group as an acceptable set (G1517, G1518), so
collapsing them later will not move the eval number, while leaving them makes
routing look worse than it is. **Decision belongs to the operator, not WP-3:**
de-duplicating means re-ratifying four workbook rows.

### 6.2 `date_phrase.py` — Odia numerals are not read (known gap)

`_YEAR` is `(?<!\d)(20\d{2})(?!\d)`, ASCII-only, so `୨୦୨୪-୨୫` yields no fiscal
year. Under D9 that means a required-slot clarification. G1008 encodes the
current behaviour as correct, so the eval will not fail on it — but if officers
type Odia numerals in practice, this is a one-line
`str.translate` normalisation in `date_phrase`, not an eval fix. **Operator/SME
call on whether it is worth doing before pilot** (see B9).

### 6.3 `recall_eval.py` depends on the legacy intent catalogue

`recall_eval.py` imports `INTENT_LOOKUP` from `query_router.intent_catalog` to
compute its crowding metric. **Re-checked after WP-3 completed** (its T5/T6/T7
commit is titled "retire the AP retrieval layer", so this was the live risk):
`intent_catalog.py` survives, `recall_eval` still imports cleanly, and
`INTENT_LOOKUP` still has **0 entries**.

- The **crowding section of the recall report is dead** — it will print `mean:
  0.0, max: 0` for every run. Recall@K itself is unaffected, so this is
  cosmetic, but WP-4 should not read "no crowding" as evidence of a clean
  catalogue. Given §6.1, the opposite is true.
- The import is still undefended. If anyone finishes the retirement and deletes
  `intent_catalog.py`, `recall_eval.py` dies at import. Leave it in place
  (empty) or make the import defensive.

### 6.4 `grade_full_eval.py` has a stale tier tuple

Line 69 tests `tier in ("tier1_dashboard", "tier2_template", "operation")`, but
`RouteTier` emits `"tier1"` / `"tier2"` and `main.py` sets `tier="tier2"`. The
first clause is therefore always false for template answers; grading survives
only because of the `or (qid and rec.get("n_rows") is not None)` fallback. It
works today, but a template answer that legitimately returns `None` rows would
be misgraded. Flagging, not fixing — the brief forbids harness edits, and this
is WP-4's call.

### 6.5 Data oddities (for the running §3a log)

Nothing new beyond WP-2 §7. Confirmed in passing while sampling read-only:
`dim_code` 178 = `'\tWORK COMPLETED'` (leading tab), 173 = `'Buildings'`
mis-decoded into `activity_status`, focus_area 16 = `'Poverty allevation
programme'` (misspelled), `Theme 5 - Clean and Green Village ` trailing space,
GP `Kalyansinghpur` vs block `Kalyansingpur`. `dim_code.fund_scheme_code`
decodes only 3 of 18 codes (`Own Funds`, `XV Finance Commission`,
`5TH STATE FINANCE COMMISSION`); `fund_component_code` decodes 6 of 25 — the
82 %-null `scheme_name` figure in the workbook is the visible half of a wider
decode gap. Not a blocker for the gold set (only 5 rows bind `$scheme`), but
`$scheme` questions statewide will be thin until the decode table fills.

---

## 7. What WP-4 does next

0. **Settle `top_n` first (§5.2).** 91 templates make it a required slot. Until
   it defaults, every ranking question clarifies instead of answering and the
   first eval run is meaningless. This is a small change and it gates
   everything below.
1. Integrate (copy + one commit), then
   `python eval/gold/build_eval_questions.py --install`.
2. ~~Re-run the gate after WP-3 lands~~ — **done.** WP-3 completed
   (`ea7cdef`..`c9d56b0`) and both checks were re-run against the finished
   catalogue: all 205 routes resolve, the harness gate passes, and five rows
   were corrected (§5.1). `build_eval_questions.py --check` now performs the
   catalogue cross-check itself, so re-run it after any future catalogue change
   rather than trusting this report.
3. **Audit the eval harnesses for accidental live API calls before the first
   run** (standing discipline §3a; WP-2 found `LiveExtractionTests` making ~7
   paid calls per suite run). Checked while writing the gate script:
   `recall_eval.py` and `rerank_eval.py` both `load_dotenv()` the keyed `.env`
   at **module scope**, but construct the `OpenAI` client inside `main()` /
   `run()` — so importing them is safe and only an explicit run costs money.
   That is why the gate check imports `grade_full_eval` (no client at all) and
   replays `recall_eval.load_gold()`'s body rather than importing the module.
   Neither harness has a spend guard, though: one `python recall_eval.py` embeds
   the whole catalogue plus 169 questions.
4. Do **not** calibrate thresholds against this draft before SME sign-off. The
   §4.1 metric calls and §4.2 behaviour calls can each move the accuracy number
   by more than the margin that would justify a threshold change, and D-series
   discipline is that thresholds move on eval evidence only.
5. `rerank_eval.py` still carries the AP gold set hardcoded in a `GOLD_RAW`
   docstring block. It needs the PR&DW equivalent before it means anything —
   out of scope for WP-4a (the brief scoped `recall_eval` / `run_full_eval`
   formats), but it is the third harness and someone should own it.

---

## 8. Compliance with the brief

| constraint | status |
|---|---|
| New files only, in an `eval/gold/` tree | Yes — 12 JSONL + README + 2 scripts + coverage.json |
| Staged outside the repo (sandbox mode) | Yes for the whole authoring run, while WP-3 held the tree. Copied into the repo only after WP-3 completed, on operator request |
| Zero git operations | Yes — the files are written but unstaged and uncommitted |
| No `Chatbot/` code touched | Yes — read-only imports in the gate check |
| No LLM calls | Yes |
| No DB writes | Yes — `panchayat_1.duckdb` opened `read_only=True` for entity sampling (D6) |
| Harnesses not modified | Yes |
| §3a: caches deleted before trusting a test run | N/A — no test suite was run; the gate check imports two modules and calls one pure function |

Two executable files ship under `eval/gold/`: `build_eval_questions.py` (the
harnesses read one concatenated file, so something has to concatenate) and
`check_harness_format.py` (the gate evidence, so it should be re-runnable). Both
are additive and outside `Chatbot/`. If the operator wants this tree to be pure
data, both can be deleted — the JSONL is self-contained and the harness formats
are documented in `eval/gold/README.md` §5.
