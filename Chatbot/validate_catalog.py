#!/usr/bin/env python3
"""
Exercise every template in query_router/template_catalog.py against the live
backend: the same tables db_factory.TABLES declares, loaded by the same adapter
the router executes through, with the date predicate appended by the same
router function.

This is the integrated version of the catalog author's validator. The original
built its own throwaway SQLite from the workbook's demo tabs; running through
db_factory.get_adapter() instead means the check covers the DuckDB dialect, the
Parquet column types and the router's real _inject_date_filter — the three
places a template can pass on SQLite and still fail in production.

Four checks per template:
  1. placeholder arity — the number of ? matches len(param_slots)
  2. positional binding — the query executes with demo values bound in slot order
  3. emptiness — the result matches expected_empty_on_demo
  4. date composability — for templates with a date_filter, the query still runs
     once the runtime's date predicate is appended, with its own parameters bound

Usage:
    cd Chatbot/backend
    python validate_catalog.py [--verbose] [--skip-emptiness]

DATA_DIR selects the data (default: the shipped 10-row Parquet stub). Exit code
is 0 only if every check passes for every template.
"""
import argparse
import os
import sys

# Demo date window, wide enough to keep every demo row in scope so the date
# check tests composability rather than re-testing emptiness.
DATE_FROM, DATE_TO = "2020-01-01", "2030-12-31"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--skip-emptiness", action="store_true",
        help="only check that every template runs; ignore expected_empty_on_demo "
             "(use when DATA_DIR points at data other than the demo extract)",
    )
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dotenv import load_dotenv
    load_dotenv()

    from db_factory import get_adapter, DATA_DIR, TABLES
    from query_router.router import (
        _inject_date_filter, bind_param_values, merge_date_params,
    )
    from query_router.template_catalog import ALL_TEMPLATES, ENTITY_TYPES

    adapter = get_adapter()
    print(f"Data: {DATA_DIR}")
    for table in TABLES:
        try:
            n = adapter.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            cols = len(adapter.execute(f'SELECT * FROM "{table}" LIMIT 0').description)
            print(f"  {table:<22} {cols:>4} columns {n:>6} rows")
        except Exception as exc:
            print(f"  {table:<22} MISSING: {exc}")

    print(f"\nValidating {len(ALL_TEMPLATES)} templates ...")
    arity = binding = emptiness = dates = 0

    for tid, t in sorted(ALL_TEMPLATES.items()):
        sql = t["sql_template"]
        slots = t["param_slots"]

        if sql.count("?") != len(slots):
            print(f"  ARITY  {tid}  {sql.count('?')} placeholders vs {len(slots)} slots")
            arity += 1
            continue

        values = {s["name"]: ENTITY_TYPES[s["entity_type"]]["demo"] for s in slots}
        params = bind_param_values(slots, values)
        try:
            rows = adapter.execute(sql, params).fetchall()
        except Exception as exc:
            print(f"  BIND   {tid}  {exc}")
            binding += 1
            continue

        if not args.skip_emptiness and (len(rows) == 0) != t["expected_empty_on_demo"]:
            state = "now returns rows" if t["expected_empty_on_demo"] else "now returns nothing"
            print(f"  FLIP   {tid}  {state}: {t['abstract_question']}")
            emptiness += 1
        elif args.verbose:
            print(f"  ok     {tid:<10} {len(rows):>3} row(s)  {t['abstract_question'][:56]}")

        if t["date_filter"]:
            try:
                dated_sql, offset, date_params = _inject_date_filter(
                    sql, t["date_filter"]["alias"], t["date_filter"]["column"],
                    t.get("date_kind"), start_date=DATE_FROM, end_date=DATE_TO,
                )
                adapter.execute(dated_sql, merge_date_params(params, offset, date_params))
            except Exception as exc:
                print(f"  DATE   {tid}  predicate does not compose: {exc}")
                dates += 1

    total = arity + binding + emptiness + dates
    n_slots = sum(1 for t in ALL_TEMPLATES.values() if t["param_slots"])
    n_dated = sum(1 for t in ALL_TEMPLATES.values() if t["date_filter"])
    print(f"\n{len(ALL_TEMPLATES)} templates · {n_slots} parameterised · {n_dated} date-filtered")
    print(f"arity {arity} · binding {binding} · emptiness {emptiness} · date composability {dates}")

    if total:
        print("\nFix the templates above, or update expected_empty_on_demo if the data changed.")
        sys.exit(1)
    print("All clear.")


if __name__ == "__main__":
    main()
