# WP-D9 REPORT — judge completeness: from "smallest sufficient set" to "every distinct finding"

**Executed:** 2026-09-04, execution agent, local mirror `C:\dev\odisha-d9`.
**Brief:** `handoffs/WPD9_judge_completeness.md`.

**Verdict: ADOPTED.** Every hard criterion in the D9.1 decision rule passed, and
three of them improved on the baseline rather than paying the bounded price the
brief had budgeted for. `judge-prompt-evidenced` is in the gate; the shipped
configuration is `complete` + `ANSWER_CAP=20`, gate-green **33/33 offline and
33/33 live**, 93/93 tests.

D9.2 did **not** run: the restatement share came in at 10.9%, below the 30%
trigger. Numbers and reasoning in §3.

---

## §0 Preconditions — one failed, and the operator cleared it

| # | precondition | result |
|---|---|---|
| 1 | WP-D7 committed; tree otherwise clean | **FAILED — see below** |
| 2 | local-mirror execution, re-mirrored, swept for existing work | pass |
| 3 | nine pinned SHAs + `decompose_corpus_stamp.json` | pass, all ten match |
| 4 | `Insights/.env` keys; `gpt-5.6-sol` reachable | pass (probed live, 4.4 s) |

**Precondition 1 failed on `DiscoverChat/context_brief.py`** — an uncommitted
one-line edit to `CONSOLIDATING_WRITER_PROMPT`, which this WP puts explicitly
out of scope:

> Do not make causal claims ever **and do not use "therefore", "because", or
> "driven by".**

This was stopped on and put to the operator rather than worked around, because
it moves the exact number run (c) measures: WPD7 §4 records the 13.3% fallback
rate as *all* causal-scan, and those three words are what the causal scan
rejects. Measuring the judge instruction against a baseline that a second,
uncontrolled change was already moving would have made (c) meaningless.

**Operator ruling, 2026-09-04: keep the edit; it is the new baseline.** That
ruling carries a cost the brief did not budget for — the published (c)
baselines no longer describe this tree — so an extra calibration run was owed,
and was made before the matrix started (§2a).

**Sweep result (the WP-D6 §0 lesson):** five mirrors carry a `DiscoverChat/`
(`odisha-chat-live`, `-d5`, `-d6`, `-d6b`, `-d7`). None contained any WP-D9
work; all five still read `ANSWER_CAP = 12` and none mentions a prompt hash.
Nothing was rebuilt that already existed.

**Not mine, left alone, as the brief instructs:** `handoffs/WPD8_hover_to_source.md`
and `DiscoverChat/experiments/logs/` (untracked call log). WP-D8's frontend set
was not dirty at any point in this session, and WP-D4b's set was not touched.
No git operation beyond read-only `status` / `log` / `rev-parse` was run.

---

## §1 D9.0 — the judge prompt is bound to its evidence

The out-of-scope silence guarantee is a property of **(model, prompt) together**.
Before this WP the gate pinned only the id, so the judge's instruction could be
rewritten — which is exactly what D9.1 does — with every check staying green
while the evidence quietly stopped describing the running system.

### What was built

- `judge.py` now carries both instructions as `PROMPT_VARIANTS`, selected by
  `DISCOVERCHAT_JUDGE_PROMPT`. `minimal` is the pre-D9 wording and is
  **byte-identical to what shipped** — its hash `ad73ea44…` equals the hash of
  the prompt taken before any edit was made. `complete` is Appendix A, not
  added to, reordered, or softened.
- `judge.prompt_sha256()` hashes the prompt **template**, not a rendered
  prompt: a rendered one carries the question and 100 candidates, so its hash
  changes every call and could never be pinned. Hashed the same way `llm.call`
  hashes prompts.
- `config.evidenced_judge_prompt()` reads the hash **out of the evidence file**
  rather than restating it as a constant — the same argument
  `evidenced_judge_model` makes, one level down: a constant can be edited in
  the same commit that changes the prompt.
- Gate check `judge-prompt-evidenced` in `gates.py`, mirroring
  `judge-model-evidenced` down to naming the requalification commands
  (`config.REQUALIFY_JUDGE_PROMPT`).
- Both experiment scripts now stamp `judge_prompt_variant` and
  `judge_prompt_sha256` into their run files alongside the model id.
- README "Requalifying the judge" extended: model id **or** prompt change →
  re-run the battery.

### Stamping the old evidence was checked, not assumed

The existing evidence files were stamped with the `minimal` hash without
re-running them. That is only honest if the prompt has not changed since those
runs, so it was verified: `judge.py` last changed in `bba9943`; both evidence
files were regenerated later, in `9272453`; and the instruction bullet has
exactly one `+`/`-` line in all of git history, so it was added once and never
edited. The committed prompt therefore *is* the prompt that produced the
evidence.

### Gate D9.0 — demonstrated both ways, as the brief requires

| step | configuration | result |
|---|---|---|
| 1 | current prompt, unchanged | **33/33 green** — `judge-prompt-evidenced` PASS, `minimal` sha `ad73ea44a482` |
| 2 | one character changed (`.` → `!` in the minimal instruction) | **32/33, RED** — names both hashes and the requalification commands |
| 3 | restored | **33/33 green** again |
| 4 | `DISCOVERCHAT_JUDGE_PROMPT=complete` | **32/33, RED** — an unmeasured instruction goes red until requalified |

Step 4 is the point of the binding rather than a nuisance: D9.1's prompt change
was caught by a gate that existed *before* the change, then cleared by
requalification — the workflow the binding is for. The existing 32 checks
stayed green throughout.

Four unit tests added (`test_behaviour.py::JudgePromptBindingTests`): both
variants stay reachable; they differ only in the changed bullets and share
every other line; the hash is of the template, not a rendering; the evidence
records a hash at all. Suite **89 → 93 tests, all passing**.

---

## §2 D9.1 — the completeness instruction, measured

Configuration: `ANSWER_CAP=20`, `DISCOVERCHAT_JUDGE_PROMPT=complete`, judge
model `gpt-5.6-sol` **unchanged** (one variable at a time), writer prompt as
the operator left it.

### §2a The calibration run the operator's ruling made necessary

Run (c) on the **old** judge instruction with the **new** writer prompt, so the
matrix had a baseline it could fairly be read against:

| (c) measure | WPD7 published | recalibrated (old judge, new writer prompt) |
|---|---:|---:|
| writer fallback rate | 13.3% | **0.0%** |
| p50 latency | 27.6 s | **23.3 s** |
| p90 latency | 55.7 s | 39.6 s |

The operator's one-line edit removed the causal-scan fallbacks outright. The
published baselines are therefore **stale for this tree**, and every (c)
comparison below is read against the recalibrated column. The brief's
thresholds are absolute numbers, so they are applied exactly as written.

### §2b The matrix — every criterion, pass/fail

| run | measure | baseline | D9.1 | criterion | verdict |
|---|---|---:|---:|---|:--:|
| (a) | false-answer rate, 20 out-of-scope runs | 0.0% | **0.0%** | must be 0.0%, no exceptions | **PASS** |
| (b) | geo hit rate | 91.2% | **100.0%** | ≥ 91.2% | **PASS** |
| (b) | place-named precision | 98.3% | **100.0%** | ≥ 96.0% | **PASS** |
| (b) | measure precision | 97.1% | **98.7%** | ≥ 95.0% | **PASS** |
| (b) | cap binding (answers reaching 20) | — | **0.0%** | ≤ 10% | **PASS** |
| (c) | writer fallback rate | 0.0% (recal.) | **0.0%** | ≤ 20% | **PASS** |
| (c) | p50 latency | 23.3 s (recal.) | **29.5 s** | ≤ 35 s | **PASS** |

**All seven hard criteria pass**, and three moved the *opposite* way to the one
the brief prepared for. The decision rule allowed precision to fall as far as
96.0% / 95.0% as "a bounded price for coverage"; instead place-named precision
rose to 100.0% and measure precision to 98.7%, while the geo hit rate went from
91.2% to 100.0%.

That is worth stating plainly, because it changes what the old instruction was
doing. The judge was not trading precision for recall. Under "keep the smallest
set that fully answers the question" it was **discarding findings that did
answer the question** — the loss was coverage, and nothing was being bought
with it.

The out-of-scope result is the one that mattered most, and it is unmoved:
0.0% across 20 question-runs offline, and 0.0% again across the live gate's 10
runs. Loosening the instruction did not make the judge start answering
questions the analysis has nothing on — the third Appendix A bullet, which
restates the silence rule explicitly, is doing its job.

### §2c Soft criteria, reported for the operator

| measure | baseline (minimal, cap 12) | D9.1 (complete, cap 20) |
|---|---:|---:|
| kept median (all 61 questions) | 3 | **8** |
| kept median (answered only) | 4 | **8** |
| kept max | 6 | **17** |
| kept mean | 2.93 | **7.39** |
| questions with ≥1 finding | 51 of 61 | **53 of 61** |
| findings shown per geo question | 3.5 | **9.35** |
| judge fell back to threshold | 0 | **0** |
| ids invented by the judge | 0 | **0** |
| (c) numerals bound | 227/232, 0 uncited | **403/406, 0 uncited** |
| (c) p90 latency | 39.6 s | 55.2 s |

The baseline column is recomputed on exactly the definitions the D9.1 column
uses, and it reproduces the brief's published "3 / 6" — so the two columns
measure the same thing. Both medians are reported because they differ and the
difference is easy to misread: WP-D5's "3" counts all 61 questions including
the ten that keep nothing, while the same set reads 4 over the 51 that keep
something.

**`kept_max` is 17 and no answer bound against the cap.** 20 is behaving as a
ceiling rather than a target, which is what the "cap binding ≤ 10%" criterion
existed to test. D42 ruling 5 is untouched: the floor still decides membership,
and the judge may still only ever reject.

---

## §3 (d) restatement share — and why D9.2 did not run

**Definition** (`run_judge_arm.restatement_key`): the fraction of kept findings
sharing `(measure, breakdown, pattern type)` with another kept finding in the
*same* answer. A decomposition has no `pattern_type` and calls its breakdown
`dimension`, so it is normalised onto the same three-part key rather than
excluded — six decompositions of one measure over one dimension restate exactly
as much as six findings do. Counted over answers with 2+ kept findings: a
single-finding answer cannot restate itself, and including it would drag the
measure toward zero precisely when the judge is being most selective.

| | baseline (minimal) | D9.1 (complete) |
|---|---:|---:|
| restatement share | 1.15% (2/174) | **10.86% (49/451)** |

**D9.2 is skipped, per the brief's own rule: 10.9% is below the 30% trigger.**

The honest reading is that the share rose about nine-fold — the completeness
instruction does let more near-neighbours through. But nearly nine in ten kept
findings still carry a distinct `(measure, breakdown, pattern type)`, and the
consolidating writer is absorbing the rest: run (c) shows 0 fallbacks and
403/406 numerals bound with none uncited. The writer's own consolidation is
handling it, which is what the brief predicted for a share this size.

Recommend re-measuring if the judge model or the writer prompt changes. The
deterministic collapse is a real option held in reserve, not a dead idea.

---

## §4 The 15 narratives, side by side

`DiscoverChat/experiments/WPD9_narratives_side_by_side.md` — old instruction vs
new, with the same writer, the same writer prompt, the same model ids and the
same questions, so the instruction is the only thing that differs. Built by
`build_judge_narratives.py` from the two saved runs; nothing was re-run to
produce it.

**Narrative quality is the operator's acceptance, not this suite's** (the D7
rule), and nothing in this WP scores prose. What the suite asserts is the
mechanical part — every numeral bound to a cited finding, no invented ids, the
causal scan green — and all of that holds.

What the operator will see, stated so the reading is not oversold: the new
answers are **longer**. "How is Chikilli doing?" goes from 6 findings to 13,
and from three paragraphs to five. On reading, the added paragraphs carry
distinct content rather than restatement — the plan's composition, an
approval-versus-status reconciliation point, the annual spending profile, the
concentration of general-component spending in a single activity status.
Whether that is what an officer wants to receive in one answer is the judgement
this WP cannot make and does not claim to have made.

---

## §5 Files touched — all inside the brief's writable set

```
DiscoverChat/judge.py                   two prompt variants, prompt_sha256()
DiscoverChat/config.py                  JUDGE_PROMPT_VARIANT, evidenced_judge_prompt(),
                                        REQUALIFY_JUDGE_PROMPT, ANSWER_CAP 12 -> 20
DiscoverChat/gates.py                   judge-prompt-evidenced
DiscoverChat/README.md                  "The prompt is qualified too, not just the id"
DiscoverChat/tests/test_behaviour.py    JudgePromptBindingTests (4 tests)
DiscoverChat/experiments/run_judge_arm.py       prompt stamp; kept/cap/restatement metrics
DiscoverChat/experiments/run_decompose_oos.py   prompt stamp
DiscoverChat/experiments/build_judge_narratives.py            NEW  the side-by-side
DiscoverChat/experiments/judge_arm_results.json               regenerated (complete)
DiscoverChat/experiments/decompose_oos_results.json           regenerated (complete)
DiscoverChat/experiments/judge_arm_BASELINE_minimal.json      NEW  kept baseline
DiscoverChat/experiments/decompose_oos_BASELINE_minimal.json  NEW  kept baseline
DiscoverChat/experiments/answer_compare_BASELINE_minimal_newwriter.json   NEW  §2a
DiscoverChat/experiments/answer_compare_BASELINE_minimal_newwriter.md     NEW  §2a
DiscoverChat/experiments/answer_compare_D91_complete.json     NEW  run (c)
DiscoverChat/experiments/WPD9_narratives_side_by_side.md      NEW  §4
handoffs/WPD9_REPORT.md                 this report
```

`answer_compare.json` / `.md` in the repo are **left as WP-D7 wrote them**; the
D9 runs ship under their own names so the D7 artefacts stay readable.

Nothing under `Insights/`, `Ask/`, `frontend/`, `deploy/`; no `.env`, no
`.gitignore`, no `PROJECT_PLAN.md`, no `LABEL_SHEET.md`. The writer prompt was
not edited by this WP. **All files are left uncommitted for the operator**, as
this project's execution sessions do.

---

## §6 Bugs found — logged, not fixed, per the brief

1. **`consolidation-prompt-is-the-operators` catches deletions, not additions.**
   It asserts that seven lines are *present* in the writer prompt, and that
   `"PM addition"` is absent. The uncommitted edit in §0 added a new writing
   rule — "do not use 'therefore', 'because', or 'driven by'" — and the check
   stayed **green**, verified both before and after this WP's changes. D40
   records the operator rejecting rules-in-the-prompt three times, so additions
   are the direction that matters, and additions are exactly what the check
   cannot see. Not fixed here: the writer prompt and its check are out of this
   WP's scope, and what counts as "the operator's prompt" is the operator's
   judgement to make. A prompt-hash binding of the same shape as D9.0 would
   close it.

2. **`run_answer_compare.py --only new` rewrites the `.json` but not the
   `.md`.** A `--only` run therefore leaves a stale `.md` sitting beside a
   fresh `.json`, which is a trap for anyone reading the `.md` as current. Not
   fixed: out of this WP's measurement path, and the fix is a one-line
   judgement about what `--only` should mean.

3. **WPD7 §6's pinned-SHA table lists the same hash for `view3_candidates.json`
   and `view3_ranked.json`** (`a5fa0a1f5f2fa659f52d89bf`). This is **not** a
   transcription error — the two files are genuinely byte-identical on disk,
   verified this session. Recorded only so a future reader does not chase it.

---

## §7 Close-out

**Pinned files, re-verified at close — all nine unchanged, matching
`WPD7_REPORT.md` §6 and `WPD6_REPORT.md` §6 exactly:**

| file | sha256 (first 24) |
|---|---|
| `view1_candidates.json` | `890767085988a6c7b61b1694` |
| `view2_candidates.json` | `5796d3c8029c5f06efe71fa5` |
| `view3_candidates.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `view1_ranked.json` | `182ff833849488cad3a15c0c` |
| `view2_ranked.json` | `44c9638c450d29af03e29818` |
| `view3_ranked.json` | `a5fa0a1f5f2fa659f52d89bf` |
| `global_feed.json` | `3da40edae324f917ce8fd511` |
| `retrieval_corpus.json` | `d08bae06f9f2065bbf368626` |
| `retrieval_corpus.npy` | `e1158e411529e21f730149ea` |

`decompose_corpus_stamp.json` present and unchanged (`c237cbfe51403bb96d77504e`).

**Regenerated evidence, as shipped:**

| file | sha256 (first 24) | generated | model | prompt |
|---|---|---|---|---|
| `judge_arm_results.json` | `89a9df3a19545ee99f9c1590` | 2026-09-04T06:07:51Z | `gpt-5.6-sol` | `complete` `b5284df7ac3d95ae` |
| `decompose_oos_results.json` | `bbc764bbe4f7c6a83785991d` | 2026-09-04T05:45:36Z | `gpt-5.6-sol` | `complete` `b5284df7ac3d95ae` |

Prompt template hashes: `minimal` `ad73ea44a482194a…`, `complete`
`b5284df7ac3d95ae…`.

**Gate at close:** `judge-model-evidenced` and `judge-prompt-evidenced` both
green on the shipped configuration; **33/33 offline, 33/33 live** (including
`live:out-of-scope-silent`, 0.0% over 10 runs); **93/93 tests**.

**Open for the operator:**

1. **Narrative length (§4)** — the acceptance this WP cannot make for you. The
   answers are richer and longer; 13 findings on one GP question is a different
   reading experience from 6.
2. **The writer-prompt edit is now load-bearing (§0, §2a).** It is
   uncommitted, it took the fallback rate to 0.0%, and it makes WPD7 §4's
   13.3% stale. It wants either committing — with that line annotated as
   superseded — or reverting deliberately.
3. **The gate weakness in §6 item 1** — whether to bind the writer prompt by
   hash the way the judge prompt now is.
4. **`ANSWER_CAP=20` is shipped** per ruling 1. Nothing bound against it
   (`kept_max` 17), so it is a ceiling in practice as well as in intent.
5. **D9.2 held in reserve (§3)** — re-measure the restatement share if the
   judge model or the writer prompt changes.

---

## §8 Reproducing this

From a local mirror, at the repo root:

```bash
# preconditions
python -c "from DiscoverChat import llm; llm.call('gpt-5.6-sol','ping',50,'probe')"

# D9.0 — the binding
python DiscoverChat/gates.py                                     # 33/33, prompt evidenced
DISCOVERCHAT_JUDGE_PROMPT=minimal python DiscoverChat/gates.py   # red: unmeasured wording

# D9.1 — the matrix
python DiscoverChat/experiments/run_decompose_oos.py --repeats 4   # (a)
python DiscoverChat/experiments/run_judge_arm.py                   # (b) and (d)
python DiscoverChat/experiments/run_answer_compare.py --only new   # (c)

# the side-by-side, built from the saved runs
python DiscoverChat/experiments/build_judge_narratives.py

# the gates and the suite
python DiscoverChat/gates.py --live
python -m unittest DiscoverChat.tests.test_retrieval DiscoverChat.tests.test_behaviour DiscoverChat.tests.test_citations
```

To revert the instruction without a revert commit — the reversion the brief
asked be kept reachable — set `DISCOVERCHAT_JUDGE_PROMPT=minimal`. The cap
stays at 20, which is harmless with the old instruction: it never selected more
than 6.
