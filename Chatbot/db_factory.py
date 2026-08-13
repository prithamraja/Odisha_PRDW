"""
Database factory — picks the right backend adapter from env config.

Env vars:
  DB_ENGINE      = "pandas" (default) | "supabase" | "duckdb_file"
  DATABASE_URL   = required when DB_ENGINE=supabase  (e.g. postgresql://user:pass@host:5432/db)
  DB_PATH        = required when DB_ENGINE=duckdb_file — path to the .duckdb file.
                   Relative paths resolve against Chatbot/, exactly like DATA_DIR,
                   so `DB_PATH=data/panchayat_1.duckdb` means the same thing to
                   pytest, `python startup.py` and uvicorn.

"pandas" remains the default: an unset DB_ENGINE behaves exactly as it did
before duckdb_file existed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

try:
    from .db_adapters import DuckDBFileAdapter, PandasAdapter, SupabaseAdapter
except ImportError:
    from db_adapters import DuckDBFileAdapter, PandasAdapter, SupabaseAdapter

_log = logging.getLogger(__name__)

# ── Shared constants ─────────────────────────────────────────────────────────

# Default: the Parquet stub the backend ships with, so a fresh clone boots
# without any data drop. Override with DATA_DIR when the real flat Parquet
# files live elsewhere (cutover: DATA_DIR=<repo>/RTGS_Data/flat).
_backend_dir = Path(__file__).resolve().parent
_default_data_dir = _backend_dir / "stub_data"
# A relative DATA_DIR is resolved against backend/, not the CWD, so `python
# startup.py`, pytest from the repo root and uvicorn all read the same folder.
_configured = os.environ.get("DATA_DIR")
DATA_DIR = (
    Path(_configured) if _configured and Path(_configured).is_absolute()
    else (_backend_dir / _configured) if _configured
    else _default_data_dir
).resolve()

# One flat table per AP departmental dataset — the data contract the template
# catalog is written against. PandasAdapter looks for <table>.parquet (preferred)
# or <table>.csv in DATA_DIR.
TABLES = [
    "pm_kisan",
    "agriculture",
    "horticulture_apmip",
    "fisheries",
    "sericulture",
    "markfed",
    "ryss",
    "survey_land_records",
]

def _resolve_db_path(configured: str) -> Path:
    """DB_PATH → an absolute path, relative entries anchored at Chatbot/."""
    path = Path(configured)
    return path.resolve() if path.is_absolute() else (_backend_dir / path).resolve()


def _seed_cache_tables(adapter) -> None:
    """Create the router's cache tables from sql/cache_tables.sql."""
    ddl_path = Path(__file__).parent / "sql" / "cache_tables.sql"
    if not ddl_path.exists():
        return
    import re
    cleaned = re.sub(r'--[^\n]*', '', ddl_path.read_text())
    for stmt in cleaned.split(";"):
        stmt = stmt.strip()
        if stmt:
            adapter.execute_ddl(stmt)


_adapter: PandasAdapter | SupabaseAdapter | DuckDBFileAdapter | None = None


def get_adapter() -> PandasAdapter | SupabaseAdapter | DuckDBFileAdapter:
    """Singleton factory — creates the adapter on first call."""
    global _adapter
    if _adapter is not None:
        return _adapter

    engine = os.environ.get("DB_ENGINE", "pandas").lower()

    if engine == "duckdb_file":
        configured = os.environ.get("DB_PATH", "")
        if not configured:
            raise RuntimeError(
                "DB_ENGINE=duckdb_file but DB_PATH is not set. "
                "Add it to your .env (e.g. DB_PATH=data/panchayat_1.duckdb)."
            )
        db_path = _resolve_db_path(configured)
        _adapter = DuckDBFileAdapter(db_path)

        # Cache tables land in the adapter's writable in-memory catalog — the
        # analytical file is attached read-only and could not hold them. See
        # DuckDBFileAdapter's docstring for why the attachment is inverted.
        _seed_cache_tables(_adapter)

        shadowed = _adapter.check_cache_table_collisions()
        if shadowed:
            _log.error(
                "[db] cache tables shadow relations in %s: %s — queries against "
                "these names read the cache, not the data",
                db_path.name, ", ".join(shadowed),
            )

        relations = _adapter.data_relations()
        print(
            f"[db] Using DuckDB file {db_path} (read-only, "
            f"{len(relations)} tables/views; cache tables in-memory)"
        )
        return _adapter

    if engine == "supabase":
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise RuntimeError(
                "DB_ENGINE=supabase but DATABASE_URL is not set. "
                "Add it to your .env or environment variables."
            )
        _adapter = SupabaseAdapter(url)

        # Ensure cache tables exist on first connect
        _seed_cache_tables(_adapter)

        print(f"[db] Using Supabase (PostgreSQL) backend")
        return _adapter

    # ── Pandas + DuckDB in-memory (default) ──────────────────────────────────
    _adapter = PandasAdapter(DATA_DIR, TABLES)

    # Ensure cache tables exist
    _seed_cache_tables(_adapter)

    print(f"[db] Loaded {len(_adapter.dataframes)}/{len(TABLES)} tables from {DATA_DIR} (DuckDB in-memory)")
    return _adapter
