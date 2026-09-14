#!/bin/bash
# =============================================================================
# WP-D11b — copy the regenerated edition set from the mirror back to Drive
# =============================================================================
# The CODE was edited on the Drive tree directly and copied INTO the mirror, so
# nothing under Insights/src, Insights/reports_prdw/*.py or DiscoverChat/ is
# copied here. What comes back is build output, from ONE candidate set, and the
# run's own evidence.
#
# It also RETIRES the two unsplit vector files on Drive (T1): the split layout
# never writes them, the new stamps do not name them, and at decompose size the
# single file is over GitHub's 100 MB limit. The commit that adopts this WP must
# record their deletion.
#
# NO GIT OPERATION IS PERFORMED. The operator commits. Refuses to run unless
# stage B finished and wrote its summary, so a partial edition set can never be
# copied over a coherent one.
set -euo pipefail

SRC="/c/dev/odisha-d11b"
DST="/i/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW"
say () { printf '  %s\n' "$*"; }

[ -f "$SRC/handoffs/WPD11b_calibration/t5_run/stage_b_summary.txt" ] || {
  echo "STOP: stage B has not completed (no t5_run/stage_b_summary.txt)"; exit 2; }

echo "=== metainsights (one candidate set) ==="
for f in global_feed.json global_feed_source_set.json insight_prose.json insight_feed.md \
         view1_candidates.json view2_candidates.json view3_candidates.json view4_candidates.json \
         view1_ranked.json view2_ranked.json view3_ranked.json view4_ranked.json \
         view1_data_quality.json view2_data_quality.json view3_data_quality.json view4_data_quality.json \
         retrieval_corpus.json.gz retrieval_corpus_stamp.json \
         decompose_corpus.json.gz decompose_corpus_stamp.json; do
  cp "$SRC/Insights/metainsights/$f" "$DST/Insights/metainsights/$f"; say "metainsights/$f"
done
for f in "$SRC"/Insights/metainsights/retrieval_corpus.part*.npy \
         "$SRC"/Insights/metainsights/decompose_corpus.part*.npy; do
  cp "$f" "$DST/Insights/metainsights/"; say "metainsights/$(basename "$f")"
done

echo "=== retire the unsplit vector files (T1) ==="
for f in retrieval_corpus.npy decompose_corpus.npy; do
  if [ -f "$DST/Insights/metainsights/$f" ]; then
    rm "$DST/Insights/metainsights/$f"; say "removed metainsights/$f"
  fi
done

echo "=== reports ==="
for f in executive_metainsight_report.md executive_metainsight_report.pdf global_feed.md \
         gamma_0.1_report.md gamma_0.3_report.md gamma_0.5_report.md \
         gamma_0.7_report.md gamma_0.9_report.md; do
  cp "$SRC/Insights/reports_prdw/$f" "$DST/Insights/reports_prdw/$f"; say "reports_prdw/$f"
done
mkdir -p "$DST/Insights/reports_prdw/wpd11b_run"
cp -r "$SRC/Insights/reports_prdw/wpd11b_run/." "$DST/Insights/reports_prdw/wpd11b_run/"
say "reports_prdw/wpd11b_run/ (the prose build's call logs)"

echo "=== the WP's evidence ==="
cp -r "$SRC/handoffs/WPD11b_calibration/." "$DST/handoffs/WPD11b_calibration/"
say "handoffs/WPD11b_calibration/"

echo
echo "Done. Nothing was committed and nothing was pushed."
