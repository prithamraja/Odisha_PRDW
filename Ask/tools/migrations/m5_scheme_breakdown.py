"""WP-6c T2, migration M5: the four tied/untied statements can answer per scheme.

    python tools/migrations/m5_scheme_breakdown.py            # apply
    python tools/migrations/m5_scheme_breakdown.py --dry-run  # print, write nothing

ONE-SHOT, like M1-M4: run once against `query_router/template_catalog.py`, diff
reviewed, committed; the file is hand-edited from then on.

WHY (pilot feedback, 2026-09-28; operator ruling the same day, lifting the
WP-6c brief's "no SQL change" for these four only). "Split the sanctioned funds
into SFC and Own Funds" is retrieved onto the statements that report the tied /
untied split — BUD-003, BUD-005, EXP-008, FND-001 — and none of them could give
one row per scheme: M2 left them alone (a window function, or a two-column
GROUP BY), so they carry no `$group_by`. The WP-6 T4 rule "a list of values is a
comparison: group by that dimension" therefore had nothing to switch.

WHAT IT DOES. The statement's first column, `v.tied_untied`, becomes

    CASE $group_by
      WHEN 'scheme' THEN v.scheme_name
      ELSE v.tied_untied  -- absent: tied_untied
    END AS group_label

and FND-001's second column, `v.fund_component_name`, becomes
`CASE WHEN $group_by IS NULL THEN v.fund_component_name END`, so a per-scheme
answer is not split again by component. The GROUP BY is by position already.

SCHEME ONLY, BY RULING. Every other breakdown would replace the tied/untied
column these four questions exist to show — "district-wise tied and untied
funds" would come back as district totals with no split at all — so they keep
today's behaviour: `breakdown.drop_unsupported` drops any other value and the
statement answers as signed off.

ABSENT IS UNCHANGED BY CONSTRUCTION: `$group_by` NULL takes the ELSE. Each
statement is executed with its Test Report parameters before anything is
written, and the row count must match.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402
from tools.migrations.m2_group_by import replace_entry_sql  # noqa: E402

TARGETS = ("BUD-003", "BUD-005", "EXP-008", "FND-001")

PRIMARY = "SELECT v.tied_untied,"
PRIMARY_NEW = [
    "SELECT CASE $group_by",
    "                WHEN 'scheme'       THEN v.scheme_name",
    "                ELSE v.tied_untied  -- absent: tied_untied",
    "              END AS group_label,",
]
SECONDARY = "v.fund_component_name,"
SECONDARY_NEW = "CASE WHEN $group_by IS NULL THEN v.fund_component_name END AS fund_component_name,"


def rewrite(qid: str, sql: str) -> list[str]:
    lines = sql.strip("\n").split("\n")
    first = lines[0]
    if not first.startswith(PRIMARY):
        raise RuntimeError(f"{qid}: expected the statement to open {PRIMARY!r}, got {first!r}")
    rest = first[len(PRIMARY):].strip()
    if rest:
        if qid != "FND-001" or rest != SECONDARY:
            raise RuntimeError(f"{qid}: unexpected first line {first!r}")
        return [*PRIMARY_NEW[:-1], PRIMARY_NEW[-1] + " " + SECONDARY_NEW, *lines[1:]]
    return [*PRIMARY_NEW, *lines[1:]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    catalog = dc.load_catalog(source, "TEMPLATE_CATALOG")
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))

    for qid in TARGETS:
        if any(s["name"] == "group_by" for s in catalog[qid]["param_slots"]):
            print(f"{qid}: already has $group_by — nothing to do", file=sys.stderr)
            return 1
        new = rewrite(qid, catalog[qid]["sql_template"])
        print(f"--- {qid}\n" + "\n".join(new[:5]) + "\n")
        source = replace_entry_sql(source, qid, new)
        oracle[qid]["params"]["group_by"] = None

    # Prove before writing: absent reproduces the Test Report; 'scheme' executes.
    from db_factory import open_analytical_db
    adapter = open_analytical_db(BACKEND / "data" / "panchayat_1.duckdb")
    migrated = dc.load_catalog(source, "TEMPLATE_CATALOG")
    try:
        for qid in TARGETS:
            want = oracle[qid]
            params = {s["name"]: want["params"].get(s["name"])
                      for s in migrated[qid]["param_slots"]}
            params["date_range"] = [params["date_range"]]
            rows = adapter.execute(migrated[qid]["sql_template"], params).fetchall()
            if len(rows) != want["rows"]:
                print(f"REFUSED {qid}: {len(rows)} rows absent, the Test Report says "
                      f"{want['rows']}", file=sys.stderr)
                return 1
            per_scheme = adapter.execute(migrated[qid]["sql_template"],
                                         {**params, "group_by": "scheme"}).fetchall()
            print(f"{qid}: absent {len(rows)} rows = the Test Report's {want['rows']}; "
                  f"per scheme {len(per_scheme)} rows")
    finally:
        adapter.close()

    if args.dry_run:
        return 0
    dc.TEMPLATE_PATH.write_text(source, encoding="utf-8")
    dc.ORACLE_PATH.write_text(json.dumps(oracle, indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
    print("wrote the catalogue and the oracle — now run tools/derive_catalog.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
