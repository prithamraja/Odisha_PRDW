# WP-1 — Engine extensions: implementation report

**Brief:** `handoffs/WP1_engine_extensions.md`
**Date:** 2026-08-13
**Scope delivered:** T0–T6 complete. Generic engine only — no domain content added.
**Gate:** all three conditions met (§2).

---

## 1. Commits

| Commit | Contents |
|---|---|
| `55c5a76` | T1 + `sql_params.py`: read-only DuckDB file adapter, `DB_ENGINE=duckdb_file`, parameter-style module |
| `0039106` | T2/T3/T4: named binding, optional slots, caveat passthrough |
| `26ddef5` | T5: 48 new tests |

Baseline `7184d5e` / `25d654d` untouched. `Chatbot/.env` never opened, never staged.
`Chatbot/data/panchayat_1.duckdb` never opened writable — verified no `.wal` or other
file appeared beside it at any point.

## 2. Gate

| # | Condition | Result |
|---|---|---|
| 1 | Everything green at T0 is still green | **Yes** — 245 → 245, identical skip/error sets |
| 2 | All new tests pass | **Yes** — 48/48 |
| 3 | Import smoke test | **Yes** — `python -c "import main"` OK, no API calls |

### Test counts, baseline vs final

| | T0 baseline | Final | Δ |
|---|---|---|---|
| passed | 245 | **293** | +48 (new tests) |
| skipped | 32 | 32 | — |
| errors | 17 | 17 | — |
| subtests passed | 33 | 33 | — |
| **failed** | **0** | **0** | — |

All 17 errors and 32 skips have one pre-existing environmental cause: the AP flat-Parquet
drop (`RTGS_Data/flat/*.parquet`) is not present in this repo. Recorded, not fixed, per the
brief. The 17 in `test_name_collisions.py` error rather than skip because its `_connect()`
has no existence guard, unlike the three endpoint suites which skip cleanly.

### A baseline-integrity problem found before any change

The first T0 run was **not trustworthy** and its numbers should be disregarded in favour of
the re-run. `Chatbot/query_router/__pycache__`, `Chatbot/tests/__pycache__` and
`Chatbot/.pytest_cache` had been copied in from the source repo with mtimes intact, so
Python's `.pyc` validation passed and it executed **bytecode compiled from
`Dontuse_Decision_Aids\Chatbot\backend\`** rather than the files in this repo. Confirmed by
reading `co_filename` out of the cached bytecode:

```
tests/__pycache__/test_date_phrase_endpoint.cpython-314-pytest-9.1.1.pyc
  co_filename: I:\...\Dontuse_Decision_Aids\Chatbot\backend\tests\test_date_phrase_endpoint.py
```

Caches were deleted and the baseline re-established; the numbers happened to be identical
(245/32/17/33), so nothing downstream is affected. All caches are gitignored, so nothing was
committed. **Worth knowing for every future agent run in this tree: a fresh copy of a Python
repo onto Drive carries executable stale bytecode. Delete `__pycache__` and `.pytest_cache`
before trusting a first test run.** This is the most consequential of the T6 findings.

---

## 3. T1 — DuckDB file adapter

`DuckDBFileAdapter` in `Chatbot/db_adapters.py`, same interface as `PandasAdapter` /
`SupabaseAdapter` (`execute`, `execute_ddl`), plus `data_relations()`,
`check_cache_table_collisions()` and `close()`. Wired as `DB_ENGINE=duckdb_file` with
`DB_PATH`; relative paths resolve against `Chatbot/`, exactly like `DATA_DIR`.
`.env.example` documents both (commented out). `.env` untouched. An unset `DB_ENGINE` still
selects `pandas` and behaves precisely as before.

### The cache-table decision, and why the obvious design is unavailable

`sql/cache_tables.sql` creates `dashboard_cache` and `query_templates`, which
`startup.seed()` then writes to — impossible inside a read-only database. The brief offered
two options; the first turns out **not to exist**:

> `duckdb.connect(path, read_only=True)` then `ATTACH ':memory:' AS cache_db`
> → `CatalogException: Cannot launch in-memory database in read-only mode!`

Read-only applies to the whole DuckDB instance, not just the file, so a read-only connection
cannot host a writable attachment at all.

**Chosen: invert the attachment.** The connection is an in-memory database; the analytical
file is attached *to it* read-only:

```
duckdb.connect(":memory:")
ATTACH '<db_path>' AS analytics (READ_ONLY)
SET search_path = 'memory.main,analytics.main'
```

This keeps **full cache-table seeding** — nothing is skipped, no log-line-and-degrade — while
neither body of SQL needs rewriting:

- cache tables are created and written unqualified in the writable in-memory catalog;
- the 19 base tables **and views** resolve unqualified through to the attached file
  (verified against a view in the test fixture, since the seven `v_*` views are absent from
  the shipped sample);
- **DuckDB itself refuses any write aimed at the file** — `InvalidInputException: Cannot
  execute statement of type "CREATE"/"INSERT" on database "analytics" which is attached in
  read-only mode`. Read-only is enforced by the engine, not by our own discipline. Asserted
  in `test_the_attached_file_refuses_writes`.

**The one cost, and its guard.** Unqualified `CREATE` targets the *first* `search_path`
entry, so `memory.main` must come first — which means an in-memory table would **shadow** a
file table of the same name. Nothing collides today (2 cache tables vs 19 domain relations),
and `check_cache_table_collisions()` returns the intersection, which `db_factory` logs at
ERROR on startup. A silently shadowed table would serve cache rows as if they were data,
which is why this is checked rather than assumed.

Verified against the real database (read-only): 19 relations, 0 collisions, cache table
writable, `$name` binding native, both write attempts refused, no stray files created.

## 4. T2 — Named-parameter execution

### Detection mechanism

Two layers, in `query_router/sql_params.py`:

1. **Explicit override wins:** a `"param_style": "named" | "positional"` key on the
   catalogue entry. An invalid value raises rather than defaulting.
2. **Otherwise sniffed from the SQL:** NAMED if at least one `$name` placeholder occurs
   **outside string literals and comments**, else POSITIONAL.

Sniffing is what keeps the change additive: no AP entry carries `param_style` and none
contains a `$` placeholder, so all 278 resolve to POSITIONAL and take a byte-identical path.
Requiring an explicit key would have meant editing all 278 entries — 278 chances to typo the
key on an entry whose SQL is already signed off. The override exists for the case the
sniffer gets wrong; the guarded literal/comment masking means I know of no such case today.

Every function masks literals (`'...'` with `''` escapes), `--` and `/*...*/` comments, and
`$$...$$` blocks to same-length filler before matching, so offsets still index the original
and `WHERE note = 'costs $5'` is neither counted nor rewritten.

### Binding

`bind_named_params()` returns `{name: value}` with **one entry per slot NAME**, however many
times the name occurs in the statement — which is the entire point, since the PR&DW idiom
`($p IS NULL OR col = $p)` repeats every parameter. `bind_for_template()` dispatches on
style; `bind_param_values()` keeps its old signature and behaviour. `position` is required
for positional slots and ignored for named ones.

### Two consequences the named path forced into the open

Both were latent bugs that would have shipped silently:

1. **Date-filter placeholder style.** DuckDB will not mix `?` and `$name` in one prepared
   statement, so an injected date predicate must match the statement it is spliced into.
   `_date_predicate` / `_inject_date_filter` now take `named=`, emitting
   `$__date_start` / `$__date_end` with a dict (double underscore, so they cannot collide
   with a Parameter Registry bind name). Positional injection, including the load-bearing
   `LIMIT ?` splice offset, is unchanged.
2. **Result-cache fingerprint.** `_exec_template` hashed `[str(p) for p in param_values]`.
   Iterating a **dict yields its keys**, so every district asked would have produced the
   same fingerprint and the second would have been served the first one's rows — a
   wrong-answer bug with no error. `_param_cache_fingerprint()` hashes sorted key/value
   pairs for dicts, and is unchanged for lists (AP cache keys are bit-identical).
   Regression-tested in `test_two_different_binds_do_not_share_a_cache_entry`.

### The `$name` → `%(name)s` translation — and an open decision

`to_pyformat()` is implemented and tested (7 cases), including doubling every literal `%` to
`%%`. That matters more than it looks: the SBM bracket is 86 keyword-matching queries full of
`LIKE '%toilet%'`, and an un-doubled `%` makes a pyformat driver raise "unsupported format
character" or consume the following characters as a format spec. The test asserts the output
is a valid Python format string, which is the same machinery psycopg2 binds through.

**It is deliberately NOT wired into `SupabaseAdapter`, because the brief's premise about that
adapter does not hold.** `SupabaseAdapter` is not psycopg2-backed: it runs an in-process
DuckDB with the `postgres` extension and `ATTACH ... (TYPE postgres)`, so statements are
parsed and bound by **DuckDB** and only an already-planned scan reaches Postgres. `$name`
dicts therefore bind natively there too, and translating would **break** a working path.
`psycopg2` appears only in `init_supabase.py`, an offline loader. (`template_catalog.to_postgres()`,
which rewrites `?`→`$1`, is dead code — defined, never called.)

Each adapter now declares `PARAMSTYLE` (all `"duckdb"` today) so the assumption is written
down rather than inferred. **Operator decision needed:** keep `to_pyformat()` as a tested
utility for a future driver-level Postgres adapter (what I did), or drop it as unused. I
kept it because T2/T5 asked for it and it is the correct code if that adapter is ever added.

## 5. T3 — Optional slots

A slot marked `{"optional": True}` binds SQL NULL when nothing was extracted, and
`_fill_slots_or_clarify` does not report it missing — no pending-clarification stall. Three
minimal insertion points:

- `optional_slots()` reads the flag off the slot dicts, so nothing extra has to be threaded
  through the call graph;
- `_check_required()` + `_resolve_slot_value()` are shared by both binders, so the positional
  and named paths cannot drift on which slot binds what;
- `_fill_slots_or_clarify` takes a keyword-only `optional=frozenset()`, passed by both
  callers. Defaulting to empty is what keeps `test_pending_clarification.py`'s 7-positional-arg
  calls working untouched.

Required slots are unchanged: absent still means pause and ask, never execute broken SQL.

**One judgement worth flagging:** a *supplied* optional value is still fully validated. If
the user says "Kendrapara" and the registry doesn't know it, the engine clarifies rather than
binding NULL. Binding NULL there would answer **state-wide** and present it as the district
the user asked for — the same confidently-wrong class the caveats exist to prevent.
Pinned in `test_a_supplied_optional_value_is_still_validated`.

## 6. T4 — Caveat passthrough

`RouteResult.caveat` → `QueryResponse.caveat`, read from the entry's `caveat` key. Additive:
`None` for entries without it, so every AP entry behaves as before.

Attached on **all three** paths that serve catalogue rows, not just the routed one:

- `/query` — via `_serve_query_id` (Tier-2 from the template, Tier-1 from `DASHBOARD_CATALOG`);
- `/context/pop` and `/operation` — via `_catalog_caveat()`, since these serve rows without
  re-routing. A caveat is a property of the question the rows answer, so a breadcrumb back or
  a top-N recomputation must not turn a caveated answer into an uncaveated one.

Kept a **separate field** rather than appended to `answer`: the answer text is regenerated by
the LLM layer, and a caveat glued into it can be paraphrased away or lost. The frontend and
answer layer are responsible for surfacing it — WP-3 should treat "renders `caveat` when
present" as a requirement, since 251/363 questions carry one.

## 7. T6 — `backend`-path and stale-AP-path findings

Nothing here was fixed: none of it is touched by my changes (per the brief). Listed by
severity.

**1. Stale bytecode from `Chatbot/backend/` — real, and it already affected a test run.**
See §2. Delete `__pycache__`/`.pytest_cache` after any fresh copy of this tree.

**2. Test data paths are off by one directory since the flattening — latent landmine.**
Four test modules compute `_BACKEND = Path(__file__).resolve().parents[1]` then
`_BACKEND.parents[1] / "RTGS_Data" / "flat"`. Under the old `Chatbot/backend/tests/` layout
that resolved to the repo root; flattened to `Chatbot/tests/`, it now resolves **one level
above the repo**:

```
resolves to : I:\My Drive\ASC Lab\LMIC AI Code repo\RTGS_Data\flat   (outside Odisha_PRDW)
would be    : I:\...\Odisha_PRDW\RTGS_Data\flat
```

Harmless today only because neither path exists. But `LMIC AI Code repo\` is the shared
parent holding every sibling project, so if an `RTGS_Data\` drop ever lands there, these AP
suites would silently start executing against **AP data from outside this repo**. Same
off-by-one in `run_consistency_eval.py:23`, `run_custom_eval.py:18`, `run_full_eval.py:20`
(`HERE.parent.parent / "RTGS_Data" / "flat"`) and `init_supabase.py:34`
(`parent.parent.parent / "ab_data"`). Affected test files:
`test_context_window_endpoint.py:16-17`, `test_date_phrase_endpoint.py:17-18`,
`test_followup_fragment.py:40-41`, `test_extraction_enums.py:37`.

**3. `test_name_collisions.py:56`** defaults `DATA_DIR` to the **CWD-relative** string
`"RTGS_Data/flat"` with no existence guard — the cause of all 17 baseline errors, and
CWD-dependent besides.

**4. `backend` in docs/usage strings only** (harmless, but stale instructions):
`init_supabase.py:4` and `startup.py:4` say `cd backend`; `pmkisan_gates.py:5`,
`recall_eval.py:11`, `rerank_eval.py:14`, `validate_catalog.py:22` say `cd Chatbot/backend`.
`db_factory.py`'s `_backend_dir` variable and comments still say "backend" — correct
behaviour (it means "the directory this file lives in"), stale name.

**5. `Chatbot/stub_data/` does not exist**, though it is `DATA_DIR`'s default. The default
`pandas` engine therefore loads 0 of 8 tables. Pre-existing and expected — the AP stub is
built by `build_stub_data.py` from an AP workbook this repo doesn't carry. It is why
`DB_ENGINE=duckdb_file` matters for WP-3 onward.

---

## 8. Edge cases and open decisions for the operator

**Decisions I'd like a ruling on:**

1. **`to_pyformat()`'s status** — keep as a tested utility for a future psycopg2 adapter, or
   drop as unused? See §4. My recommendation: keep.
2. **Optional-slot semantics in the *retrieval* layers.** T3 covered routing and binding, the
   minimal clean insertion point. Four modules still read `param_slots` as if every slot were
   required, and WP-3/WP-4 will meet them: `reranker.py:65` (advertises a template's
   filterable slots to the rerank model), `suggestions.py:63` and `followup_classifier.py:33`
   (follow-up chip slots), `fragment_reroute.py:46` (geo slots), and `router._scope_sibling`
   (`needed <= frame.bound_params`, an AP `-S/-D/-M` mechanism that D2's consolidated
   templates make moot). None is wrong today; all deserve a look once real optional slots
   exist. **Suggest scoping this into WP-3.**
3. **Date filtering for PR&DW** is implemented for named SQL but unexercised by real content:
   the workbook binds fiscal year as an ordinary `$fin_year` parameter rather than through
   `date_filter`. If WP-3 keeps it that way, `date_kind` never fires for Odisha. Worth
   confirming, because `date_kind: "year"` compares against **integers** and Odisha's
   `fin_year` is the `'2024-2025'` **string** — a `date_filter` on `fin_year` would raise a
   binder error (I hit exactly this writing the tests).

**Edge cases, documented in code:**

4. **Tagged dollar quoting `$tag$...$tag$` is genuinely ambiguous** with `$name` parameters —
   an opening `$tag$` is indistinguishable from `$tag` followed by `$`. It is not masked;
   `to_pyformat()` logs a warning instead of mangling it silently. No catalogue SQL uses it,
   and WP-3 should keep it that way (ordinary `'...'` literals).
5. **`_inject_date_filter` counts `?` with `str.count("?")`**, not the literal-masked
   counter, so a `?` inside a string literal in a *positional* template would shift the
   splice offset. Pre-existing; deliberately left alone rather than risk changing AP
   behaviour. `sql_params.positional_count()` is the corrected version if it's ever wanted.
6. **Cache-table shadowing** — guarded and logged, see §3.
7. **Test fixtures build a fresh `.duckdb` in `tempfile.mkdtemp()`**, never in the repo and
   never on Drive. `test_named_binding.py` includes a view, so the `v_*` resolution path is
   covered before `create_views.sql` arrives.

**Still blocking downstream (unchanged by WP-1, as the brief said):** `create_views.sql` —
the seven `v_*` views remain absent; the adapter confirms 19 relations. WP-3's execution gate
needs them.
