#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D15b T0: what `SlotExtractor.geography` returns for every question of
the two real question sets (set A), before any change.

    python handoffs/WPD15b_spelling/record_geography.py <mirror> <out.json>

<mirror> is the tree whose slot reader is recorded (the pre-WP-D15b one for
T0). The questions are read from the WP-D15b mirror's own copies of
judge_picks.json and test_questions_query_mapping.csv.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def questions():
    held = json.loads((REPO / "DiscoverChat" / "experiments" / "judge_picks.json")
                      .read_text(encoding="utf-8"))["entries"]
    out = [("held:" + e["id"], e["question"]) for e in held]
    with open(REPO / "test_questions_query_mapping.csv", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=1):
            # Query codes repeat in the file, so the row number is the key.
            out.append((f"csv:{i:03d}:{row['query_code']}", row["topic"]))
    return out


FIELDS = ("gp_lgd_codes", "gp_names", "blocks", "districts", "mentions")

if __name__ == "__main__":
    mirror, target = sys.argv[1], sys.argv[2]
    sys.path.insert(0, mirror)
    import logging
    logging.basicConfig(level=logging.ERROR)
    from DiscoverChat.slots import SlotExtractor
    se = SlotExtractor()
    record = {}
    for qid, text in questions():
        geo = se.geography(text)
        record[qid] = {"question": text, **{k: geo[k] for k in FIELDS}}
    Path(target).write_text(json.dumps(record, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    print(len(record), "questions recorded from", mirror, "->", target)
