# Odisha PR&DW Analytics — Project Plan & Decision Log

Maintained by the PM session. Last updated: **2026-08-13 (post WP-1)**.
Read `ODISHA_PRDW_BOOTSTRAP.md` first — this document layers the *current* plan,
decisions, and state on top of it. Implementation agents receive work via
`handoffs/WP*.md` briefs and reply with `REPORT.md` at the repo root.

---

## 1. Operating model

- **Operator** (project owner) controls all implementation agents and makes all edits.
- **PM session** is strictly advisory: it authors briefs, plans, and reviews as
  `.md` files only. It does not modify code or data.
- Rhythm per the bootstrap: **handoffs in, reports out**. One agent run per
  working tree; commit before trusting a prior session's report.
- Current workstream: **Ask/Chatbot backend only.** Discover (MetaInsights) and
  the Track frontend are explicitly deferred. No deploy work (`railway.json`
  deferred until deployment is in scope).

## 2. Verified state of the repo (2026-08-13)

- Git initialized with baseline commit `7184d5e` (pre-adaptation snapshot) and
  `25d654d` (file moves). Working tree clean. `.gitignore` excludes `.env`
  (holds live API keys — never print or commit), `__pycache__`, `*.duckdb`,
  `~$*`, and `frontend/`.
- `Chatbot/requirements.txt` — present (fastapi, uvicorn, pandas, duckdb,
  python-dotenv, openai, rapidfuzz, numpy, pyngrok, psycopg2-binary).
- `Chatbot/data/panchayat_1.duckdb` — the sample analytical DB. **Verified:**
  all 19 base tables present; row counts match the data dictionary exactly
  (gram_panchayat 20, plan 204, planned_activity 12,704, activity_expenditure
  12,730, voucher 12,440, activity_voucher 5,976, admin_approval 2,101,
  technical_approval 2,134, physical_progress 8,267, dim_code 717).
  **The seven `v_*` views are NOT present** — see Blockers.
- `AI_Chatbot_Questions.xlsx` — the **signed-off** query catalogue (operator
  ratified 2026-08-13). 363 questions, 10 brackets; 95 Yes / 251 Partial /
  17 No answerability; all 346 answerable rows carry SQL tested against
  panchayat_1.duckdb (325 PASS, 21 PASS with 0 rows, 17 SKIP). Plus 13
  dropped beneficiary questions (NSAP columns empty). The Parameter Registry
  sheet (20 bind names with source columns and allowed-values queries) is the
  spec for the entity layer.
- `panchayat_database_description_v2 (1).docx` — data dictionary; matches the
  DB. Key traps it documents: fiscal year must be the full `'2024-2025'`
  string; two expenditure conventions (cash basis via vouchers vs plan basis
  via activity_expenditure — every answer must state which); 2023-24
  step-change in reporting completeness poisons cross-year trends; approval
  tables cover only ~17% of activities (absence ≠ unapproved); `scheme_name`
  82% null; SARPANCH/SARAPANCH/sarpanch spelling split; dim_code decode
  requires both the `variable` predicate and a VARCHAR cast.
- The AP domain content (template_catalog, dashboard_catalog, rerank_context,
  entity registry, pmkisan_gates, build_stub_data, tests) is intact and serves
  as worked examples until each is replaced per the bootstrap's KEEP/EDIT/
  REWRITE table.

## 3. Decision log

| # | Decision | Rationale |
|---|---|---|
| D1 | **Named parameter binding**: extend the runtime to execute the workbook's `$name` SQL verbatim (DuckDB dict binding natively; `$name`→`%(name)s` translation in the Postgres adapter). Do **not** convert to positional `?`. | Binding syntax has no routing-performance effect; keeping the tested SQL verbatim avoids conversion bugs (repeated `$param` occurrences make positional expansion error-prone). Auditability is a side benefit, not the driver. |
| D2 | **Consolidated templates + optional slots** (operator re-examined 2026-08-13; confirmed on performance grounds): one template per question with `($p IS NULL OR col = $p)` optional geography filters — NOT AP-style per-scope variants (~1,100–1,400 entries). Absent optional slot binds NULL; no clarification stall. Required slots keep current behavior. **Scope-phrased paraphrases** ("…in {Block}…", "…in {District}…") are indexed per family for embedding recall, all resolving to the one template. | Moves the scope decision out of the noisy LLM-rerank layer (sibling variants → sibling-paraphrase ties, top-K crowding — both documented AP failure modes; AP's variants were a workaround for the positional-required engine, and its reranker descriptions were family-level anyway) into deterministic extraction + registry validation. Keeps the SQL surface at the 346 execution-tested queries. The workbook already splits questions where scope changes output *shape* (e.g. PLN-003 vs PLN-004), which is the only split that earns its keep. Escape hatch: if WP-4 evals show scope misrouting, split only the offending families, on eval evidence. |
| D3 | **Caveats are first-class**: catalogue entries carry the workbook's Answerability Note; the answer payload must surface it. | 251/363 questions are "Partial" — a Partial answer without its caveat is the confidently-wrong failure mode. |
| D4 | **Statewide trajectory**: the 20-GP DB is a sample; production is ~6,800 GPs (30 districts, 314 blocks). Geography must resolve to `gp_lgd_code` before binding (never raw names); collision clarification chips; the collision test is written NOW with synthetic duplicate names since the sample can't exercise it. Entity registry loads values from the DB so statewide is a data swap, not a redesign. | Operator confirmed 2026-08-13. GP and person names repeat statewide. |
| D5 | **Language/keyword dictionary as data, not code**: SBM-bracket questions (86) identify activities by keyword-matching `activity_name`/`activity_desc`, currently romanized-English in the sample but any-language statewide. A concept→keywords lookup (multilingual, incl. transliterations) will live as a data table the SQL joins against; the same source feeds entity aliases. A keyword-coverage profile (% of activity text matching nothing) becomes a standing data-quality report. | Operator offered to supply a dictionary file. Keyword lists frozen inside 86 signed-off SQL strings could not grow without re-ratification. |
| D6 | **Drive discipline**: this Drive folder is ground truth for code and docs. The runtime and all tooling open the `.duckdb` **read-only**; any write-requiring or heavy execution uses a local copy. No servers/npm from this folder. | Bootstrap lesson; DuckDB temp files fail on Drive. |
| D7 | **Execution model**: strictly advisory PM (this file and `handoffs/*.md`); all edits via the operator's own agent. | Operator directive 2026-08-13. |
| D8 | **Keep `to_pyformat()`** as a tested utility, not wired to any adapter. `SupabaseAdapter` binds through DuckDB's postgres extension, so `$name` dicts bind natively there — translation would break a working path. The utility is correct code for a future driver-level (psycopg2) adapter. Each adapter declares `PARAMSTYLE`. | PM ruling on WP-1 report §8.1, accepting the implementer's analysis. |
| D9 | **Fiscal year is an ordinary named slot** (`$date_range` etc.), never a `date_filter` injection — `date_kind` machinery stays dormant for PR&DW (its `year` kind compares integers; Odisha's fiscal year is the `'2024-2025'` string). `date_phrase.py` (WP-2) maps phrasings ("FY 24-25", "last year", "this year") onto the exact full-form string. A question with no year stated follows required-slot behavior — clarification chip — for v1; revisit from pilot logs if officers overwhelmingly mean "current year". | PM ruling on WP-1 report §8.3. |
| D10 | **Geography binds LGD codes end-to-end — decided in principle (D4); the SQL predicate rewrite (`gp_name = $gp_name` → `gp_lgd_code = $gp_code`) is a WP-3 decision** pending `create_views.sql`, which determines whether the views expose block/district codes. WP-2 must deliver name→code resolution machinery regardless, so WP-3's choice is a predicate edit, not new design. | Workbook SQL filters on names (safe for the 20 unique sample GPs, unsafe statewide). Operator has waived byte-level SQL fidelity in favor of performance/correctness. |

## 3a. Standing disciplines (learned in this repo — additional to the bootstrap's)

- **Delete `Chatbot/**/__pycache__` and `Chatbot/.pytest_cache` after any fresh copy of this
  tree, before trusting a first test run.** WP-1 found the copied caches executing stale
  bytecode compiled from the *source repo's* paths (`co_filename` proved it). Every WP brief's
  T0 includes this.
- **Commit the tree before and after every agent run** (bootstrap rule, restated because the
  tree currently accumulates operator file moves between runs).

## 4. Stage plan → work packages

| WP | Scope | Gate | Status |
|---|---|---|---|
| WP-1 | Engine extensions: DuckDB-file adapter (read-only), named binding (D1), optional slots (D2), caveat passthrough (D3). No domain content. | Baseline test suite still green + new unit tests green. | **DONE — gate green** (report: `handoffs/REPORT.md`; PM replay confirmed 293/32/17 on 2026-08-13). Commits `55c5a76`..`8af162e`. |
| WP-2 | Entity layer: registry generated from the Parameter Registry sheet (values loaded from the DB, read-only); name→LGD-code resolution with clarification chips; extractor enums generated from the registry; fiscal-year phrase mapping (D9); lakh/crore amount normalization; collision test with synthetic duplicates (D4); alias scaffolding (Odia/colloquial). | `test_extraction_enums` green; collision test green; baseline preserved modulo documented AP-fixture swaps. | **Brief ready: `handoffs/WP2_entity_layer.md`** |
| WP-3 | Catalogue: xlsx → `template_catalog.py` + caveats + scope-phrased paraphrases (D2); geography predicate decision (D10); dashboard picks; `rerank_context.py` family descriptions (Bracket/Module/Submodule as family structure); 17 No + 13 dropped wired into fallback as known-unanswerable; audit of the four retrieval-layer modules that assume all slots required (`reranker.py`, `suggestions.py`, `followup_classifier.py`, `fragment_reroute.py`, plus retire `router._scope_sibling` — WP-1 report §8.2); answer layer must render `caveat` when present; no `$tag$` quoting in catalogue SQL (WP-1 report §8.4). | Structural tests green; all 346 queries execute with sample binds matching the workbook Test Report row counts. | Blocked on `create_views.sql` |
| WP-4 | Gold eval set (≥100 questions, officer phrasing, Odia/English/code-mixed) + recall/routing evals; then threshold calibration from eval evidence only. | Recall@30 ≈ 97%, end-to-end ≈ 96–97% parity benchmarks. | After WP-3 |
| WP-5 | Gates file `prdw_gates.py` (replaces `pmkisan_gates.py`): catalogue validity, routing accuracy, extraction-enum agreement, model-identity check. | "Gate-green" is a single command. | Can start alongside WP-3 |

## 5. Blockers & asks (operator)

1. **`create_views.sql`** — the seven `v_*` views are missing from this copy of
   the DB; all 346 tested queries depend on them. Blocks WP-3's execution gate.
   When supplying it: if the views don't already expose **block and district LGD
   codes** (not just names), say so — it decides D10's predicate rewrite.
2. **`q_*.py` workbook-builder modules** (optional but valuable) — would let
   WP-3 generate the catalogue programmatically instead of parsing the xlsx;
   the workbook notes a JSON export is a small addition.
3. Fuller workbook version if one exists — "How to use" references "What
   changed" and "Findings" sheets not present in this copy.
4. Later: full LGD geography roster (statewide), SBM keyword dictionary file
   (D5), SME contact for eval grading (WP-4).

## 6. Standing risks

- **SBM undercount statewide** (D5): keyword matching silently shrinks on
  unseen-language text — mitigated by the dictionary + coverage profile.
- **Nondeterministic routing** (~3% flip on replay per AP): never open a
  regression on a single miss; use the consistency runner.
- **Model risk**: pin model names; identity check in gates; on any model swap
  check the completion-token budget first (bootstrap lessons).
- **Denominator caveat**: percentage questions divide by the 20 loaded GPs,
  not the official roster, until statewide reference data loads.
- **Excel lock file** (`~$AI_Chatbot_Questions.xlsx`) indicates the workbook
  is open on the operator's machine — re-export before any WP-3 parse to be
  sure the saved file is current.
