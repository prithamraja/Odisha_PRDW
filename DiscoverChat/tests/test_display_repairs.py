# -*- coding: utf-8 -*-
"""WP-D13 Fix 7 T1 (D66): no doubled words in display sentences.

`glossary.render` translated text that was already in officer words a second
time: "across 7 LSDG theme values" became "across 7 LSDG LSDG theme values".
The rule now: a replacement is skipped where the text at that place already
reads as the replacement. Offline, no model calls. Run:
    python -m pytest DiscoverChat/tests/test_display_repairs.py -q
"""
from __future__ import annotations

import re
import unittest

from DiscoverChat import config  # noqa: F401  -- first, puts Insights/src on the path
from DiscoverChat import checks, glossary
from DiscoverChat import corpus as corpus_mod

DOUBLE = re.compile(r"\b([A-Za-z]{3,})\s+\1\b", re.I)
_CORPUS = None


def _corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = corpus_mod.load()
    return _CORPUS


def _old_render(text: str, view: str) -> str:
    """The pre-fix pass: the same table and pattern, every match replaced."""
    if not text or view not in glossary._CONFIGS:
        return text
    table, pattern = glossary._substitution(view)
    return pattern.sub(lambda m: table[m.group(0)], text)


def _old_display(record) -> str:
    shown = _old_render(record.sentence, record.view)
    if record.is_decomposition:
        shown = glossary.direction_in_words(
            shown, record.data.get("measure", ""), record.data.get("signs", ""))
    return shown


def _new_doubles(shown: str, stored: str) -> list:
    already = {m.group(0).lower() for m in DOUBLE.finditer(stored)}
    return [m.group(0) for m in DOUBLE.finditer(shown)
            if m.group(0).lower() not in already]


def _removal_only(after: str, before: str) -> bool:
    words = iter(before.split())
    return all(word in words for word in after.split())


class RenderRuleTests(unittest.TestCase):
    def test_already_translated_text_is_left_alone(self):
        cases = {
            "across 7 LSDG theme values": "across 7 LSDG theme values",
            "across 7 theme values": "across 7 LSDG theme values",
            "the largest theme": "the largest LSDG theme",
            "the LSDG theme Theme 4": "the LSDG theme Theme 4",
        }
        for text, want in cases.items():
            self.assertEqual(glossary.render(text, "view1"), want, text)

    def test_a_longer_phrase_already_present_is_left_alone(self):
        # `banks` -> "reported banks and cooperative banks"; the phrase holds
        # the word twice, and both copies sit inside the phrase.
        text = "reported banks and cooperative banks totals 24 facilities"
        self.assertEqual(glossary.render(text, "view4"), text)
        self.assertEqual(glossary.render("banks totals 24 facilities", "view4"),
                         "reported banks and cooperative banks totals 24 "
                         "facilities")

    def test_raw_column_names_still_translate(self):
        self.assertEqual(glossary.render("fund_untied_total in gp_name values",
                                         "view1"),
                         _old_render("fund_untied_total in gp_name values",
                                     "view1"))
        self.assertEqual(glossary.raw_columns(
            glossary.render("fund_untied_total", "view1"), "view1"), [])


class CorpusSweepTests(unittest.TestCase):
    """Every display sentence of both corpora, before and after."""

    @classmethod
    def setUpClass(cls):
        cls.changed, cls.same, cls.problems = [], 0, []
        for record in _corpus().all():
            before, after = _old_display(record), record.display_sentence()
            if _new_doubles(after, record.sentence):
                cls.problems.append((record.id, "doubled word left"))
            if checks.numerals(after) != checks.numerals(before):
                cls.problems.append((record.id, "a digit changed"))
            if before == after:
                cls.same += 1
                continue
            cls.changed.append((record, before, after))

    def test_no_doubled_word_the_stored_sentence_lacks(self):
        self.assertEqual(self.problems, [])

    def test_only_the_doubled_sentences_change(self):
        self.assertEqual(len(self.changed), 6656)
        self.assertEqual(self.same, 71183 - 6656)
        for record, before, after in self.changed:
            self.assertTrue(_new_doubles(before, record.sentence), record.id)

    def test_a_change_only_removes_the_repetition(self):
        exact, garbled = 0, []
        for record, before, after in self.changed:
            self.assertTrue(_removal_only(after, before), record.id)
            removed = len(before.split()) - len(after.split())
            if removed == len(_new_doubles(before, record.sentence)):
                exact += 1
            else:
                garbled.append(record)
        self.assertEqual(exact, 6498)
        # The other 158: view4's "reported banks and cooperative banks",
        # which the old pass expanded twice inside itself (a 16-word garble).
        self.assertEqual(len(garbled), 158)
        self.assertTrue(all("reported banks and cooperative banks"
                            in r.display_sentence() for r in garbled))

    def test_member_labels_render_as_before(self):
        """The layout's member labels go through `render` too (WP-D12 §8)."""
        labels = set()
        for record in _corpus().all():
            if record.is_decomposition:
                for member in corpus_mod.members_of(record.data):
                    labels.add((record.view, str(member.get("member", ""))))
        changed = [(v, m) for v, m in labels
                   if glossary.render(m, v) != _old_render(m, v)]
        self.assertGreater(len(labels), 400)
        self.assertEqual(changed, [])


if __name__ == "__main__":
    unittest.main()
