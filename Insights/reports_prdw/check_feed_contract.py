"""WP-D3 T4a — the feed contract check (D16).

D16 freezes `phase5c_global_feed.py`'s emitted JSON shape: the PR&DW frontend
will be the AP frontend ported, so the AP writer's output is the contract and
any difference is a STOP.

The contract itself is `feed_contract_reference.json`, beside this file. It was
derived by running the AP deployment's own writer, unmodified, over the AP repo
mirror's ranked candidate JSONs -- that file's `how_this_was_derived` states
exactly what was and was not stubbed. It is data, not an assertion, and it can
be re-derived.

The check runs TWICE, by two independent methods, because "the schema is
unchanged" is easy to assert and easy to be wrong about:

  METHOD 1 -- ARTEFACT. Our emitted `global_feed.json` is walked to a TYPED KEY
  PATH SET (every key path, plus the JSON type found at it) and compared with
  the reference's. This catches a renamed key, a moved key, a dropped key, an
  added key, and a key whose type changed.

  METHOD 2 -- SOURCE. Our writer's `json.dump({...})` literal, its `weighting`
  block, its `_row_dict` and its rejected-row constructor are parsed with `ast`
  and their key lists compared IN ORDER with the reference's. This covers what
  method 1 cannot see because the data did not exercise it -- with 32 findings
  against a TOP_K of 50 nothing is ever rejected, so
  `highest_scoring_rejected` is a present-but-empty array and its element
  schema has to be read off the constructor.

Usage:
    python Insights/reports_prdw/check_feed_contract.py --base Insights
Exit 0 = the contract holds. Non-zero = STOP.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, "feed_contract_reference.json")

# Dicts that are MAPS keyed by view name, not records. AP has nine views and
# PR&DW three, so expanding them would make every view name look like a field.
_MAP_FIELDS = {"reach", "weights"}


def typed_paths(node, prefix="") -> set:
    """Every key path in a JSON document, with the type found at it."""
    out = set()
    t = type(node).__name__
    if isinstance(node, dict):
        out.add(f"{prefix}: object")
        scalar_valued = node and all(
            isinstance(v, (int, float, str, bool)) or v is None
            for v in node.values()
        )
        if scalar_valued and prefix.split(".")[-1] in _MAP_FIELDS:
            out.add(f"{prefix}.<map>: "
                    f"{sorted({type(v).__name__ for v in node.values()})}")
            return out
        for k, v in node.items():
            out |= typed_paths(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        out.add(f"{prefix}: array")
        for item in node:
            out |= typed_paths(item, f"{prefix}[]")
    else:
        if t in ("int", "float"):
            t = "number"       # a count and a rounded score are both numbers
        out.add(f"{prefix}: {t}")
    return out


def dict_literal_keys(src: str, marker: str) -> list:
    tree = ast.parse(src)
    if marker == "json.dump":
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "dump"
                    and node.args and isinstance(node.args[0], ast.Dict)):
                return [k.value for k in node.args[0].keys
                        if isinstance(k, ast.Constant)]
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == marker:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    return [k.value for k in sub.keys
                            if isinstance(k, ast.Constant)]
    return []


def nested_dict_keys(src: str, outer_key: str) -> list:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "dump"
                and node.args and isinstance(node.args[0], ast.Dict)):
            d = node.args[0]
            for k, v in zip(d.keys, d.values):
                if (isinstance(k, ast.Constant) and k.value == outer_key
                        and isinstance(v, ast.Dict)):
                    return [kk.value for kk in v.keys
                            if isinstance(kk, ast.Constant)]
    return []


def rejected_row_keys(src: str) -> list:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "select_top":
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "append"
                        and sub.args and isinstance(sub.args[0], ast.Dict)):
                    return [k.value for k in sub.args[0].keys
                            if isinstance(k, ast.Constant)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="the Insights directory")
    args = ap.parse_args()
    base = os.path.abspath(args.base)
    prdw_json = os.path.join(base, "metainsights", "global_feed.json")
    prdw_src = os.path.join(base, "src", "phase5c_global_feed.py")

    reference = json.load(open(REFERENCE, encoding="utf-8"))
    failures = []

    print("=" * 72)
    print("WP-D3 T4a — FEED CONTRACT CHECK (D16)")
    print("=" * 72)
    print(f"  contract  : {os.path.basename(REFERENCE)} "
          f"(derived {reference['derived_on']})")
    print(f"  artefact  : {prdw_json}")
    print(f"  writer    : {prdw_src}")

    # ---------------------------------------------------------- METHOD 1 ---
    ours = json.load(open(prdw_json, encoding="utf-8"))
    ref_paths = set(reference["typed_paths"])
    our_paths = typed_paths(ours)

    def empty_array_prefixes(paths: set) -> set:
        return {p[: -len(": array")] + "[]" for p in paths
                if p.endswith(": array")
                and not any(q.startswith(p[: -len(": array")] + "[]")
                            for q in paths)}

    ours_empty = empty_array_prefixes(our_paths)
    ref_empty = empty_array_prefixes(ref_paths)

    def unexercised(path, empties):
        return any(path.startswith(e) for e in empties)

    raw_missing = sorted(ref_paths - our_paths)
    raw_added = sorted(our_paths - ref_paths)
    missing = [p for p in raw_missing if not unexercised(p, ours_empty)]
    added = [p for p in raw_added if not unexercised(p, ref_empty)]
    skipped = ([p for p in raw_missing if unexercised(p, ours_empty)]
               + [p for p in raw_added if unexercised(p, ref_empty)])

    print(f"\nMETHOD 1 — emitted artefact, typed key paths")
    print(f"  {len(ref_paths)} contract paths, {len(our_paths)} ours")
    for p in missing:
        print(f"    MISSING: {p}")
    for p in added:
        print(f"    ADDED:   {p}")
    if missing:
        failures.append(f"{len(missing)} contract path(s) absent from ours")
    if added:
        failures.append(f"{len(added)} path(s) in ours that the contract "
                        f"does not have")
    if skipped:
        print(f"  {len(skipped)} path(s) UNEXERCISED — the array holding them "
              f"is present but empty in one document, so the data could not "
              f"reach them. Method 2 covers these:")
        for p in sorted(skipped):
            print(f"    unexercised: {p}")
    if not missing and not added:
        print("  IDENTICAL — every key path and every type matches"
              + (" (excluding the unexercised paths above)" if skipped else ""))

    # ---------------------------------------------------------- METHOD 2 ---
    src = open(prdw_src, encoding="utf-8").read()
    ours_keys = {
        "json_dump_top_level": dict_literal_keys(src, "json.dump"),
        "weighting_block":     nested_dict_keys(src, "weighting"),
        "feed_row":            dict_literal_keys(src, "_row_dict"),
        "rejected_row":        rejected_row_keys(src),
    }
    print(f"\nMETHOD 2 — writer source, dict-literal keys in order")
    for name, expected in reference["source_keys"].items():
        got = ours_keys[name]
        if got == expected:
            print(f"  {name}: {len(got)} keys, IDENTICAL and in the same order")
        else:
            failures.append(f"{name} differs")
            print(f"  {name}: DIFFERS")
            print(f"    contract : {expected}")
            print(f"    ours     : {got}")

    # ------------------------------------------------------- shape facts ---
    print("\nSHAPE FACTS")
    print(f"  feed rows          : {len(ours['feed'])}")
    print(f"  rejected rows      : {len(ours['highest_scoring_rejected'])}")
    print(f"  views in `weights` : {sorted(ours['weighting']['weights'])}")
    print(f"  weights            : {ours['weighting']['weights']}")
    print(f"  reach              : {ours['weighting']['reach']}")
    print(f"  rank_decay         : {ours['weighting']['rank_decay']}")
    print(f"  seeds_per_view     : {ours['weighting']['seeds_per_view']}")

    print("\n" + "=" * 72)
    if failures:
        print(f"CONTRACT CHECK FAILED — {len(failures)} problem(s): {failures}")
        print("D16: any difference is a STOP.")
        return 1
    print("CONTRACT CHECK PASSED — the emitted schema is the AP writer's, "
          "field for field, by both methods.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
