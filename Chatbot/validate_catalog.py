#!/usr/bin/env python3
"""
Execute every template in query_router/template_catalog.py against the live
backend and check it against the workbook's own answers.

    cd Chatbot
    python validate_catalog.py [--verbose] [--limit N]

This is the COMMAND-LINE form of tests/test_catalog_execution.py — same oracle,
same binds, same adapter — so that "the catalogue is valid" is a command with an
exit code rather than a judgement call. WP-5's gates file calls this.

WHAT IT CHECKS, per template
  1. binding      every declared slot has a `$name` in the statement and vice
                  versa, and the statement is detected as NAMED (decision D1)
  2. execution    it runs against the real DuckDB, through the real adapter,
                  with the seven v_* views created the way the app creates them
  3. row counts   the number of rows matches the workbook's Test Report sheet
                  at the sample parameters it recorded

WHY ROW COUNTS ARE AN EXACT CHECK
  SQL is deterministic. Routing is not — identical replays flip ~3% of questions
  and must never be regressed on a single miss — but nothing here goes near the
  router's LLM. A mismatch is a real defect every time: in the conversion from
  the workbook, in the D10 geography rewrite, or in the view wiring.

  It is also the only end-to-end check that the geography rewrite is SEMANTICALLY
  neutral. Every `$gp_name` predicate was moved off `gp_name` onto `gp_lgd_code`,
  and binding a name where a code is expected returns zero rows with no error
  anywhere — which is exactly what this catches, because the oracle records how
  many rows each query returned BEFORE the rewrite.

Exit code is 0 only if every template passes every check.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE_PATH = HERE / "tests" / "data" / "workbook_test_report.json"
DB_PATH = HERE / "data" / "panchayat_1.duckdb"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N templates (smoke check)")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    sys.path.insert(0, str(HERE))
    from dotenv import load_dotenv
    load_dotenv()

    from db_factory import open_analytical_db, VIEWS
    from query_router.entity_validator import EntityValidator
    from query_router.sql_params import NAMED, param_style
    from query_router.template_catalog import TEMPLATE_CATALOG, bind
    from tools.build_catalog import mask_literals

    if not args.db.exists():
        print(f"no database at {args.db}", file=sys.stderr)
        return 2
    if not ORACLE_PATH.exists():
        print(f"no oracle at {ORACLE_PATH} — run tools/build_catalog.py",
              file=sys.stderr)
        return 2

    oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    adapter = open_analytical_db(args.db)
    validator = EntityValidator(adapter)

    print(f"Database: {args.db}")
    for view in VIEWS:
        n = adapter.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        print(f"  {view:<12} {n:>8,} rows")

    missing = sorted(set(TEMPLATE_CATALOG) ^ set(oracle))
    if missing:
        print(f"\ncatalogue and oracle disagree on {len(missing)} ids: "
              f"{missing[:10]}", file=sys.stderr)
        return 1

    print(f"\nValidating {len(TEMPLATE_CATALOG)} templates ...")
    binding = execution = counts = 0
    ids = sorted(TEMPLATE_CATALOG)
    if args.limit:
        ids = ids[:args.limit]

    for qid in ids:
        template = TEMPLATE_CATALOG[qid]
        slots = template["param_slots"]
        declared = {s["name"] for s in slots}
        in_sql = set(re.findall(r"\$(\w+)", mask_literals(template["sql_template"])))

        if declared != in_sql or param_style(template) != NAMED:
            print(f"  BIND   {qid}  slots={sorted(declared)} sql={sorted(in_sql)} "
                  f"style={param_style(template)}")
            binding += 1
            continue

        # The Test Report binds GP NAMES; the rewritten SQL wants LGD codes.
        # Resolved through the real validator rather than a lookup of this
        # script's own, so a break in name->code resolution fails here too.
        code_bound = {s["name"] for s in slots if s.get("bind") == "code"}
        values = {}
        for name, value in oracle[qid]["params"].items():
            if value is not None and name in code_bound:
                resolved = validator.validate(str(value), name.replace("_name", ""))
                value = resolved.resolved_code or value
            values[name] = value

        try:
            sql, params = bind(qid, values)
            rows = adapter.execute(sql, params).fetchall()
        except Exception as exc:
            print(f"  EXEC   {qid}  {type(exc).__name__}: {exc}")
            execution += 1
            continue

        expected = oracle[qid]["rows"]
        if len(rows) != expected:
            print(f"  ROWS   {qid}  got {len(rows)}, Test Report says {expected}")
            counts += 1
        elif args.verbose:
            print(f"  ok     {qid:<14} {len(rows):>4} row(s)  "
                  f"{template['abstract_question'][:56]}")

    zero_row = sum(1 for q in ids if oracle[q]["rows"] == 0)
    total = binding + execution + counts
    print(f"\n{len(ids)} templates · {zero_row} legitimately return no rows")
    print(f"binding {binding} · execution {execution} · row counts {counts}")

    if total:
        print("\nEvery mismatch is a real defect — SQL is deterministic here.")
        return 1
    print("All clear.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
