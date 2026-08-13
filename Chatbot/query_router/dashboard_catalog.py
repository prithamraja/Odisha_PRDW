"""
Tier-1 dashboard queries — precomputed, parameter-free, served from dashboard_cache.

EMPTY FOR AP v1. The PM-JAY set was removed with the rest of the health-insurance
content; AP dashboards are a curated deliverable of a later phase, not a mechanical
port of the 278-template Ask catalog.

Everything downstream handles an empty catalog: startup.seed() writes zero
dashboard_cache rows, VectorRetriever indexes only the templates, and the router's
`query_id.startswith("D")` fast-path is simply never taken (no AP template id
starts with "D").

Each entry, once they exist, is: question (natural language) + sql (no parameters).
"""

DASHBOARD_CATALOG: dict[str, dict] = {}
