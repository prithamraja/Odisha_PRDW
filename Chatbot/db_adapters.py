"""
Database adapters — unified interface for Pandas, DuckDB, and Supabase (PostgreSQL).

Each adapter exposes:
  execute(sql, params=None) → DBResult
    .description   → list[str]  (column names)
    .fetchone()    → tuple | None
    .fetchmany(n)  → list[tuple]
    .fetchall()    → list[tuple]

`params` is either a LIST (positional `?` placeholders — the AP catalog) or a
DICT (named `$name` placeholders — the Odisha PR&DW catalogue). Every adapter
here is DuckDB-backed, so both bind natively; see query_router/sql_params.py for
how a catalogue entry's style is detected, and `PARAMSTYLE` below for what a
future non-DuckDB adapter would have to translate to.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DBResult:
    """Thin wrapper that stores all rows in-memory so the cursor can be closed."""

    def __init__(self, col_names: list[str], rows: list[tuple]):
        self._col_names = col_names
        self._rows = rows
        self._pos = 0

    @property
    def description(self) -> list[str]:
        return self._col_names

    def fetchone(self) -> tuple | None:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: int = 1) -> list[tuple]:
        end = min(self._pos + size, len(self._rows))
        chunk = self._rows[self._pos:end]
        self._pos = end
        return chunk

    def fetchall(self) -> list[tuple]:
        remaining = self._rows[self._pos:]
        self._pos = len(self._rows)
        return remaining


# ── DuckDB Adapter ────────────────────────────────────────────────────────────

class DuckDBAdapter:
    """Wraps a duckdb.DuckDBPyConnection."""

    PARAMSTYLE = "duckdb"   # binds `?` lists and `$name` dicts natively

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params: list[Any] | dict[str, Any] | None = None) -> DBResult:
        if params:
            rel = self._conn.execute(sql, params)
        else:
            rel = self._conn.execute(sql)
        col_names = [d[0] for d in rel.description]
        rows = rel.fetchall()
        return DBResult(col_names, rows)


# ── DuckDB file adapter (read-only .duckdb on disk) ───────────────────────────

class DuckDBFileAdapter:
    """A `.duckdb` file on disk, opened READ-ONLY, plus a writable scratch
    catalog for the router's cache tables.

    WHY THE FILE IS NEVER OPENED WRITABLE
        The Odisha analytical DB (`data/panchayat_1.duckdb`) lives in a
        Google Drive-synced folder. DuckDB writes a `.wal` alongside the
        database and memory-maps it; Drive's sync daemon rewriting either file
        underneath an open handle corrupts the database. Read-only opens create
        no WAL and take no write lock, which is the only safe mode there.

    THE CACHE-TABLE PROBLEM AND THE ATTACH INVERSION
        `sql/cache_tables.sql` creates `dashboard_cache` and `query_templates`,
        which startup.seed() then writes to — impossible in a read-only
        database. The obvious fix (open read-only, `ATTACH ':memory:'` for the
        cache tables) is not available: DuckDB refuses outright with
        "Cannot launch in-memory database in read-only mode".

        So the attachment is INVERTED. The connection itself is in-memory and
        writable; the analytical file is attached to it READ_ONLY:

            duckdb.connect(":memory:")
            ATTACH '<db_path>' AS analytics (READ_ONLY)
            SET search_path = 'memory.main,analytics.main'

        The result is that unqualified names resolve the way both bodies of SQL
        expect, with no rewriting of either:
          - cache tables are CREATEd and written in the in-memory catalog
            (unqualified CREATE targets the first search_path entry, so
            `memory.main` must come first);
          - the 19 base tables and the `v_*` views resolve through to the
            attached file;
          - DuckDB itself rejects any write aimed at the file, so read-only is
            enforced by the engine rather than by our own care.

        The cost of `memory.main` coming first is that an in-memory table would
        SHADOW a file table of the same name. Nothing collides today
        (`dashboard_cache`/`query_templates` against 19 domain tables), and
        `check_cache_table_collisions()` reports it loudly if that ever changes
        — a silently shadowed table would serve stale cache rows as if they were
        data.

    Thread safety: one connection behind a lock, as SupabaseAdapter does.
    """

    PARAMSTYLE = "duckdb"   # binds `?` lists and `$name` dicts natively

    DATA_ALIAS = "analytics"

    def __init__(self, db_path: Path, *, memory_limit: str = "512MB"):
        import duckdb
        import threading

        path = Path(db_path)
        if not path.exists():
            raise RuntimeError(
                f"DB_ENGINE=duckdb_file but no database at {path}. "
                "Set DB_PATH to the .duckdb file (relative paths resolve "
                "against the Chatbot/ directory)."
            )
        self.db_path = path.resolve()

        self._conn = duckdb.connect(":memory:")
        self._conn.execute(f"SET memory_limit = '{memory_limit}'")
        # Single-quote escaping: a path containing ' would otherwise break out
        # of the ATTACH string literal.
        literal = self.db_path.as_posix().replace("'", "''")
        self._conn.execute(
            f"ATTACH '{literal}' AS {self.DATA_ALIAS} (READ_ONLY)"
        )
        self._conn.execute(
            f"SET search_path = 'memory.main,{self.DATA_ALIAS}.main'"
        )
        self._lock = threading.Lock()

    def execute(self, sql: str, params: list[Any] | dict[str, Any] | None = None) -> DBResult:
        with self._lock:
            if params:
                rel = self._conn.execute(sql, params)
            else:
                rel = self._conn.execute(sql)
            # DML (INSERT/UPDATE/DELETE) — no result rows
            if rel.description is None:
                return DBResult([], [])
            col_names = [d[0] for d in rel.description]
            rows = rel.fetchall()
            return DBResult(col_names, rows)

    def execute_ddl(self, sql: str) -> None:
        """Run a DDL statement (CREATE TABLE, etc.) that returns no rows."""
        with self._lock:
            self._conn.execute(sql)

    def data_relations(self) -> list[str]:
        """Table and view names in the attached read-only file."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT table_name FROM duckdb_tables() WHERE database_name = ? "
                "UNION SELECT view_name FROM duckdb_views() WHERE database_name = ? "
                "ORDER BY 1",
                [self.DATA_ALIAS, self.DATA_ALIAS],
            ).fetchall()
        return [r[0] for r in rows]

    def check_cache_table_collisions(self) -> list[str]:
        """Names present in BOTH catalogs, where the in-memory one wins.

        Empty is the healthy answer. A non-empty list means a cache table is
        shadowing a domain table of the same name and queries against it are
        reading the cache instead of the data.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT table_name FROM duckdb_tables() WHERE database_name = 'memory' "
                "INTERSECT ("
                "  SELECT table_name FROM duckdb_tables() WHERE database_name = ? "
                "  UNION SELECT view_name FROM duckdb_views() WHERE database_name = ?"
                ") ORDER BY 1",
                [self.DATA_ALIAS, self.DATA_ALIAS],
            ).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# ── Pandas Adapter (default) ──────────────────────────────────────────────────

class PandasAdapter:
    """DuckDB in-memory backend. Loads each CSV as a DuckDB table on startup
    via read_csv_auto, then serves all queries from DuckDB's columnar memory.

    Historical note: this used to load CSVs into pandas DataFrames and then
    register DuckDB views over them. That doubled memory (pandas + view
    metadata) and made queries re-read CSVs from disk. The current version
    is ~3–4x smaller in RAM (DuckDB columnar storage) with no disk re-reads
    at query time — the name PandasAdapter is kept only to avoid breaking
    the factory import path.
    """

    PARAMSTYLE = "duckdb"   # binds `?` lists and `$name` dicts natively

    def __init__(self, data_dir: Path, tables: list[str]):
        import duckdb

        self._conn = duckdb.connect()  # pure in-memory, no file
        # Cap DuckDB's buffer pool so it doesn't balloon to 80% of container
        # RAM on a 1 GB Hobby instance. Working set for our queries stays
        # well under this; spills to disk if needed.
        self._conn.execute("SET memory_limit = '256MB'")
        self.dataframes: dict[str, object] = {}  # kept for backwards compat only

        for table in tables:
            # Prefer parquet (smaller, typed, faster to load). Fall back to
            # CSV so local dev against the raw ab_data/ directory still works.
            pq_path = data_dir / f"{table}.parquet"
            csv_path = data_dir / f"{table}.csv"
            if pq_path.exists():
                self._conn.execute(
                    f"CREATE TABLE {table} AS "
                    f"SELECT * FROM read_parquet('{pq_path.as_posix()}')"
                )
                self.dataframes[table] = True
            elif csv_path.exists():
                self._conn.execute(
                    f"CREATE TABLE {table} AS "
                    f"SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true)"
                )
                self.dataframes[table] = True

    def execute(self, sql: str, params: list[Any] | dict[str, Any] | None = None) -> DBResult:
        if params:
            rel = self._conn.execute(sql, params)
        else:
            rel = self._conn.execute(sql)
        # DML (INSERT/UPDATE/DELETE) — no result rows
        if rel.description is None:
            return DBResult([], [])
        col_names = [d[0] for d in rel.description]
        rows = rel.fetchall()
        return DBResult(col_names, rows)

    def execute_ddl(self, sql: str) -> None:
        """Run a DDL statement (CREATE TABLE, etc.) that returns no rows."""
        self._conn.execute(sql)


# ── Supabase / PostgreSQL Adapter ─────────────────────────────────────────────

class SupabaseAdapter:
    """Uses DuckDB as the query engine with Postgres as the storage backend.

    Rationale: the query catalog was written in DuckDB SQL dialect (DATE_DIFF,
    ROUND(double, int), DISTINCT in window functions, etc.), which plain
    Postgres cannot execute. Instead of rewriting hundreds of queries, we
    attach Postgres as an external database inside an in-process DuckDB
    instance via the postgres extension. DuckDB pulls the rows it needs and
    runs aggregations in its own columnar engine, so both the dialect
    mismatch and Postgres's temp-file disk pressure for large GROUP BYs
    disappear.

    Thread safety: we use a single DuckDB connection guarded by a lock.
    FastAPI's default thread pool is fine for demo-scale concurrency.

    PARAMSTYLE is "duckdb", not "pyformat", and that is not an oversight: the
    statement is parsed and bound by the in-process DuckDB engine, and only the
    scan of an already-planned query reaches Postgres. So `$name` dicts bind
    natively here too, and running the SQL through sql_params.to_pyformat()
    would BREAK it. The translation exists for a driver-level Postgres adapter
    (psycopg2, as in init_supabase.py) if one is ever added — see REPORT.md.
    """

    PARAMSTYLE = "duckdb"

    def __init__(self, database_url: str):
        import duckdb
        import threading

        # Railway's TCP proxy requires SSL; DuckDB's postgres extension does
        # not default to it, so force it on the URL if the caller omitted it.
        if "sslmode=" not in database_url:
            sep = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{sep}sslmode=require"
        self._url = database_url

        # Single-threaded: Railway's TCP proxy drops parallel DuckDB→Postgres
        # connections under heavy fan-out, which crashes mid-query. One
        # connection is plenty for demo throughput.
        self._conn = duckdb.connect(config={"threads": "1"})
        # Cap DuckDB's buffer pool so it doesn't balloon to 80% of container
        # RAM on a 1 GB Hobby instance. Working set for our queries stays
        # well under this; spills to disk if needed.
        self._conn.execute("SET memory_limit = '256MB'")
        self._conn.execute("INSTALL postgres")
        self._conn.execute("LOAD postgres")
        self._conn.execute(f"ATTACH '{database_url}' AS pg (TYPE postgres)")
        self._conn.execute("USE pg.public")

        self._lock = threading.Lock()

    def execute(self, sql: str, params: list[Any] | dict[str, Any] | None = None) -> DBResult:
        with self._lock:
            if params:
                rel = self._conn.execute(sql, params)
            else:
                rel = self._conn.execute(sql)
            # DML (INSERT/UPDATE/DELETE) — no result rows
            if rel.description is None:
                return DBResult([], [])
            col_names = [d[0] for d in rel.description]
            rows = rel.fetchall()
            return DBResult(col_names, rows)

    def execute_ddl(self, sql: str) -> None:
        """Run a DDL statement (CREATE TABLE, etc.) that returns no rows."""
        with self._lock:
            self._conn.execute(sql)
