# WP-D5 brief — findings-retrieval chatbot (v1)

**Workstream:** Discover. **Nature: BUILD, staged and gated.** The deliverable
is a separate chatbot that gives conversational access to pre-mined
MetaInsight findings. It computes nothing, mines nothing, and never writes a
number of its own. **Authored:** PM, 2026-09-01, from the InsightPilot design
session. Not yet registered in `PROJECT_PLAN.md`; not yet dispatched.

**Design rulings this brief encodes (operator/user, 2026-09-01 session):**

1. **Separate chatbot.** Not a change to Ask. Ask's gates, router, and
   ratified accuracy numbers are not touched. The user owns the user-facing
   routing between the two products.
2. **Correlations only — no causal analysis anywhere.** Outcome variables are
   not reliable enough to support causal claims. "Why" questions get a
   scope-honest reframe, never an answer. (Needs a D-number in the decision
   log; the Discover block is D40+ — check for collisions before assigning.)
3. **Retrieval corpus goes wide from the onset:** every candidate that passes
   twin-merge and prefilter is indexed — not just the ranked/feed cut.
4. **Hybrid retrieval, tested not assumed:** embedding cosine plus a
   structural slot-hit boost (geography, measure). The boost survives only if
   the D5.1 experiment shows it beats cosine-only; the concern it addresses is
   that templated finding sentences cluster by template, not slot values, so
   cosine alone may miss "the officer's own GP".
5. **Floor, not top-N.** If nothing clears the relevance threshold, the bot
   says the current analysis has nothing on this. Never stretch a weak match.
6. **Finding text is deterministic; the LLM writes only connective prose**,
   under the WP-D4 pattern: free writer, mechanical nothing-invented checks,
   different-model verifier, template fallback. No writing rules in the
   prompt (the operator has rejected that three times).
7. **Embedder is Qwen (key already in `Insights/.env`).** Asymmetric use:
   queries carry one fixed task instruction (`Instruct: ...\nQuery: ...`, the
   Qwen3 convention), documents are embedded plain. Instruction text, model
   id, and dimensions pinned together in config (D17 discipline). The
   document side embeds an enriched retrieval text, not the bare sentence —
   sentence + view title + glossary-expanded measure (reuse phase5b's
   `column_glossary` dicts) + breakdown/subspace labels + exception member
   names — to stop templated sentences clustering by template. Follow-up
   turns embed a self-contained contextualized rewrite, never the raw
   fragment. Queries also pass through a deterministic abbreviation/synonym
   expansion (GPDP, XV FC, ODF, scheme shorthand) authored as a data file,
   SBM-dictionary style. The exact embedded text is stored in the corpus
   sidecar for auditability. **No shared domain preamble on document or query
   embeddings** — identical text on every vector blurs the distinctions
   retrieval depends on; domain background belongs to the generative
   components (ruling 8), not the embedder.
8. **The writer and classifier get a domain context brief; the embedder does
   not.** The connective-prose writer and the turn classifier receive a
   panchayat-system context brief per the WP-D4 Appendix A pattern (verbatim,
   never paraphrased), and the verifier receives the same brief (the T4
   lesson: a verifier without the writer's context flags what the context
   asked for).

---

## What v1 is, and is not

**Is:** three conversational moves over the pre-mined corpus.

- **Retrieve** — score the question against the corpus; everything above the
  relevance threshold (after the diversity rule collapses near-duplicates) is
  the answer set. Presentation adapts to its size: a few findings are rendered
  fully from their deterministic sentences; a larger set gets a consolidated
  answer (connective prose grouping the findings, under the same safety net)
  with each member navigable via follow-up. The count is a property of the
  question — narrow questions get one finding, broad ones get the sweep.
  Every answer stamped "as of <run date>".
- **Navigate** — follow-ups walk finding structure: an exception member, a
  shared measure, sibling findings. No free exploration.
- **Decline honestly** — a number-lookup question routes the user to Ask
  (link/message, never a proxied or improvised answer); a "why" question gets
  the reframe: state what the data shows about the subject and both/any open
  readings, offer the describable next steps.

**Is not (explicitly out of scope, later WPs):** decompose (gap arithmetic),
drill-down chips, a correlation pattern type, live/scoped mining
("Investigate"), any frontend integration, any change to the feed shape (D16:
frozen contract), any change to Ask.

---

## Files in scope (writable) — nothing else

```
Insights/src/phase5d_retrieval_corpus.py   NEW — corpus + embeddings builder
Insights/metainsights/retrieval_corpus.*   NEW — build outputs (corpus, embeddings, stamp)
DiscoverChat/**                            NEW — the chatbot service (mirror Ask/ conventions)
handoffs/WPD5_REPORT.md                    your report
```

**DO NOT TOUCH:** every existing file under `Insights/src/` (import from
them; never edit), `Insights/metainsights/global_feed.json` and the ranked/
candidate files (read-only inputs; verify SHAs unchanged at the end),
`Ask/**` (import/read only), domain packs, `Data/`, reports, `PROJECT_PLAN.md`,
any `.env` (use for keys; never print, copy, or write). Bugs found in existing
code: log in the report, do not fix. No git operation beyond read-only
`status`/`log`/`rev-parse`.

## Preconditions — verify, then STOP on failure

1. **Committed tree** (`git status` clean at start; dirty → STOP and report).
2. **Local-mirror execution only** (D6): never run Python against the Drive
   path. Mirror per the bootstrap §6 recipe.
3. **Pinned candidate set intact:** SHA-256 of the files in
   `Insights/metainsights/` matches the WPD3b report. Mismatch → STOP.
4. `Insights/.env` provides the API keys (prose model + embedding model).
   Missing → STOP.

## Read first (with why)

| File | Why |
|---|---|
| `handoffs/ODISHA_PRDW_BOOTSTRAP.md` | Product, lineage, operating lessons |
| `Insights/metainsights/view{1,2,3}_candidates.json` | The corpus inputs: 5,000 / 122 / 2 candidates (5,124 total) |
| `Insights/src/phase5_ranking.py` | `generate_nl_summary` (the deterministic sentence per candidate — reuse, don't reinvent), twin-merge, and the candidate fields |
| `Insights/src/phase2_engine.py` | `MetaInsightCandidate` shape; `RANKING_PREFILTER_CAP = 5000` (view1 sits AT the cap — see Risks) |
| `Insights/src/discover_config.py` | The shared prose-model constant and budget discipline (D17) — the chatbot's writer uses this, not its own constant |
| `Insights/src/prose_gate.py` | The deterministic gate; D5.2 extends its vocabulary with the causal-verb ban |
| `Ask/query_router/entity_extractor.py`, `entity_validator.py` | The geography/slot extraction to reuse for the structural boost (LGD-code matching, not string similarity — transliterated Odia names are unreliable as text, per WP-4a) |
| `handoffs/WPD4_REPORT.md` | The writer + safety-net pattern and its measured lessons (incl. T4: the verifier must see the full writer context, or it flags what the context asked for) |

---

## Stages and gates

### D5.0 — Retrieval corpus build

New script `phase5d_retrieval_corpus.py`. For every candidate passing
twin-merge (apply `merge_twin_candidates` to the loaded candidate files —
prefilter is already applied upstream by the cap):

- the deterministic sentence (via `generate_nl_summary`, imported),
- coordinates: view, measure, breakdown, base subspace, pattern type,
  commonness highlight, exception members and categories,
- the engine score (conciseness × impact) and per-view rank if ranked,
- whether it made the 32-finding feed,
- the enriched retrieval text (per ruling 7) and its embedding (Qwen, model
  id + dims + query instruction pinned in config),
- the run stamp (`candidate_set_id`), carried on every record.

Output is a sidecar in `Insights/metainsights/` — the feed's JSON is never
modified (D16). Regeneration is part of this script so corpus and embeddings
can never drift from the candidate set.

**Gate:** two consecutive builds byte-identical apart from timestamps
(embeddings cached/pinned so this holds); record counts reported per view;
SHA check proves the existing candidate/feed files are unchanged.

### D5.1 — Retrieval layer + the hybrid experiment

A scoring module plus an offline CLI harness (no chatbot yet):
`score(question) → ranked findings`. Score = cosine similarity + slot-hit
boost (geography resolved through Ask's extractor to LGD codes; measure
matched through a small keyword map authored as data, like the SBM
dictionary). Engine-score quality floor and relevance threshold are explicit
knobs, not constants buried in code.

**Gate — the experiment that decides the design:** a labeled question set
(~50–60: own-GP/block/district questions sampling all 20 GPs; measure
questions; vague "is spending on track" questions; questions the corpus
genuinely has nothing on; a few why-shaped ones for later reuse). Run
three arms — bare-sentence embedding, enriched retrieval text, enriched +
structural boost — and the operator labels the FULL set of relevant findings
per question (not just the top hit), so broad questions — where the answer is
legitimately several findings — get a measurable recall, not just a top-1
check. Metrics: recall of the labeled set above threshold, irrelevant-shown
rate, and — separately — hit-rate on the own-GP subset, where the structural
boost is predicted to matter most. The labels
set the threshold and quality floor. If cosine-only matches hybrid within
noise, drop the boost and simplify: the numbers decide, not the argument.

### D5.2 — The chatbot service

`DiscoverChat/`: FastAPI service mirroring Ask's conventions (read-only data
access, `.env` config, tests runnable by module name). Turn handling:

- **Classifier** (LLM or rules — implementer's call, but the routing decision
  must be logged per turn): retrieve / navigate / decline-to-Ask /
  why-reframe.
- **Response assembly:** finding sentences and figures verbatim from the
  corpus; LLM writes connective prose only, WP-D4 pattern end to end —
  mechanical check that no numeral appears that isn't in the supplied
  findings, different-model verifier receiving the writer's full context
  (T4 lesson), one regeneration, then fall back to the bare finding
  sentences. Prose model and budget from `discover_config` (D17).
- **Prose gate extension:** causal-verb ban (caused, drives, explains,
  leads to, due to, results in, because-of constructions) added to the
  deterministic gate; association vocabulary is the sanctioned replacement.

**Gate — a deterministic behavior suite, green as one command** (the
`prdw_gates.py` spirit): number-lookup → decline + Ask route; why-question →
reframe with limits stated; no-match → honest "nothing on this"; every
numeral in every response traceable to a corpus sentence; causal-verb scan
green over the full suite's outputs; run stamp present in every answer.

### D5.3 — Operator pilot gate

End-to-end transcript labeling on the D5.1 question set plus free
interaction. Ask-style metrics: answered-well, declined-correctly, and
confidently-wrong (the one that matters most — target the Ask bar of low
single digits). Threshold/floor values ratified here become config, and the
product-placement decision (who gets v1, how it sits next to Ask) is made by
the operator with the user's routing plan.

---

## Operator decisions needed before dispatch

1. Assign the D-number for the correlations-only ruling and for this WP's
   design (D40+ block; verify no collision — D30 collided twice).
2. v1 audience: internal/pilot first, or the same review-meeting officers as
   the reports (sets how hard the D5.3 gate is).
3. Confirm the free-writer + safety-net pattern for connective prose (this
   brief assumes yes, per the WP-D4 outcome).
4. Starting quality-floor policy (brief default: index everything, floor
   tuned at D5.1 — confirm indexing candidates that failed ranking is
   acceptable to display when relevant, with their coverage stated).
5. Deploy target for `DiscoverChat/` (Railway alongside Ask, or local-only
   until D5.3 passes).

## Risks — known, accepted, or watched

- **view1 sits exactly at `RANKING_PREFILTER_CAP = 5000`:** the "wide"
  corpus is still score-truncated for view1. Accepted for v1; log the raw
  pre-cap count in the D5.0 report so the operator can raise the cap in a
  future mining run if retrieval misses look cap-related.
- **view3 contributes only 2 candidates:** GP-performance questions will
  often legitimately hit "nothing on this". Expected; not a retrieval bug.
- **Templated-sentence embedding clustering** is the failure mode the hybrid
  boost exists for; D5.1 measures it instead of assuming it.
- **Cross-workstream import of Ask's extractor** couples Discover to Ask's
  code. Acceptable read-only; if Ask refactors, the D5 suite catches it. Do
  not copy-paste the extractor — drift is worse than coupling.
- **Frontend has an unchecked prose path (D40 item 5, unresolved):** nothing
  in this WP touches the frontend, but any future wiring of DiscoverChat into
  it must not inherit that path. Noted so it isn't forgotten.
