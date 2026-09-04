# WP-D9 brief — judge completeness: from "smallest sufficient set" to "every distinct finding"

**Workstream:** Discover. **Nature: BUILD, staged and gated — adoption by
measurement.** The judge currently keeps a median of 3 and at most 6
findings because its prompt asks for the smallest sufficient set — a
readability rule written when findings rendered as bare blocks. WP-D7 moved
presentation to the consolidating writer, so the judge's set is now input to
a narrative, not what the officer reads. This WP raises the ceiling to 20,
rewrites the instruction as completeness-with-no-repeats, binds the judge's
prompt to its safety evidence (a gap found 2026-09-03), and ships the change
only if the numbers hold. **Authored:** PM, 2026-09-03. Not yet registered in
`PROJECT_PLAN.md`; D-numbers to be assigned by the operator.

**Operator rulings this brief encodes (2026-09-03):**

1. **`ANSWER_CAP` 12 → 20.** A ceiling, not a target (D42 ruling 5 stands:
   the floor decides membership; the count is a property of the question).
2. **The judge's instruction changes from minimality to completeness:** keep
   every finding that adds distinct information to the answer; drop
   near-repeats — the same point over another slice of the data — keeping
   the clearest one. The near-repeat rule is retained verbatim in spirit; only
   "smallest set" goes. Exact wording in Appendix A.
3. **The judge's prompt is bound to its evidence, like its model id.** The
   out-of-scope silence guarantee is a property of (model, prompt) together;
   today the gate checks only the model. `judge-prompt-evidenced` closes
   that. Any future prompt edit goes red until requalified — same as a model
   swap.
4. **Adoption is decided by the D9.1 matrix, not by preference.** The
   decision rule is written below before any run. If it fails, the
   instruction reverts (config), the cap stays at 20 (harmless with the old
   instruction), and the report says why.

**Concurrency:** runs in PARALLEL with **WP-D8 (frontend hover-to-source,
`handoffs/WPD8_hover_to_source.md`)** — its writable set is
`frontend/ab-dashboard-main/src/{services/discover-api.ts, lib/discover-answer.ts,
lib/discover-answer.test.ts, components/insights/**, pages/Index.test.tsx}` and
`handoffs/WPD8_REPORT.md`; expect those paths dirty in `git status`, touch none
of them, list them in your self-audit as not-yours. It forbids itself
`DiscoverChat/**`, so the two sets are disjoint by construction. Also WP-D4b's
set per the WP-D6 brief's list — touch none of it. **Must start from a
committed baseline including the WP-D7 work** (WPD7_REPORT §5 file set). Not
committed → STOP.

---

## D9.0 — bind the judge prompt to its evidence (first, before anything changes)

- The judge evidence files (`judge_arm_results.json`,
  `decompose_oos_results.json`) gain the SHA-256 of the judge prompt that
  produced them (the call log already records `prompt_sha256` per call — the
  prompt *template* hash is what gets stored, computed the same way for both
  the file and the gate).
- New gate check `judge-prompt-evidenced`: the configured prompt's hash must
  equal the evidence file's, else red with a message naming the
  requalification commands (mirror `judge-model-evidenced`).
- README "Requalifying the judge" extended: model id OR prompt change →
  re-run the battery.

**Gate D9.0:** demonstrated both ways — the check is green on the current
prompt; a one-character prompt edit turns it red; restored, green again. The
existing 32/32 offline gate stays green. **Do this before D9.1**, so D9.1's
prompt change is caught by a gate that exists, then cleared by
requalification — the workflow the binding is for.

## D9.1 — the completeness instruction, measured

Config: `ANSWER_CAP=20`; judge prompt per Appendix A (the current prompt
kept reachable as the reversion, e.g. `DISCOVERCHAT_JUDGE_PROMPT=minimal`).

**The matrix — every run on the same question sets WP-D5/D7 used, so the
baselines are the published ones:**

| run | script | measures | baseline (arm D / D7) |
|---|---|---|---:|
| (a) out-of-scope battery | `run_decompose_oos.py --repeats 4` | false-answer rate over 20 question-runs | 0.0% |
| (b) 60-question retrieval set | `run_judge_arm.py` | kept median / max; cap-binding rate; geo hit-rate; place-named precision; measure precision | 3 / 6; 0%; 91.2%; 98.3%; 97.1% |
| (c) 15-question writer set | `run_answer_compare.py` | writer fallback rate; numerals bound; latency p50 / p90 | 13.3%; 225/229; 27.6 s / 55.7 s |
| (d) restatement share | new, small: over (b)'s kept sets | fraction of kept findings sharing (measure, breakdown, pattern type) with another kept finding in the same answer | report |

**Decision rule, fixed before running — hard criteria, all required:**

- (a) false-answer rate **0.0%**. Any out-of-scope question that keeps
  anything, on any run, fails the WP. No exceptions, no re-rolls.
- (b) geo hit-rate **≥ 91.2%** (the change exists to gain coverage; it may
  not lose it); place-named precision **≥ 96.0%** and measure precision
  **≥ 95.0%** (a bounded price for coverage — more than ~2 points means the
  judge is keeping on-topic-but-not-answering findings, which the officer
  pays for).
- (c) writer fallback rate **≤ 20%**; p50 latency **≤ 35 s**.
- Cap binding on **≤ 10%** of (b)'s answers — if the judge hits 20 often,
  20 is not a ceiling and the instruction is a sweep, not a judgement.

Soft criteria, reported for the operator: kept median/max; (d) restatement
share; the 15 narratives side by side (old judge → writer vs new judge →
writer) for the operator's reading — narrative quality is the operator's
acceptance, as in D7.

**On pass:** the new prompt becomes the default, the evidence files are
regenerated from these runs (with the new prompt hash and the model id), and
`judge-prompt-evidenced` / `judge-model-evidenced` are green on the shipped
configuration. **On fail:** revert the instruction, keep the cap, regenerate
nothing, report the matrix in full — a measured "no" is a deliverable.

## D9.2 — near-repeat collapse (conditional)

Only if D9.1's restatement share exceeds **30%**: add a deterministic
pre-judge collapse of records sharing (view, measure, breakdown, subspace,
pattern type, highlight) — keeping the highest-scoring — alongside the
existing sentence-identical diversity rule. Then re-run (a)–(d) and apply the
same decision rule. If the share is below 30%, skip and say so; the writer's
own consolidation is handling it.

**Gate D9.2 (if run):** the collapse is proven lossless on distinct findings
(no two records with different coordinates ever merge — a test with a seeded
pair) and the matrix passes as in D9.1.

---

## Files in scope (writable) — nothing else

```
DiscoverChat/**                  judge prompt, config, gates, evidence files, tests, README
handoffs/WPD9_REPORT.md          your report
```

**DO NOT TOUCH:** everything under `Insights/`, `Ask/**`, `LABEL_SHEET.md`,
`PROJECT_PLAN.md`, every `.env`, `.gitignore`, `deploy/**`. WP-D4b's set.
The writer prompt (`CONSOLIDATING_WRITER_PROMPT`) is out of scope — the
standing `consolidation-prompt-is-the-operators` check must stay green. Bugs
found: log, don't fix. No git operation beyond read-only
`status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. WP-D7 file set committed; tree otherwise clean except WP-D4b's set,
   WP-D8's frontend set (concurrency note above), and PM-edited handoffs. Any
   other dirty path → STOP.
2. Local-mirror execution only; re-mirror first. **Sweep for existing work
   before building** (the WP-D6 §0 lesson).
3. Pinned SHAs per WPD7_REPORT §6 (all nine) plus `decompose_corpus_stamp.json`
   present. Mismatch → STOP.
4. `Insights/.env` keys present; `gpt-5.6-sol` (the evidenced judge model)
   reachable. The judge model is NOT changed in this WP — one variable at a
   time; a Sol→Luna question is a separate WP with its own requalification.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD5_REPORT.md` §2.4a | Arm D: why the judge exists, how selectivity was tuned (74 → 6), and the baseline table you are measured against |
| `handoffs/WPD7_REPORT.md` §4 | The writer that now consumes the judge's set; its 13.3% fallback rate and 27.6 s p50 are your (c) baselines |
| `DiscoverChat/judge.py` | The prompt (lines ~82–83 are the instruction you replace) and the id-only containment you must not weaken |
| `DiscoverChat/gates.py` | `judge-model-evidenced` — the pattern D9.0 mirrors |
| `DiscoverChat/experiments/run_judge_arm.py`, `run_decompose_oos.py`, `run_answer_compare.py` | The matrix; extend outputs, don't fork scripts |
| `DiscoverChat/config.py` | `ANSWER_CAP`, env conventions, where the prompt selector lives |

## Report

`handoffs/WPD9_REPORT.md`: the D9.0 red/green demonstration; the full D9.1
matrix as one table (baseline vs new, every criterion marked pass/fail);
the decision and its reason; the restatement share and whether D9.2 ran;
the 15 side-by-side narratives (as a separate `.md`, referenced); the
regenerated evidence files' hashes; WP-D7-style close-out with pinned SHAs
re-verified.

---

## Appendix A — the judge instruction (replaces the two bullets at judge.py ~82–83; everything else in the judge prompt unchanged)

> - **Keep every finding that adds distinct information to the answer.** How
>   many that is depends on the question — a narrow one may have a single
>   answer, a broad one many. Completeness matters: a finding the officer
>   would want and does not get is a worse failure than one extra.
> - **Where several findings make the same point over different slices of
>   the data, keep the clearest one, not all of them.** The engine mines the
>   same pattern over many overlapping slices; near-repetition is not extra
>   evidence. Two findings are distinct when they tell the officer different
>   things, not when they are worded differently.
> - **Keep nothing for a question the findings do not answer.** On-topic is
>   not the same as answering; if none of the candidates answers the
>   question, return none.

The third bullet restates the out-of-scope behaviour explicitly, because the
first bullet loosens the instruction that used to carry it implicitly. Do not
add to, reorder, or soften these three.
