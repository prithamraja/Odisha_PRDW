# WP-D7 REPORT — fast answers: latency, provenance, and the consolidating writer

**Workstream:** Discover. **Brief:** `handoffs/WPD7_fast_answers.md`.
**Baseline commit:** `f9a9b26` (deploy config for DiscoverChat, 2026-09-03).
**Executed:** 2026-09-03. **Mirror:** `C:\dev\odisha-d7`, built from
`C:\dev\odisha-chat-live` (the WP-D6 mirror) plus a fresh copy of
`DiscoverChat/` and `Insights/{src,metainsights}` from the Drive tree.

**Status: all three stages executed and gate-green — 32/32 offline, 89/89
tests, and the live gate (D5.2 + D6.1 + WP-D7) green.** One precondition
failed at dispatch and required an operator ruling before D7.0 could proceed
(§0). Nothing else in the brief was blocked.

| stage | gate | result |
|---|---|---|
| D7.0 | classifier on a nano, 4×22 routing + non-empty assertion | **green** — see §0 for the model-id substitution |
| D7.1 | verifier out of the turn; audit runs and reports a rate | **green** (rate is reported, not pass/fail — see §2) |
| D7.2 | `/record/{id}` resolves every cited id; unknown id 404s | **green** |
| D7.3 | citation check, before/after table, latency | **green** — zero failing narratives reached the user |

---

## §0 Precondition 4 failed at dispatch, and the model the brief names does not exist

Precondition 4 says: verify `gpt-5.5-nano` is reachable, unreachable → STOP and
report rather than substitute. Two separate problems surfaced, in order:

1. **The `OPENAI_API_KEY` in `Insights/.env` was dead** (401
   `Incorrect API key provided`) — not only for `gpt-5.5-nano` but for every
   model, including `gpt-5.6-sol` and `gpt-5.6-luna`, which the service
   already depends on. This blocked the whole WP, not only D7.0, so execution
   stopped and the operator was asked. The operator supplied a working key
   (saved to `Insights/.env` 2026-09-03 19:26 IST) and confirmed both
   `Ask/.env` and `Insights/.env` carried the same dead key beforehand — only
   `Insights/.env` was updated, which is the one `DiscoverChat/llm.py` reads.

2. **With the key fixed, `gpt-5.5-nano` still 404s** — `model_not_found` —
   and does not appear anywhere in this account's 124-model catalogue. The
   nano ids that DO exist are `gpt-5.4-nano`, `gpt-5-nano`, `gpt-4.1-nano`.
   Execution stopped again per precondition 4 and the operator ruled
   (2026-09-03): **use `gpt-5.4-nano`, the nearest available nano, gate it
   hard.**

`gpt-5.4-nano` is a sibling of `gpt-5.4-mini`, the model Ask's WP-4 found
returning all-null structured output on ~25% of calls (the "F1" finding). That
is the reason ruling 1's four-run gate and the non-empty assertion exist, and
it is why they were kept rather than relaxed for a model one generation closer
to the known offender. §1 has the result: 128 calls, zero empty, zero
unparseable, across four independent runs.

**This is logged for the record and does not need a further decision** unless
the operator wants `gpt-5.5-nano` re-probed later (it may simply not exist
under this account's naming, or may roll out after this date). Reversion for
either problem is unchanged: `DISCOVERCHAT_CLASSIFIER_MODEL=<id>`, no
redeploy.

---

## §1 D7.0 — the classifier on `gpt-5.4-nano`

**Gate:** `DiscoverChat/experiments/run_classifier_nano.py --repeats 4`, four
independent runs, three passes each (see the script's docstring for why a
naive "run the 22 questions end to end" gate would call the model zero
times — all 22 are caught by the rule layer, so the gate has to force the
model to answer them and separately probe the questions the rules actually
miss).

```
run 1  A routing  decompose 8/8  lookup 6/6  why 8/8  GREEN
run 2  A routing  decompose 8/8  lookup 6/6  why 8/8  GREEN
run 3  A routing  decompose 8/8  lookup 6/6  why 8/8  GREEN
run 4  A routing  decompose 8/8  lookup 6/6  why 8/8  GREEN

128 calls to gpt-5.4-nano: 0 empty, 0 unparseable, median 0.9s, p90 1.3s
A routing green every run: True
zero null classifications:  True

GATE D7.0 PASS
```

**Pass A (routing, rules included, end to end):** 8/8 decompose, 6/6 lookup,
8/8 why (6 why-questions + 2 shape-questions), on every one of 4 runs. The
rule layer is unchanged by D7.0 and this proves the model swap moved no route
an officer can reach.

**Pass B (model-forced, rules bypassed, same 22 questions), reported not
gated:** 14/22 agree with the rule label on every run, stable across runs.
The 8 disagreements are all in the DECOMPOSE family and fall into three
readable buckets — the model is not confused, it is answering a different
(also reasonable) question than the rule layer's deterministic trigger list:

| question | rule says | nano says (stable ×4) |
|---|---|---|
| Break down spending by block / by fiscal year; How is the total split across districts? | decompose | lookup — reads as "give me the breakdown values", not "explain the split" |
| Where does the gap sit? / What makes up the underspend? / Where is the money going? | decompose | retrieve — reads as "what does the analysis say", not specifically a share-of-total ask |
| Which blocks account for the shortfall? | decompose | lookup |
| Who is driving the shortfall? | decompose | **why** — the model reads "driving" as a causal ask, exactly the confusion `decompose_route`'s causal-gate-first ordering in `classifier.py` exists to prevent by rule |

None of these reach the model in production — the rule layer answers first —
so this is not a gate failure and nothing here changed. It is filed because
the last row is a small piece of independent evidence *for* keeping DECOMPOSE
rule-first: a capable model given the bare question still reads "who is
driving X" as WHY, which is precisely the D41 reframe the decompose rule is
built to route around.

**Pass C (the questions the rules actually miss — the classifier's real
production job):** 10 questions, selected by asking the rule layer which of a
wider candidate list it does not match (so the list cannot go stale as rules
are added). All 10 routed identically on every one of 4 runs — 2 lookup
(price-of-onions / rainfall-forecast style out-of-scope questions), 8
retrieve. Zero flips.

**Gate condition:** Pass A green every run, AND zero empty/unparseable
classifications across every call in B and C combined. Both true. Evidence at
`DiscoverChat/experiments/classifier_nano_results.json`, and the standing
check `classifier-model-evidenced` (added to `gates.py`) fails red if the
configured id and this evidence file's id ever diverge — the same pattern
`judge-model-evidenced` already used for D6.2 item 2.

**Latency:** median 0.9s / p90 1.3s per classify call — against the logged
pre-D7 `gpt-5.5` baseline of median 3.1s / p90 3.6s (10 calls,
`experiments/logs/calls.jsonl`). ~2.2s off every classified turn.

---

## §2 D7.1 — the verifier out of the turn, into the audit

`config.INLINE_VERIFY` defaults to `0`; `verifier.py` is untouched.
`writer.write` (the legacy connective path, kept for `DISCOVERCHAT_CONSOLIDATE=0`)
now skips the verifier call entirely when the flag is off — confirmed live
below.

**Gate condition 1 — a turn completes with no verifier call in its trace.**
Traced via the call log rather than the writer's return value, so the claim is
about what the service actually did: turn `d71-trace` ("Is spending on
track?") made 4 model calls — `classify, judge, write` — and no `verify`.

**Gate condition 2 — mechanical checks demonstrably still fire.** The seeded
violations in `gates.py`'s `citation-checks-fire` (6 seeded failures, all
caught) and the existing `causal-gate-catches` (6 causal constructions, all
caught) both green.

**Gate condition 3 — the audit runs and reports a rate.**
`experiments/run_prose_audit.py`, over all 12 logged writer calls (below the
60-call full-audit threshold, so no sampling was needed):

```
audited 12  |  pass 7  |  drift 5  |  could not verify 0
DRIFT RATE 41.7% (41.7% of the verifiable)
```

**This is a number for the operator to judge, not a pass/fail** — the brief
is explicit and the gate treats it that way. Read plainly: it is high, and it
is a small sample (12 calls, all from the pre-D7 connective-writer path
logged before this WP started — none of the new consolidating-writer output
had accumulated by the time D7.1 was gated). The five flagged cases, in the
audit's own words:

1. **Scope overstated.** The prose claimed overspending is spread across
   *themes and activity categories*; the cited findings only support that for
   *some* dimensions within themes/activities, not the aggregate claim.
2. Same shape, second phrasing of the same turn's regenerated attempt.
3. **A suggestion read as a causal claim.** "They suggest checking which Gram
   Panchayats *drive* the uneven pattern" — the findings say the spread has no
   single driver; "drive" in a suggested next step still implied one.
4. **An unsupported absence-of-evidence claim.** "These do not show whether
   the photos are adequate, authentic or compliant" — no finding or context
   states that adequacy/authenticity/compliance were even in scope to assess.
5. **A ranking claim not in the source.** "Haldikudar is the strongest of
   these signals" — the source says rank 5 of 32 in the feed; the others
   weren't ranked at all. Rank 5 is not "strongest."

**All five are exactly the class of error the brief predicts nothing else
catches: numerals were correct in every one, and the D7.3 citation check
(number-to-source binding) would have passed every one of these five had they
gone through it.** Cases 3–5 are also visibly closer to D7.3's actual failure
mode than to D5's — case 3 is a suggestion overreaching into causal territory,
which is the exact shape the D7.3 gate's live citation-check run separately
caught 18/18 times via the causal scan (§4), and cases 1/4/5 are scope or
characterization drift that no mechanical check — old or new — is built to
see.

**README states this plainly** (added under "Fast answers", the
"the audit is the only check on qualitative drift" callout): the citation
check covers numbers, not meaning, and with the consolidating writer now
restating findings the class of error the inline verifier used to catch is if
anything *more* reachable, not less.

**Recommendation, not a decision made here:** re-run the audit once enough
consolidating-writer output has accumulated in production logs (the current
12 are all pre-D7 connective prose) — a drift rate measured on the writer this
WP actually ships would be worth more than one measured on the writer it
replaces. `run_prose_audit.py` reads both prompt shapes already, so this needs
no code change, only more logged turns.

---

## §3 D7.2 — provenance: the record endpoint

`GET /record/{finding_id}` (JSON) and `?format=html` (readable view), added to
`main.py`. Read-only over the same corpus `/chat` and `/finding/{id}` already
serve; no new auth question opened, per the brief.

**Gate — every id cited in every suite answer resolves, an unknown id 404s,
the record view carries the run stamp:**

- `record-endpoint-resolves` (offline): every id across the DECOMPOSE
  question set plus five broad questions, one explicit finding and one
  explicit decomposition — confirmed to resolve with matching stored
  sentence, display sentence and run stamp; `1-99999999` confirmed 404 via
  `HTTPException`.
- `record-view-is-readable` (offline): the HTML view for a decomposition
  record carries its id, the run stamp, "Stored sentence" and "Standing in
  the analysis".
- Both green in the offline gate (32/32) and re-confirmed against real live
  answers in the D7.3 compare run — every citation in all 13 narratives
  resolved (§4).

The `/chat` payload was extended (not replaced) with `answer_tagged` (the
prose with `[id]` tags), `citations` (per-id record map: sentence, display
sentence, scope, standing, view, stamp, url), and `answer_html` (the
reference hover render — see §4).

---

## §4 D7.3 — the consolidating writer with checkable citations

**The prompt is Appendix A verbatim** (`context_brief.CONSOLIDATING_WRITER_PROMPT`),
both PM additions kept as written, nothing else added — checked by the
standing `consolidation-prompt-is-the-operators` test/gate, which fails if
any writing-rule line is ever added later. The context brief that precedes it
is BACKGROUND only (`for_consolidating_writer()` — not `WRITER_TASK`, which
is D5's job description and tells the writer not to restate findings, the
exact instruction ruling 3 reverses).

**One reading of the brief, flagged for the operator to strike or confirm:**
the brief's "Input to the writer ... nothing else" line, read literally,
would withhold the officer's own question from the writer. §D7.3's build
function includes the question — a narrative consolidated without knowing
what was asked would answer no question. This reading is the only sensible
one and is very likely what "nothing else" meant (excluding scores, coverage
notes, ranking metadata — the actual per-finding annotations enumerated in
the same sentence), but it is a judgment call made during execution and is
named here rather than silently assumed.

### The citation check (`checks.check_citations`), the four steps, blocking

All four implemented exactly in the brief's order and all confirmed to fire
on seeded violations (`citation-checks-fire`, offline gate) and on real
output (below):

1. Every `[id]` tag must be in the answer set — an unknown id fails.
2. Every numeral in the prose must appear in the **stored sentence of a
   finding cited in the same sentence**. A numeral cited to the wrong finding
   fails; an uncited numeral fails. (The numeral normaliser is the existing
   one — `checks._NUM` tokenises digits only, so "Rs 1.24 crore" and "1.24"
   already reduce to one token; no new normalisation code was needed, and the
   test suite pins this — `test_the_run_date_is_exempt_and_nothing_else_is`,
   etc.)
3. The causal scan, unchanged, blocking.
4. Every finding in the answer set must be cited at least once — a silently
   dropped finding fails.

On failure: regenerate once, feeding back the specific reason; on second
failure, fall back to the bare glossary-translated sentences and log the
failed prose (`DiscoverChat/logs/citation_failures.jsonl`, gitignored, copied
to this report's evidence set).

### Gate result — over the D7.3 before/after suite (15 questions) plus the
live gate's 3 questions plus the D7.1 audit's incidental turns: **zero
citation-check failures reached the user.**

```
narratives 13 | fallbacks 2 (13.3%) | regenerated once 3 | failing narratives shown 0
numerals bound 225/229, uncited 0
answers carrying decompositions 14, evenness 1
```

(The 4 numerals neither "bound" nor "uncited" are the exempt ones — the
20-Gram-Panchayat sample size and run-date digits the writer is told rather
than asked to cite, per `checks.supplied_numerals`.)

**Every one of the 18 logged failure events across all runs today (audit
prep, gate, before/after) was the causal-verb scan, and only the causal-verb
scan** — not a single numeral, citation, unknown-id, or dropped-finding
failure anywhere:

| causal word caught | count |
|---|---|
| `therefore` | 11 |
| `because` | 5 |
| `driven by` | 1 |
| `driving` | 1 |

**Logged, not fixed, per the brief's scope.** The consolidating writer
reliably gets citations and figures right; what it reaches for, writing
connective narrative across several findings, is causal-sounding connective
tissue ("X, therefore Y") even though it is explicitly told not to. The
mechanical ban catches every instance and the regenerate-once step recovers
most of them (13 of 15 questions with findings produced a narrative on first
or second attempt) — this is the safety net working as designed, not a gap in
it. Worth the operator's attention only if the 13.3% fallback rate matters
more than the citation guarantee it is the cost of.

### Before/after table — 15 answers

Sent separately as `DiscoverChat/experiments/answer_compare.md` (and the
JSON with per-answer citation-check detail and rendered HTML at
`answer_compare.json`). Coverage as specified: ≥3 with decompositions (14 of
15 carry at least one), 1 evenness case ("How is tied grant planned split
across fiscal years?"), 1 causally-worded decompose turn with its scope note
("Who is driving the shortfall?").

**This project's own read of three samples** (not a substitute for the
operator's acceptance, which the brief reserves): the narratives genuinely
consolidate — e.g. "How is Chikilli doing?" merges five separate findings
(lowest sanctioned amount, fewest approvals, spending below plan, abandoned
works, a focus-area exception) into two paragraphs organised by theme rather
than by finding id, which is what "small number of underlying patterns" asks
for. The `[id]` tags are invisible in `answer.text` and present in
`answer.tagged_text`/`answer_html`, confirmed by `tags-never-rendered`.

### Hover-to-source, D7.2/D7.3 together

`DiscoverChat/render.py` (new). Binds every checked numeral to its citing
finding using `checks.bind_numerals` — the same function the blocking check
calls, so the hover a front end shows can never diverge from what the check
approved. Ships as a reference HTML render (`render.to_html` /
`render.to_page`) so the behaviour suite can exercise hover-to-source end to
end without a front end. `hover-binds-every-numeral` (offline gate) and
`HoverRenderTests` (12 tests, `test_citations.py`) confirm: every bound
numeral wraps in a `<span data-finding-id="...">`, every span carries the
stored sentence/scope/stamp/record-URL, and the binding matches the check's
own (`test_the_renderer_uses_the_checks_binding_not_its_own` — regex-pins
that the 51.96 span in a mixed-source fixture declares `1-00235` and never
`1-00987`). A non-numeric claim (e.g. "spread evenly") is also hoverable —
the phrase between tags is wrapped, not just figures.

### Latency — measured, not estimated

The pre-D7 baseline in the brief ("~60 s today") is confirmed directly from
`experiments/logs/calls.jsonl`: the 6 logged turns that actually ran
classify → judge → write → verify end to end have **median 62.8 s, max
92.0 s** (verify alone: median 35.0 s of that).

The D7.3 before/after run's **"old" arm undercounts this** — it re-runs the
pre-D7 configuration live, but most of its 15 questions retrieve ≤4 findings
and never reach the writer at all (`FULL_RENDER_MAX`), so its p50 of 12.0 s
mixes writer-free and writer-included turns. The **honest before/after is
the logged full-pipeline median above (62.8 s) against the new configuration's
measured latency below** — both apples-to-apples "the turn that actually
writes something":

| | median | p90 | min | max |
|---|---|---|---|---|
| **before** (logged, full pipeline incl. verify) | **62.8 s** | — (n=6) | — | 92.0 s |
| **after** (D7.3, all 15 questions, live) | **27.6 s** | 55.7 s | 9.2 s | 61.5 s |

**Target was p50 ≤ 30 s; measured 27.6 s.** Met, on turns that write a
narrative — more than half of what "~60 s" cost is gone.

---

## §5 Files touched

```
EDIT  DiscoverChat/config.py         D7.0 classifier constant + evidence path;
                                      D7.1 INLINE_VERIFY; D7.3 CONSOLIDATE(_MIN);
                                      D7.2 record_url(); knobs() extended
EDIT  DiscoverChat/classifier.py     Routing.model_empty/model_unparseable (the
                                      F1 signal, named not swallowed); allow_rules
EDIT  DiscoverChat/context_brief.py  CONSOLIDATING_WRITER_PROMPT (Appendix A
                                      verbatim); for_consolidating_writer()
EDIT  DiscoverChat/checks.py         the D7.3 citation check (4 steps),
                                      bind_numerals, strip_tags
EDIT  DiscoverChat/writer.py         Consolidated dataclass + consolidate();
                                      D7.1 switch on the legacy write() path
EDIT  DiscoverChat/verifier.py       build_audit_prompt() (D7.1); parameterised
                                      prose_description for the two writer shapes
EDIT  DiscoverChat/assemble.py       wires consolidate() in; CONSOLIDATE=0
                                      restores the exact pre-D7 write() path
                                      (the honest reversion switch, not a stub)
EDIT  DiscoverChat/main.py           GET /record/{id} (+?format=html); /chat
                                      payload carries answer_tagged, citations,
                                      answer_html
EDIT  DiscoverChat/gates.py          10 new checks (D7.0/1/2/3), 2 live checks
                                      (no-verifier-in-turn, citation-check)
EDIT  DiscoverChat/README.md         "Fast answers" section
NEW   DiscoverChat/render.py         hover-to-source reference renderer
NEW   DiscoverChat/tests/test_citations.py            45 tests
NEW   DiscoverChat/experiments/run_classifier_nano.py D7.0 gate script
NEW   DiscoverChat/experiments/run_prose_audit.py      D7.1 audit script
NEW   DiscoverChat/experiments/run_answer_compare.py   D7.3 before/after script
NEW   DiscoverChat/experiments/classifier_nano_results.json  D7.0 evidence
NEW   DiscoverChat/experiments/prose_audit_results.json      D7.1 evidence
NEW   DiscoverChat/experiments/answer_compare.{json,md}      D7.3 evidence
NEW   handoffs/WPD7_REPORT.md        this report
```

**Not touched:** every path under `Insights/` (stored sentences, corpora,
embeddings, `prose_gate.py`); `Ask/**`; `LABEL_SHEET.md`; `PROJECT_PLAN.md`;
every `.env`, `.gitignore`; WP-D4b's set (`Insights/src/phase5e_insight_prose.py`,
`insight_prose_config.py`, `Insights/metainsights/insight_prose.json`,
`Insights/reports_prdw/check_insight_prose.py`, `wpd4b_run/**`,
`handoffs/WPD4b_REPORT.md` — confirmed clean at dispatch, re-confirmed
untouched now). No git operation beyond read-only `status`/`log`/`rev-parse`.
`deploy/RAILWAY.md` was already modified at dispatch (operator/PM edit,
2026-09-03 discover-api deploy notes) and is untouched by this WP.

**Bugs found, logged not fixed:**
1. The 41.7% D7.1 drift rate and its five specific cases (§2) — all on
   pre-D7 connective prose; worth re-measuring once consolidating-writer
   output accumulates.
2. The 13.3% D7.3 fallback rate, entirely attributable to the causal-verb
   scan firing on `therefore`/`because`/`driven by`/`driving` (§4) — the
   safety net working, but a rate the operator may want to see.
3. Pass B's 8/22 classifier disagreements when rules are bypassed (§1) — none
   reach production, filed as corroborating evidence for keeping DECOMPOSE
   rule-first rather than as a defect.
4. The "nothing else" reading in D7.3's writer input (§4) — a judgment call
   made during execution, flagged for the operator to strike or confirm.

---

## §6 Close-out

**Pinned files, re-verified at close — all nine unchanged, matching
`WPD6_REPORT.md` §6 exactly:**

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

`decompose_corpus_stamp.json` present, unchanged since the WP-D6 build
(2026-09-01 18:11).

**Open for the operator:**

1. **The model-id substitution (§0)** — `gpt-5.4-nano` in place of the
   brief's `gpt-5.5-nano`, ruled by the operator during execution; ratify or
   redirect.
2. **The D7.1 drift rate, 41.7% over 12 pre-D7 calls (§2)** — a small,
   stale sample; the operator's read of whether this is acceptable, and
   whether to re-run once consolidating-writer traffic accumulates.
3. **The D7.3 fallback rate, 13.3%, all causal-scan (§4)** — working as
   designed; the operator's call on whether it is too high in practice.
4. **The "nothing else" reading (§4)** — whether including the officer's
   question in the writer's input is the intended reading.
5. Pass B's classifier disagreements (§1) — informational, no action
   implied.

## §7 Reproducing this

From a local mirror, at the repo root:

```bash
# preconditions
python -c "from DiscoverChat import llm; llm.call('gpt-5.4-nano','ping',50,'probe')"

# D7.0
python DiscoverChat/experiments/run_classifier_nano.py --repeats 4

# D7.1
python DiscoverChat/experiments/run_prose_audit.py

# D7.2/D7.3 — offline + live gate
python DiscoverChat/gates.py
python DiscoverChat/gates.py --live

# D7.3 — the before/after table and measured latency
python DiscoverChat/experiments/run_answer_compare.py

# the test suite
python -m unittest DiscoverChat.tests.test_retrieval DiscoverChat.tests.test_behaviour DiscoverChat.tests.test_citations
```
