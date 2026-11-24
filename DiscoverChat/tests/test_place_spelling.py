# -*- coding: utf-8 -*-
"""WP-D15b -- place names typed with spelling mistakes. Offline: no model.

    python -m pytest DiscoverChat/tests/test_place_spelling.py -q

The sample cases run on Ask's registry and the committed sheet store; the
"several close names" path (R22) runs on a made-up registry, because the
sample has no such case.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from DiscoverChat import config  # noqa: F401  -- first, so Ask/ is on sys.path
from DiscoverChat import assemble, classifier, place
from DiscoverChat.retrieval import Result
from DiscoverChat.slots import SlotExtractor


class FakeValidator:
    """A made-up registry: exact names only (and Ask's aliases, which point at
    names this registry does not hold, so none resolves)."""

    def __init__(self, names):
        self.names = names

    def registry_values(self, level):
        return [n if isinstance(n, str) else n[0] for n in self.names.get(level, [])]

    def validate(self, surface, level):
        for n in self.names.get(level, []):
            name, code = (n, None) if isinstance(n, str) else n
            if name.casefold() == str(surface).strip().casefold():
                return SimpleNamespace(resolved_value=name, resolved_code=code)
        raise ValueError(surface)


def loose(geo):
    return [(r["level"], r["name"], r["typed"]) for r in geo["readings"]
            if r["how"] == "loose"]


class _Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.se = SlotExtractor()
        cls.store, why = place.open_store()
        if cls.store is None:
            raise unittest.SkipTest(why)

    def line(self, text):
        return place.reading_note(text, self.se.read_places(text)["readings"])


class LinesTests(_Sample):
    """The T2 table."""

    def test_one_close_match(self):
        self.assertEqual(self.line("How is Barpalli block doing?"),
                         'Reading "Barpalli" as Barpali block.')

    def test_both_levels_r4(self):
        self.assertEqual(self.line("What should I know about Kalimella?"),
                         'Reading "Kalimella" as Kalimela block. For the Gram '
                         'Panchayat, ask about "Kalimela GP".')
        plan = place.resolve("What should I know about Kalimella?",
                             self.se.read_places("What should I know about Kalimella?")["mentions"],
                             self.store,
                             readings=self.se.read_places("What should I know about Kalimella?")["readings"])
        self.assertEqual([(p["level"], p["code"]) for p in plan.places], [("block", "3843")])
        self.assertEqual(plan.note, "")          # said once, by the reading line

    def test_two_places_one_misspelt(self):
        self.assertEqual(self.line("Compare Kalimela block and Barpalli block"),
                         'Reading "Barpalli" as Barpali block.')

    def test_level_word_beats_an_exact_match(self):
        text = "How is Sharagada block doing?"
        geo = self.se.read_places(text)
        self.assertEqual(self.line(text), 'Reading "Sharagada" as Sheragada block.')
        self.assertEqual(geo["gp_names"], [])
        self.assertEqual(geo["blocks"], ["Sheragada"])

    def test_exact_name_never_reread(self):
        geo = self.se.read_places("How is Sharagada doing?")
        self.assertEqual(loose(geo), [])
        self.assertEqual(geo["gp_names"], ["Sharagada"])

    def test_aliases_are_silent(self):
        geo = self.se.read_places("Tell me about Khurda")
        self.assertEqual(geo["districts"], ["Khordha"])
        self.assertEqual([r["how"] for r in geo["readings"]], ["alias"])
        self.assertEqual(self.line("Tell me about Khurda"), "")

    def test_exact_question_fields_unchanged(self):
        with mock.patch.object(config, "LOOSE_PLACES", False):
            off = self.se.read_places("What should I know about Kalimela?")
        on = self.se.read_places("What should I know about Kalimela?")
        for key in ("gp_lgd_codes", "gp_names", "blocks", "districts", "mentions"):
            self.assertEqual(on[key], off[key], key)
        self.assertNotIn("readings", off)
        self.assertEqual(loose(on), [])

    def test_switch_off(self):
        with mock.patch.object(config, "LOOSE_PLACES", False):
            geo = self.se.read_places("What should I know about Kalimella?")
        self.assertEqual((geo["blocks"], geo["gp_names"]), ([], []))
        self.assertNotIn("readings", geo)

    def test_every_ask_resolves(self):
        text = "What should I know about Kalimella?"
        for c in place.loose_choices(text, self.se.read_places(text)["readings"]):
            alt = c["alternative"]
            ask = place._ask({"name": alt["name"], "level": alt["level"]})
            geo = self.se.read_places(ask)
            plan = place.resolve(ask, geo["mentions"], self.store, readings=geo["readings"])
            self.assertEqual([(p["level"], p["name"]) for p in plan.places],
                             [(alt["level"], alt["name"])])


class NotFoundTests(_Sample):
    """The T3 cases."""

    def test_close_name_offered(self):
        nf = self.se.read_places("How is Bhedan block doing?")["not_found"]
        self.assertEqual(place.not_found_message(nf),
                         'I could not find a place called "Bhedan" in the data.\n'
                         'Close names in the data: Bheden block.')

    def test_nothing_close(self):
        nf = self.se.read_places("How is Rampur block doing?")["not_found"]
        self.assertEqual(place.not_found_message(nf),
                         'I could not find a place called "Rampur" in the data.')

    def test_unmarked_is_left_alone(self):
        geo = self.se.read_places("Is Laxmipoor behind on anything?")
        self.assertEqual((geo["readings"], geo["not_found"]), ([], []))

    def test_lowercase_marked_words_are_not_places(self):
        # Hindi words typed in English beside a level word (set A rows).
        for text in ("Khordha me kitne GP ka GPDP approval pending hai?",
                     "How many assets were created in each GP during 2024-2025?"):
            self.assertEqual(self.se.read_places(text)["not_found"], [], text)

    def _turn(self, text):
        se = self.se

        class R:
            extractor = se
            corpus = SimpleNamespace(all=lambda: [])
        a = assemble.Assembler(R(), allow_model=False, use_judge=False, sheets=self.store)
        searched = []

        def ret(message, turn_id=None):
            searched.append(message)
            return (Result(slots=se.extract(message), hits=[], considered=0,
                           best_cosine=0.0, threshold=config.CANDIDATE_FLOOR,
                           collapsed_count=0), {"used": False})
        a._retrieve = ret
        with mock.patch.object(assemble.classifier, "classify",
                               return_value=classifier.Routing(
                                   move=classifier.RETRIEVE, source="rule", reason="t")):
            return a.answer(text), searched

    def test_the_turn_ends_with_the_message(self):
        answer, searched = self._turn("How is Bhedan block doing?")
        self.assertEqual(searched, [], "a not-found turn searched")
        self.assertTrue(answer.text.startswith(
            'I could not find a place called "Bhedan" in the data.\n'
            'Close names in the data: Bheden block.\n\n('))
        self.assertEqual(answer.place["mode"], "not_found")
        self.assertEqual(answer.findings, [])

    def test_another_place_read_first_line_above(self):
        answer, searched = self._turn("How is Rampur block doing compared with Barpali block?")
        self.assertEqual(len(searched), 1)
        self.assertTrue(answer.text.startswith(
            'I could not find a place called "Rampur" in the data.'))
        self.assertNotIn("Close names", answer.text)
        self.assertEqual([p["name"] for p in answer.place["answered"]], ["Barpali"])

    def test_the_line_leads_a_turn_with_no_sheet(self):
        answer, _ = self._turn("Compare Kalimella, Bheden, Laxmipur and Boipariguda")
        self.assertTrue(answer.text.startswith('Reading "Kalimella" as Kalimela block.'))
        self.assertEqual(answer.place["mode"], "no_sheet")
        self.assertTrue(answer.lead.startswith('Reading "Kalimella"'))

    def test_a_sheet_turn_carries_the_line_and_the_facts(self):
        answer, _ = self._turn("How is Barpalli block doing?")
        self.assertTrue(answer.text.startswith('Reading "Barpalli" as Barpali block.'))
        self.assertEqual(answer.place["mode"], "full")
        self.assertEqual(answer.place["readings"][0]["how"], "loose")
        self.assertEqual(answer.place["readings"][0]["typed"], "Barpalli")


class MadeUpRegistryTests(unittest.TestCase):
    """R22 and the tie rule, on names the sample does not have."""

    def extractor(self, names):
        return SlotExtractor(validator=FakeValidator(names))

    def test_several_close_names(self):
        se = self.extractor({"block": ["Gopalpur", "Gopalpura", "Gopalapur", "Gopapur"],
                             "district": ["Ganjam"], "gp": [("Tikiri", "1")]})
        text = "How is Gopalpure doing?"
        geo = se.read_places(text)
        self.assertEqual(loose(geo), [("block", "Gopalpur", "Gopalpure")])
        self.assertEqual(place.reading_note(text, geo["readings"]),
                         'Reading "Gopalpure" as Gopalpur block. Other close names: '
                         'Gopalapur block, Gopalpura block, Gopapur block.')
        payload = place.spelling_payload(text, geo["readings"], geo["not_found"])
        self.assertEqual([c["ask"] for c in payload["close_names"]],
                         ["Gopalapur block", "Gopalpura block", "Gopapur block"])

    def test_tie_block_before_gp(self):
        se = self.extractor({"block": ["Gopalpura"], "gp": [("Gopalapur", "7")],
                             "district": ["Ganjam"]})
        geo = se.read_places("How is Gopalpure doing?")
        self.assertEqual(loose(geo)[0][:2], ("block", "Gopalpura"))

    def test_tie_then_the_alphabet(self):
        se = self.extractor({"block": ["Gopalpura", "Gopalapur"], "gp": [("Tikiri", "1")],
                             "district": ["Ganjam"]})
        geo = se.read_places("How is Gopalpure doing?")
        self.assertEqual(loose(geo)[0][:2], ("block", "Gopalapur"))

    def test_the_choice_is_the_same_every_run(self):
        se = self.extractor({"block": ["Gopalpur", "Gopalpura", "Gopalapur", "Gopapur"],
                             "district": ["Ganjam"], "gp": [("Tikiri", "1")]})
        first = se.read_places("How is Gopalpure doing?")["readings"]
        for _ in range(5):
            self.assertEqual(se.read_places("How is Gopalpure doing?")["readings"], first)


if __name__ == "__main__":
    unittest.main()
