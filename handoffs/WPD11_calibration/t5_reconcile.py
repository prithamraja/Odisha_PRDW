"""WP-D11 T5 reconciliation gate: amended pack vs the pre-change baseline."""
import duckdb, os, sys

BASE = r"C:\dev\odisha-d11\Insights\views_baseline"
NEW  = r"C:\dev\odisha-d11\Insights\views_prdw"
con = duckdb.connect(); con.execute("SET TimeZone='UTC'")

def pq(d, v):
    return f"read_parquet('{os.path.join(d, v + '.parquet')}'.replace('\\\\','/'))"

def path(d, v):
    return os.path.join(d, v + ".parquet").replace("\\", "/")

def rd(d, v):
    return f"read_parquet('{path(d, v)}')"

fails = []
def check(name, ok, detail=""):
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("  " + detail if detail else ""))
    if not ok:
        fails.append(name)

PROFILE_DIMS = ["social_composition", "gp_size", "remoteness", "digital_readiness",
                "has_panchayat_bhawan", "has_csc", "plc_available"]

print("=" * 78)
print("1. ROW COUNTS")
print("=" * 78)
for v, exp in [("view1_activity_lifecycle", 12704), ("view2_geo_month_cube", 1440),
               ("view3_gp_performance", 120)]:
    n = con.execute(f"SELECT count(*) FROM {rd(NEW, v)}").fetchone()[0]
    check(f"{v}: {n:,}", n == exp, f"expected {exp:,}")
n4 = con.execute(f"SELECT count(*) FROM {rd(NEW,'view4_gp_profile')}").fetchone()[0]
d4 = con.execute(f"SELECT count(DISTINCT gp_lgd_code) FROM {rd(NEW,'view4_gp_profile')}").fetchone()[0]
check(f"view4_gp_profile: {n4} rows / {d4} distinct gp_lgd_code", n4 == 20 and d4 == 20, "expected 20 / 20")

print()
print("=" * 78)
print("2. EVERY PRE-EXISTING COLUMN OF VIEWS 1-3 IDENTICAL TO BASELINE")
print("=" * 78)
for v, grain in [("view1_activity_lifecycle", ["activity_code"]),
                 ("view2_geo_month_cube", ["gp_lgd_code", "month"]),
                 ("view3_gp_performance", ["gp_lgd_code", "fiscal_year"])]:
    old = con.execute(f"DESCRIBE SELECT * FROM {rd(BASE,v)}").fetchall()
    new = con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,v)}").fetchall()
    oldc = {c[0]: c[1] for c in old}
    newc = {c[0]: c[1] for c in new}
    added = [c for c in newc if c not in oldc]
    removed = [c for c in oldc if c not in newc]
    check(f"{v}: no pre-existing column removed", not removed, str(removed))
    check(f"{v}: exactly the 7 profile dimensions added", sorted(added) == sorted(PROFILE_DIMS), str(sorted(added)))
    dtype_change = [c for c in oldc if c in newc and oldc[c] != newc[c]]
    check(f"{v}: no dtype change on a pre-existing column", not dtype_change, str(dtype_change))
    # value equality, keyed on the grain, over every pre-existing column
    cols = [c for c in oldc if c in newc]
    on = " AND ".join(f'o."{k}" IS NOT DISTINCT FROM n."{k}"' for k in grain)
    diffs = " OR ".join(f'o."{c}" IS DISTINCT FROM n."{c}"' for c in cols)
    q = (f"SELECT count(*) FROM {rd(BASE,v)} o JOIN {rd(NEW,v)} n ON {on} WHERE {diffs}")
    nd = con.execute(q).fetchone()[0]
    unmatched = con.execute(
        f"SELECT count(*) FROM {rd(BASE,v)} o LEFT JOIN {rd(NEW,v)} n ON {on} WHERE n.\"{grain[0]}\" IS NULL"
    ).fetchone()[0]
    check(f"{v}: all {len(cols)} pre-existing columns byte-identical on all rows",
          nd == 0 and unmatched == 0, f"{nd} differing rows, {unmatched} unmatched")

print()
print("=" * 78)
print("3. THE SEVEN DIMENSION SPLITS (fact 2), ON view4 AND ON EVERY VIEW")
print("=" * 78)
EXPECTED = {
    "social_composition":   {"ST-majority": 2, "SC-majority": 3, "Mixed": 15},
    "gp_size":              {"Under 2,500": 2, "2,500 to 5,000": 9, "5,000 to 10,000": 7, "10,000 and above": 2},
    "remoteness":           {"Near": 14, "Far": 6},
    "digital_readiness":    {"Ready": 10, "Not ready": 10},
    "has_panchayat_bhawan": {"Yes": 14, "No": 6},
    "has_csc":              {"Yes": 12, "No": 8},
    "plc_available":        {"No": 18, "Yes": 2},
}
for d, exp in EXPECTED.items():
    got = dict(con.execute(
        f'SELECT "{d}", count(*) FROM {rd(NEW,"view4_gp_profile")} GROUP BY 1').fetchall())
    check(f"view4.{d}", got == exp, f"got {got} expected {exp}")
# and the same GP-level split reached views 1-3
print("  -- distinct GPs per band on views 1-3 (must equal view4's split) --")
for v in ["view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance"]:
    for d, exp in EXPECTED.items():
        got = dict(con.execute(
            f'SELECT "{d}", count(DISTINCT gp_lgd_code) FROM {rd(NEW,v)} GROUP BY 1').fetchall())
        if got != exp:
            check(f"{v}.{d}", False, f"got {got}")
    print(f"  [PASS] {v}: all seven bands carry the same GP split as view4")
# 'Not reported' must appear nowhere on this drop
for v in ["view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance", "view4_gp_profile"]:
    tot = 0
    for d in PROFILE_DIMS:
        tot += con.execute(f"SELECT count(*) FROM {rd(NEW,v)} WHERE \"{d}\" = 'Not reported'").fetchone()[0]
    check(f"{v}: zero 'Not reported' cells (every sample GP has a profile)", tot == 0, str(tot))
# and no 'NA' band anywhere
for v in ["view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance", "view4_gp_profile"]:
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,v)}").fetchall()
            if c[1] == "VARCHAR"]
    tot = sum(con.execute(f"SELECT count(*) FROM {rd(NEW,v)} WHERE \"{c}\" = 'NA'").fetchone()[0]
              for c in cols)
    check(f"{v}: the string 'NA' appears in no VARCHAR column", tot == 0, str(tot))

print()
print("=" * 78)
print("4. SUM(view4.m) == SUM(view3.m) FOR EVERY SHARED MEASURE")
print("=" * 78)
v3 = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,'view3_gp_performance')}").fetchall()]
v4 = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,'view4_gp_profile')}").fetchall()]
shared = [c for c in v3 if c in v4 and c not in
          (["gp_lgd_code", "gp_name", "block_code", "block_name", "district_code",
            "district_name", "fiscal_year"] + PROFILE_DIMS)]
print(f"  shared measures: {len(shared)}")
# THE EQUALITY RULE, and why it is not bit equality on the money columns.
# view3 sums 120 GP-year cells; view4 sums 20 GP cells built from the same
# addends in a different order. Floating-point addition is not associative, so
# two correct totals over the same rupees can differ in the last bit of a
# double -- and on this drop five of the eighteen do, by 1 to 2 ULP (relative
# 1e-16). That is IEEE-754, not a difference of attribution: every one of the
# five is identical when rounded to the paise, and the thirteen count measures
# are bit-identical because they are integers held exactly in a double.
# The rule enforced here is therefore: EXACT on every count measure, and equal
# to the paise AND within 2 ULP on every money measure.
import math
for m in shared:
    a = con.execute(f'SELECT SUM("{m}") FROM {rd(NEW,"view3_gp_performance")}').fetchone()[0]
    b = con.execute(f'SELECT SUM("{m}") FROM {rd(NEW,"view4_gp_profile")}').fetchone()[0]
    if a == b:
        check(f"SUM {m}: {a!r} (bit-exact)", True)
    else:
        ulps = abs(a - b) / math.ulp(abs(a))
        ok = round(a, 2) == round(b, 2) and ulps <= 2
        check(f"SUM {m}: view3={a!r} view4={b!r}", ok,
              f"equal to the paise, {ulps:.0f} ULP apart (float summation order)")
missing = [c for c in v3 if c not in v4 and c not in ["fiscal_year"]]
print(f"  view3 columns NOT on view4 (expected: work_proposed_cost only): {missing}")
check("only work_proposed_cost is absent from view4", missing == ["work_proposed_cost"], str(missing))

print()
print("=" * 78)
print("5. PROFILE MEASURE TOTALS AND THE CHIKILLI GUARD")
print("=" * 78)
pop, hh = con.execute(
    f'SELECT SUM(population_total), SUM(households) FROM {rd(NEW,"view4_gp_profile")}').fetchone()
check(f"view4 SUM population_total = {pop:,.0f}", pop == 115246, "expected 115,246")
check(f"view4 SUM households = {hh:,.0f}", hh == 26132, "expected 26,132")
row = con.execute(
    f'SELECT gp_name, n_activities, n_admin_approvals, population_total, social_composition, gp_size '
    f'FROM {rd(NEW,"view4_gp_profile")} WHERE gp_name = \'Chikilli\'').fetchall()
check("view4: Chikilli row present", len(row) == 1, str(row))
if row:
    check(f"view4: Chikilli n_admin_approvals = {row[0][2]:.0f} with profile populated",
          row[0][2] == 0 and row[0][3] > 0, str(row[0]))

print()
print("=" * 78)
print("6. NO X-pii COLUMN NAME IN ANY PARQUET SCHEMA")
print("=" * 78)
PII = ["basic_info_email_address", "basic_info_mobile", "basic_info_address",
       "basic_info_gp_attractions"]
for v in ["view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance", "view4_gp_profile"]:
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,v)}").fetchall()]
    hits = [p for p in PII if p in cols]
    check(f"{v}: {len(cols)} columns, 0 X-pii", not hits, str(hits))

print()
print("=" * 78)
print("COLUMN COUNTS")
print("=" * 78)
for v in ["view1_activity_lifecycle", "view2_geo_month_cube", "view3_gp_performance", "view4_gp_profile"]:
    n = con.execute(f"SELECT count(*) FROM {rd(NEW,v)}").fetchone()[0]
    c = len(con.execute(f"DESCRIBE SELECT * FROM {rd(NEW,v)}").fetchall())
    try:
        b = len(con.execute(f"DESCRIBE SELECT * FROM {rd(BASE,v)}").fetchall())
    except Exception:
        b = "-"
    print(f"  {v}: {n:,} rows, {c} columns (baseline {b})")

print()
print("=" * 78)
print(f"T5 RECONCILIATION: {len(fails)} failure(s)")
for f in fails:
    print("  FAILED:", f)
print("=" * 78)
sys.exit(1 if fails else 0)
