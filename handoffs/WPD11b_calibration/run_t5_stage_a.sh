#!/bin/bash
# =============================================================================
# WP-D11b T5, stage A — every artefact that needs NO embedding call
# =============================================================================
# The global feed, the five gamma editions, the executive report + PDF, the
# insight prose sidecar and the feed markdown, all from the one candidate set
# the T4 re-mine and re-rank produced. Stage B (run_t5_stage_b.sh) builds the
# two corpora and runs the checkers and DiscoverChat gates; it is separate only
# because the embedding endpoint's behaviour changed under this WP (see
# WPD11b_REPORT §1) and the corpora wait on the operator's ruling on it. The
# stamp is written ONCE here and re-read by stage B, so the whole set still
# carries one DISCOVER_RUN_STAMP.
#
# Never regenerate a subset of the editions (the brief's cut-line): this runs
# the whole of stage A or stops.
#
# Run from the local mirror root (C:\dev\odisha-d11b), never from the Drive mount.
set -euo pipefail

cd "$(dirname "$0")/../.."
LOG=handoffs/WPD11b_calibration/t5_run
mkdir -p "$LOG"

export DISCOVER_RUN_STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "DISCOVER_RUN_STAMP=$DISCOVER_RUN_STAMP" | tee "$LOG/stamp.txt"
DRIVE_ENV="/i/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW/Insights/.env"

step () {
  local name="$1"; shift
  echo ""
  echo "=============================================================="
  echo "T5 STEP: $name   ($(date -u +%H:%M:%SZ))"
  echo "=============================================================="
  "$@" 2>&1 | tee "$LOG/$name.log"
  local rc="${PIPESTATUS[0]}"
  echo "  -> exit $rc"
  return "$rc"
}

step global_feed      python Insights/src/phase5c_global_feed.py
step gamma            python Insights/src/phase5c_gamma_reports.py
step exec_report      python Insights/src/phase5b_report.py
# The build first, bare; the feed markdown second, from the sidecar it wrote
# (WP-D11 §7.18 -- --emit-feed-md on the build call re-renders the OLD prose).
step insight_prose    python Insights/src/phase5e_insight_prose.py --env "$DRIVE_ENV"
step insight_feed_md  python Insights/src/phase5e_insight_prose.py \
                             --emit-feed-md --no-reading-notes

echo ""
echo "T5 STAGE A COMPLETE — stamp $DISCOVER_RUN_STAMP"
