# WP-D4b brief — insight prose as a feed-build step (productionize the trial)

**Workstream:** Discover. **Nature: BUILD.** Turn the accepted WP-D4 design
(D40 item 11) into a repeatable pipeline step that produces checked, fluent
prose for **every feed finding — all 32, not the trial's 15** — written to a
sidecar file. Nothing is wired to the frontend yet (placement awaits the D16
contract-v2 conversation); this WP makes the prose exist, checked and
replayable, on every feed build. **Authored:** PM, 2026-09-01 (D43).

**Runs CONCURRENTLY with WP-D5** (`handoffs/WPD5_retrieval_chatbot.md`).
The two writable sets are disjoint — verified by the PM:
WP-D5 owns `Insights/src/phase5d_retrieval_corpus.py`,
`Insights/metainsights/retrieval_corpus.*`, `DiscoverChat/**`,
`handoffs/WPD5_REPORT.md`; none of those is yours, and nothing of yours is
theirs. Expect WP-D5's files to appear in `git status` while you run: list
them in your self-audit as not-yours, touch none of them.

---

## Files in scope (writable) — nothing else

```
Insights/src/phase5e_insight_prose.py        NEW — the production step
Insights/src/insight_prose_config.py         NEW, only if constants outgrow phase5e
Insights/metainsights/insight_prose.json     NEW — the output sidecar
Insights/reports_prdw/check_insight_prose.py NEW — replayable checker
Insights/reports_prdw/wpd4b_run/**           run + gate logs
handoffs/WPD4b_REPORT.md                     your report
```

**DO NOT TOUCH:** every EXISTING file under `Insights/src/` (import from them,
never edit — `discover_config.py` included), `Insights/prose_trial/**` (the
frozen trial record — port its logic by writing new code in phase5e, never by
editing it), `Insights/metainsights/global_feed.json` and the candidate/ranked
files (read-only; SHA-verified unchanged at the end), everything WP-D5 owns
(above), `Ask/**`, domain packs, `Data/`, `PROJECT_PLAN.md`, any `.env` (use
for keys; never print, copy, or write). Bugs in existing code: log, don't fix.
**No git operation** beyond read-only `status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. **Committed tree, with the concurrency exception:** `git status` clean
   EXCEPT paths inside WP-D5's writable set, which a concurrent agent may be
   writing — exclude those paths from the check, list them in your report.
   Any OTHER dirty path → STOP.
2. **Local-mirror execution only** (D6); rebuild views per the calibration
   README recipe step 1 (the packet builder needs the parquet files).
3. **Pinned candidate set intact:** SHA-256 of the candidate/ranked/feed files
   in `Insights/metainsights/` matches the WPD3b report §4 (ignore
   `retrieval_corpus.*` and `insight_prose.*` — new files, not pinned).
   Mismatch on a pinned file → STOP.
4. `Insights/.env` provides the API keys. Missing → STOP.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD4_prose_trial.md` | The accepted design this WP productionizes — its Appendix A (context template + slot values) is embedded VERBATIM in your build |
| `Insights/prose_trial/REVIEW.md` + the trial scripts | Round-2 behavior is the acceptance baseline; port the packet/check/verify logic, don't reinvent it |
| `handoffs/WPD4_REPORT.md` | Measured lessons, incl. the verifier fact/action split and the starvation incident |
| `Insights/metainsights/global_feed.json` | The 32 inputs (`feed` array, in order) |
| `Insights/src/phase5b_report.py` | Enrichment paths the packet builder reuses; the `column_glossary` dicts for definitions |
| `Insights/src/discover_config.py` | Prose-model constant + budget discipline (D17) — import, never edit |

## The design, fixed by D40 (do not re-litigate)

Per finding: packet = engine structure + display-formatted measured figures +
companion statistics + one-line variable definitions (unit, money basis, sign
convention, value meanings, from the signed glossary) + both year display
forms. **No caution or scope-note layer; nothing interpretive** (D40 item 9).
Writer: one batch, instantiated context verbatim, no rules or style
instructions; split by view only if the input cap forces it. Checks: every
numeral in the finding's packet or a context slot value; every name in the
packet; no database tokens; lead ≤ 2 sentences, detail ≤ ~200 words. Verifier:
different model, fact/action split (factual claims need support and claim
mapping; suggested actions must merely not assert or contradict), sees the
packet + the instantiated context. Failure → regenerate once with the reason →
fall back to the finding's current template sentence (**ratified**, D40 item
11). Token ceilings 16k in / 8k writer / 4k verifier, budget check first.

**One addition over the trial (D43): retry-on-empty.** A verifier call that
returns nothing parseable is retried ONCE at the same ceiling before being
treated as fail-to-verify — round 2 lost a sound rendering to a one-off
starvation. Both calls logged.

## Tasks

### T1 — Port and extend the packet builder
**Do:** packets for all 32 feed rows, same recipe as the trial (provenance
recorded per figure).
**Done when:** 32 packets; every figure traces to the pinned set, the views,
or a published reading note.
**Escalate if:** a rank-16–32 finding's figures cannot come from existing
enrichment paths — mark the packet thin and continue; never improvise
calculations.

### T2 — The build step
**Do:** `phase5e_insight_prose.py`, one command, standalone (reads
`global_feed.json` + views; edits no existing pipeline file): packets → writer
batch → checks → verifier (with retry-on-empty) → regenerate-once → fallback →
write `insight_prose.json`. The file is deleted before writing (the
stale-suite rule, in code); one run stamp + the `candidate_set_id` on every
record; per-record fields: feed rank, finding identity, lead, detail, status
(first-pass / regenerated / fell-back), attempts with verdicts, usage.
**Done when:** two consecutive runs differ only in stamp and any LLM wording —
every deterministic field byte-identical.
**Trap:** the D17 silent-empty-prose failure — budget check before first use.

### T3 — The replayable checker
**Do:** `check_insight_prose.py --base Insights`: re-runs the nothing-invented
checks over the shipped sidecar from the shipped packets; asserts one stamp
across all records; `candidate_set_id` matches the feed's source set; all 32
ranks present exactly once; every fell-back record carries its template
sentence verbatim; every regenerated/fallback record carries the verdict that
caused it.
**Done when:** green on your build; state plainly which parts replay on the
Drive copy and which need a mirror with views.

### T4 — Report the quality profile, don't tune it
**Do:** first-pass / regenerated / fell-back counts, ranks 1–15 vs 16–32
separately (the trial baseline is 11/3/1 on ranks 1–15). Materially worse on
16–32 → report and analyze; change no thresholds, no prompts beyond the brief.

## Spend guard

Hard cap **120 calls** (expect ~40–60). Ceilings as above. Record `usage`
on every call (D28 rule 8). Cap reached → stop, deliver, report.

## Non-goals

No frontend work, no contract/schema change, no display wiring, no re-mining,
no edits to existing pipeline files, no touching WP-D5's files, no re-running
the trial, no threshold tuning.

## Escalation protocol

STOP: precondition failures beyond the concurrency exception; pinned-hash
mismatch; empty completions after two budget-check attempts. Decide-and-
document: batch splitting, check normalizations, config placement, sidecar
field details beyond the required set.

## Gate

1. Build runs as one command; 32/32 records; checker green.
2. Determinism: the T2 two-run comparison holds.
3. Every record's layer-2 checks green (fallbacks marked, verbatim).
4. Usage recorded, under cap.
5. `git status` = your writable set, plus WP-D5's files listed as not-yours.
6. **PM/operator gate:** quality profile reviewed (T4); the sidecar becomes
   the input to the contract-v2 placement conversation.

## Report — `handoffs/WPD4b_REPORT.md`

§0 gate table · §1 what ran (models, budget-check evidence, batch structure) ·
§2 quality profile (1–15 vs 16–32, with round-2 baseline) · §3 what each
safety layer caught, with quotes · §4 retry-on-empty: did it fire, what did it
save · §5 cost/usage · §6 defects in existing code (logged, not fixed) ·
§7 decision journal · §8 self-audit (writable set exactly; WP-D5 files
disclosed as not-yours; git read-only).
