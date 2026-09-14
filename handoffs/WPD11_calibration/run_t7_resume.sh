#!/bin/bash
# WP-D11 T7, resumed from step 5.
#
# Steps 1-4 (ranking, global feed, gamma editions, executive report + PDF)
# completed against candidate set d619a72e4fe98d5f and are NOT re-run: they were
# generated after the `_VOLUME_MEASURE` fix, so they already carry view4's
# size-share context, and re-running them would spend LLM calls to reproduce
# artefacts that are already correct. The candidate-set id every artefact stamps
# is derived from the candidate FILE HASHES, not from DISCOVER_RUN_STAMP, so a
# resumed run stamps the same id -- which is what the gate actually checks.
#
# What is re-run, and why:
#   insight_prose    never ran. The first script passed --emit-feed-md on the
#                    build invocation, and that flag renders the shipped sidecar
#                    and EXITS. The old 32-finding / 3-section prose was
#                    re-rendered and no new sidecar was written.
#   retrieval_corpus stopped: Ask's entity registry was absent from the mirror.
#                    Ask/data/panchayat_1.duckdb is now in place.
set -euo pipefail

cd "$(dirname "$0")/../.."
LOG=handoffs/WPD11_calibration/t7_run
mkdir -p "$LOG"

export DISCOVER_RUN_STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "DISCOVER_RUN_STAMP=$DISCOVER_RUN_STAMP" | tee "$LOG/stamp_resume.txt"

step () {
  local name="$1"; shift
  echo ""
  echo "=============================================================="
  echo "T7 STEP: $name"
  echo "=============================================================="
  "$@" 2>&1 | tee "$LOG/$name.log"
  local rc="${PIPESTATUS[0]}"
  echo "  -> exit $rc"
  return "$rc"
}

step insight_prose    python Insights/src/phase5e_insight_prose.py
step insight_feed_md  python Insights/src/phase5e_insight_prose.py \
                             --emit-feed-md --no-reading-notes
step retrieval_corpus python Insights/src/phase5d_retrieval_corpus.py
step decompose_corpus python Insights/src/phase5f_decompose.py

step check_editions   python Insights/reports_prdw/check_editions_prdw.py
step check_feed       python Insights/reports_prdw/check_feed_contract.py
step check_prose      python Insights/reports_prdw/check_insight_prose.py

step chat_gates       python DiscoverChat/gates.py
step chat_tests       python -m unittest discover -s DiscoverChat/tests -v
step chat_gates_live  python DiscoverChat/gates.py --live

echo ""
echo "=============================================================="
echo "T7 RESUME COMPLETE — stamp $DISCOVER_RUN_STAMP"
echo "=============================================================="
