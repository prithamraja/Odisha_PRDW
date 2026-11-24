#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D14 T7: the profile sheet scale test on a made-up state.

    python handoffs/WPD14_scale/run_scale.py [--out C:/dev/odisha-d14-scale]

1. MAKE THE STATE (DuckDB, out of core). Each sample Gram Panchayat is copied
   `COPIES` times -> 6,800, with new codes and names ("Kalimela 017"). In a
   fixed order (copy k, then the sample Gram Panchayat's position by code) they
   are dealt into `BLOCKS` blocks and each block into one of `DISTRICTS`
   districts, with new codes and names. Every money column of copy k is
   multiplied by 0.5 + (k mod 101) / 100 -- the same factor in every view, so
   view1 and view3 still agree. Counts are left as they are. Only the views the
   builder reads (1, 3, 4) are made. Nothing is written inside the repo.
2. BUILD the store with `phase5g_profile_sheets.py --synthetic`, timed from
   the outside (process start to exit).
3. MEASURE: store size, largest file, lookups (each in a fresh process),
   memory added by opening the store, sheets written.
4. CHECK: checks 2, 3, 5 and 6 on the made-up store.

Writes `measurements.json` beside this script; no data.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BUILDER = REPO / "Insights" / "src" / "phase5g_profile_sheets.py"
SAMPLE_VIEWS = REPO / "Insights" / "views_prdw"

COPIES = 340
BLOCKS = 314
DISTRICTS = 30
LOOKUPS = 1000
SEED = 14

MONEY = {
    "view1": ["total_cost", "fund_tied_total", "fund_untied_total",
              "fund_abandoned_total", "fund_tied_general", "fund_tied_sc",
              "fund_tied_st", "fund_untied_general", "fund_untied_sc",
              "fund_untied_st", "work_proposed_cost", "fund_sanctioned_total",
              "fund_sanctioned_general", "fund_sanctioned_sc",
              "fund_sanctioned_st", "tec_approval_cost", "total_expenditure",
              "gen_amount", "sc_amount", "st_amount",
              "approved_cost_action_plan", "technical_approved_cost",
              "admin_approved_cost", "overspend_vs_plan",
              "overspend_vs_sanction", "asset_unit_cost"],
    "view3": ["planned_cost", "sanctioned_total", "work_proposed_cost",
              "expenditure_total", "overspend_vs_plan", "overspend_vs_sanction",
              "payment_amount", "receipt_amount"],
    "view4": ["planned_cost", "sanctioned_total", "expenditure_total",
              "overspend_vs_plan", "overspend_vs_sanction", "payment_amount",
              "receipt_amount", "osr_collected"],
}
FILES = {"view1": "view1_activity_lifecycle.parquet",
         "view3": "view3_gp_performance.parquet",
         "view4": "view4_gp_profile.parquet"}


def make_state(views_out: Path) -> dict:
    import duckdb
    views_out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for v, f in FILES.items():
        con.execute(f"CREATE VIEW s_{v} AS SELECT * FROM "
                    f"read_parquet('{(SAMPLE_VIEWS / f).as_posix()}')")
    n_gp = con.execute("SELECT COUNT(*) FROM s_view4").fetchone()[0]
    # The made-up places. i = the fixed dealing order.
    con.execute(f"""
    CREATE TABLE place AS
    WITH g AS (SELECT gp_lgd_code AS orig, trim(gp_name) AS gname,
                      ROW_NUMBER() OVER (ORDER BY gp_lgd_code) - 1 AS gi
               FROM s_view4),
         c AS (SELECT g.*, r.range AS k, r.range * {n_gp} + g.gi AS i
               FROM g CROSS JOIN range({COPIES}) r),
         b AS (SELECT c.*, (i * {BLOCKS}) // ({COPIES} * {n_gp}) AS bi FROM c)
    SELECT orig, k, i, bi, (bi * {DISTRICTS}) // {BLOCKS} AS di,
           0.5 + (k % 101) / 100.0 AS f,
           '9' || lpad(CAST(gi + 1 AS VARCHAR), 2, '0')
               || lpad(CAST(k AS VARCHAR), 3, '0') AS new_gp,
           gname || ' ' || lpad(CAST(k AS VARCHAR), 3, '0') AS new_gp_name
    FROM b""")
    con.execute("""
    CREATE TABLE place2 AS SELECT *,
        '8' || lpad(CAST(bi AS VARCHAR), 4, '0') AS new_block,
        'Block ' || lpad(CAST(bi + 1 AS VARCHAR), 3, '0') AS new_block_name,
        '7' || lpad(CAST(di AS VARCHAR), 2, '0') AS new_district,
        'District ' || lpad(CAST(di + 1 AS VARCHAR), 2, '0') AS new_district_name
    FROM place""")
    counts = {}
    for v, f in FILES.items():
        cols = [r[0] for r in con.execute(f"DESCRIBE s_{v}").fetchall()]
        sel = []
        for c in cols:
            if c == "gp_lgd_code":
                sel.append("p.new_gp AS gp_lgd_code")
            elif c == "gp_name":
                sel.append("p.new_gp_name AS gp_name")
            elif c == "block_code":
                sel.append("p.new_block AS block_code")
            elif c == "block_name":
                sel.append("p.new_block_name AS block_name")
            elif c == "district_code":
                sel.append("p.new_district AS district_code")
            elif c == "district_name":
                sel.append("p.new_district_name AS district_name")
            elif c == "activity_code":
                sel.append("s.activity_code || '-' || CAST(p.k AS VARCHAR) "
                           "AS activity_code")
            elif c in MONEY[v]:
                sel.append(f"CAST(s.{c} * p.f AS DOUBLE) AS {c}")
            else:
                sel.append(f"s.{c}")
        out = (views_out / f).as_posix()
        con.execute(f"COPY (SELECT {', '.join(sel)} FROM s_{v} s JOIN place2 p "
                    f"ON s.gp_lgd_code = p.orig ORDER BY p.i) TO '{out}' "
                    f"(FORMAT parquet)")
        counts[v] = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out}')"
                                ).fetchone()[0]
    counts["gps"] = con.execute("SELECT COUNT(DISTINCT new_gp) FROM place2").fetchone()[0]
    counts["blocks"] = con.execute("SELECT COUNT(DISTINCT new_block) FROM place2").fetchone()[0]
    counts["districts"] = con.execute("SELECT COUNT(DISTINCT new_district) FROM place2").fetchone()[0]
    con.close()
    return counts


CHILD = r"""
import json, os, sys, time, psutil
sys.path.insert(0, sys.argv[1])
proc = psutil.Process()
from DiscoverChat.profile_store import ProfileStore
rss0 = proc.memory_info().rss
t0 = time.perf_counter()
store = ProfileStore(sys.argv[2], allow_synthetic=True)
store.verify()
t1 = time.perf_counter()
sheet = store.get(sys.argv[3], sys.argv[4])
t2 = time.perf_counter()
rss1 = proc.memory_info().rss
assert sheet is not None and sheet["code"] == sys.argv[4]
print(json.dumps({"open_ms": (t1 - t0) * 1e3, "get_ms": (t2 - t1) * 1e3,
                  "rss_added_mb": (rss1 - rss0) / 2**20,
                  "sentences": len(sheet["sentences"])}))
"""


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="C:/dev/odisha-d14-scale")
    ap.add_argument("--lookups", type=int, default=LOOKUPS)
    ap.add_argument("--skip-make", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    if REPO in out.resolve().parents or out.resolve() == REPO:
        print("STOP: the made-up state must be written outside the repo")
        return 2
    views, store_dir = out / "views_prdw", out / "store"
    m = {"what_this_is": "WP-D14 T7 scale test measurements (no data).",
         "machine": None, "method": {}}
    try:
        import platform
        import psutil
        m["machine"] = (f"{platform.processor()} | {psutil.cpu_count(False)} "
                        f"cores / {psutil.cpu_count()} logical | "
                        f"{psutil.virtual_memory().total / 2**30:.1f} GB RAM | "
                        f"{platform.platform()} | Python {platform.python_version()}")
    except Exception:                                    # pragma: no cover
        pass

    if not args.skip_make:
        t = time.perf_counter()
        m["made_up_state"] = make_state(views)
        m["made_up_state"]["seconds"] = round(time.perf_counter() - t, 1)
        print("made-up state:", m["made_up_state"])

    # ── build ───────────────────────────────────────────────────────────────
    t = time.perf_counter()
    build = subprocess.run(
        [sys.executable, str(BUILDER), "--synthetic", "--views-dir", str(views),
         "--out-dir", str(store_dir), "--whole-name", "the state"],
        capture_output=True, text=True)
    build_s = time.perf_counter() - t
    print(build.stdout, build.stderr)
    if build.returncode:
        return build.returncode
    m["build_seconds"] = round(build_s, 1)
    m["builder_output"] = build.stdout.strip().splitlines()
    m["method"]["build_seconds"] = (
        "Wall clock around the builder subprocess (`phase5g_profile_sheets.py "
        "--synthetic`), process start to exit: imports, DuckDB queries over "
        "the three parquets, writing out every sentence, compressing and "
        "writing the store, hashing it for the stamp.")

    stamp = json.loads((store_dir / "profile_sheets_stamp.json").read_text("utf-8"))
    files = [store_dir / f["file"] for f in stamp["files"]] + [
        store_dir / "profile_sheets_stamp.json"]
    m["store_bytes"] = sum(f.stat().st_size for f in files)
    m["store_mb"] = round(m["store_bytes"] / 1e6, 1)
    m["largest_file"] = max((f.stat().st_size, f.name) for f in files)
    m["largest_file_mb"] = round(m["largest_file"][0] / 1e6, 1)
    m["files"] = [(f.name, f.stat().st_size) for f in files]
    m["method"]["store_mb"] = ("Sum of the bytes of every store file (index, "
                               "parts, stamp), MB = 10^6 bytes.")
    m["sheets"] = {lv: c["sheets"] for lv, c in stamp["counts"].items()}
    m["sentences"] = {lv: c["sentences"] for lv, c in stamp["counts"].items()}

    # ── lookups, each in a fresh process ────────────────────────────────────
    sys.path.insert(0, str(REPO))
    from DiscoverChat.profile_store import ProfileStore
    keys = [(lv, c) for lv in ("all", "district", "block", "gp")
            for c in ProfileStore(store_dir, allow_synthetic=True).codes(lv)]
    rng = random.Random(SEED)
    sample = [rng.choice(keys) for _ in range(args.lookups)]
    runs = []
    t = time.perf_counter()
    for level, code in sample:
        r = subprocess.run([sys.executable, "-c", CHILD, str(REPO),
                            str(store_dir), level, code],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stderr)
            return 1
        runs.append(json.loads(r.stdout))
    m["lookups"] = {
        "n": len(runs),
        "levels": {lv: sum(1 for k in sample if k[0] == lv)
                   for lv in ("all", "district", "block", "gp")},
        "get_ms_median": round(statistics.median(r["get_ms"] for r in runs), 2),
        "get_ms_p95": round(pct([r["get_ms"] for r in runs], 0.95), 2),
        "get_ms_max": round(max(r["get_ms"] for r in runs), 2),
        "open_ms_median": round(statistics.median(r["open_ms"] for r in runs), 1),
        "open_ms_p95": round(pct([r["open_ms"] for r in runs], 0.95), 1),
        "open_plus_get_ms_p95": round(pct([r["open_ms"] + r["get_ms"]
                                           for r in runs], 0.95), 1),
        "rss_added_mb_median": round(statistics.median(r["rss_added_mb"]
                                                       for r in runs), 1),
        "rss_added_mb_max": round(max(r["rss_added_mb"] for r in runs), 1),
        "seconds": round(time.perf_counter() - t, 1),
    }
    m["method"]["lookup"] = (
        f"{len(runs)} keys drawn uniformly (seed {SEED}) from all sheet keys. "
        "Each in its own new Python process: import the reader, open the store "
        "(`verify()`: read the stamp, SHA-256 every file, load the index), then "
        "time `get(level, code)` alone with perf_counter. `get_ms` is the "
        "lookup; `open_ms` is the one-off open a service pays once at start, "
        "reported separately. The OS file cache is warm after the first "
        "process (the store is read by each open's hash pass).")
    m["method"]["memory"] = (
        "psutil RSS in the same fresh process: after importing the reader, "
        "before opening; and after `verify()` plus one `get()`. The "
        "difference is the memory added by opening the store and reading one "
        "sheet. Median and maximum over the lookup processes.")
    print(json.dumps(m["lookups"], indent=1))

    # ── checks 2, 3, 5, 6 on the made-up store ──────────────────────────────
    t = time.perf_counter()
    chk = subprocess.run(
        [sys.executable, str(BUILDER), "--check", "--synthetic", "--only",
         "2,3,5,6", "--views-dir", str(views), "--out-dir", str(store_dir)],
        capture_output=True, text=True)
    print(chk.stdout, chk.stderr)
    m["checks"] = chk.stdout.strip().splitlines()
    m["checks_green"] = chk.returncode == 0
    m["checks_seconds"] = round(time.perf_counter() - t, 1)

    targets = {
        "build under 10 minutes": m["build_seconds"] < 600,
        "store under 300 MB": m["store_bytes"] < 300e6,
        "largest file under 95 MB": m["largest_file"][0] < 95e6,
        "lookup median and p95 under 50 ms": (m["lookups"]["get_ms_median"] < 50
                                              and m["lookups"]["get_ms_p95"] < 50),
        "memory added under 100 MB": m["lookups"]["rss_added_mb_max"] < 100,
        "sheets 6,800 + 314 + 30 + 1": m["sheets"] == {
            "all": 1, "district": DISTRICTS, "block": BLOCKS,
            "gp": 6800},
    }
    m["targets"] = targets
    (HERE / "measurements.json").write_text(
        json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, ok in targets.items():
        print(f"  {'MET   ' if ok else 'MISSED'} {name}")
    return 0 if all(targets.values()) and m["checks_green"] else 1


if __name__ == "__main__":
    sys.exit(main())
