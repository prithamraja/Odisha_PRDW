# WP-1 — Engine extensions (handoff brief)

**For:** the operator-controlled implementation agent.
**Read first:** `ODISHA_PRDW_BOOTSTRAP.md`, then `PROJECT_PLAN.md` (decisions D1–D3, D6) at the repo root.
**Scope:** generic engine only. No domain content (no PR&DW catalogue, registry, or prompts — those are WP-2/WP-3).

## Context you need

- Repo root: `i:\My Drive\ASC Lab\LMIC AI Code repo\Odisha_PRDW`. Git is initialized; baseline commit `7184d5e` predates all changes; working tree is clean. Windows, PowerShell 5.1 (no `&&`).
- The PR&DW catalogue (in `AI_Chatbot_Questions.xlsx`, integrated later in WP-3) uses DuckDB **named** parameters — `$district_name` etc., often repeated within a query via the optional-filter pattern `($district_name IS NULL OR col = $district_name)` where binding NULL disables the filter. The current engine contract (`Chatbot/query_router/template_catalog.py`) is positional `?` with ordered, required `param_slots`.
- Project decisions (see PROJECT_PLAN.md for rationale): extend the runtime to named binding (D1), add optional-with-NULL slots (D2), thread a caveat field through to the answer payload (D3). Keep workbook SQL verbatim — never convert to positional.
- `Chatbot/data/panchayat_1.duckdb` holds the 19 base tables (verified against the data dictionary). The seven `v_*` views are absent (`create_views.sql` awaited) — nothing in WP-1 depends on them.

## Hard constraints

- Work only inside the repo root (plus your session scratchpad for temp files). Never touch `frontend/`.
- The root is Google Drive-synced. **Never open `Chatbot/data/panchayat_1.duckdb` writable.** Runtime code opens it `read_only=True`; for test fixtures, build a fresh temp `.duckdb` in the scratchpad.
- `Chatbot/.env` holds live API keys — never print or commit it (already gitignored).
- Do not delete or rewrite AP domain content (template/dashboard/rerank catalogues, entity registry, `pmkisan_gates.py`, `build_stub_data.py`, existing tests). Engine changes must keep them working.
- No LLM API calls anywhere in this package.

## Tasks

**T0 — Baseline.** `pip install -r Chatbot/requirements.txt` (add pytest if missing). From `Chatbot/`: `python -m pytest tests/ -q` **before any change**; record exact pass/fail counts. Pre-existing failures are recorded, not silently fixed.

**T1 — DuckDB file adapter.** Add a file-backed adapter to `Chatbot/db_adapters.py` (same interface as `PandasAdapter`/`SupabaseAdapter`) opening a `.duckdb` file `read_only=True`. Wire into `db_factory.py` as `DB_ENGINE=duckdb_file` with a `DB_PATH` env var (relative paths resolve against `Chatbot/`, like `DATA_DIR`). Cache tables (`sql/cache_tables.sql`) can't be created in a read-only DB — solve cleanly (e.g. ATTACH an in-memory DB for cache tables, or skip seeding for this engine with a clear log line) and document the choice. Update `.env.example` only (never `.env`) with the new engine config pointing at `data/panchayat_1.duckdb`. Default engine behavior must be unchanged unless `DB_ENGINE=duckdb_file` is set.

**T2 — Named-parameter execution.** Extend the execution path so a catalogue entry whose SQL uses `$name` placeholders executes by binding a dict: natively in DuckDB adapters; translated `$name` → `%(name)s` in the Postgres/Supabase adapter (conservative regex `\$[A-Za-z_][A-Za-z0-9_]*`; take care not to mangle `$` inside string literals; note edge cases in the report). The positional `?` path must keep working unchanged for the AP catalogue. Choose and document the detection mechanism (presence of `$` placeholders, or an explicit catalogue field).

**T3 — Optional slots.** Add an optional-slot concept to routing/binding: a slot marked optional with no extracted value binds NULL — no pending-clarification stall. Required slots behave exactly as today. Find the minimal clean insertion point (`query_router/router.py`, `models.py`, `pending_resolver.py`).

**T4 — Caveat passthrough.** Add an optional caveat/answerability-note field to the catalogue entry schema, threaded through to the answer payload the API returns (for the LLM answer layer and frontend to surface). Additive — entries without it behave as today.

**T5 — Tests.** New tests in `Chatbot/tests/`: named-binding execution against a scratchpad-built temp `.duckdb`; the `$`→pyformat translation; optional-slot NULL binding vs required-slot stall; caveat passthrough. Re-run the full suite.

**T6 — Grep** the repo for hardcoded `backend` path segments (the source repo had `Chatbot/backend/`, now flattened) and stale AP path references; list findings in the report (fix only what your changes touch).

## Gate (definition of done)

1. Everything that passed at T0 baseline still passes.
2. All new tests pass.
3. Import smoke test succeeds (e.g. `python -c "import main"` from `Chatbot/` — no API calls; import-level is enough).

## Deliverables

- Logical commits as you go (baseline is already committed).
- `REPORT.md` at the repo root: what changed and why; baseline vs final test counts; the cache-table decision; the named-binding detection mechanism; `backend`-path findings; edge cases and open decisions for the operator.
