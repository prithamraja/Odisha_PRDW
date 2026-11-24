#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D15c T4.5: the changed step 6 over every stored WP-D15 trial answer.

    python handoffs/WPD15c_trial/standing_offline.py

No model call. For each answer of the four WP-D15 arms (current, sheet,
sheet_choose, sheet_midsize: 168 answers), the place facts that turn handed are
rebuilt by the shipped code (`place.resolve` on the question, the committed
store); the step is run on every attempt the writer made. Writes standing_offline.json and prints every sentence flagged.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import logging
logging.basicConfig(level=logging.ERROR)

from DiscoverChat import checks, place, corpus as corpus_mod     # noqa: E402
from DiscoverChat.slots import SlotExtractor                     # noqa: E402
from DiscoverChat.experiments import held_picks                  # noqa: E402

TRIAL = REPO / "handoffs" / "WPD15_trial"
ARMS = ["current", "sheet", "sheet_choose", "sheet_midsize"]


def main():
    store, why = place.open_store()
    extractor = SlotExtractor()
    corpus = corpus_mod.load()
    held = {e["id"]: f for e, f in held_picks.usable(held_picks.load_held(), corpus)}
    out = {"answers": 0, "sentences_checked": 0, "phrases": 0, "flagged": []}
    for arm in ARMS:
        run = json.loads((TRIAL / f"{arm}.json").read_text(encoding="utf-8"))
        for r in run["results"]:
            out["answers"] += 1
            plan = place.resolve(r["question"],
                                 extractor.geography(r["question"])["mentions"], store)
            facts = place.all_facts(place.groups_for(plan, store))
            findings = held.get(r["id"], [])
            # Every attempt the writer made, not only the shown one: the five
            # WP-D15 false alarms were all on first attempts.
            for attempt, text in enumerate(r["attempt_prose"], start=1):
                out["attempts"] = out.get("attempts", 0) + 1
                step = checks.check_standing(text, list(findings) + facts,
                                             facts, mode="log")
                out["sentences_checked"] += step["checked"]
                out["phrases"] += step["phrases"]
                for f in step["failures"]:
                    out["flagged"].append({"arm": arm, "id": r["id"],
                                           "run": r.get("run", 1),
                                           "attempt": attempt, **f})
    (Path(__file__).parent / "standing_offline.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out['answers']} answers ({out['attempts']} attempts), {out['sentences_checked']} sentences citing "
          f"a place fact, {out['phrases']} standing phrases, "
          f"{len(out['flagged'])} flagged")
    for f in out["flagged"]:
        print(f"  {f['arm']} {f['id']} r{f['run']}: {f['phrase']!r} | "
              f"{checks.strip_tags(f['sentence'])} | {f['cited_place_facts']}")


if __name__ == "__main__":
    main()
