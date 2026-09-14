#!/bin/bash
# =============================================================================
# WP-D11 — copy the deliverables from the local mirror back to the Drive repo
# =============================================================================
# The build and the engine never run from the Drive mount (DuckDB spills temp
# files Drive cannot take), so everything is produced in C:\dev\odisha-d11 and
# copied back here. Parquet views are NOT copied: Insights/views_prdw/ is build
# output and is gitignored.
#
# NO GIT OPERATION IS PERFORMED. The operator commits.
#
# Usage:  bash handoffs/WPD11_calibration/sync_back.sh [--editions]
#   --editions   also copy the regenerated feed / prose / corpora / reports.
#                Omit it if T7 was not reached, so a partial edition set can
#                never be copied over a coherent one.
set -euo pipefail

SRC="/c/dev/odisha-d11"
DST="/i/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW"
EDITIONS="${1:-}"

say () { printf '  %s\n' "$*"; }

echo "=== the pack (source of truth for the build) ==="
for f in sources.yaml derived_columns.sql validation.yaml build_crosswalk.py crosswalk.csv; do
  cp "$SRC/Insights/domain_pack_prdw/$f" "$DST/Insights/domain_pack_prdw/$f"; say "$f"
done
for f in "$SRC"/Insights/domain_pack_prdw/views/*.sql; do
  cp "$f" "$DST/Insights/domain_pack_prdw/views/"; say "views/$(basename "$f")"
done

echo "=== the engine and pipeline configs ==="
for f in phase2_engine.py phase4a_engine.py phase4b_engine.py phase5_ranking.py \
         phase5b_report.py phase5b_dual_reports.py phase5c_global_feed.py \
         phase5d_retrieval_corpus.py phase5f_decompose.py; do
  cp "$SRC/Insights/src/$f" "$DST/Insights/src/$f"; say "src/$f"
done
cp "$SRC/DiscoverChat/glossary.py" "$DST/DiscoverChat/glossary.py"; say "DiscoverChat/glossary.py"

echo "=== build reports (committed; the Parquets are not) ==="
for f in validation_report.txt view_summaries.txt; do
  cp "$SRC/Insights/reports_prdw/$f" "$DST/Insights/reports_prdw/$f"; say "reports_prdw/$f"
done

echo "=== the WP's own record ==="
mkdir -p "$DST/handoffs/WPD11_calibration"
cp "$SRC/handoffs/WPD11_REPORT.md" "$DST/handoffs/WPD11_REPORT.md"; say "WPD11_REPORT.md"
cp -r "$SRC/handoffs/WPD11_calibration/." "$DST/handoffs/WPD11_calibration/"
say "WPD11_calibration/ ($(ls "$SRC/handoffs/WPD11_calibration" | wc -l) entries)"

if [ "$EDITIONS" = "--editions" ]; then
  echo "=== the regenerated edition set (T7) ==="
  for f in global_feed.json global_feed_source_set.json insight_prose.json insight_feed.md \
           retrieval_corpus.json.gz retrieval_corpus.npy retrieval_corpus_stamp.json \
           decompose_corpus.json.gz decompose_corpus.npy decompose_corpus_stamp.json \
           view1_candidates.json view2_candidates.json view3_candidates.json view4_candidates.json \
           view1_ranked.json view2_ranked.json view3_ranked.json view4_ranked.json \
           view1_data_quality.json view2_data_quality.json view3_data_quality.json view4_data_quality.json; do
    [ -f "$SRC/Insights/metainsights/$f" ] && { cp "$SRC/Insights/metainsights/$f" "$DST/Insights/metainsights/$f"; say "metainsights/$f"; }
  done
  for f in executive_metainsight_report.md executive_metainsight_report.pdf global_feed.md \
           gamma_0.1_report.md gamma_0.3_report.md gamma_0.5_report.md \
           gamma_0.7_report.md gamma_0.9_report.md; do
    [ -f "$SRC/Insights/reports_prdw/$f" ] && { cp "$SRC/Insights/reports_prdw/$f" "$DST/Insights/reports_prdw/$f"; say "reports_prdw/$f"; }
  done
else
  echo "=== editions NOT copied (pass --editions once T7 has run in full) ==="
fi

echo
echo "Done. Nothing was committed and nothing was pushed."
