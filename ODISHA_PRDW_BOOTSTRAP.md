# Odisha PR&DW — agent onboarding and bootstrap guide

You are working in a **fresh copy** of a proven codebase, being adapted for the
**Odisha Panchayati Raj & Drinking Water Department (PR&DW)**. This document is
self-contained: it tells you what the system is, where this code came from, what
state the copy is in, which files are reusable engine versus domain content to
re-author, the build order with acceptance gates, and the hard-won lessons from
the two previous deployments. Read it fully before touching code.

**Lineage:** this is the third deployment of the same system.
1. **UP / PM-JAY** (health insurance, Uttar Pradesh) — the original build.
2. **AP / RTGS Agriculture** (seven farm schemes, Andhra Pradesh) — the first
   replication; this copy was taken from that repo
   (`Dontuse_Decision_Aids`, branch `fresh-decision-aids`, ~commit 2672032,
   2026-08-13).
3. **Odisha PR&DW** — this instance. Your job.

The engine survived two domains intact. The domain content (SQL templates,
entity registries, prompts, descriptions, eval sets) was rewritten each time.
That split is the whole replication strategy — respect it.

---

## 1. What this product is

A three-mode analytics product for government programme officers who don't
write SQL:

- **Ask** — natural-language questions answered from a *curated catalogue* of
  vetted SQL (never free-form LLM-generated SQL). FastAPI backend in
  `Chatbot/`. **This is the current workstream.**
- **Discover** — an automated insight-mining pipeline (MetaInsight framework)
  that searches flat analytical views for statistical patterns and emits a
  ranked feed plus an LLM-written executive report. **Not yet copied into this
  instance** — it comes as a later workstream (`Metainsights_anomalies/` in the
  source repo).
- **Track** — a geographic choropleth explorer (`frontend/`; separate
  workstream, out of scope for now).

### The two load-bearing design principles — never violate these

1. **No free-form SQL generation.** Every answerable question maps to a
   pre-authored, validated SQL entry (a cached "dashboard" query or a
   parameterised template). The LLM only routes questions to catalogue entries
   and extracts parameter entities. This is both the accuracy story and the
   security/compliance story — the ministry can audit the finite query set.
2. **LLM as translator, never analyst.** The LLM turns structured, engine-
   produced results into prose and routes questions. It never computes a
   number and never sees row-level data — only questions, catalogue text,
   entity names, and aggregates. Lead with this when the ministry asks about
   LLM API use.

### How Ask routes a question (all generic machinery, all present in this copy)

```
question → preprocess/normalize
         → vector retrieval: embed question, top-K nearest catalogue questions
         → LLM reranker: pick the one right query_id (or no_match)
             (each candidate carries a family-level "↳" description from
              rerank_context.py — the model judges by description, not word
              overlap)
         → entity extraction (LLM) for the template's parameter slots
         → entity validation: exact → alias → fuzzy, against the registry
         → pending-clarification resolution (chips) if a slot can't bind
         → execute: cached dashboard result OR parameterised SQL (DuckDB
           locally / Postgres deployed)
         → rows + chart hint + follow-up context + suggestions
```

Three-zone confidence handling (`query_router/config.py`): high similarity →
answer; ambiguous → clarification chips; low → graceful fallback with
suggestions. Follow-up fragments ("in Ganjam?") are handled deterministically
by `fragment_reroute.py` — they keep the prior question's context.

---

## 2. State of this copy (as of 2026-08-13)

The layout was **flattened**: what was `Chatbot/backend/` in the source repo is
now `Chatbot/` directly. Check for any hardcoded `backend` path segments
(deploy config, imports, docs) as you touch files.

Deliberately **not** copied (do not go looking for them, do not recreate them):
AP datasets (`real_data/`), AP eval question sets and all eval *result* files
(`eval_questions_*.json`, `*_results.jsonl`, graded/mapping/consistency CSVs),
the embedding caches (`.tmp/` — the vector retriever rebuilds its index
automatically, keyed by a hash of the catalogue), `.pytest_cache/`, and AP
one-off repro scripts.

Known **gaps to fix immediately** (Stage-0 chores):
- `requirements.txt` and `railway.json` were not copied. Recover them from the
  source repo or ask the operator. Nothing installs or deploys without them.
- `pmkisan_gates.py` and `build_stub_data.py` are AP domain files that came
  along. Keep them briefly as worked examples, then replace with
  `prdw_gates.py` / a PR&DW stub-data builder and delete the AP versions.
- There is no git history in this copy's favour — confirm with the operator
  whether this instance is its own repo; if not, `git init` early so agent
  runs are auditable.

---

## 3. File inventory: reuse vs. re-author

Legend: **KEEP** = generic engine, use unchanged. **EDIT** = generic code with
embedded domain config/prompts — update the marked parts in place.
**REWRITE** = pure domain content, author from scratch (the copied file is your
worked example — read it, gut it, write PR&DW content).

### `Chatbot/` (app shell and harness)

| Path | Status | Notes |
|---|---|---|
| `main.py`, `db.py`, `db_adapters.py`, `db_factory.py`, `startup.py`, `start.py`, `init_supabase.py`, `sql/cache_tables.sql` | KEEP | App shell, DB abstraction (DuckDB local / Postgres deploy), cache seeding. Point config at PR&DW data. |
| `recall_eval.py`, `rerank_eval.py`, `run_full_eval.py`, `run_custom_eval.py`, `run_consistency_eval.py`, `grade_full_eval.py`, `gen_consistency_summary.py`, `aggregate_consistency.py` | KEEP (harness) | Eval harnesses are generic; the gold question sets they consume are per-domain — author PR&DW ones (see Stage 3). The consistency runner exists because **routing is nondeterministic** (~3/97 questions flip on identical replays in AP); it is how you tell a real regression from replay noise. Never open a bug on a single miss without a replay. |
| `validate_catalog.py`, `dump_catalog.py` | KEEP | Catalogue sanity checks; wire them into the gates file. |
| `pmkisan_gates.py` | REPLACE | AP's acceptance gates. Write `prdw_gates.py` in its image: catalogue validity, routing accuracy on the gold set, extraction-enum agreement, model-identity check. "Gate-green" must be a command, not a judgment call. |
| `build_stub_data.py` | REPLACE | AP synthetic-data builder; write the PR&DW equivalent once the data dictionary exists. |

### `Chatbot/query_router/`

| Path | Status | Notes |
|---|---|---|
| `router.py`, `models.py`, `context_store.py`, `operations.py`, `echo.py`, `vector_retriever.py`, `pending_resolver.py`, `fragment_reroute.py` | KEEP | Core routing, context, param-stall/clarify resolution, deterministic fragment handling. A few AP example strings may linger — cosmetic only. |
| `config.py` | EDIT | Model names, retrieval K, confidence thresholds. Thresholds (`NO_MATCH_LOWER`, `CLARIFY_UPPER`, `CLARIFY_SCORE_MARGIN`) were calibrated on the AP catalogue — re-calibrate **only after** the PR&DW catalogue and eval set exist, and only from eval evidence, never from a single flipped question. |
| `date_phrase.py` | EDIT | Year-phrase → SQL window. Review calendar assumptions: agricultural seasons don't apply; PR&DW likely cares about fiscal years, quarters, audit years. |
| `column_metadata.py` + `column_types.json` | EDIT | Generic classifier; review pattern rules against PR&DW column names. |
| `entity_validator.py` | EDIT | The exact→alias→fuzzy cascade is generic. `REGISTRY_CONFIG`, the `_load()` DB queries, and the state-level-terms list are domain content: new entity types, source tables, and aliases (Odia-language and colloquial synonyms live here). |
| `entity_extractor.py` | EDIT | Generic LLM extraction; refresh few-shot examples. **The enum lists in the prompt must be complete and generated from the registry** — see lesson list. |
| `preprocessor.py`, `fallback.py`, `suggestions.py`, `zones.py`, `followup_classifier.py` | EDIT | Generic logic with domain example strings and user-facing copy. |
| `reranker.py` | EDIT | Logic generic; the system prompt's disambiguation rules encode domain ambiguity pairs — rewrite as PR&DW ambiguities emerge from evals. |
| `rerank_context.py` | REWRITE | Family-level "↳" descriptions for every template. Pure domain prose, and the largest file the AP port added. Author one description per question *family* (parameter variants share it word-for-word); a test enforces full coverage and no template in two families. Read this file's docstring — it documents the authoring contract. |
| `template_catalog.py` | REWRITE | The parameterised SQL templates (AP: 293 entries). **The single biggest authoring task.** Author against flat analytical views wherever possible, not normalized tables. |
| `dashboard_catalog.py` | REWRITE | Pre-computed/cached queries for the most common questions. |
| `intent_catalog.py` + `intent_classifier.py` | DROP or leave unbuilt | Legacy routing path (`USE_VECTOR_RETRIEVAL=False`). The vector path is primary; don't invest here. |

### `Chatbot/tests/`

Copy came with the full AP suite. **Do not regenerate tests from scratch** —
nearly every file is a regression test for a defect a previous deployment paid
to find. Three buckets:

1. **Structural invariants — run unchanged, use as definition-of-done for the
   catalogue:** `test_rerank_context.py` (every template described, none in two
   families), `test_param_binding.py` (every slot binds),
   `test_extraction_enums.py` (prompt enums agree with the registry). These
   fail on day one and go green as PR&DW content is authored. That is the
   point.
2. **Engine behavior — keep logic, swap AP fixtures for PR&DW ones:**
   context store/window, zones and follow-ups, fragments, pending
   clarification/resolver, router miss path, reranker parse, vector retriever,
   operations, column metadata, date phrases. Zero test-logic changes.
3. **Port the concept, not the file:** `test_name_collisions.py` — see the
   name-collision lesson below; write the PR&DW equivalent around its unique
   keys. `test_land_units.py` — acre/cent→hectare is agriculture-only; drop,
   but note the analogous PR&DW trap is lakh/crore amount normalization.

---

## 4. The domain: what changes for PR&DW

You should receive a **ministry context bundle** before building domain
content:
- Data dictionary (schemas, grains, PK/FK, code lists/enums, update cadence)
- Sample data extract
- Question catalogue material (target user questions, MIS report formats,
  review-meeting templates, KPI definitions with exact numerator/denominator)
- Reference/master data (geography hierarchy with **LGD codes**, Odia aliases)
- A named domain expert (SME) for metric sign-off and eval grading

**If any of this is missing, flag it to the operator before authoring** —
especially ratified metric definitions, which every SQL template will encode.

Expected entity model (verify against the bundle, don't assume):
- **Geography/institutions:** the three-tier hierarchy — Gram Panchayat →
  Block/Panchayat Samiti → District/Zilla Parishad — plus habitations/villages
  for drinking-water assets. This replaces AP's village→mandal→district.
- **People:** sarpanches, secretaries, elected representatives; possibly
  beneficiaries.
- **Programme objects:** works/projects, Finance Commission grant instalments,
  GPDP plans, audits, drinking-water schemes/assets, expenditure records.
- **Statuses/enums:** fund-release stages, work-completion stages, water
  quality/functionality categories.

**Name collisions are a first-class design constraint, not an edge case.** In
AP, joining people by name silently merged distinct farmers; the fix was to
resolve every person to a unique ID before any template binds. PR&DW is worse:
GP names repeat across blocks and districts, and sarpanch/secretary names
repeat everywhere. Every template that takes a GP, village, or person must bind
a resolved unique code (LGD codes for geography), never a raw name, with
clarification chips when a name is ambiguous. Build this in from the first
template, and write the collision test early.

---

## 5. Build order (each stage has a gate)

**Stage 0 — chores + understand the domain (no domain code).** Fix the copy
gaps (§2). Read the data dictionary and question material. Produce a short
mapping doc: the flat analytical views for this domain (grain, dimensions,
measures), the entity types with their unique keys and alias needs, and metric
definitions with SME sign-off. *Gate: operator + SME approve the mapping doc.*

**Stage 1 — data foundation.** Load PR&DW data behind the `db_factory`
abstraction; build the flat views; write the stub-data builder for local dev.
*Gate: row counts and spot-check aggregates confirmed by SME.*

**Stage 2 — entity layer.** Registry + aliases in `entity_validator.py`,
extraction few-shots and registry-generated enums in `entity_extractor.py`,
the collision guard. *Gate: `test_extraction_enums` green; collision test
green.*

**Stage 3 — catalogue.** Dashboard entries for the top common questions;
parameterised templates against the views; `rerank_context.py` family
descriptions as you go. Build the gold eval set in parallel (≥100 questions,
phrased the way real officers talk, bilingually — Odia/English/code-mixed).
*Gate: structural tests green; recall and end-to-end routing accuracy on the
gold set at parity with prior deployments (recall@30 ≈ 97%, end-to-end ≈
96/97 behaving-correctly were the benchmarks).*

**Stage 4 — tune and pilot.** Re-calibrate confidence thresholds on eval
evidence; consistency replays; UAT with real officers; feed unanswered
questions back into the catalogue and aliases.

---

## 6. Hard-won lessons from UP and AP (do not relearn these)

**Environment and process**
- **Never run DuckDB writes, npm, or servers on a Google Drive-synced
  directory.** DuckDB can't create temp files there and npm breaks. The Drive
  repo is ground truth for code and reports; run pipelines from a local
  mirror (e.g. under `C:\dev\`) and sync artifacts back.
- **One agent run per working tree.** Two AP runs on one uncommitted tree
  silently reverted each other's edits. Commit (or at least re-run tests)
  before trusting any prior session's report.
- **Routing is nondeterministic.** Identical replays flip ~3% of questions.
  Always re-run before reporting a regression; grade evals by "acceptable
  answer set", not exact-ID match, or you will chase phantom regressions.
- Every agent run ends with a REPORT.md (what changed, gate results, open
  operator decisions). Handoffs in, reports out — that's the operating rhythm.

**Model risk**
- **Pin model names and add a model-identity check to the gates.** An upstream
  swap to a smaller extraction model broke name extraction (~2/3 None on some
  names) with no code change. Proved by A/B on the model, not the prompt.
- **On any model swap, check the completion-token budget first.** A reasoning
  model silently consumed a 2,000-token budget entirely on reasoning and
  returned empty strings; a report was generated with every section blank and
  nothing failed loudly.

**Routing and extraction**
- **Extraction-prompt enums must be complete and generated from the
  registry.** Incomplete enum lists caused silently wrong answers (9 rows
  instead of 38; 200 confidently wrong rows). The agreement test exists for
  this; keep it green.
- **Reranker descriptions are family-level.** One strong description per
  question family; the model picks the variant from the parameter structure.
  Per-variant descriptions caused confusion, not precision.
- **Don't tune confidence thresholds off single incidents.** AP's ambiguous-
  zone margin was nearly re-tuned over what turned out to be a sibling-
  paraphrase tie artefact firing on 1/97 questions.

**Data and content**
- **Keep zero-activity rows** in any performance view (LEFT JOIN from the
  master/roster table). Institutions with no activity are the finding — for
  PR&DW, a GP that filed nothing is exactly what a review meeting needs.
- **Validation logs, never fixes.** Data-quality defects (duplicates, nulls,
  stale records) are analytically meaningful; preserve and report them.
- **Budget for multilingual explicitly.** Local-language and code-mixed
  phrasings work through the embedding retriever only after aliases and eval
  questions are authored bilingually. Colloquial usage lives in the alias
  list ("sarkari" → PUBLIC); expect to grow it continuously from query logs.

---

## 7. What comes after Chatbot

The **Metainsights/Discover** pipeline is the second workstream: copy
`Metainsights_anomalies/src/` (engine) from the source repo, author a
`domain_pack_prdw/` (sources.yaml, derived_columns.sql, views/*.sql,
validation.yaml — two worked examples exist: `domain_pack/` for UP,
`domain_pack_rtgs/` for AP), and update the `VIEW*_CONFIG` declarations and
column glossaries. Do **not** copy `data_fix.py` (UP-specific data repairs).
`discover_config.py` (central model + token budget) comes along unchanged.
Frontend rebrand is the third workstream. Ask the operator before starting
either.
