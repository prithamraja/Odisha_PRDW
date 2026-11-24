#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D15d: record `SlotExtractor().read_places(q)` for the 369 questions.

    python handoffs/WPD15d_not_found/record_reading.py before.json
    python handoffs/WPD15d_not_found/record_reading.py after.json
    python handoffs/WPD15d_not_found/record_reading.py --compare before.json after.json

The questions: WP-D15b harness set A (the 245 CSV rows and the 53 held
questions), set C (14), and the WPD15d brief's Appendix A (57). --compare:
every field of `after` equals `before`, and the only key `before` has that
`after` lacks is `not_found` (pass mark 1).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "handoffs" / "WPD15b_spelling"))


def appendix_a():
    text = (REPO / "handoffs" / "WPD15d_not_found_off.md").read_text(encoding="utf-8")
    text = text[text.index("## Appendix A"):]
    rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \|$", text, re.M)
    return [(f"A:{int(n):02d}", q.strip(), "STOP" in today) for n, q, today in rows]


def questions():
    from record_geography import questions as set_a
    import harness
    out = [(qid, q) for qid, q in set_a()]
    out += [(f"C:{i:02d}", q) for i, (q, _) in enumerate(harness.SET_C, start=1)]
    out += [(qid, q) for qid, q, _ in appendix_a()]
    return out


def record(target):
    import logging
    logging.basicConfig(level=logging.ERROR)
    from DiscoverChat.slots import SlotExtractor
    se = SlotExtractor()
    qs = questions()
    rec = {qid: {"question": q, "reading": se.read_places(q)} for qid, q in qs}
    (HERE / target).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    stops = [qid for qid, q in qs if rec[qid]["reading"].get("not_found")
             and not rec[qid]["reading"].get("readings")]
    print(f"{len(rec)} questions -> {target}; turns that would end with the message: "
          f"{len(stops)} {stops}")


def compare(a, b):
    before = json.loads((HERE / a).read_text(encoding="utf-8"))
    after = json.loads((HERE / b).read_text(encoding="utf-8"))
    problems, dropped = [], 0
    for qid, x in before.items():
        y = after.get(qid)
        if y is None:
            problems.append(f"{qid}: missing")
            continue
        rb, ra = x["reading"], y["reading"]
        gone = set(rb) - set(ra)
        if gone - {"not_found"}:
            problems.append(f"{qid}: keys gone {sorted(gone)}")
        if set(ra) - set(rb):
            problems.append(f"{qid}: new keys {sorted(set(ra) - set(rb))}")
        for k in set(ra) & set(rb):
            if ra[k] != rb[k]:
                problems.append(f"{qid}: {k} changed")
        dropped += "not_found" in gone
    print(json.dumps({"questions": len(before), "not_found_key_dropped": dropped,
                      "problems": problems[:20], "problem_count": len(problems),
                      "result": "PASS" if not problems else "FAIL"}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    record(sys.argv[1])
