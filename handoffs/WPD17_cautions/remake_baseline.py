#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D17 T4.2: re-make WP-D15's switch-off baseline on the new breakdown store.

    python handoffs/WPD17_cautions/remake_baseline.py <old_code_dir> <mirror>

<old_code_dir> holds the chat's code as it was before WP-D15 (commit f0c5efb:
DiscoverChat/ and Insights/src/ from `git archive f0c5efb`), Ask/, and the NEW
breakdown store under Insights/metainsights/. The questions and the query
vectors are WP-D15's own (<mirror>/handoffs/WPD15_trial/offline_baseline_*),
so no query is embedded and the answers differ from the old baseline only
where the store changed. Writes <mirror>/handoffs/WPD15_trial/
offline_baseline_answers.json.gz in WP-D15's layout, and prints which answers
changed against the previous file.
"""
import gzip
import json
import sys
from pathlib import Path

old_code, mirror = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(old_code))
import logging                                                     # noqa: E402
logging.basicConfig(level=logging.ERROR)
import numpy as np                                                 # noqa: E402

from DiscoverChat import assemble, config                          # noqa: E402
from DiscoverChat.retrieval import Retriever                       # noqa: E402

assert not (old_code / "DiscoverChat" / "place.py").exists(), \
    "this is not the pre-WP-D15 code"
assert Path(config.__file__).resolve().is_relative_to(old_code.resolve()), \
    f"config imported from {config.__file__}, not the old code"

trial = mirror / "handoffs" / "WPD15_trial"
with gzip.open(trial / "offline_baseline_answers.json.gz", "rt", encoding="utf-8") as fh:
    previous = json.load(fh)
vectors = np.load(trial / "offline_baseline_vectors.npy")

retriever = Retriever()
retriever._query_cache = {t: vectors[i] for i, t in enumerate(previous["vector_texts"])}
assembler = assemble.Assembler(retriever, allow_model=False)
answers = {}
for q in previous["questions"]:
    a = assembler.answer(q)
    d = a.as_dict()
    d["citations_full"] = a.citations
    answers[q] = json.loads(json.dumps(d, ensure_ascii=False, sort_keys=True))

out = dict(previous)
out["candidate_set_id"] = config.load_stamp()["candidate_set_id"]
out["answers"] = answers
out["what_this_is"] = (
    previous["what_this_is"] + " Re-made 2026-11-24 for WP-D17 (R28): the same "
    "code (f0c5efb), the same questions and query vectors, on the rebuilt "
    "breakdown store without its four typed-in cautions "
    "(handoffs/WPD17_cautions/remake_baseline.py).")
with gzip.open(trial / "offline_baseline_answers.json.gz", "wt", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, sort_keys=True)

changed = [q for q in previous["questions"] if previous["answers"][q] != answers[q]]
print(f"{len(answers)} answers re-made from {old_code}; {len(changed)} differ from "
      f"the previous baseline:")
for q in changed:
    fields = sorted(k for k in answers[q] if answers[q].get(k) != previous["answers"][q].get(k))
    text_only = previous["answers"][q]["text"] != answers[q]["text"]
    print(f"  {q!r}: {fields}{' (text)' if text_only else ''}")
