# WP-6e — Show the reranker the phrasings that found each candidate (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `Ask/query_router/vector_retriever.py` (`retrieve_scored`); `Ask/query_router/reranker.py` (`_RERANK_SYS`, `rerank`, the candidate listing); `Ask/query_router/router.py` (`_route_vector`, the one production `rerank(...)` call ~L2482); `Ask/rerank_eval.py` (the other caller); `Ask/recall_eval.py` (`crowding_extra`); `handoffs/WP6_REPORT.md` §5 ("the reranker never sees paraphrases"); `handoffs/WP6d_REPORT.md` §5, §8.2, §9.
**Sequencing:** WP-6d has landed (`2c2c7bf`..`3721862`). **Build on `3721862`**, in a fresh mirror (`C:\dev\odisha-wp6e`, a plain copy of `Ask/`).
**Scope:** one change. It is an experiment behind a config switch, measured against WP-6d's runs. **Not in scope, deliberately:** the four fixes the WP-6d report hands back — reranker notes on BUD-003 / BUD-005, the plain-count total, the PLN-007 "delayed" phrasing and the refusal-precedence rule, the EXP-009 / TRD-002 note. They are held back so this run measures one thing. If they changed at the same time, no row's movement could be attributed. Also out of scope: catalogue, paraphrase, `rerank_context.py` and `_DISAMBIGUATION` changes of any kind; retrieval thresholds; `VECTOR_TOP_K`.

## 0. Why this package exists

Ask answers in two stages:

- **Search** compares the question against every catalogue question **and every example phrasing** (3,465 vectors, about 9 phrasings per template) and keeps the best 30 distinct templates.
- **The reranker** (`gpt-5.4-mini`) then picks one or declines. It sees only each candidate's catalogue question, its generated "↳" note and its accepted filters. **It never sees the phrasings.**

That gap keeps costing rows. When a phrasing is what brought a candidate in, the reranker judges that candidate on text that does not resemble the officer's words:

- WP-6 lost two rows this way.
- In WP-6d, BUD-003's new phrasings put it at retrieval rank 0 for pilot rows 1007 / 1009, and the reranker still declined both.
- Eval_1 row 42 had EXP-009 at rank 0, and the reranker picked TRD-002.

**Offline measurement** by the PM (2026-09-28): all 237 cached recall queries replayed against the current index in `C:\dev\odisha-wp6d\.tmp`, no API calls.

- For essentially **every** candidate, the best-matching vector is a phrasing, not the catalogue question. So the reranker is almost never shown the text that made search choose it.
- Search walks on average 63 vectors to collect 30 templates (p90 110, max 179). That is the gate 8 crowding line (32.2 / 146) plus the 30 themselves.
- Extra reranker input per call, against about 5,800 tokens today (≈1,040 of instructions plus ≈4,770 of listing):

| what each candidate carries | mean | p90 | max |
|---|--:|--:|--:|
| 1 best phrasing | +700 | +773 | +872 |
| **the rule below, cap 4 (the operator's choice)** | **+1,121** | **+1,756** | **+2,151** |
| the rule, no cap | +1,455 | +2,501 | +4,579 |

**Operator ruling, 2026-09-28.** Show each candidate the phrasings search walked through before it reached the 30th distinct template, best first, **capped at 4 per candidate**. So if four phrasings of one template outrank another template's best, all four are shown.

## 1. Hard constraints

- **One switch.** `config.RERANK_EXAMPLES_PER_CANDIDATE = 4`. Setting it to `0` must reproduce WP-6d's reranker input **byte-for-byte**, with a test asserting it. Adoption or rollback is then a one-line config change.
- **No change to what search returns.** The 30 candidates, their order and their scores are identical with the switch on or off; test it. The examples are extra information handed along, never a re-ranking.
- **No change to the catalogue**, its paraphrases, `rerank_context.py` or `_DISAMBIGUATION`. `derive_catalog.py --check` and `validate_catalog.py` (343 / 0) stay green untouched.
- Ask-side paths only; Drive `.duckdb` read-only; `.env` untouched; every paid run through `confirm_spend`; Ask stays on `gpt-5.4-mini`; no file serving "sector" or "Sankalp" changes.

## 2. Tasks

### T1 — Search hands back the walked phrasings

Give `VectorRetriever` a method alongside `retrieve_scored`, for example `retrieve_with_examples(query, k, per_candidate)`, that returns the same `(qid, display, score)` list plus `examples: dict[qid, list[str]]`.

- Walk the vectors in descending score and stop when the (k+1)-th distinct template would begin. That is exactly the set `crowding_extra` counts.
- For each candidate, keep up to `per_candidate` of its walked vectors, best first.
- **Skip the vector that is the catalogue question itself**, because the reranker already sees it.
- Return the phrasing as written in the catalogue, not the `_clean`-ed embedding text.
- One embedding call, as today. `retrieve_scored` keeps its signature and output for every other caller.
- Refusal entries and dashboards are treated exactly like templates.

### T2 — The reranker shows them

`rerank(query, candidates, client, examples=None)`. Under each candidate that has examples, after the "↳" and "accepts filters" lines:

```
    found by: "How much of the sanctioned amount came from a given scheme in a given year?"
              "Split the sanctioned funds into SFC and Own Funds in a given year"
```

One sentence joins the rules in `_RERANK_SYS`, beside the existing "judge by the ↳ description" rule:

> *"found by:" lines are the example phrasings that brought a candidate into this list — they show how officers word that question. The "↳" line says what it measures. When the two point different ways, decide by what the candidate measures.*

`router._route_vector` passes the examples when the switch is above 0. `rerank_eval.py` gains a `--examples N` flag, so the offline harness can compare both ways.

### T3 — Tests

- Switch at 0: prompt identical to WP-6d. Switch at 4: a stubbed index with five phrasings of one template ranked above another's best shows exactly four, best first, and never the catalogue question.
- The candidate list is unchanged in both states.
- The walk stops at the (k+1)-th template.
- Record the prompt token count of one real listing in the test notes (via `tiktoken o200k_base` if installed, or `len/4`).

### T4 — Measure, in two stages

**Stage 1 — the rows the reranker has been getting wrong** (~40 calls, `confirm_spend`). Run each with the switch at 4:
- WP-6c pilot rows 1002, 1007, 1009;
- WP-6d pilot rows 1032, 1043, 1044;
- Eval_1 rows 42, 49, 211, 315;
- the two WP-6 §5 rows ("completed sanitation activities under Swachh Bharat" → STS-003; "activities within the sanitation category" → PLN-049).

Report per row: WP-6d's outcome, this outcome, and the examples the reranker was shown for the picked and the expected template. **Stage 1 is for understanding, not a gate.** Continue to stage 2 whatever it shows. Only stop and report if the switch at 4 makes the reranker fail to return valid JSON or time out on any row.

**Stage 2 — the regression runs, switch at 4:**
1. **Eval_1 replay** (314 rows, ~1,000 calls), graded unchanged, diffed row by row against `handoffs/WP6d_eval1_replay.csv` (293 / 5 / 0 / 4).
2. **One gold replay** (275 rows, ~800 calls), sequential, graded unchanged, diffed row by row against `handoffs/WP6d_gold_replay_run1.csv` (90.2%, 6 confidently wrong) and WP-6's three verdicts.
3. **The 44 pilot rows** (~150 calls), diffed against `handoffs/WP6d_pilot_replay.csv`.

**What to report beside the headline numbers**, because they are what decides adoption:
- **Look-alike families.** Every row whose expected or served template is in the SBM keyword families (compost pits, segregation, IHHL), the plan-versus-cashbook pairs (EXP-* versus the cashbook entries), or uploaded-versus-approved (PLN-001 / PLN-002 family). List each such row that changed outcome, either way. These are the families the "↳" design protects, and where extra wording is most likely to mislead.
- **Answer↔ask shift.** The count of no-match / ambiguous clarifications before and after. More examples could make the reranker more decisive, which is good only if the extra answers are right.
- **Cost and speed.** Mean and p90 reranker prompt tokens, and reranker latency, before and after (from `llm_usage`).

### T5 — Report

`handoffs/WP6e_REPORT.md`:
- the stage 1 table;
- the three diffs;
- the look-alike list;
- the clarification counts;
- tokens and latency;
- spend;
- **a recommendation**: keep the switch at 4, or set it to 0.

**Leave the switch at 4 in the committed code unless** the gold replay's confidently-wrong count exceeds WP-6d's 6, or Eval_1 incorrect exceeds WP-6d's 4. In either case commit it at 0 and say so. **The operator decides adoption.**

## Gate (definition of done)

1. Switch at 0 is byte-identical to WP-6d's reranker input; the candidate list is identical in both states; the full suite and `prdw_gates.py` are green.
2. Stage 1 reported in full.
3. Eval_1, gold and pilot runs complete, each diffed row by row against WP-6d, with the look-alike list and the clarification counts.
4. Token and latency figures reported. Mean added reranker input within about 20% of the PM's offline figure (+1,121 tokens); if it is not, explain why.
5. No catalogue, paraphrase, note or threshold change; this brief and the report committed, one commit per task, not pushed.

**Expected spend:** about 2,000 calls, all through `confirm_spend`.

| run | calls |
|---|--:|
| stage 1 | ~40 |
| Eval_1 | ~1,000 |
| gold | ~800 |
| pilot | ~150 |
