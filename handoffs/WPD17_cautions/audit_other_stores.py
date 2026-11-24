#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D17 T2 point 4: the same fault in the other two stores? Reported, fixes
nothing. No model call.

    python handoffs/WPD17_cautions/audit_other_stores.py

Mined insights (retrieval_corpus): every sentence is split into parts (at a
full stop, a semicolon or "Exception:"); a part that holds a digit and stands
word for word on at least MIN_RECORDS records whose subjects (subspace phrase
plus measures) number at least MIN_SUBJECTS is listed. A figure computed for
one subject cannot repeat word for word across many different subjects unless
it is fixed text or a whole-sample figure.

Profile sheets: which existing check proves a sheet sentence is rebuilt from
the sheet's own figures (reported from the builder's own check, run here).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import logging                                                     # noqa: E402
logging.basicConfig(level=logging.ERROR)
from DiscoverChat import corpus as corpus_mod                      # noqa: E402

MIN_RECORDS = 10
MIN_SUBJECTS = 5
SPLIT = re.compile(r"(?<=[.;])\s+|\s+(?=Exception)")


def main():
    corpus = corpus_mod.load()
    parts = defaultdict(lambda: {"records": set(), "subjects": set()})
    findings = [f for f in corpus.all() if not f.is_decomposition]
    for f in findings:
        subject = (f.data.get("subspace_phrase", ""), tuple(f.data.get("measures", [])))
        for part in SPLIT.split(f.sentence):
            part = part.strip()
            if re.search(r"\d", part):
                parts[part]["records"].add(f.id)
                parts[part]["subjects"].add(subject)
    repeated = sorted(((p, len(v["records"]), len(v["subjects"]))
                       for p, v in parts.items()
                       if len(v["records"]) >= MIN_RECORDS
                       and len(v["subjects"]) >= MIN_SUBJECTS),
                      key=lambda x: -x[1])
    import phase5g_profile_sheets as p5g
    from DiscoverChat import profile_store
    sheet_check = p5g.check_sentences(profile_store.default_store())
    out = {
        "mined_insights": {
            "records": len(findings),
            "parts_with_a_digit": len(parts),
            "threshold": {"min_records": MIN_RECORDS, "min_subjects": MIN_SUBJECTS},
            "repeated_parts": [{"part": p, "records": n, "subjects": s}
                               for p, n, s in repeated],
        },
        "profile_sheets": {
            "check": "phase5g_profile_sheets.check_sentences (--check 5; gate "
                     "line profile-sheets-formatter-parity)",
            "result": sheet_check,
        },
    }
    path = Path(__file__).parent / "audit_other_stores.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if k != "mined_insights" else
                          {**v, "repeated_parts": v["repeated_parts"][:25]})
                      for k, v in out.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
