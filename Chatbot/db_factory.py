"""
Database factory — picks the right backend adapter from env config.

Env vars:
  DB_ENGINE      = "pandas" (default) | "supabase"
  DATABASE_URL   = required when DB_ENGINE=supabase  (e.g. postgresql://user:pass@host:5432/db)
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from .db_adapters import PandasAdapter, SupabaseAdapter
except ImportError:
    from db_adapters import PandasAdapter, SupabaseAdapter

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

_adapter: PandasAdapter | SupabaseAdapter | None = None


def get_adapter() -> PandasAdapter | SupabaseAdapter:
    """Singleton factory — creates the adapter on first call."""
    global _adapter
    if _adapter is not None:
        return _adapter

    engine = os.environ.get("DB_ENGINE", "pandas").lower()

    if engine == "supabase":
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise RuntimeError(
                "DB_ENGINE=supabase but DATABASE_URL is not set. "
                "Add it to your .env or environment variables."
            )
        _adapter = SupabaseAdapter(url)

        # Ensure cache tables exist on first connect
        ddl_path = Path(__file__).parent / "sql" / "cache_tables.sql"
        if ddl_path.exists():
            import re
            raw = ddl_path.read_text()
            cleaned = re.sub(r'--[^\n]*', '', raw)
            for stmt in cleaned.split(";"):
                stmt = stmt.strip()
                if stmt:
                    _adapter.execute_ddl(stmt)

        print(f"[db] Using Supabase (PostgreSQL) backend")
        return _adapter

    # ── Pandas + DuckDB in-memory (default) ──────────────────────────────────
    _adapter = PandasAdapter(DATA_DIR, TABLES)

    # Ensure cache tables exist
    ddl_path = Path(__file__).parent / "sql" / "cache_tables.sql"
    if ddl_path.exists():
        import re
        raw = ddl_path.read_text()
        cleaned = re.sub(r'--[^\n]*', '', raw)
        for stmt in cleaned.split(";"):
            stmt = stmt.strip()
            if stmt:
                _adapter.execute_ddl(stmt)

    print(f"[db] Loaded {len(_adapter.dataframes)}/{len(TABLES)} tables from {DATA_DIR} (DuckDB in-memory)")
    return _adapter
