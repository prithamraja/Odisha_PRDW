#!/bin/bash
# WP-D11 T7, final leg. Everything before decompose_corpus is already built
# against candidate set d619a72e4fe98d5f and MUST NOT be re-run -- in particular
# insight_prose, which cost 124 of the 150-call budget.
set -euo pipefail
cd "$(dirname "$0")/../.."
LOG=handoffs/WPD11_calibration/t7_run
mkdir -p "$LOG"
export DISCOVER_RUN_STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
step () {
  local name="$1"; shift
  echo ""; echo "=============================================================="
  echo "T7 STEP: $name"; echo "=============================================================="
  "$@" 2>&1 | tee "$LOG/$name.log"
  local rc="${PIPESTATUS[0]}"; echo "  -> exit $rc"; return "$rc"
}
step decompose_corpus python Insights/src/phase5f_decompose.py
step check_editions   python Insights/reports_prdw/check_editions_prdw.py
step check_feed       python Insights/reports_prdw/check_feed_contract.py
step check_prose      python Insights/reports_prdw/check_insight_prose.py
step chat_gates       python DiscoverChat/gates.py
step chat_tests       python -m unittest discover -s DiscoverChat/tests -v
step chat_gates_live  python DiscoverChat/gates.py --live
echo ""; echo "T7 TAIL COMPLETE"
