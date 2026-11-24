#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D15b T1: build DiscoverChat/ordinary_words.json -- the words the loose
place pass never tries, because they are the ordinary words of this domain.

    python handoffs/WPD15b_spelling/build_ordinary_words.py

No outside data and no model. The vocabulary is gathered from what the system
itself already says and reads:
  * every stored and displayed sentence of both insight corpora;
  * every profile sheet sentence;
  * the chat's own word lists (measure keywords, query expansion, decompose
    triggers, number words) and its prompt texts (context_brief);
Ask's question catalogue is deliberately NOT a source: the 245 rows of
test_questions_query_mapping.csv (pass mark 1's set A) are the catalogue's own
questions, so using it would make that test circular.
Place names are NOT removed here. The slot reader removes every token of every
registry name and alias when it starts, so the same file serves the sample and
a statewide name list alike.

Words are lowercased letters only (a-z, apostrophes and hyphens split words);
words of fewer than 3 letters are dropped (the loose pass never tries a single
word under 5 letters anyway).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "Ask"))
import logging
logging.basicConfig(level=logging.ERROR)

WORD = re.compile(r"[A-Za-z]+")


def words(text, out):
    for w in WORD.findall(str(text or "")):
        if len(w) >= 3:
            out.add(w.lower())


def walk(obj, out):
    if isinstance(obj, str):
        words(obj, out)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            walk(k, out)
            walk(v, out)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            walk(v, out)


def main():
    from DiscoverChat import config, context_brief, corpus as corpus_mod
    from DiscoverChat import profile_store
    sources = {}

    vocab = set()
    for f in corpus_mod.load().all():
        words(f.sentence, vocab)
        words(f.display_sentence(), vocab)
    sources["insight corpora (stored and displayed sentences)"] = len(vocab)

    before = len(vocab)
    store = profile_store.default_store()
    for level in profile_store.LEVELS:
        for code in store.codes(level):
            for s in store.sentences(level, code):
                words(s["sentence"], vocab)
                words(s["note"], vocab)
    sources["profile sheet sentences"] = len(vocab) - before

    before = len(vocab)
    for path in (config.DATA_MEASURE_KEYWORDS, config.DATA_QUERY_EXPANSION,
                 config.DATA_DECOMPOSE_TRIGGERS, config.DATA_NUMBER_WORDS):
        walk(json.loads(Path(path).read_text(encoding="utf-8")), vocab)
    for name in dir(context_brief):
        value = getattr(context_brief, name)
        if isinstance(value, str) and name.isupper():
            words(value, vocab)
    sources["the chat's word lists and prompt texts"] = len(vocab) - before

    out = {
        "what_this_is": (
            "WP-D15b: the ordinary words of this domain, which the loose place "
            "pass in slots.py never tries as a misspelt place name. Built by "
            "handoffs/WPD15b_spelling/build_ordinary_words.py from the "
            "system's own sentences and word lists (no outside data). Place "
            "names are removed by the slot reader at start-up, against the "
            "registry it loads, not here. Lowercase."),
        "sources": sources,
        "words": sorted(vocab),
    }
    path = REPO / "DiscoverChat" / "ordinary_words.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(vocab):,} words -> {path}; {sources}")


if __name__ == "__main__":
    main()
