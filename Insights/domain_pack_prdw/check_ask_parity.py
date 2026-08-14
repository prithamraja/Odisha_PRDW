"""Ask <-> Discover parity check — the proof behind derived_columns.sql's
"verbatim" claim.

NOT PART OF THE PIPELINE. `build_views.py` never reads this file. It is a
maintenance / replay script: it registers the sources exactly as this pack's
sources.yaml declares them, runs `Data/create_views.sql` UNMODIFIED against
them, and then diffs the resulting `v_activity` (the view the Ask chatbot's
parameterised queries read) against the built `view1_activity_lifecycle.parquet`,
column by column, on the shared activity grain.

Why it exists. The whole point of the Discover workstream is that an Ask answer
and a Discover finding cannot disagree about a number. `derived_columns.sql`
claims to re-express create_views.sql verbatim; this script is what turns that
claim into a measurement. Run it after ANY edit to derived_columns.sql or
views/view1_*.sql.

Expected result on the WP-D1 drop: 41 columns compared, 0 mismatching, all
12,704 activities. Numerics are compared to the paisa; strings and flags
exactly; NULL-vs-NULL counts as equal.

Two columns are deliberately absent from view1 and are asserted so:
  * days_since_sanction — non-reproducible (DATE_DIFF against CURRENT_DATE)
  * every free-text / document-number column — §9.6

Usage (paths default to the repo layout, relative to this file):
    python Insights/domain_pack_prdw/check_ask_parity.py \
        [--data-dir Data] [--views-dir Insights/views_prdw] \
        [--create-views-sql Data/create_views.sql]

Exit code is 0 when every compared column matches, 1 otherwise.
"""
import argparse, os, sys
import duckdb, yaml

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(os.path.dirname(here))
p = argparse.ArgumentParser(description="Diff v_activity against view1_activity_lifecycle.")
p.add_argument("--data-dir", default=os.path.join(repo, "Data"))
p.add_argument("--views-dir", default=os.path.join(repo, "Insights", "views_prdw"))
p.add_argument("--create-views-sql", default=None,
               help="defaults to <data-dir>/create_views.sql")
p.add_argument("--pack", default=here)
args = p.parse_args()

D = os.path.abspath(args.data_dir).replace("\\", "/")
V = os.path.abspath(args.views_dir).replace("\\", "/")
CV = args.create_views_sql or os.path.join(args.data_dir, "create_views.sql")

CAST_SQL = {"date": "DATE", "float": "DOUBLE", "int": "BIGINT",
            "bool": "BOOLEAN", "timestamp": "TIMESTAMP"}

con = duckdb.connect()
con.execute("SET TimeZone='UTC'")

# 1. register the sources exactly as sources.yaml declares them
with open(os.path.join(args.pack, "sources.yaml"), encoding="utf-8") as fh:
    src = yaml.safe_load(fh)
for name, spec in src["tables"].items():
    reader = f"read_csv('{D}/{spec['file']}', all_varchar=true, header=true)"
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {reader}").fetchall()]
    casts = spec.get("casts") or {}
    sel = ", ".join(
        (f'CAST("{c}" AS {CAST_SQL[casts[c]]}) AS "{c}"' if c in casts else f'"{c}"')
        for c in cols)
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT {sel} FROM {reader}")

# 2. run the Ask views unmodified
with open(CV, encoding="utf-8") as fh:
    con.execute(fh.read())
print(f"create_views.sql executed against {D} -> v_exp, v_approval, v_activity, ...")

con.execute("CREATE OR REPLACE VIEW view1 AS "
            f"SELECT * FROM read_parquet('{V}/view1_activity_lifecycle.parquet')")
n_ask, n_disc = con.execute(
    "SELECT (SELECT count(*) FROM v_activity), (SELECT count(*) FROM view1)").fetchone()
print(f"rows: v_activity={n_ask:,}  view1={n_disc:,}")

# 3. (view1 column, Ask expression, 'n'umeric | 's'tring)
PAIRS = [
    ("gp_name", "a.gp_name", "s"), ("block_name", "a.block_name", "s"),
    ("district_name", "a.district_name", "s"), ("fiscal_year", "a.fiscal_year", "s"),
    ("focus_area_name", "a.focus_area_name", "s"), ("theme", "a.theme", "s"),
    ("status_label", "a.status_label", "s"), ("work_type_label", "a.work_type_label", "s"),
    ("activity_type_label", "a.activity_type_label", "s"),
    ("activity_for_label", "a.activity_for_label", "s"),
    ("is_costless", "CASE a.is_costless_activity WHEN '1' THEN 'Costless' "
                    "WHEN '0' THEN 'Costed' ELSE 'Unknown' END", "s"),
    ("sanction_authority", "a.sanction_authority", "s"),
    ("sanctioned_scheme_name", "a.sanctioned_scheme_name", "s"),
    ("fund_component_name", "a.fund_component_name", "s"),
    ("tied_untied", "a.tied_untied", "s"),
    # v_activity does not project tec_approval_required; v_approval does.
    ("tec_approval_required", "ap.tec_approval_required", "s"),
    ("total_cost", "a.total_cost", "n"),
    ("total_expenditure", "a.total_expenditure", "n"),
    ("gen_amount", "a.gen_amount", "n"), ("sc_amount", "a.sc_amount", "n"),
    ("st_amount", "a.st_amount", "n"),
    ("approved_cost_action_plan", "a.approved_cost_action_plan", "n"),
    ("technical_approved_cost", "a.technical_approved_cost", "n"),
    ("admin_approved_cost", "a.admin_approved_cost", "n"),
    ("work_proposed_cost", "a.work_proposed_cost", "n"),
    ("tec_approval_cost", "a.tec_approval_cost", "n"),
    ("fund_sanctioned_general", "a.fund_sanctioned_general", "n"),
    ("fund_sanctioned_sc", "a.fund_sanctioned_sc", "n"),
    ("fund_sanctioned_st", "a.fund_sanctioned_st", "n"),
    ("fund_sanctioned_total", "a.fund_sanctioned_total", "n"),
    ("sanction_scheme_rows", "a.scheme_rows", "n"),
    ("evidence_uploads", "a.evidence_uploads", "n"),
    ("is_started", "a.is_started", "n"), ("is_completed", "a.is_completed", "n"),
    ("is_ongoing", "a.is_ongoing", "n"), ("is_abandoned", "a.is_abandoned", "n"),
    ("is_under_approval", "a.is_under_approval", "n"),
    ("is_admin_approved", "a.is_admin_approved", "n"),
    ("has_approval_cost_only", "a.has_approval_cost_only", "n"),
    ("has_technical_approval", "COALESCE(a.has_technical_approval, 0)", "n"),
    ("has_progress_evidence", "a.has_progress_evidence", "n"),
]

exprs = []
for col, ask, kind in PAIRS:
    if kind == "n":
        cmp = (f'CASE WHEN v."{col}" IS NULL AND ({ask}) IS NULL THEN 0 '
               f'WHEN v."{col}" IS NULL OR ({ask}) IS NULL THEN 1 '
               f'WHEN abs(v."{col}" - ({ask})) > 0.005 THEN 1 ELSE 0 END')
    else:
        cmp = f'CASE WHEN v."{col}" IS NOT DISTINCT FROM ({ask}) THEN 0 ELSE 1 END'
    exprs.append(f'SUM({cmp}) AS "{col}"')

cur = con.execute(
    "SELECT " + ", ".join(exprs) +
    " FROM view1 v JOIN v_activity a ON a.activity_code = v.activity_code"
    " LEFT JOIN v_approval ap ON ap.activity_code = v.activity_code")
names = [d[0] for d in cur.description]
bad = [(n, x) for n, x in zip(names, cur.fetchone()) if x]

print(f"\ncolumns compared: {len(PAIRS)}   mismatching: {len(bad)}")
for n, x in bad:
    print(f"   MISMATCH {n}: {x:,} rows")
if not bad:
    print(f"   every compared column is identical on all {n_disc:,} activities")

# 4. the deliberate absences
v1cols = [c[0] for c in con.execute("DESCRIBE view1").fetchall()]
excluded = [c for c in v1cols if c in (
    "days_since_sanction", "activity_name", "activity_desc", "search_text",
    "sanction_authority_raw", "tec_approval_authority", "adm_approval_no",
    "tec_approval_order_no", "scheme_name", "expenditure_id", "plan_code")]
print(f"excluded-by-role columns found in view1: {excluded or 'none'}")

sys.exit(1 if (bad or excluded or n_ask != n_disc) else 0)
