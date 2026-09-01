# WP-D6 brief — decompose (gap arithmetic), plus two inherited fixes

**Workstream:** Discover. **Nature: BUILD, staged and gated.** The deliverable
is the "where does the gap sit" capability: deterministic decompositions of a
measure's gap or total along one dimension, precomputed at build time,
retrieved and rendered by DiscoverChat like any other finding. Plus two
punch-list items inherited from WP-D5 (§D6.2). **Authored:** PM, 2026-09-01.
Not yet registered in `PROJECT_PLAN.md`; not yet dispatched; D-numbers for the
rulings below to be assigned by the operator (next free after D43; check for
collisions).

**Concurrency:** WP-D4b may still be writing its set
(`Insights/src/phase5e_insight_prose.py`, `insight_prose_config.py`,
`Insights/metainsights/insight_prose.json`,
`Insights/reports_prdw/check_insight_prose.py`, `wpd4b_run/**`,
`handoffs/WPD4b_REPORT.md`). Disjoint from this WP's set — touch none of it,
list it in your self-audit as not-yours. WP-D5 execution is complete
(`handoffs/WPD5_REPORT.md`); its D5.3 operator gate is **open-parked** (the
labelling sheet awaits the operator) — nothing in this WP claims or advances
D5.3.

**Design rulings this brief encodes (operator/user, 2026-09-01 session):**

1. **Decompose is precomputed, not live.** The chatbot stays a
   retrieval-only service: it computes nothing at question time, so nothing
   it says can be arithmetically wrong at runtime. A new build step
   enumerates every valid decomposition and stores the results; DiscoverChat
   retrieves them exactly as it retrieves findings.
2. **Decompose is arithmetic, never inference.** Each decomposition is an
   accounting identity: member contributions sum to the total (or gap) they
   decompose, and a reconciliation gate proves it for every stored record.
   No correlation, no causal language (D41 stands: correlations-only project
   ruling; decompose is below even that bar — it is bookkeeping).
3. **Deterministic sentences, glossary vocabulary.** Decomposition prose is
   template-generated at build time (reuse the `column_glossary` translation
   the corpus builder uses), passes the prose gate, and is stored alongside
   the numbers. The chatbot's writer may add connective prose around it under
   the WP-D4 safety net, never restate the numbers.
4. **The decompose answer names the concentration, honestly.** Sorted by
   contribution, top members shown, remainder aggregated ("12 others account
   for Rs X"). When a gap is spread evenly, the decomposition SAYS it is
   spread evenly — "no single member accounts for it" is a first-class
   result, mirroring the evenness pattern's framing.

---

## D6.0 — the decomposition builder

New script `Insights/src/phase5f_decompose.py`. For each analytical view:

- **What gets decomposed:** each gap-type measure (view1: `overspend_vs_plan`,
  `overspend_vs_sanction`; plus each view's additive volume/amount measures
  as totals) — confirm the exact list against the view configs and record it
  in the report.
- **Along what:** every categorical dimension of the view, at subspace depth
  0 and 1 (global, and within each single-filter subspace whose impact
  clears the engine's existing 1% floor). Temporal dimensions included as
  breakdowns (a gap by fiscal year is a legitimate decomposition).
- **Stored per record:** the triple (measure, dimension, subspace), each
  member's value and share, the total, an explicit row for
  null/unknown members (never silently dropped), the deterministic sentence,
  the run stamp, and an embedding of an enriched retrieval text (same
  recipe and same Qwen configuration as the findings corpus — ruling 7 of
  the WP-D5 brief applies verbatim).
- **Output:** a sidecar next to the retrieval corpus
  (`Insights/metainsights/decompose_corpus.*`). The findings corpus, the
  feed, and all pinned files are untouched.

**Gate D6.0:** (a) reconciliation — every stored record's members sum to its
total within float tolerance, checked exhaustively, zero failures; (b) two
consecutive builds byte-identical apart from timestamps; (c) pinned-file SHAs
unchanged; (d) record counts per view reported.

## D6.1 — chatbot integration

- A **decompose intent** in the turn classifier: "where does the gap sit",
  "which blocks account for", "break down X by Y", "who is driving the
  shortfall" — trigger vocabulary authored as data, alongside the existing
  routing rules. Classification decisions logged per turn, as today.
- Retrieval over the decompose sidecar uses the same machinery (floor,
  judge path with its containment properties, diversity rule). Where a
  question is answerable both by findings and by a decomposition, both may
  appear — the decomposition ranked by the same relevance score, not
  privileged.
- The nothing-invented check learns the decompose records as an allowed
  numeral source (their numbers are build-time artifacts, exactly like
  finding figures).
- **Display glossary (scope addition, PM 2026-09-01, operator-approved):**
  finding sentences currently render in engine vocabulary
  (`fund_untied_total`, `gp_name`, `is_completed`) — acceptable in a
  labelling sheet, not in an officer-facing answer. Add a deterministic
  render-time translation in DiscoverChat that maps column names to officer
  phrases, reusing the same `column_glossary` dicts the corpus builder's
  enriched text already uses (read from `Insights/src/phase5b_report.py`;
  do not fork the dicts — import or load them from the one source). No LLM
  anywhere in this path; translation applies to every rendered sentence,
  findings and decompositions alike. Gaps in the glossary (a column with no
  entry) render the raw name and are LISTED in the report rather than
  papered over — the missing entries are PM/operator content to author, not
  the implementer's to invent.

**Gate D6.1:** extend the one-command offline gate and the behavior suite:
decompose questions route correctly; every numeral in a decompose answer
traces to a stored record; evenness-shaped decompositions render the
"spread evenly" sentence, not a fake concentration; a raw-column-name scan
over every rendered sentence in the suite comes back empty for every column
that HAS a glossary entry (known gaps excepted and listed); existing 13/13
checks and 43/43 tests stay green.

## D6.2 — the two inherited fixes

1. **Prose-gate causal-verb ban** (deferred from WP-D5 §4 item 3 —
   `Insights/src/prose_gate.py` was outside that WP's writable set; it is
   inside this one, and disjoint from WP-D4b's files). Add the banned list
   (caused, drives, explains, leads to, due to, results in, because-of
   constructions) with the association vocabulary as the sanctioned
   replacement; run the gate over the full behavior suite's outputs and the
   stored decompose sentences.
2. **Judge-model binding.** Record the model id the WP-D5 four-run
   out-of-scope stability evidence was measured on (see WPD5_REPORT §2.4a and
   `DiscoverChat/config.py`). The offline gate asserts the configured
   `JUDGE_MODEL` equals the evidenced id; a mismatch fails the gate with a
   message naming the requalification step — re-run the four-run
   out-of-scope battery (`run_judge_arm.py`'s repeat mode) and update the
   evidenced id with the new run's log reference. Document the step in
   `DiscoverChat/README.md`.

**Gate D6.2:** gate red with a swapped `DISCOVERCHAT_JUDGE_MODEL` env var,
green with the evidenced one; prose-gate scan green over suite outputs and
decompose sentences.

---

## Files in scope (writable) — nothing else

```
Insights/src/phase5f_decompose.py          NEW — decomposition builder
Insights/src/prose_gate.py                 EDIT — D6.2 item 1 ONLY (additive: the ban list)
Insights/metainsights/decompose_corpus.*   NEW — build outputs
DiscoverChat/**                            EDIT — intent, retrieval wiring, gates, README, tests
handoffs/WPD6_REPORT.md                    your report
```

**DO NOT TOUCH:** every other file under `Insights/src/` (import only), the
candidate/ranked/feed JSONs and `retrieval_corpus.*` (read-only; verify pinned
SHAs at close), `Ask/**`, domain packs, `Data/`, reports, `PROJECT_PLAN.md`,
`LABEL_SHEET.md` (the operator's parked D5.3 deliverable — leave it exactly as
committed), any `.env`. WP-D4b's set per the concurrency note. Bugs found in
existing code: log, don't fix. No git operation beyond read-only
`status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. **Committed tree except concurrent sets:** clean `git status` apart from
   WP-D4b's listed paths and PM-edited handoffs. Any other dirty path → STOP.
   (If the WP-D5 work is still uncommitted at dispatch time, STOP — this WP
   edits `DiscoverChat/**` and must start from a committed baseline of it.)
2. **Local-mirror execution only** (D6-the-decision): never run Python against
   the Drive path.
3. **Pinned candidate set intact** per WPD3b §4, plus `retrieval_corpus.*`
   SHAs as recorded in WPD5_REPORT — mismatch → STOP.
4. `Insights/.env` provides the API keys. Missing → STOP.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/WPD5_retrieval_chatbot.md` | The design rulings this WP extends (esp. rulings 6–8) |
| `handoffs/WPD5_REPORT.md` | §2.4a (the judge path and its containment), §4 (deferred items), close-out file lists |
| `DiscoverChat/README.md`, `config.py`, `assemble.py`, `judge.py`, `gates.py` | The service this WP extends; the gate you must keep green |
| `Insights/src/phase5d_retrieval_corpus.py` | The corpus-builder pattern to mirror (enriched text, embeddings, stamping, determinism) |
| `Insights/src/phase5b_report.py` | `column_glossary` dicts for sentence vocabulary |
| `Insights/src/prose_gate.py` | The gate D6.2 extends — additive change only |
| The view parquet files / view configs | The measures and dimensions that define the decomposition space |

## Report

`handoffs/WPD6_REPORT.md`: counts (decompositions stored per view, per
measure), the reconciliation result stated as a number, gate transcripts,
the exact decomposable-measure list with any judgment calls, the evidenced
judge-model id and its log reference, and the WP-D5-style close-out
(files touched / not touched / not-yours, pinned SHAs re-verified).
