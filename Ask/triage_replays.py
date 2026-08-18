"""Cross-reference the graded replays; report only what replays agree on.

BOOTSTRAP DISCIPLINE, MADE MECHANICAL. Routing flips on roughly 3% of questions
between identical replays (PROJECT_PLAN §6), so a single miss is evidence of
nothing. WP-4's rule is that no failure may be reported as a regression without
appearing in at least 2 of 3 replays. Reading three graded files by eye is how
that rule gets quietly skipped, so it is a script.

  python triage_replays.py eval_full_graded_run1.json eval_full_graded_run2.json ...

Prints three sections:
  CONFIRMED   a non-hit in >= majority of replays — the real triage list
  NOISE       a non-hit in a minority — listed, never acted on
  FLIPS       every question whose verdict was not identical across replays,
              which is the flip rate the consistency benchmark is about
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# `clarify_as_ratified` is here for the reason D31.3 gives: a clarification the
# gold row itself declares as the ratified outcome (G1524's tier question, under
# D18.P3) is the system behaving as designed, and counting it as a failure made
# the project pay an accuracy point for shipping what it had ruled.
PASSING = {"hit", "partial", "clarify_as_ratified", "clarify_gold_offered",
           "excluded"}


def main(paths: list[Path]) -> None:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    n_runs = len(runs)
    majority = n_runs // 2 + 1

    verdicts: dict[int, list[str]] = defaultdict(list)
    picked: dict[int, list[str]] = defaultdict(list)
    meta: dict[int, dict] = {}
    for recs in runs:
        for r in recs:
            verdicts[r["n"]].append(r["verdict"])
            picked[r["n"]].append(str(r.get("query_id")))
            meta.setdefault(r["n"], r)

    print(f"replays: {n_runs}  ({', '.join(p.name for p in paths)})")
    print(f"questions: {len(verdicts)}   majority threshold: {majority}/{n_runs}\n")

    for name, recs in zip(paths, runs):
        counts = Counter(r["verdict"] for r in recs)
        passing = sum(v for k, v in counts.items() if k in PASSING)
        print(f"  {name.stem:<28} behaving correctly "
              f"{passing/len(recs):6.1%}  ({passing}/{len(recs)})  "
              + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    confirmed, noise = [], []
    for n, vs in verdicts.items():
        bad = [v for v in vs if v not in PASSING]
        if not bad:
            continue
        (confirmed if len(bad) >= majority else noise).append((n, vs))

    print(f"\n── CONFIRMED failures (non-hit in >= {majority}/{n_runs}) — "
          f"{len(confirmed)} ──")
    for n, vs in sorted(confirmed):
        rec = meta[n]
        print(f"  #{n} [{'/'.join(sorted(set(vs)))}] gold={rec.get('gold')} "
              f"picked={'/'.join(sorted(set(picked[n])))}")
        print(f"      {rec['q'][:96]}")

    print(f"\n── REPLAY NOISE (non-hit in a minority) — {len(noise)} ──")
    print("  Listed, not acted on: a miss this unstable is the ~3% flip rate,")
    print("  not a defect. Acting on it is how a threshold gets tuned to noise.")
    for n, vs in sorted(noise):
        print(f"  #{n} {'/'.join(vs)}  {meta[n]['q'][:70]}")

    flips = {n: vs for n, vs in verdicts.items() if len(set(vs)) > 1}
    print(f"\n── VERDICT FLIPS across replays — {len(flips)}/{len(verdicts)} "
          f"= {len(flips)/len(verdicts):.1%} ──")
    for n, vs in sorted(flips.items()):
        print(f"  #{n} {' -> '.join(vs)}  {meta[n]['q'][:60]}")

    id_flips = {n: ps for n, ps in picked.items() if len(set(ps)) > 1}
    print(f"\n── ROUTE FLIPS (different query_id across replays) — "
          f"{len(id_flips)}/{len(picked)} = {len(id_flips)/len(picked):.1%} ──")
    for n, ps in sorted(id_flips.items()):
        print(f"  #{n} {' -> '.join(ps)}  {meta[n]['q'][:60]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main([Path(a) for a in sys.argv[1:]])
