# Odisha PR&DW Analytics — Project Plan & Decision Log

Maintained by the PM session. Last updated: **2026-08-13 (post WP-4a; Discover workstream opened)**.
Read `ODISHA_PRDW_BOOTSTRAP.md` first — this document layers the *current* plan,
decisions, and state on top of it. Implementation agents receive work via
`handoffs/WP*.md` briefs and reply with `REPORT.md` at the repo root.

---

## 1. Operating model

- **Operator** (project owner) controls all implementation agents and makes all edits.
- **PM session** authors briefs, plans, and reviews, and — since D21
  (2026-08-13) — also **executes non-code work directly**: read-only data
  profiling/analysis and all `.md` deliverables. Implementation agents receive
  only code-writing packages (`.py`; WP-D1 will rule on pack YAML/SQL). The PM
  still modifies no code or data and runs no git.
- Rhythm per the bootstrap: **handoffs in, reports out**. One agent run per
  working tree; commit before trusting a prior session's report.
- Current workstreams (2026-08-13, operator decision): **two in parallel** —
  **Ask** (WP-4 evals / WP-5 gates, `Chatbot/` + `eval/`) and **Discover**
  (WP-D0…WP-D3, `Insights/`). They are **file-disjoint** (D14); the
  one-agent-per-working-tree rule still applies, so concurrent runs use the
  WP-4a sandbox pattern (author outside the repo, copy in after). The Track
  frontend stays deferred. No deploy work (`railway.json` deferred until
  deployment is in scope).

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
| D12 | ~~Rebuild `dim_code` from `code_descriptions_updated.xlsx`~~ **RESCINDED 2026-08-13** — the operator withdrew the `20_GP_flattened_data` drop as incorrect before anything was executed. No code, database, or catalogue change ever happened under D12 (the WP-3 T1b task was removed from the brief unrun). The DB's `dim_code` stands as shipped. | Drop declared incorrect by operator. |
| D18 | **Rulings on WP-4a report §0 (PM, 2026-08-13):** (P1) `$top_n` becomes optional-with-default-10 in the generated catalogue — no officer says "top 10"; leaving it required makes every ranking question stall and poisons the first eval run. Ceiling stays 1,000 (operator-ratified). (P2) Genuine judgment thresholds (`$threshold`, `$amount_threshold`, 15 templates) **ask** — a league table topped by a two-activity focus area is the confidently-wrong class; SME may overrule once, for the class. (P3) GP/block tier collisions **clarify** in v1 (consistent with D4); revisit on pilot evidence. (P4) duplicate workbook rows: stands as ruled in D13.4. (P5) Odia numerals: **fix now** — one-line digit normalization in `date_phrase.py`, with the G1008 gold row updated to expect an answer. (P6) SBM under-weighting in the gold set: accepted as reasoned. | WP-4a report §0, §§4–6. |
| D13 | **Rulings on WP-3 report §12 (PM, 2026-08-13):** (1) caveat appended verbatim to the deterministic answer text AND kept as a response field — accepted, strengthens D3 (WP-1's separate-field-only stance assumed an LLM-regenerated answer; `echo_answer` is deterministic and no frontend renders fields yet); (2) SQL-derived optionality wins over the Parameter Registry sheet for the 12 disagreements — the sheet needs the edit (team ask); (3) ALR-001/ALR-008's optional `$date_range` stands as a workbook-endorsed exception to D9; (4) the four duplicate question pairs keep both IDs (traceability to the signed-off workbook; identical SQL means either route is correct — WP-4 grading must treat them as acceptable-answer sets); (5) dashboards stay OFF until operator+SME ratify the 21-entry proposal, the pinned `'2024-2025'` year, and caveats-on-tiles; (6) statewide pagination for unbounded exception reports is deferred to pilot evidence — with `top_n` ratified at 1,000 (operator, commit `96179d8`), oversize requests clarify. **D11.4 is closed: ceiling 1,000, ratified.** | WP-3 report §§5.2, 6.5, 9, 10, 12. |
| D11 | **Rulings on WP-2 report §8:** (1) a bare four-digit year reads as the fiscal year *starting* in it ("2024" → `2024-2025`) — keep, pinned in tests, revisit from pilot logs; (2) unqualified "SFC" → `5TH STATE FINANCE COMMISSION` (the current one), "4th SFC" reaches the 4th — keep; (3) rename `EntityCandidate.village` to a tier-neutral name in WP-3; (4) `top_n` ceiling 1000 accepted **provisionally** — WP-3 must check whether any listing template legitimately needs more statewide (a full GP listing is ~6,800) and raise it then; (5) thin alias tables accepted — they fill from the D5 dictionary file and query logs, not guesses. | PM rulings 2026-08-13. |
| D14 | **Discover workstream opens in parallel with Ask** (operator, 2026-08-13). File-disjoint: Discover agents touch only `Insights/` + `handoffs/WPD*`; Ask agents touch `Chatbot/`, `eval/`, `handoffs/WP[0-9]*`. Shared files (`PROJECT_PLAN.md`, this decision log) are PM-only. | No merge conflicts between parallel agent runs; the tree stays trustworthy. |
| D15 | **Discover v1 mines the 20-GP sample from `Data/`; statewide is a data swap.** Operator confirms statewide arrives later **in the same one-CSV-per-table format**. The pack therefore keeps every scale assumption in declarative files only (`expected_rows`, `post_view` checks) — one-file updates, no logic changes. Views are **geography-complete from day one**: district/block/GP names + LGD codes on every view (sourced from `gram_panchayat`, which carries the codes — not dependent on the pending `v_*` amendment, §5.6a); rate/average measures carried as **numerator + denominator** at base grain, never pre-computed ratios (block/district roll-ups must not become averages-of-averages); sample-vs-statewide differences in `VIEW*_CONFIG` dimensions/depth kept as a single marked switch (the `_DB_SOURCES` pattern). Cardinality flip is expected: sample findings are GP-grained; statewide, district (30) and block (314) become headline breakdown dimensions and GP (~6,800) becomes subspace/exception grain. | Operator 2026-08-13: "we need to compare not just on GPs but on blocks and districts as well." |
| D16 | **Discover feed contract = AP's feed JSON shape, frozen.** The eventual PR&DW frontend will be the AP frontend ported, so `phase5c_global_feed.py`'s existing output shape (documented in its file header) is the contract. No shape change without an operator decision. | Operator confirmed 2026-08-13. WP-D3's gate validates against this. |
| D17 | **Discover prose model: GPT-5.6** (operator choice 2026-08-13). Set **only** via the shared constant in `discover_config.py`; the implementing agent verifies the exact API model ID against OpenAI's live model list (do not guess variants) and runs the **completion-token budget check before first use** — GPT-5.x are reasoning models, which is precisely the silently-empty-prose failure mode the shared constant exists to prevent. Diff the first report for hollow sections. Model pinned + identity check in the eventual Discover gates. Uses the existing `.env` OpenAI key; `.env` itself untouched. | Handoff §4 lesson; bootstrap model-risk discipline. |
| D19 | **Brief format v2** (operator accepted 2026-08-13, **provisional — operator will revisit**): WP-D briefs onward use the structured skeleton — files-in-scope/do-not-touch allowlist, verifiable preconditions, read-first-with-why, objective, non-goals, inline facts-you-need (load-bearing constraints restated in one line each, cross-references kept as provenance only), per-task Do/Done-when/Traps/Escalate-if, cut-line, escalation protocol (STOP vs decide-and-document), gate, and an exact report section spec. Pilot: `handoffs/WPD0_view_mapping.md`. Ask-side briefs unaffected until the operator extends it. | Operator dissatisfaction with the AP-style dense-paragraph briefs; per-task done-checks and a single escalation protocol reduce dropped sub-requirements and PM review cost. |
| D20 | **The operator is the Discover SME** ("think of me as the SME on this piece of work", 2026-08-13): metric-definition sign-off (WP-D0 gate) and finding calibration (WP-D2, top-15/view labeled real / already-known / spurious) are operator calls — no external SME channel, no proxy arrangement. A statewide re-calibration still happens as an *event* when the full data lands, with the operator in the same seat. Scope: Discover only — WP-4a's outstanding SME sign-off (gold-set metric definitions/behavior calls) is NOT covered unless the operator says so. | Operator directive 2026-08-13. |
| D21 | **PM executes non-code work directly** (operator, 2026-08-13): documentation/analysis packages — WP-D0 first — are done by the PM session itself; implementation agents receive only code-writing work (`.py`). The PM remains barred from modifying code/data and from git operations. `handoffs/WPD0_view_mapping.md` stands as the PM's own work order and spec. **Sub-question resolved 2026-08-13: pack YAML/SQL counts as code — WP-D1 goes to an implementation agent.** | Operator: "why don't we handle this ourselves… we'll only give files to write code (like .py) to an agent." Refines D7's execution split. |
| D22 | **WP-D0 gate GREEN** (operator-as-SME, 2026-08-13): mapping-doc §9 approved **in full as recommended** — three-view slate (assets folded, no equity view in v1), money-funnel naming with SPENT default + the two signed cross-basis overspend measures, temporal scope (temporal mining on view2 only, deterministic count-caveat across FY 2023-24, phantom FY 2026-27 excluded), GP × fiscal_year grain for view3, completion measures kept as known-degenerate, raw free-text/document numbers excluded, sparse dimensions deferred to statewide. Also confirmed: **two PM sessions in parallel is intentional** — the §6 write convention stands. | Operator rulings 2026-08-13; `Insights/DISCOVER_VIEW_MAPPING.md` is the signed spec. |
| D23 | **PM rulings on the WP-D1 report (2026-08-14).** (1) Decision journal D-1..D-14 **accepted in full** — expressly blessing D-2 (overspend null semantics: coalesce vs-plan, NULL vs-sanction — pins statewide behaviour), D-9 (`voucher_pk_norm` is a derivation in the staging layer, the same double-cast idiom `create_views.sql` itself uses — not a data fix), and D-12 (the two verification `.py` scripts ship inside the pack as non-pipeline tooling; re-runnable parity beats format purity). (2) The five measured glossary corrections applied to WP-D2's Appendix A; `⟦PENDING-WPD1⟧` slots filled (70/17/26 columns, zero renames). (3) PM recommendations on the three SME flags: keep `n_tech_approvals` = 2,095 (Ask agreement wins; the 39 TA-without-AA records stay logged + become a team ask); SC/ST apparent transposition → team ask, no Discover impact in-sample; `authority_clean` ELSE passthrough → leave for the sample, add to the statewide-arrival checklist (any change must be paired Ask+Discover via `create_views.sql`, never pack-only). **Operator confirmed all four items 2026-08-14 — WP-D1 gate CLOSED green**; the SC/ST, TA-without-AA and decode questions proceed as team asks (§5.6d), the authority residue as the statewide checklist item (§5.6e). | WP-D1 report §§4–7; PM replay green 2026-08-14. |

## 3a. Standing disciplines (learned in this repo — additional to the bootstrap's)

- **Delete `Chatbot/**/__pycache__` and `Chatbot/.pytest_cache` after any fresh copy of this
  tree, before trusting a first test run.** WP-1 found the copied caches executing stale
  bytecode compiled from the *source repo's* paths (`co_filename` proved it). Every WP brief's
  T0 includes this.
- **Commit the tree before and after every agent run** (bootstrap rule, restated because the
  tree currently accumulates operator file moves between runs).
- **Audit every test/eval harness for accidental live API calls before running it.** WP-2
  found `LiveExtractionTests` making ~7 paid OpenAI calls on every suite run (it
  `load_dotenv()`s the keyed `.env`, then "skips if no key"). Now opt-in via
  `PRDW_LIVE_EXTRACTION=1`. Check the same pattern in the eval harnesses before WP-4.
- **The data-oddities log lives in WP reports** (validation logs, never fixes — bootstrap).
  Running list: WP-2 report §7 — leading tab in `'\tWORK COMPLETED'` (dim_code 178),
  `'Buildings'` mis-decoded into activity_status (code 173), `'Poverty allevation'`
  misspelling (focus_area 16), GP `Kalyansinghpur` vs block `Kalyansingpur`, theme trailing
  spaces, scheme_name 82% null. These feed the eventual ministry data-quality report.

## 4. Stage plan → work packages

| WP | Scope | Gate | Status |
|---|---|---|---|
| WP-1 | Engine extensions: DuckDB-file adapter (read-only), named binding (D1), optional slots (D2), caveat passthrough (D3). No domain content. | Baseline test suite still green + new unit tests green. | **DONE — gate green** (report: `handoffs/REPORT.md`; PM replay confirmed 293/32/17 on 2026-08-13). Commits `55c5a76`..`8af162e`. |
| WP-2 | Entity layer: registry generated from the Parameter Registry sheet (values loaded from the DB, read-only); name→LGD-code resolution with clarification chips; extractor enums generated from the registry; fiscal-year phrase mapping (D9); lakh/crore amount normalization; collision test with synthetic duplicates (D4); alias scaffolding (Odia/colloquial). | `test_extraction_enums` green; collision test green; baseline preserved modulo documented AP-fixture swaps. | **DONE — gate green** (report: `handoffs/WP2_REPORT.md`; PM replay confirmed 359/33/0 on 2026-08-13). Commits `de3b052`..`56d3501`. Note: the brief's "20 bind names" was a PM miscount — the sheet has 19; nothing is missing. |
| WP-3 | Catalogue: xlsx → generated `template_catalog.py` (346) + `unanswerable_catalog.py` (30) + `rerank_context.py` (327 families) via committed `tools/build_catalog.py`; D10 decided (GP binds LGD code — 302 predicates rewritten, oracle-proven neutral; block/district bind validated names pending view amendment); caveats rendered verbatim on all three serving paths; AP retrieval layer retired; dashboard proposal (21, ships OFF pending ratification). | Structural tests green; 346/346 row-count agreement with the workbook Test Report. | **DONE — gate green** (report: `handoffs/WP3_REPORT.md`; PM replay 2026-08-13: suite 391/28/0 + `validate_catalog.py` all-clear). Commits `ea7cdef`..`96179d8`. |
| WP-4a | Gold eval set draft: 205 questions, 10 brackets, 60/24/17 EN/mixed/Odia, 19 unanswerables, 11 ambiguity, acceptable-answer sets. | Coverage thresholds; every route resolves in the shipped catalogue; harness-format check. | **DONE — gate green** (report: `handoffs/WP4a_REPORT.md`; PM re-ran both checks 2026-08-13: 205 records OK, harness gate PASS). Output uncommitted pending integration. **SME sign-off outstanding — now the critical path** for grading conclusions: 7 metric definitions, 11 behavior calls, 34 Odia phrasing rows (report §4). |
| WP-4 | Integrate gold set; apply D18 fixes (`top_n` default, Odia digits, unanswerable-gold upgrade); fix graded-harness defects (stale tier tuple, undefended import, no spend guards); port/retire the two AP endpoint suites; run recall + end-to-end + consistency evals; triage failures with replays. **No threshold calibration until SME sign-off** (WP-4c). | Recall@30 ≈ 97%, end-to-end ≈ 96–97% parity benchmarks; every reported failure replay-confirmed. | **Brief ready: `handoffs/WP4_eval_run.md`** |
| WP-5 | Gates file `prdw_gates.py` (replaces `pmkisan_gates.py`): catalogue validity, routing accuracy, extraction-enum agreement, model-identity check. | "Gate-green" is a single command. | Can start alongside WP-3 |
| WP-D0 | Discover view mapping (no code): map `Data/` + the `v_*` definitions onto the archetypes (lifecycle, geography×month cube, GP performance w/ zero-activity rows, equity-feasibility verdict); dimensions/temporal/measures/impact per view with the cash-vs-plan basis stated for **every** money measure; geography-complete per D15; rates as num+denom; temporal-scope proposal for the 2023-24 step-change; column crosswalk draft (every staged column → role, AP `demo_crosswalk.csv` mechanics); sample-vs-statewide `VIEW*_CONFIG` switch plan. | Operator (as Discover SME, D20) approves the mapping doc. | **DONE — gate green** (D22: §9 approved in full, 2026-08-13; PM executed directly per D21; `Insights/DISCOVER_VIEW_MAPPING.md` is the signed spec) |
| WP-D1 | Author `domain_pack_prdw/` (sources.yaml, derived_columns.sql, three views/*.sql, validation.yaml, crosswalk.csv) per the signed mapping doc; no staging script needed (`Data/` is the direct input); build under `--strict` from a local mirror; validation report (defects logged, never fixed). | Clean `--strict` build; row counts + the mapping doc's audited reconciliation targets hit (documented deltas only); crosswalk complete; validation report delivered. | **DONE — gate green** (report `handoffs/WPD1_REPORT.md`; PM replay green 2026-08-14: build exit 0 / 0 failed checks, Ask↔Discover parity 41 cols 0 mismatches, crosswalk 182/182; operator-SME confirmed the four D23 items 2026-08-14). Reminder: tree commit required before WP-D2 dispatch — `074dfc9` alone is a non-building mid-flight snapshot. |
| WP-D2 | `VIEW*_CONFIG`s + column glossaries + audience framing; run phase4b→5→5b; D17 model-budget check; calibration on top-15/view. | Operator-as-SME calibration (D20): top-15/view labeled real / already-known / spurious; no nonsense findings in top ranks. Sample validates machinery; re-calibration re-runs when statewide lands. | **Brief pre-drafted: `handoffs/WPD2_mining_calibration.md`** — `⟦PENDING-WPD1⟧` slots to be filled by PM from the WP-D1 report before dispatch; incl. PM-authored glossary appendix |
| WP-D3 | Global feed + gamma editions; verify against the frozen AP feed shape (D16); all editions regenerated from one candidate set. | Feed validates against the AP contract; no stale-edition mix. | After WP-D2 |

## 5. Blockers & asks (operator)

1. **`create_views.sql` — RESOLVED (2026-08-13).** Team supplied it at
   `Data/create_views.sql`. **PM acceptance validation: 346/346 queries
   reproduce the workbook Test Report row counts exactly** (views created on a
   scratch copy; zero mismatches, zero errors; 17 documented skips). Seven
   views: v_activity/v_plan/v_asset/v_progress/v_voucher + building blocks
   v_exp/v_approval (both 1:1 rollups). Facts WP-3 needs: `v_activity` grain is
   one row per planned activity; `search_text` = `LOWER(activity_name || ' ' ||
   COALESCE(activity_desc,''))`; `status_label` is TRIM/tab-cleaned in views
   (WP-2's marked one-line `_DB_SOURCES` switch now applies — view value is
   clean `'WORK COMPLETED'`), while `theme` keeps its trailing space; views
   expose `gp_lgd_code` but NOT block/district codes → D10: GP binds code,
   block/district bind registry-validated names for the pilot (additive view
   amendment is the statewide option — `gram_panchayat` carries the codes).
   Minor, flag-only: file header says V4 (validation proves V5-compatible);
   `days_since_sanction` computes to CURRENT_DATE while its comment says
   "end of plan year" — unused by the catalogue, tell the team, don't touch.
   WP-3 runs Path A; Path B is moot.
2. **`q_*.py` workbook-builder modules** (optional but valuable) — would let
   WP-3 generate the catalogue programmatically instead of parsing the xlsx;
   the workbook notes a JSON export is a small addition.
3. Fuller workbook version if one exists — "How to use" references "What
   changed" and "Findings" sheets not present in this copy.
4. Later: full LGD geography roster (statewide), SBM keyword dictionary file
   (D5), SME contact for eval grading (WP-4).
5. **Raw-data history (2026-08-13):** the first drop (`20_GP_flattened_data`)
   was withdrawn by the operator as incorrect; all conclusions from it stay
   void (incl. the rescinded D12 and the Meri-Panchayat-JSON opportunity list —
   do not re-raise unless corroborated by a correct source). The replacement —
   **`Data/` (one CSV per table) + `table_sources_and_changes.docx`** — was
   verified by the PM: schema AND content are identical to the shipped
   `panchayat_1.duckdb` (19/19 tables, columns, row counts, money totals to
   the paisa, `dim_code` byte-identical). The docx is the build-provenance
   document for the existing DB, and it was built post-fix of the 987-date
   parsing bug it describes. **No rework anywhere; WP-1/WP-2 stand.**
   Resolved by it: (a) `plan.approval_date` comes from the Activity-wise
   Expenditure scrape (`plan_code_status` is a generated, always-empty
   placeholder) — ask closed; (b) `gram_panchayat` carries geography *codes*
   merged from the voucher source, so D10 has a dimension to resolve
   block/district codes against. Still standing (DB-verified, drop-independent):
   the `plan_year`/`fiscal_year` naming split in approval tables; the
   `dim_code` oddities ('Buildings' code 173, the `'\t'` tab). Note: `Data/`
   is the per-table CSV format `PandasAdapter` loads — keep as the canonical
   raw export and the template for the statewide load / stub-data builder.
6. **Discover asks (2026-08-13, updated 08-14):** (a) statewide `Data/` drop
   when ready — operator confirmed same one-CSV-per-table format (D15);
   (b) ~~name the Discover SME~~ RESOLVED — the operator is the Discover SME
   (D20); (c) **commit the current tree** — the completed pack, WPD1 report and
   WPD2 brief (commit `074dfc9` alone is a non-building mid-flight snapshot);
   (d) **team asks from WP-D1** (relay to the data team): supply decode
   descriptions for `output_type` (all 8 codes undescribed — view1 mines them
   as 'Code 101'…'Code 110'), `community_service_code` (3), and the missing
   `training_category_code`/`training_organiser_code` dim_code rows entirely;
   confirm whether `admin_approval_scheme.fund_sanctioned_sc/_st` vs
   `activity_expenditure.sc/st` are transposed (same two values, ₹3,226,802 and
   ₹440,000, swapped between the tables — WPD1 report §5.5); confirm whether a
   technical approval without an administrative approval (39 records,
   ₹4,200,502) is legitimate process or a data defect (report §4);
   (e) **statewide-arrival checklist opened**: re-profile `authority_clean`'s
   ELSE residue for personal names (report §5.6) before any statewide mining
   run; any cleaning change goes to `create_views.sql` + pack together, paired.
7. **Team asks after WP-3 (2026-08-13):** (a) the additive view amendment —
   `gp_lgd_code` on `v_asset`/`v_progress`, `block_code` + `district_code` on
   the geography views (finishes D10 for statewide; not pilot-blocking);
   (b) Parameter Registry sheet: correct the 12 optionality cells where the
   SQL disagrees (WP-3 report §5.2); (c) confirm intent on the four duplicate
   question pairs (EXP-031/032, BUD-014/017, EXP-009/011, EXP-026/030);
   (d) cosmetic: views file header says V4; `days_since_sanction`
   code/comment mismatch (unused by the catalogue).

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
- **Discover temporal contamination**: the 2023-24 reporting-completeness
  step-change will dominate Trend/ChangePoint pattern types unless WP-D0
  scopes the mining window or wires a deterministic known-artifact caveat.
  A "finding" that restates the reporting artifact is the Discover analogue
  of the confidently-wrong answer.
- **Two PM sessions editing `PROJECT_PLAN.md` concurrently** (observed
  2026-08-13: Ask-side D18/WP-4a rows landed mid-edit of this session's
  Discover update). Convention until retired: each PM session re-reads the
  file immediately before editing and touches only its workstream's rows;
  decision numbers are claimed in the log before first use.
