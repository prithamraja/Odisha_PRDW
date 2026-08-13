# Odisha PR&DW — gold eval set (WP-4a, first draft)

205 questions phrased the way officers actually ask them, each carrying an
expected route into the signed-off `AI_Chatbot_Questions.xlsx` catalogue and an
expected *behaviour*. This is what WP-4's recall and end-to-end evals grade
against.

**Status: DRAFT, pending SME ratification.** Nothing here has been graded
against a running system, and no question has been reviewed by a domain expert.
The routes are the author's reading of the workbook; the Odia and code-mixed
phrasings are the author's, not an Odia speaker's. See `handoffs/WP4a_REPORT.md`
for the sign-off list.

Benchmarks to beat, from the two prior deployments: **recall@30 ≈ 97 %**,
**end-to-end ≈ 96–97 %** behaving correctly.

---

## 1. Files

One JSONL file per catalogue bracket, plus two files for question classes that
sit outside the catalogue's 10 brackets.

| file | bracket | rows |
|---|---|--:|
| `planning.jsonl` | Planning | 42 |
| `sanitation_sbm.jsonl` | Sanitation (SBM) | 34 |
| `budgeting_funding.jsonl` | Budgeting & Funding | 22 |
| `expenditure.jsonl` | Expenditure | 22 |
| `implementation_progress.jsonl` | Implementation & Progress | 24 |
| `monitoring_alerts_dq.jsonl` | Monitoring, Alerts & Data Quality | 15 |
| `sanctions_approvals.jsonl` | Sanctions & Approvals | 11 |
| `assets.jsonl` | Assets | 10 |
| `trends_comparison.jsonl` | Trends & Comparison | 9 |
| `decision_support.jsonl` | Decision Support | 6 |
| `beneficiaries_dropped.jsonl` | *(dropped bracket — all unanswerable)* | 4 |
| `out_of_domain.jsonl` | *(not a catalogue bracket)* | 6 |

Plus:

| file | what it is |
|---|---|
| `build_eval_questions.py` | concatenates the above into the shapes the harnesses read |
| `check_harness_format.py` | the gate check: loads the built files with the harnesses' own parsers |
| `coverage.json` | machine-readable snapshot of the counts in §8 |

`build_eval_questions.py` and `check_harness_format.py` are the only executable
files here. They are additive tooling — no harness was modified. If the operator
prefers this tree to be pure data, both can be deleted; the JSONL files are
self-contained and the harness formats are documented in §5.

---

## 2. Record schema

One JSON object per line. **Harness-consumed** keys are the ones
`run_full_eval.py` reads; everything else is WP-4a metadata that the harness
ignores (it accesses specs through `.get()` on named keys only).

### Harness-consumed

| key | type | meaning |
|---|---|---|
| `n` | int | Stable unique id. Allocated in per-bracket ranges (Planning 1001–, SBM 1201–, …) so it never shifts when a question is added. |
| `q` | str | The question, exactly as typed. |
| `gold` | str | The expected workbook Question ID, or `"no_match"` when declining is the correct behaviour. |
| `acc` | list[str] | **Acceptable answer set** — additional Question IDs that are equally correct. See §3. |
| `partial` | bool | `true` ⇒ *clarification carrying a gold-set chip is an acceptable outcome*. See §4. |
| `excluded` | bool | Always `false` in this draft. Reserved for rows the SME rules out of the accuracy gate. |
| `src` | str | Provenance, `WP4a-gold/<file stem>`. |
| `session` | `"prev"` | Present only on follow-up fragments: reuse the previous question's session. **Ordering is load-bearing** — see §6. |

### WP-4a metadata

| key | type | meaning |
|---|---|---|
| `id` | str | `G<n>`. What `prior_id` and the report refer to. |
| `bracket` | str | Catalogue bracket, derived from the gold ID. |
| `lang` | enum | `en` \| `code_mixed` \| `odia` (script) \| `odia_translit` (romanised). |
| `case_type` | enum | `standard` \| `followup` \| `ambiguity` \| `unanswerable` \| `out_of_domain`. |
| `expected_behavior` | enum | `answer` \| `context_preserving_reroute` \| `clarify` \| `cannot_answer` \| `graceful_fallback`. |
| `expected_entities` | dict | Slot → value the extractor should bind, keyed by the workbook's **SQL bind names** (`date_range`, `district_name`, `block_name`, `gp_name`, `focus_area`, `theme`, `scheme`, `status`, `threshold`, `amount_threshold`, `deadline`, `activity_code`, …). Values are the exact strings the registry stores. **`top_n` never appears** — no officer says "top 10"; it is a LIMIT the system supplies, not an entity extracted from the question. See `WP4a_REPORT.md` §5.2. |
| `entity_surface` | list[str] | The surface-form phenomenon under test (alias, misspelling, lakh/crore, trailing space, …). |
| `dashboard_eligible` | bool | Whole-of-sample, no geography bound ⇒ a natural pre-computed dashboard entry. |
| `expected_result` | object | Ground truth beyond the route ID. See §7. |
| `answerability` | str | The workbook's own `Yes` / `Partial` / `No` / `Dropped` verdict for the gold row. **Not the same thing as `partial`.** |
| `unanswerable_ref` | str | For `gold: "no_match"` rows: the workbook ID this question corresponds to, so the refusal can be traced to a documented data gap. |
| `prior_id` | str | For follow-ups: the `id` of the question that must precede it. |
| `sme_review` | bool | Flagged for domain-expert sign-off (all Odia-language rows, plus judgement calls). |
| `notes` | str | Why this row exists and what would count as failing it. |

---

## 3. The acceptable-answer-set convention

**Grade by acceptable answer set, never by exact-ID match.** 24 rows carry a
non-empty `acc`. A route is a hit if `query_id ∈ {gold} ∪ acc`.

This is not leniency, it is noise control. Three things make exact-ID grading
report failures that are not failures:

1. **The workbook contains literal duplicates.** `EXP-010`, `EXP-026` and
   `EXP-030` are the same parameterised question three times; `EXP-031`/`EXP-032`
   and `BUD-014`/`BUD-017` are pairs. Exact-ID grading on the triple manufactures
   a 2-in-3 failure rate out of nothing.
2. **Sibling templates are both right.** "GPDP status for a block" is legitimately
   `PLN-001` (count uploaded) or `PLN-003` (percentage uploaded). "Utilisation" is
   legitimately planned-basis (`EXP-003`) or sanctioned-basis (`EXP-023`).
3. **Routing is nondeterministic.** ~3 % of questions flip on identical replays
   (AP). Never open a regression on a single miss — use
   `run_consistency_eval.py`.

Where an `acc` entry encodes a real semantic difference rather than a duplicate,
the `notes` field says so and the answer is expected to state which basis it
used (decision D3, caveats are first-class).

---

## 4. `partial` means "clarifying is acceptable here"

`grade_full_eval.py` buckets a clarification that offers a gold-set chip as
`partial` when the spec sets `partial: true`, and as `clarify_gold_offered`
otherwise. This draft uses `partial: true` **only** on the 11 `ambiguity` rows,
where a clarification *is* the correct outcome — not on the 251 workbook rows
whose answerability is "Partial". The workbook's verdict lives in the separate
`answerability` field. Setting `partial: true` broadly would score every
clarification as a pass and hollow out the eval.

Expected behaviour by `case_type`:

| `case_type` | correct outcome | graded as |
|---|---|---|
| `standard` | answers with a gold-set template | `hit` |
| `followup` | rebinds the changed slot, keeps the prior subject | `hit` |
| `ambiguity` | asks, offering a gold-set chip | `partial` |
| `unanswerable` | declines honestly | `hit` (grade() treats `gold == "no_match"` + no answer as correct) |
| `out_of_domain` | declines, offers catalogue suggestions | `hit` |

For `unanswerable` and `out_of_domain`, **routing to a nearby template is the
failure the row exists to catch** — `grade()` returns `wrong_template` for it.
That is the whole point of the 19 unanswerable rows: `activity_nsap` has zero
rows and `asset_unit_cost` is 100 % NULL, so a confident number is worse than a
refusal.

---

## 5. Harness formats

`build_eval_questions.py` emits both.

**`Chatbot/eval_questions_full.json`** — a JSON array of the records above, in
file order. Read by `run_full_eval.py`, `run_custom_eval.py` and
`run_consistency_eval.py`; graded by `grade_full_eval.py`.

**`<repo root>/test_questions_query_mapping.csv`** — columns `query_code`,
`topic`, `intent`, read by `recall_eval.py`. 169 of the 205 rows: follow-up
fragments, unanswerables and out-of-domain questions are excluded because they
have no catalogue entry to rank, so including them would depress recall@30 with
rows that cannot be retrieved by construction. `intent` carries the bracket
(`recall_eval` uses it only as a crowding label).

```
python eval/gold/build_eval_questions.py --check     # validate, write nothing
python eval/gold/build_eval_questions.py             # write beside the gold files
python eval/gold/build_eval_questions.py --install   # write where the harnesses look
python eval/gold/check_harness_format.py             # the gate check
```

`--check` also **cross-checks the gold set against the live catalogue**: every
`gold` and `acc` id must exist in `TEMPLATE_CATALOG`/`DASHBOARD_CATALOG`, every
`unanswerable_ref` in `UNANSWERABLE_CATALOG`, and every `expected_entities` key
must be a real `param_slot` on the gold template. Run it after any catalogue
change — that check is what caught five wrong rows when WP-3's catalogue landed.
If `Chatbot/` will not import, the cross-check is skipped with a warning and the
structural checks still run.

---

## 6. Follow-up fragments: order is load-bearing

`run_full_eval.py` resolves `"session": "prev"` to the session of the
**immediately preceding record**. A follow-up must therefore sit directly after
its prior question, in the same file. `prior_id` records which question that is,
and `build_eval_questions.py --check` fails the build if the two ever drift
apart.

The 11 fragments cover: a bare block name, a year-only edit, a direction flip
(English and code-mixed), an SBM item swap, a status swap, a narrowing with no
interrogative at all ("only Khordha please"), the brief's canonical "and in
Ganjam?", and a transliterated-Odia slot-only fragment ("Bhubaneswar block ru?").

---

## 7. Expected-result evidence

42 rows carry `expected_result`, transcribed from the workbook's **Test Report**
sheet — the row counts and first-three-rows samples from the runs that validated
the SQL against `panchayat_1.duckdb`:

```json
"expected_result": {
  "row_count": 1,
  "test_status": "PASS",
  "params_used": "{\"date_range\": \"2024-2025\", \"district_name\": null, ...}",
  "sample_output": " planned_cost  actual_expenditure  pct_utilised\n 112921943.0  42578449.6  37.71",
  "source": "AI_Chatbot_Questions.xlsx : Test Report sheet"
}
```

Evidence is attached **only** where the gold question binds no geography, because
the Test Report ran every query with geography = NULL over the 20-GP sample. A
gold question that names a block would not reproduce those counts. The authoring
script asserts this invariant.

These figures are ground truth for the 20-GP sample DB only. They change on any
data reload, and every percentage divides by 20 loaded GPs rather than the ~6,800
official roster (standing denominator caveat).

---

## 8. Coverage

### 8.1 By file × language × case type

| file | n | en | code_mixed | odia | odia_translit | standard | followup | ambiguity | unanswerable | out_of_domain | dash | evid |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `planning.jsonl` | 42 | 25 | 11 | 4 | 2 | 32 | 3 | 4 | 3 | 0 | 13 | 9 |
| `sanitation_sbm.jsonl` | 34 | 20 | 9 | 3 | 2 | 30 | 1 | 2 | 1 | 0 | 29 | 11 |
| `budgeting_funding.jsonl` | 22 | 13 | 5 | 2 | 2 | 19 | 1 | 1 | 1 | 0 | 9 | 6 |
| `expenditure.jsonl` | 22 | 13 | 5 | 2 | 2 | 20 | 1 | 1 | 0 | 0 | 16 | 9 |
| `implementation_progress.jsonl` | 24 | 14 | 6 | 2 | 2 | 18 | 2 | 2 | 2 | 0 | 8 | 4 |
| `monitoring_alerts_dq.jsonl` | 15 | 10 | 3 | 1 | 1 | 11 | 0 | 0 | 4 | 0 | 0 | 0 |
| `sanctions_approvals.jsonl` | 11 | 7 | 2 | 1 | 1 | 9 | 2 | 0 | 0 | 0 | 1 | 1 |
| `assets.jsonl` | 10 | 6 | 2 | 1 | 1 | 6 | 1 | 0 | 3 | 0 | 1 | 1 |
| `trends_comparison.jsonl` | 9 | 5 | 2 | 1 | 1 | 8 | 0 | 1 | 0 | 0 | 1 | 1 |
| `decision_support.jsonl` | 6 | 3 | 2 | 0 | 1 | 5 | 0 | 0 | 1 | 0 | 0 | 0 |
| `beneficiaries_dropped.jsonl` | 4 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| `out_of_domain.jsonl` | 6 | 4 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| **total** | **205** | **122** | **49** | **19** | **15** | **158** | **11** | **11** | **19** | **6** | **78** | **42** |

Language: 59.5 % English / 23.9 % code-mixed / 16.6 % Odia (9.3 % script,
7.3 % transliterated) — against the 60/25/15 target.

### 8.2 Distribution vs the catalogue

Denominator is the 195 rows in the 10 catalogue brackets; `Beneficiaries` and
`Out of domain` sit outside it.

| bracket | gold | gold % | catalogue | catalogue % |
|---|--:|--:|--:|--:|
| Planning | 42 | 21.5 | 86 | 23.7 |
| Sanitation (SBM) | 34 | 17.4 | 86 | 23.7 |
| Budgeting & Funding | 22 | 11.3 | 46 | 12.7 |
| Implementation & Progress | 24 | 12.3 | 40 | 11.0 |
| Expenditure | 22 | 11.3 | 38 | 10.5 |
| Monitoring, Alerts & Data Quality | 15 | 7.7 | 23 | 6.3 |
| Sanctions & Approvals | 11 | 5.6 | 14 | 3.9 |
| Assets | 10 | 5.1 | 12 | 3.3 |
| Trends & Comparison | 9 | 4.6 | 12 | 3.3 |
| Decision Support | 6 | 3.1 | 6 | 1.7 |

SBM is the one deliberate under-weight (17.4 % against 23.7 %). Its 86 workbook
rows are ~5 lifecycle stages × ~17 item concepts — near-mechanical variants of
one template shape — so proportional sampling would have bought 20 more rows of
the same test. The small brackets are correspondingly over-weighted because each
needs a floor of coverage regardless of share.

164 distinct workbook Question IDs appear as a `gold` or `acc` target (45 % of
the 363-row catalogue).

---

## 9. What the phrasing deliberately exercises

Registry behaviour pinned by at least one row each:

- **Fiscal year (D9/D11):** `2024-25`, `24-25`, `FY 24-25`, `2024-2025`,
  `financial year 2024-2025`, `last year` → `2024-2025`, two years in one
  question, and Odia numerals `୨୦୨୪-୨୫` (a **known gap** — `date_phrase`'s regex
  is ASCII-only, so G1008 expects a clarification, not an answer).
- **Relative dates resolve against the DATA, not the clock:** `last year` is the
  second-newest *loaded* year.
- **No-year control cases:** PLN-038 and EXP-002 are multi-year trend templates
  with no `$date_range` slot, so they must *not* clarify. Without these, "always
  clarify when no year is stated" would pass the eval.
- **Geography aliases and misspellings:** `khurda` → Khordha (alias table),
  `Kordha` and `Bhubaneshwar` (must reach the fuzzy tier — not in the alias table).
- **Tier collisions (D4):** `Laxmipur`, `Bheden`, `Kalimela` are each both a GP
  and a block *in the 20-GP sample*. Expected: clarify, never a silent pick.
- **Scheme colloquials (D11.2):** `CFC` / `15th FC` / `15th CFC` → XV Finance
  Commission; **unqualified `SFC` → 5TH STATE FINANCE COMMISSION**.
- **Amounts:** `Rs 1000`, `1 lakh`, `5 lakh`, `Rs 1,00,000`.
- **Stored-string traps:** `Theme 5 - Clean and Green Village ` (trailing space)
  and `\tWORK COMPLETED` (leading tab, TRIM-cleaned in the views).
- **Same slot, different unit:** `$threshold` is days in G1701/G1706 and percent
  in G1707/G1952.
- **A bare activity code** (`125711758`) that must not read as a year or amount.
- **Decoys:** "weather in Bhubaneswar" (real block name), "Sarpanch of Andhrua"
  (real GP, no person data anywhere), "MGNREGA wage rate this year" (adjacent
  programme in `dim_welfare_scheme`, bindable date phrase, no wage data).

---

## 10. Regenerating

The JSONL files are hand-authored content, not generated from the workbook — the
whole point is that the phrasing is *not* the workbook's. Edit them directly.
`coverage.json` is a snapshot written when the set was authored; the two harness
artefacts are derived and rebuildable at any time:

```
python eval/gold/build_eval_questions.py --install
python eval/gold/check_harness_format.py
```

To add a question: append to the right bracket file with an unused `n` in that
bracket's range, then re-run the builder's `--check`. If it is a follow-up, place
it directly after its prior question and set `prior_id`.
