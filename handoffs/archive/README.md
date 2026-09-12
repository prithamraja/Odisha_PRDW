# Archive

- `AI_Chatbot_Questions.xlsx` — the signed-off question catalogue of **2026-08-13** (363 questions; every answerable one's SQL tested against `panchayat_1.duckdb`). It was the Ask catalogue's source of truth until **WP-6 T0 (2026-09-12)**. Since then `Ask/query_router/template_catalog.py` is the source of truth, and no tool in the build or gate path reads this workbook. To see what the sign-off said as catalogue files, run `python Ask/tools/import_workbook.py --out-dir <new directory>` (it only ever creates files).
