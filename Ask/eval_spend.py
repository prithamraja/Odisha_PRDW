"""The spend guard every paid eval harness goes through.

WHY THIS EXISTS (standing discipline §3a, WP-4a §7.3). WP-2 found
`LiveExtractionTests` making ~7 paid OpenAI calls on every suite run: it
`load_dotenv()`d the keyed `.env`, then "skipped if no key" — which on a machine
that HAS a key is not a skip. The eval harnesses were one layer up from the same
trap. `python recall_eval.py` embedded the whole catalogue plus every gold
question; `python run_full_eval.py` replayed 209 questions through the real
router, each one an embed + a rerank + an extraction. Neither printed what it
was about to do, and neither asked.

So: print the estimate, then require an explicit confirmation. `--yes` on the
command line for a person, `PRDW_EVAL_CONFIRM=1` for a scripted run — the same
opt-in shape WP-2 gave the live extraction tests, for the same reason.

The estimate is deliberately a CALL count rather than a rupee figure: token
prices move and a wrong number is worse than none, while "209 questions x 3
calls" is exactly what a reader needs to decide whether to press go. Report the
actual totals afterwards, from the run.
"""
from __future__ import annotations

import os
import sys

CONFIRM_ENV = "PRDW_EVAL_CONFIRM"


def confirm_spend(
    harness: str,
    items: list[tuple[str, int]],
    *,
    confirmed: bool = False,
) -> None:
    """Print the call estimate and stop unless the run was confirmed.

    `items` is [(what, how many API calls)]. A zero-call item is still printed —
    "0 (cached)" is information, and a reader who expected a charge and sees
    zero has learned the cache is working rather than that nothing ran.

    Exits with status 2 rather than raising, because the caller is a __main__
    script and a traceback would bury the one line that matters.
    """
    total = sum(max(0, n) for _, n in items)
    width = max((len(label) for label, _ in items), default=0)
    print(f"\n── {harness}: estimated API spend ──")
    for label, count in items:
        print(f"  {label:<{width}}  {count if count else '0 (cached)'} calls")
    print(f"  {'TOTAL':<{width}}  ~{total} calls")

    if confirmed or os.environ.get(CONFIRM_ENV) == "1":
        print("  confirmed — running\n")
        return

    print(
        f"\n  REFUSING TO SPEND. Re-run with --yes, or set {CONFIRM_ENV}=1 for "
        f"an unattended run.\n"
        f"  Nothing was sent; no API client has been constructed.\n"
    )
    sys.exit(2)
