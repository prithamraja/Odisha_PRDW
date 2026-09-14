#!/bin/bash
# =============================================================================
# WP-D11b T5, stage B — the two corpora, then every checker and gate
# =============================================================================
# Runs after run_t5_stage_a.sh and re-uses ITS run stamp, so the whole edition
# set carries one DISCOVER_RUN_STAMP. The corpora are built in the split layout
# (T1); the findings corpus embeds only the records the T4 re-mine made new, and
# the decompose corpus should embed nothing (its records are SUM-only and the
# twins are AVG). Every gate below is RECORDED, red or green -- a red gate is a
# result to hand the operator, never a reason to stop recording the others or to
# regenerate prose (the brief's cut-line and D61 ruling 2).
#
# Run from the local mirror root (C:\dev\odisha-d11b).
set -uo pipefail

cd "$(dirname "$0")/../.."
LOG=handoffs/WPD11b_calibration/t5_run
export DISCOVER_RUN_STAMP="$(sed -n 's/^DISCOVER_RUN_STAMP=//p' "$LOG/stamp.txt")"
[ -n "$DISCOVER_RUN_STAMP" ] || { echo "STOP: no stage-A stamp in $LOG/stamp.txt"; exit 2; }
echo "DISCOVER_RUN_STAMP=$DISCOVER_RUN_STAMP (from stage A)"

declare -A RESULT
step () {
  local name="$1"; shift
  echo ""
  echo "=============================================================="
  echo "T5 STEP: $name   ($(date -u +%H:%M:%SZ))"
  echo "=============================================================="
  "$@" 2>&1 | tee "$LOG/$name.log"
  local rc="${PIPESTATUS[0]}"
  echo "  -> exit $rc"
  RESULT[$name]=$rc
  return "$rc"
}

# The corpora must succeed: a stale sidecar may not ship beside a new set.
step retrieval_corpus python Insights/src/phase5d_retrieval_corpus.py || exit 1
step decompose_corpus python Insights/src/phase5f_decompose.py        || exit 1

# The checkers and gates: all of them, whatever each one says.
# --base is REQUIRED by both; the first stage-B run omitted it and both exited
# 2 on argparse without checking anything (WPD11b_REPORT §5). Re-run by hand.
step check_editions   python Insights/reports_prdw/check_editions_prdw.py --base Insights
step check_feed       python Insights/reports_prdw/check_feed_contract.py --base Insights
step check_prose      python Insights/reports_prdw/check_insight_prose.py --rebuild-roster
step chat_gates       python DiscoverChat/gates.py
step chat_tests       python -m unittest discover -s DiscoverChat/tests -v
step chat_gates_live  python DiscoverChat/gates.py --live

echo ""
echo "=============================================================="
echo "T5 STAGE B — stamp $DISCOVER_RUN_STAMP"
for k in retrieval_corpus decompose_corpus check_editions check_feed check_prose \
         chat_gates chat_tests chat_gates_live; do
  printf '  %-18s exit %s\n' "$k" "${RESULT[$k]:-not run}"
done | tee "$LOG/stage_b_summary.txt"
