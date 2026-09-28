"""WP-6d T1, migration M6: three rankings stop asking for a floor nobody states.

    python tools/migrations/m6_ranking_floor.py            # apply (idempotent)
    python tools/migrations/m6_ranking_floor.py --check    # exit 1 if not applied

SLOT DECLARATIONS ONLY. No SQL text changes; the Test Report counts are proved
before anything is written.

WHY (operator ruling, 2026-09-28). IMP-009, IMP-019 and IMP-020 end

    GROUP BY 1
    HAVING COUNT(*) >= $threshold
    ORDER BY <rate> ASC, …
    LIMIT $top_n

The HAVING is a small-denominator guard — "only rank groups with at least N
activities" — that the question text never mentions. The slot was required, the
router never defaults a threshold, so every "which focus area has the lowest
completion rate?" was asked "At least how many activities?", a number the
officer cannot know the meaning of. Ruled: no floor by default; show the bottom 10.

WHAT IT WRITES, on those three ids only (listed here, never matched by pattern):

  `$threshold`  "optional": True, "default": "1"  — beside WP-6c's derived
                `unit` / `direction`, which are kept. A default, not just
                optional: an absent optional binds NULL and `HAVING COUNT(*) >=
                NULL` drops every row. `COUNT(*) >= 1` is true of every group, so
                1 is exactly "no floor".
  `$top_n`      keeps "default": "10" and gains "superlative_means_one": False —
                the router keeps ten rows for a question worded in the singular
                (FY 2025-26: the bottom ten focus areas all sit at 0%, so one row
                would name the largest of the ties as though it were the answer).

`tools/derive_catalog.py` carries the same three ids (RANKING_FLOOR_DEFAULTS) and
refuses a default on any other threshold.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402

TARGETS = ("IMP-009", "IMP-019", "IMP-020")
FLOOR = {"optional": True, "default": "1"}


def _migrated(slot: dict) -> dict:
    """The slot as M6 declares it; any other slot comes back unchanged."""
    if slot["name"] == "threshold":
        out = {"name": slot["name"], "entity_type": slot["entity_type"], **FLOOR}
        # derive_catalog writes unit/direction last; keep them, in that place.
        out.update({k: v for k, v in slot.items() if k not in out})
        return out
    if slot["name"] == "top_n":
        return {**slot, "superlative_means_one": False}
    return slot


def rewrite(source: str) -> tuple[str, list[str]]:
    """(new source, the ids whose slot lines changed)."""
    lines = source.split("\n")
    changed = []
    for qid, start, end in dc._entry_spans(lines):
        if qid not in TARGETS:
            continue
        opened, closed = dc._find_block(lines, start, end, dc.SLOTS_OPEN, dc.SLOTS_CLOSE, qid)
        for k in range(opened + 1, closed):
            stripped = lines[k].strip()
            slot = ast.literal_eval(stripped[:-1] if stripped.endswith(",") else stripped)
            new = _migrated(slot)
            if new != slot or list(new) != list(slot):
                lines[k] = f"{dc._ITEM_PAD}{dc.py(new)},"
                changed.append(qid)
    return "\n".join(lines), sorted(set(changed))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 when the catalogue still needs M6")
    args = ap.parse_args()

    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    new_source, changed = rewrite(source)
    if args.check:
        if changed:
            print(f"M6 NOT applied: {', '.join(changed)}", file=sys.stderr)
            return 1
        print("M6 applied: " + ", ".join(TARGETS))
        return 0
    if not changed:
        print("M6 already applied — nothing to do")
        return 0

    before = dc.load_catalog(source, "TEMPLATE_CATALOG")
    after = dc.load_catalog(new_source, "TEMPLATE_CATALOG")
    for qid in TARGETS:
        if before[qid]["sql_template"] != after[qid]["sql_template"]:
            print(f"REFUSED {qid}: the SQL text changed", file=sys.stderr)
            return 1
        for slot in after[qid]["param_slots"]:
            if slot["name"] == "threshold" and ("unit" not in slot or "direction" not in slot):
                print(f"REFUSED {qid}: $threshold lost its unit/direction", file=sys.stderr)
                return 1

    # Prove before writing: the Test Report's recorded parameters still give its
    # row count, and the default floor gives every group (the bottom ten).
    from db_factory import open_analytical_db
    oracle = json.loads(dc.ORACLE_PATH.read_text(encoding="utf-8"))
    adapter = open_analytical_db(BACKEND / "data" / "panchayat_1.duckdb")
    try:
        for qid in TARGETS:
            sql = after[qid]["sql_template"]
            want = oracle[qid]
            params = {s["name"]: want["params"].get(s["name"]) for s in after[qid]["param_slots"]}
            params["date_range"] = [params["date_range"]]
            rows = adapter.execute(sql, params).fetchall()
            if len(rows) != want["rows"]:
                print(f"REFUSED {qid}: {len(rows)} rows with the Test Report's parameters "
                      f"{want['params']}, it says {want['rows']}", file=sys.stderr)
                return 1
            floor = adapter.execute(sql, {**params, "threshold": "1", "top_n": "10"}).fetchall()
            print(f"{qid}: Test Report ({want['params'].get('threshold')}, "
                  f"{want['params'].get('top_n')}) {len(rows)} rows = {want['rows']}; "
                  f"default floor 1 -> {len(floor)} rows")
    finally:
        adapter.close()

    dc.TEMPLATE_PATH.write_text(new_source, encoding="utf-8")
    print(f"wrote {', '.join(changed)} — now run tools/derive_catalog.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
