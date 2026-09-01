# -*- coding: utf-8 -*-
"""Retrieval, slots and expansion — no model calls, no network.

Run by module name, Ask's convention (the venvs have no pytest and the test
directories have no __init__ discovery):

    python -m unittest DiscoverChat.tests.test_retrieval
"""
import unittest

from DiscoverChat import config, corpus as corpus_mod
from DiscoverChat.retrieval import Retriever, collapse_near_duplicates
from DiscoverChat.slots import SlotExtractor, expand


class ExpansionTests(unittest.TestCase):
    def test_abbreviation_keeps_the_officers_word(self):
        text, applied = expand("How is GPDP spending going?")
        self.assertIn("Gram Panchayat Development Plan", text)
        self.assertIn("GPDP", text)
        self.assertEqual([a["surface"] for a in applied], ["GPDP"])

    def test_longest_pattern_wins(self):
        """'XV FC' must not be consumed as 'FC' or left as two fragments."""
        text, applied = expand("XV FC funds")
        self.assertIn("XV Finance Commission (XV FC)", text)
        self.assertEqual(len(applied), 1)

    def test_expansion_does_not_loop(self):
        """'GP' -> 'Gram Panchayat (GP)' must not re-expand its own output."""
        text, _ = expand("GP")
        self.assertEqual(text.count("Gram Panchayat"), 1)

    def test_unknown_text_is_untouched(self):
        text, applied = expand("Is spending on track in Barpali block?")
        self.assertEqual(text, "Is spending on track in Barpali block?")
        self.assertEqual(applied, [])


class SlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor = SlotExtractor()

    def test_gp_resolves_to_an_lgd_code(self):
        slots = self.extractor.extract("How is Chikilli doing?")
        self.assertEqual(slots.gp_names, ["Chikilli"])
        self.assertTrue(slots.gp_lgd_codes[0].isdigit())

    def test_district_alias_resolves(self):
        slots = self.extractor.extract("what about Sundergarh?")
        self.assertEqual(slots.districts, ["Sundargarh"])

    def test_a_name_that_is_both_gp_and_block_resolves_as_both(self):
        """Kalimela is a Gram Panchayat AND a block. Picking one silently is
        the confidently-wrong class; boosting both is the honest reading."""
        slots = self.extractor.extract("Kalimela sanctions")
        self.assertIn("Kalimela", slots.gp_names)
        self.assertIn("Kalimela", slots.blocks)

    def test_unknown_place_resolves_to_nothing(self):
        slots = self.extractor.extract("How is Nowhereville doing?")
        self.assertFalse(slots.has_geography)

    def test_measure_words_map_to_columns(self):
        slots = self.extractor.extract("Where is money planned but not spent?")
        self.assertIn("overspend_vs_plan", slots.measures)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = corpus_mod.load()

    def test_pin_matches(self):
        """Both corpora, and both under ONE pin (WP-D6).

        The single pin is the load-bearing half. The two files are concatenated
        into one matrix and scored against one query vector, so vectors from
        different pins would not be comparable and the ranking over them would
        be arithmetic on unrelated numbers.
        """
        stamp = config.assert_pin_matches_corpus()
        d_stamp = config.decompose_stamp()
        expected = stamp["records"] + (d_stamp["records"] if d_stamp else 0)
        self.assertEqual(len(self.corpus), expected)
        self.assertEqual(self.corpus.meta["findings"], stamp["records"])
        if d_stamp:
            self.assertEqual(d_stamp["embedding_pin_fingerprint"],
                             stamp["embedding_pin_fingerprint"])

    def test_vectors_are_row_aligned_and_unit_length(self):
        import numpy as np
        self.assertEqual(self.corpus.vectors.shape[0], len(self.corpus))
        norms = np.linalg.norm(self.corpus.vectors, axis=1)
        self.assertTrue(np.allclose(norms, 1.0, atol=1e-3))

    def test_enrichment_separates_what_the_sentence_does_not(self):
        """The reason the enriched text exists, asserted as a fact about the
        corpus: bare sentences collide, enriched texts do not.

        Scoped to the findings, which is where the collision was measured --
        `generate_nl_summary` never names the base subspace, so 2,464 of 4,239
        records share a sentence with some other record. The decomposition
        builder names its slice in every sentence and carries no `bare_text`
        to compare, so the property is not defined for it. Its own uniqueness
        is checked below.
        """
        findings = [r for r in self.corpus.records
                    if r.get("record_type") != "decomposition"]
        bare = {r["bare_text_sha256"] for r in findings}
        rich = {r["embed_text_sha256"] for r in findings}
        self.assertLess(len(bare), len(findings))
        self.assertEqual(len(rich), len(findings))

    def test_every_embedded_text_is_distinct(self):
        """Across BOTH corpora. Two records sharing an embedded text share a
        vector, and retrieval then cannot tell them apart at all — which is the
        failure the enrichment recipe exists to prevent, and adding a second
        corpus is exactly the event that could reintroduce it."""
        texts = {r["embed_text_sha256"] for r in self.corpus.records}
        self.assertEqual(len(texts), len(self.corpus))

    def test_geography_holds_no_engine_tokens(self):
        """'EVEN' is a pattern shape, not a Gram Panchayat."""
        for finding in self.corpus.all():
            self.assertNotIn("EVEN", finding.geography["gp_names"])
            for name in finding.geography["gp_names"]:
                self.assertFalse(name.startswith("PERIOD_"))

    def test_every_finding_carries_the_run_stamp(self):
        """ONE candidate set behind everything an answer can show.

        The findings carry it per record; the decomposition sidecar carries it
        once, on the payload, and `corpus.load` refuses to concatenate two
        corpora whose ids differ. Both are asserted, because an answer prints
        one run stamp and a mixed pair would date half of it wrongly.
        """
        ids = {r["candidate_set_id"] for r in self.corpus.records
               if r.get("record_type") != "decomposition"}
        self.assertEqual(len(ids), 1)
        d_stamp = config.decompose_stamp()
        if d_stamp:
            self.assertEqual(d_stamp["candidate_set_id"], ids.pop())


class DiversityTests(unittest.TestCase):
    class _Fake:
        def __init__(self, fid, sentence):
            self.id, self.sentence = fid, sentence

    def _hit(self, fid, sentence, score):
        from DiscoverChat.retrieval import Hit
        return Hit(finding=self._Fake(fid, sentence), cosine=score, boost=0.0,
                   score=score)

    def test_identical_sentences_collapse_to_the_best(self):
        hits = [self._hit("a", "same", 0.9), self._hit("b", "same", 0.8),
                self._hit("c", "other", 0.7)]
        kept, dropped = collapse_near_duplicates(hits)
        self.assertEqual([h.finding.id for h in kept], ["a", "c"])
        self.assertEqual(dropped, 1)

    def test_the_survivor_keeps_the_collapsed_ids(self):
        hits = [self._hit("a", "same", 0.9), self._hit("b", "same", 0.8)]
        kept, _ = collapse_near_duplicates(hits)
        self.assertEqual(kept[0].collapsed, ["b"])


class BoostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever()

    def test_the_boost_fires_only_on_findings_that_name_the_place(self):
        slots = self.retriever.extractor.extract("How is Chikilli doing?")
        boost, why = self.retriever.structural_boost(slots)
        rows = [i for i, value in enumerate(boost) if value > 0]
        self.assertTrue(rows)
        for row in rows:
            finding = self.retriever.corpus.finding(row)
            self.assertIn("Chikilli", finding.geography["gp_names"])

    def test_no_slots_means_no_boost(self):
        slots = self.retriever.extractor.extract("what is happening")
        boost, _ = self.retriever.structural_boost(slots)
        self.assertEqual(float(boost.max()), 0.0)


if __name__ == "__main__":
    unittest.main()
