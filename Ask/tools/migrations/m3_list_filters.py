"""WP-6 T4, migration M3: list-valued filters and multi-year spans.

    python tools/migrations/m3_list_filters.py            # apply, print decisions
    python tools/migrations/m3_list_filters.py --dry-run  # decisions only

ONE-SHOT, like M1 and M2. A pure textual substitution of two fixed idioms:

    ($slot IS NULL OR v.col = $slot)       ->  ($slot IS NULL OR v.col IN (SELECT UNNEST($slot)))
    v.fiscal_year = $date_range            ->  v.fiscal_year IN (SELECT UNNEST($date_range))

for the categorical and geography slots the brief names — focus_area, theme,
scheme, status, plan_type, district_name, block_name — and for `$date_range`.
ONE FORM, DuckDB's: a list binds natively, and `IS NULL` still reads an absent
slot as "no filter". A scalar binds as a one-element list (the binder wraps it:
`router._resolve_slot_value` and the catalogue's own `bind()`), so a single value
behaves exactly as before and the Test Report counts are unchanged.

A SLOT BECOMES LIST-CAPABLE ONLY WHERE EVERY USE OF IT WAS CONVERTED. Each
converted slot is marked `"list": True` on the template; a slot with any other
use left in the statement (a required `= $focus_area`, arithmetic on
`$date_range`) stays scalar there, and the migration prints why. `derive_catalog
--check` then holds the flag and the SQL together.

THE PAIRED-YEAR TEMPLATES KEEP SCALAR YEARS. `$date_range` / `$date_range_2` are
a pair whose direction is pinned (D30.3); a list in one of them would be a third
meaning. They are skipped for `$date_range`, and printed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from tools import derive_catalog as dc  # noqa: E402

CATEGORICAL = ("focus_area", "theme", "scheme", "status", "plan_type",
               "district_name", "block_name")


def _optional_idiom(slot: str) -> re.Pattern:
    return re.compile(
        rf"\(\${slot}(\s+)IS\s+NULL\s+OR\s+(\w+\.\w+)(\s*)=\s*\${slot}\)")


_FISCAL_YEAR = re.compile(r"\b(\w+\.fiscal_year)(\s*)=\s*\$date_range\b(?!_)")


def _other_uses(sql: str, slot: str) -> list[str]:
    """Uses of `$slot` that are neither its NULL guard nor a converted IN."""
    masked = dc.mask_literals(sql)
    left = re.sub(rf"\${slot}\s+IS\s+NULL\b", "", masked)
    left = re.sub(rf"UNNEST\(\${slot}\)", "", left)
    return [m.group(0) for m in re.finditer(rf".{{0,24}}\${slot}\b(?!_)", left)]


def convert(qid: str, entry: dict) -> tuple[str, list[str], dict[str, str]]:
    """(new sql, slots made list-capable, {slot: why it stayed scalar})."""
    sql = entry["sql_template"]
    names = {s["name"] for s in entry["param_slots"]}
    made, kept = [], {}
    for slot in (*CATEGORICAL, "date_range"):
        if slot not in names:
            continue
        if slot == "date_range" and "date_range_2" in names:
            kept[slot] = "a paired-year template (D30.3)"
            continue
        if slot == "date_range":
            trial = _FISCAL_YEAR.sub(r"\1\2IN (SELECT UNNEST($date_range))", sql)
        else:
            trial = _optional_idiom(slot).sub(
                lambda m: f"(${slot}{m.group(1)}IS NULL OR {m.group(2)}{m.group(3)}"
                          f"IN (SELECT UNNEST(${slot})))", sql)
        if trial == sql:
            kept[slot] = "no convertible use"
            continue
        other = _other_uses(trial, slot)
        if other:
            kept[slot] = "also used as " + "; ".join(o.strip() for o in other[:2])
            continue
        sql = trial
        made.append(slot)
    return sql, made, kept


def rewrite_entry(source: str, qid: str, new_sql: str, made: list[str]) -> str:
    lines = source.split("\n")
    spans = {q: (s, e) for q, s, e in dc._entry_spans(lines)}
    start, end = spans[qid]
    sql_open = next(k for k in range(start, end) if lines[k] == '        "sql_template": """')
    sql_close = next(k for k in range(sql_open + 1, end) if lines[k] == '""",')
    new_lines = new_sql.strip("\n").split("\n")
    lines[sql_open + 1:sql_close] = new_lines
    end += len(new_lines) - (sql_close - sql_open - 1)
    slots_open, slots_close = dc._find_block(lines, start, end, dc.SLOTS_OPEN,
                                             dc.SLOTS_CLOSE, qid)
    for k in range(slots_open + 1, slots_close):
        text = lines[k].strip().rstrip(",")
        slot = eval(text, {"__builtins__": {}})          # a dict literal we wrote
        if slot["name"] in made:
            slot["list"] = True
            lines[k] = f"            {dc.py(slot)},"
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source = dc.TEMPLATE_PATH.read_text(encoding="utf-8")
    catalog = dc.load_catalog(source, "TEMPLATE_CATALOG")
    tally: dict[str, int] = {}
    scalar: dict[str, dict[str, int]] = {}
    for qid, entry in catalog.items():
        new_sql, made, kept = convert(qid, entry)
        for slot in made:
            tally[slot] = tally.get(slot, 0) + 1
        for slot, why in kept.items():
            if why != "no convertible use":
                print(f"SCALAR {qid:<12} ${slot}: {why}")
            scalar.setdefault(slot, {}).setdefault(why.split(" as ")[0], 0)
            scalar[slot][why.split(" as ")[0]] += 1
        if made and not args.dry_run:
            source = rewrite_entry(source, qid, new_sql, made)

    print("\nlist-capable, by slot: " + ", ".join(f"${s} {n}" for s, n in sorted(tally.items())))
    for slot, reasons in sorted(scalar.items()):
        print(f"  ${slot} left scalar: " + ", ".join(f"{w} ×{n}" for w, n in reasons.items()))
    if args.dry_run:
        return 0
    after = dc.load_catalog(source, "TEMPLATE_CATALOG")
    assert set(after) == set(catalog)
    dc.TEMPLATE_PATH.write_text(source, encoding="utf-8")
    print(f"wrote {dc.TEMPLATE_PATH.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
