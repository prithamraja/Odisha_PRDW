#!/bin/bash
# =============================================================================
# WP-D11 T7 — regenerate EVERY published artefact from the one new candidate set
# =============================================================================
# Handoff §4 / WP-D3b: the feed, the five gamma editions, insight_prose.json +
# insight_feed.md, the executive report + PDF, and both retrieval sidecars all
# derive from ONE candidate set. A mixed set is a defect, so this is one script
# and not a checklist -- either the whole sequence runs or none of it does.
#
# DISCOVER_RUN_STAMP is exported ONCE, at the top, so every artefact generated
# below carries the same stamp. That is the mechanism the "same candidate-set
# hash in every stamp" gate check reads.
#
# Run from the local mirror root (C:\dev\odisha-d11), never from the Drive mount.
set -euo pipefail

cd "$(dirname "$0")/../.."          # -> the mirror root
LOG=handoffs/WPD11_calibration/t7_run
mkdir -p "$LOG"

export DISCOVER_RUN_STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "DISCOVER_RUN_STAMP=$DISCOVER_RUN_STAMP" | tee "$LOG/stamp.txt"

step () {                            # step <name> <command...>
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

# 1. rank all four views (the ranker's own view list now holds view4)
step ranking          python Insights/src/phase5_ranking.py

# 2. the cross-view global feed + its provenance sidecar
step global_feed      python Insights/src/phase5c_global_feed.py

# 3. the five gamma editions (0.1 .. 0.9), discovered from phase4a_engine
step gamma            python Insights/src/phase5c_gamma_reports.py

# 4. the executive report and its PDF  (LLM calls)
step exec_report      python Insights/src/phase5b_report.py

# 5. insight prose, then the feed markdown -- TWO invocations, not one.
#
# `--emit-feed-md` renders the SHIPPED sidecar and EXITS: its own help says
# "no API call, no rebuild of the sidecar". Passing it on the BUILD
# invocation, as the first version of this script did, silently re-renders the
# PREVIOUS candidate set's prose and never writes a new insight_prose.json at
# all -- which is exactly a mixed edition set, and it is invisible unless you
# check the sidecar's mtime. The build must run first, bare.
step insight_prose    python Insights/src/phase5e_insight_prose.py

# Reading notes OFF per D48-1; that flag is `--emit-feed-md only`.
step insight_feed_md  python Insights/src/phase5e_insight_prose.py \
                             --emit-feed-md --no-reading-notes

# 6. the two retrieval sidecars, in the WP-D10 spellings
step retrieval_corpus python Insights/src/phase5d_retrieval_corpus.py
step decompose_corpus python Insights/src/phase5f_decompose.py

# 7. the checkers
step check_editions   python Insights/reports_prdw/check_editions_prdw.py
step check_feed       python Insights/reports_prdw/check_feed_contract.py
step check_prose      python Insights/reports_prdw/check_insight_prose.py

# 8. DiscoverChat: offline gates, unit tests, then the live turns
step chat_gates       python DiscoverChat/gates.py
step chat_tests       python -m unittest discover -s DiscoverChat/tests -v
step chat_gates_live  python DiscoverChat/gates.py --live

echo ""
echo "=============================================================="
echo "T7 COMPLETE — stamp $DISCOVER_RUN_STAMP"
echo "=============================================================="
