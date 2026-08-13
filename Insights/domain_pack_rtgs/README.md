# domain_pack_rtgs — Andhra Pradesh RTGS Decision Aid (Discover)

The domain pack for the AP Agriculture department's "Discover" mode. Format and
runner contract are documented in [`../domain_pack/README.md`](../domain_pack/README.md);
the UP PM-JAY pack next door stays untouched as the worked example.

```
domain_pack_rtgs/
├── demo_crosswalk.csv     # every in-scope column -> analytical role (gate artifact)
├── sources.yaml           # 7 staged CSVs + explicit casts
├── derived_columns.sql    # district map, stg_* views, stg_benefit_long spine
├── views/                 # 4 output views
└── validation.yaml        # PK / FK / categorical / date checks + post-view grain
```

## Building

Run everything from the execution mirror (never the Drive path — DuckDB cannot
spill temp files there):

```bash
python scripts/build_demo_crosswalk.py     # -> domain_pack_rtgs/demo_crosswalk.csv
python scripts/stage_flat_csvs.py          # RTGS_Data/flat/*.parquet -> rtgs_csv/*.csv
cd Metainsights_anomalies
python src/build_views.py --pack domain_pack_rtgs --data-dir rtgs_csv \
                          --views-dir views_rtgs --reports-dir reports_rtgs
```

`rtgs_csv/`, `views_rtgs/` and `reports_rtgs/` are build outputs and are
gitignored; all three rebuild from the two committed scripts plus this pack.

## Scope

Columns may come only from the Demo Field Inventory sheet of
`RTGS_Data/RTGS _Decision Aid_Demo.xlsx`, plus all 21 `pm_kisan` columns (the
sheet omits that dataset). `demo_crosswalk.csv` records the role of every one of
them; nothing carrying an `excluded_*` role is staged, so no Bank/DBT field and
no personal identifier reaches a view. Aadhaar is staged as the join spine, is
consumed inside `derived_columns.sql`, and appears in no view.

## The four views

| view | grain | rows |
|---|---|---|
| `view1_scheme_benefits` | one benefit row across 7 scheme files | 5,844 |
| `view2_farmer_360` | one distinct Aadhaar | 1,140 |
| `view3_agri_crop` | one Agriculture input-subsidy registration | 1,114 |
| `view4_markfed_procurement` | one MARKFED procurement transaction | 1,086 |

`survey_land_records` feeds nothing: it has no benefit column and no Aadhaar, so
it can neither contribute a benefit row nor be attached to a farmer.

Views 1 and 2 both read `stg_benefit_long`, so the per-farmer totals in view2
are by construction the sum of the rows in view1.
