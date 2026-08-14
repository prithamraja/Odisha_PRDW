"""Is the SC/ST swap in the raw data, or introduced downstream?
Reads the CSVs as pure text - no pack, no casts, no views."""
import duckdb, os
here = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(here, "Data").replace("\\", "/")
con = duckdb.connect()
for t in ["admin_approval_scheme", "activity_expenditure", "planned_activity",
          "activity_fund", "admin_approval"]:
    con.execute(f"CREATE OR REPLACE VIEW {t} AS SELECT * FROM "
                f"read_csv('{D}/{t}.csv', all_varchar=true, header=true)")


def q(label, sql, n=40):
    print(f"\n--- {label}")
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        print("    (no rows)")
        return
    print("    " + " | ".join(cols))
    for r in rows[:n]:
        print("    " + " | ".join("NULL" if v is None else str(v) for v in r))


# 1. RAW header order, straight from the file - a shifted-column ingestion bug
#    would show as a header/position mismatch.
q("raw CSV header line: admin_approval_scheme", f"""
SELECT * FROM read_csv('{D}/admin_approval_scheme.csv', all_varchar=true,
                       header=false, max_line_size=100000) LIMIT 1
""")
q("raw CSV header line: activity_expenditure", f"""
SELECT * FROM read_csv('{D}/activity_expenditure.csv', all_varchar=true,
                       header=false, max_line_size=100000) LIMIT 1
""")

# 2. Non-null counts and sums, as pure text -> numeric only for the sum
q("raw non-null counts + sums", """
SELECT 'admin_approval_scheme.fund_sanctioned_sc' col,
       count(fund_sanctioned_sc) n, sum(CAST(fund_sanctioned_sc AS DOUBLE)) total
FROM admin_approval_scheme
UNION ALL SELECT 'admin_approval_scheme.fund_sanctioned_st',
       count(fund_sanctioned_st), sum(CAST(fund_sanctioned_st AS DOUBLE)) FROM admin_approval_scheme
UNION ALL SELECT 'activity_expenditure.sc',
       count(sc), sum(CAST(sc AS DOUBLE)) FROM activity_expenditure
UNION ALL SELECT 'activity_expenditure.st',
       count(st), sum(CAST(st AS DOUBLE)) FROM activity_expenditure
UNION ALL SELECT 'admin_approval_scheme.fund_sanctioned_general',
       count(fund_sanctioned_general), sum(CAST(fund_sanctioned_general AS DOUBLE)) FROM admin_approval_scheme
UNION ALL SELECT 'activity_expenditure.general',
       count(general), sum(CAST(general AS DOUBLE)) FROM activity_expenditure
""")

# 3. THE decisive test: same activities, and do the values line up crosswise?
q("every activity with a non-null SC or ST on EITHER side", """
WITH s AS (SELECT activity_code, fund_sanctioned_sc AS sanc_sc, fund_sanctioned_st AS sanc_st
           FROM admin_approval_scheme
           WHERE fund_sanctioned_sc IS NOT NULL OR fund_sanctioned_st IS NOT NULL),
     e AS (SELECT activity_code, sc AS exp_sc, st AS exp_st
           FROM activity_expenditure WHERE sc IS NOT NULL OR st IS NOT NULL)
SELECT COALESCE(s.activity_code, e.activity_code) AS activity_code,
       s.sanc_sc, s.sanc_st, e.exp_sc, e.exp_st,
       CASE WHEN s.sanc_st IS NOT DISTINCT FROM e.exp_sc
             AND s.sanc_sc IS NOT DISTINCT FROM e.exp_st THEN 'CROSSWISE EQUAL'
            WHEN s.sanc_sc IS NOT DISTINCT FROM e.exp_sc
             AND s.sanc_st IS NOT DISTINCT FROM e.exp_st THEN 'straight equal'
            ELSE 'neither' END AS verdict
FROM s FULL OUTER JOIN e ON e.activity_code = s.activity_code
ORDER BY 1
""")

# 4. summary of the verdict column
q("verdict tally", """
WITH s AS (SELECT activity_code, fund_sanctioned_sc AS sanc_sc, fund_sanctioned_st AS sanc_st
           FROM admin_approval_scheme
           WHERE fund_sanctioned_sc IS NOT NULL OR fund_sanctioned_st IS NOT NULL),
     e AS (SELECT activity_code, sc AS exp_sc, st AS exp_st
           FROM activity_expenditure WHERE sc IS NOT NULL OR st IS NOT NULL)
SELECT CASE WHEN s.sanc_st IS NOT DISTINCT FROM e.exp_sc
             AND s.sanc_sc IS NOT DISTINCT FROM e.exp_st THEN 'CROSSWISE EQUAL'
            WHEN s.sanc_sc IS NOT DISTINCT FROM e.exp_sc
             AND s.sanc_st IS NOT DISTINCT FROM e.exp_st THEN 'straight equal'
            ELSE 'neither' END AS verdict, count(*)
FROM s FULL OUTER JOIN e ON e.activity_code = s.activity_code
GROUP BY 1
""")

# 5. does activity_fund agree with either side? it has its own sc/st splits
q("activity_fund sc/st for the same activities", """
WITH ids AS (SELECT activity_code FROM admin_approval_scheme
             WHERE fund_sanctioned_sc IS NOT NULL OR fund_sanctioned_st IS NOT NULL)
SELECT f.activity_code,
       f.fund_tied_sc, f.fund_tied_st, f.fund_untied_sc, f.fund_untied_st,
       s.fund_sanctioned_sc, s.fund_sanctioned_st
FROM activity_fund f
JOIN ids USING (activity_code)
JOIN admin_approval_scheme s USING (activity_code)
ORDER BY 1
""")

# 6. is activity_for (the SC/ST/General beneficiary code) a tiebreaker?
q("activity_for on those activities (111=General 112=sc 113=st 114=ALL)", """
WITH ids AS (SELECT activity_code, fund_sanctioned_sc, fund_sanctioned_st
             FROM admin_approval_scheme
             WHERE fund_sanctioned_sc IS NOT NULL OR fund_sanctioned_st IS NOT NULL)
SELECT ids.activity_code, a.activity_for,
       ids.fund_sanctioned_sc, ids.fund_sanctioned_st, e.sc AS exp_sc, e.st AS exp_st
FROM ids JOIN planned_activity a USING (activity_code)
LEFT JOIN activity_expenditure e USING (activity_code)
ORDER BY a.activity_for, 1
""")
