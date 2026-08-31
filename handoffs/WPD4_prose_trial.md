# WP-D4 brief — prose trial v2 (context-driven writer + safety net)

**Workstream:** Discover. **Nature: TRIAL.** The deliverable is a review
document. No published artifact changes; nothing is wired to the feed, the
reports, or the frontend. **Authored:** PM, 2026-08-31 (D40, as revised).

**Design (operator, 2026-08-31, superseding v1 of this brief):** no writing
rules constrain the model. The writer receives a context brief (Appendix A,
verbatim) plus the 15 findings — each as its current feed sentence with
deterministically computed reference figures — and writes freely. Safety lives
entirely AFTER the writer: mechanical nothing-invented checks and a
different-model verifier, invisible to the writing step. There is no separate
rules document — this brief is self-contained, and quality is judged directly
on the outputs at the operator gate.

---

## Files in scope (writable) — nothing else

```
Insights/prose_trial/**            all trial code, packets, outputs, logs (NEW directory)
handoffs/WPD4_REPORT.md            your report
```

**DO NOT TOUCH:** every existing file under `Insights/src/`,
`Insights/metainsights/`, `Insights/reports_prdw/`, the domain packs, `Data/`,
`Ask/`, `eval/`, `handoffs/` (except your report), `PROJECT_PLAN.md`, any
`.env` (use for keys; never print, copy, or write). **No git operation** beyond
read-only `status`/`log`/`rev-parse`. Bugs found in existing code: log in the
report, do not fix.

## Preconditions — verify, then STOP on failure

1. **The tree is committed** (`git status` clean at start; dirty → STOP and
   report, per the standing discipline).
2. **Local-mirror execution only** (D6): never run Python against the Drive
   path. Rebuild views via the calibration README recipe step 1 if the
   reference-figure computation needs the parquet files.
3. **The pinned candidate set is intact:** SHA-256 of the six files in
   `Insights/metainsights/` must match WPD3b report §4 exactly. Mismatch → STOP.
4. `Insights/.env` provides the OpenAI key. Missing → STOP.

## Read first (with why)

| File | Why |
|---|---|
| Appendix A below | The writer's entire prompt context — embed verbatim, never paraphrase |
| `Insights/metainsights/global_feed.json` | The 15 inputs = feed ranks 1–15 (`feed` array, in order); each row's `summary` is the finding's current sentence |
| `Insights/src/phase5b_report.py` | How figure enrichment and reading notes are computed today — reuse for reference figures, don't reinvent |
| `Insights/src/discover_config.py` | The shared prose-model constant (D17) and its budget-check discipline |
| `handoffs/WPD3_REPORT.md` §4.4 | Two past prose bugs (`.env` path; silently missing caveats) — the failure modes the safety net exists for |

## Objective

Send one batch request — Appendix A + 15 finding packets — to the pinned prose
model; receive 15 two-part insights (lead, 1–2 sentences; detail, up to ~200
words). Run the safety net per finding. Failures regenerate once; a second
failure falls back to the current feed sentence. Deliver a side-by-side review
document the operator labels.

## Non-goals

No regeneration of the feed, editions, or executive report. No contract/schema
change. No frontend work. No re-mining. No style constraints or style checks of
any kind — style is the operator's judgment at the gate, not code's. No
investigation of the frontend one-liners (separate, PM-owned).

## Facts you need (one line each)

- The prose model is pinned by D17 via the shared `discover_config` constant;
  GPT-5.x are reasoning models — run the completion-token budget check before
  first use or you get silently empty prose.
- The feed's `summary` field is frozen by D16 — your output goes only in the
  review document.
- Every figure the model may use must be in its packet or in Appendix A's
  background; the model computes nothing (the checks enforce this).
- Appendix A's background facts each trace to a published reading note — add
  none, remove none; if one looks wrong, STOP and report rather than edit it.
- `Insights/.env` loads from `BASE_DIR/.env`, not the repo root (WPD3 §4.4).

## Tasks

### T1 — Finding packets (deterministic)

**Do:** For each of the 15 findings, emit one packet: the current feed
`summary` sentence verbatim, plus reference figures computed by reusing the
existing enrichment paths — display-formatted exactly as they may appear in
prose ("Rs 42.61 lakh", "5 out of 9"), covering the finding's own numbers
(totals, shares, leader values, per-year figures where the pattern is a trend)
and the exception detail the engine recorded (which places, and whether each is
opposite-direction, different-pattern, or no-clear-pattern, in words).
**Done when:** 15 packets exist; every figure traces to the pinned candidate
set, the views, or a published reading note (provenance recorded per figure).
**Trap:** raw floats — the packet carries display strings, because the checks
do substring matching.
**Escalate if:** a finding's natural figures cannot be computed from existing
enrichment paths — mark the packet thin and continue; do not improvise new
calculations.

### T2 — The writer call (one batch)

**Do:** One request to the pinned prose model: Appendix A verbatim, then the 15
packets. No rules, no style instructions, no phrasing suggestions beyond what
Appendix A itself says. Ask for clearly delimited output per finding: lead
line, then detail block. Run the D17 budget check first.
**Done when:** 15 two-part renderings exist; request/response and `usage`
logged.
**Trap:** truncation mid-batch — if the response cuts off, split into smaller
batches rather than raising the output cap past its ceiling.

### T3 — Nothing-invented checks (code, per finding, both parts)

**Do:** Assert: (a) every numeral appears verbatim in that finding's packet or
in Appendix A's background figures; (b) every place/person/category name
appears in the packet; (c) no raw database token — column identifiers,
"(varies)", "PERIOD_…", engine pattern-type enums; (d) lead ≤ 2 sentences,
detail ≤ ~200 words.
**Done when:** machine-readable pass/fail per check per finding.
**Trap:** loose normalization ("51.96" matching "5,196"). **No style checks —
none.** If the model ignored the background context or wrote in an order you
wouldn't have chosen, that is the operator's call at the gate, not a failure.

### T4 — Verifier (AI, per finding)

**Do:** A *different* model than the writer (choose from what the existing keys
serve; verify the ID against the live model list per D17; record the choice —
same-vendor-only is acceptable if disclosed). Input: the packet + Appendix A's
background + the rendering. Question: does the rendering claim anything the
packet and background do not support, or lose/weaken a limitation they state?
Output JSON: `pass` (each core claim mapped to a packet/background entry) or
`fail` (quoting the drifted claim, naming the missing or contradicted fact).
Vague verdict = fail-to-verify, not pass.
**Done when:** 15 verdicts logged machine-readably.
**Trap:** rubber-stamping — the claim mapping on pass is not optional.

### T5 — Failure path

**Do:** Any T3/T4 failure → regenerate that one finding (single-finding call:
Appendix A + its packet + the failure reason) → re-run T3+T4 → still failing →
final rendering is the current feed sentence, marked `FELL BACK`.
**Done when:** all 15 findings carry a final rendering that is either
check-green or an explicit fallback.

### T6 — Review document

**Do:** `Insights/prose_trial/REVIEW.md`: per finding — current feed text |
final lead + detail | check results | verifier verdict | status (first-pass /
regenerated / fell back). Head it with
the candidate-set id and totals: first-pass rate, what the code checks caught,
what the verifier caught that code missed (with quotes), total calls and cost.
**Done when:** the document reads without opening any other file.

## Spend guard

Hard cap **60 API calls** (writer batch + verifier + regenerations; expect
~20). Per-call limits, set in code: input under **16,000 tokens** (a packet
overflow means T1 went wrong — STOP, don't send); writer output capped at
**8,000 completion tokens**, verifier at **4,000**. These ceilings interact
with the D17 budget check, which guards the opposite failure — reasoning
models spend hidden thinking tokens and return empty text if starved. Budget
check shows truncation → split the batch (T2 trap) before touching ceilings;
record whatever numbers actually worked. Worst case ≈ 60 × (16k + 8k) ≈ 1.44M
tokens — small money; record `usage` on every call regardless (D28 rule 8).
Any cap reached → stop, deliver what exists, report the shortfall.

## Cut line

If the cap bites: findings 1–8 through T1–T5 beat all 15 through T1–T6. T4 is
not cuttable — measuring what the verifier catches is half the point of the
trial.

## Escalation protocol

STOP (report, don't proceed): precondition failures; pinned-set hash mismatch;
empty completions after two budget-check attempts; an Appendix A background
fact that appears wrong. Decide-and-document (report journal): batch splitting,
check normalizations, verifier model choice, packet field details.

## Gate

1. All 15 final renderings check-green or explicit fallbacks.
2. Verifier verdicts logged with claim mappings/quotes — no vague verdicts.
3. Usage recorded, under cap.
4. `git status` shows exactly the writable set.
5. **Operator gate (not yours):** the operator labels each of the 15 — adopt /
   adopt-with-edits / reject — judging against the current text. That labeling
   decides whether this design goes to production and what the context brief
   needs changed.

## Report — `handoffs/WPD4_REPORT.md`

§0 gate table · §1 what ran (models, IDs, budget-check evidence, batch
structure) · §2 results table (per finding: status, checks, verdict) · §3 what
each safety layer caught, with quotes — the core question is whether the
verifier caught real drift the code checks missed · §4 cost and usage · §5
defects found in existing code (logged, not fixed) · §6 decision journal · §7
self-audit (files written = allowlist; git read-only).

---

## Appendix A — the context brief (the writer's verbatim prompt context)

> You are writing for a decision-aid system used by government officials in
> Odisha's Department of Panchayati Raj & Drinking Water. The system
> automatically analyses village-level planning and spending records —
> development plans, sanctions, payments, works and photo evidence from
> Gram Panchayats, blocks, and districts — and surfaces patterns worth an official's attention.
>
> Your readers are busy block-, district- and state-level officials, not data
> analysts. They read these insights to decide where to direct attention:
> which districts to question, which records to reconcile, which local
> practices to check at the next review.
>
> Below are 15 findings from the analysis engine, each written in the engine's
> internal style — accurate but full of database language — along with
> reference figures for each. Rewrite each finding as an insight a senior
> officer would find clear and actionable:
> - a one-to-two-sentence lead the officer sees first;
> - a short detail paragraph explaining what was found, which places are
>   exceptions and in what way, and what is worth checking or asking at the
>   next review.
>
> Write naturally, in plain English. Use the reference figures where they
> strengthen the point; use no number that is not provided. Be direct about
> what the data can and cannot establish — these records are incomplete in
> known ways described below, and an insight that overstates certainty could
> send an official after the wrong problem.
>
> Background to reflect where relevant:
> - Sanction records exist for only about one work in six, so figures on a
>   sanctioned basis describe that subset, and a falling sanctioned value can
>   mean fewer sanctions or fewer sanctions being entered.
> - Cost-free activities (training, campaigns, services) began being recorded
>   only in 2023-24, so activity counts jump at that boundary for a reporting
>   reason, not a real one.
> - Total cashbook spending has not grown across these years, while the share
>   of spending linked to a planned activity rose from 2.7% to 53.2% — a rise
>   in "linked spending" is mostly better record-keeping.
> - March concentrates payments every year; it is the fiscal year-end and this
>   is normal government cash flow.
> - Output categories "Code 101" to "Code 110" have no descriptions on file;
>   nothing can be concluded about what they contain until the department
>   supplies the decode.
> - "Uncategorised" assets are works with no asset category recorded — about
>   two-thirds of all works; it is not itself a kind of asset.
> - Only 17 works in the whole sample are marked completed, so completion
>   figures measure recording practice, not delivery.
> - Voucher and payment counts are workload, not a performance rating.
> - This is a 20-Gram-Panchayat sample; percentages describe the sample, not
>   the state.

*(Implementation note, not part of the prompt: every bullet above traces to
the published reading notes in the executive report and the signed glossary —
the agent embeds this text verbatim and adds nothing.)*
