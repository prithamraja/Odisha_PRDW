"""Regression: nearest-question chips on the miss path must keep entities the
user already gave — "…in Lucknow" must not degrade to "…in a district?".
The fill previously happened only on the reranker near-miss branch, so
zone-level no-match chips rendered with bare placeholders."""
import time
import unittest
from types import SimpleNamespace

from query_router import router
from query_router.models import (
    ClarificationNeeded,
    EntityCandidate,
    EntityNotFound,
    ExtractedEntity,
)


TEMPLATE_MAP = {
    "Q7": {"param_slots": [{"name": "block", "entity_type": "block"}]},
    "Q9": {"param_slots": [{"name": "block", "entity_type": "block"}]},
}

SCORED = [
    ("Q7", "How many claims were filed in {block}?", 0.22),
    ("Q9", "What is enrolment by gender in {block}?", 0.18),
]


class StubValidator:
    def validate(self, value, entity_type):
        if entity_type == "block" and value:
            return SimpleNamespace(resolved_value="Baruasagar")
        raise ValueError(f"unknown {entity_type}: {value}")


class NoMatchChipFillTests(unittest.TestCase):
    def setUp(self):
        self._real_extract = router.extract_entities

        def fake_extract(user_query, slots, client, **kwargs):
            found = {}
            if "block" in slots:
                found["block"] = "baruasagar"
            return found  # never a district → elicitation is skipped

        router.extract_entities = fake_extract

    def tearDown(self):
        router.extract_entities = self._real_extract

    def _run(self):
        return router._no_match(
            SCORED,
            "how many women in baruasagar block",
            "how many women in baruasagar block",
            time.monotonic(),
            validator=StubValidator(),
            openai_client=object(),
            template_map=TEMPLATE_MAP,
        )

    def test_miss_chips_are_prefilled_with_user_entities(self):
        result = self._run()
        self.assertEqual(result.clarification.reason, "no_match")
        labels = [chip.label for chip in result.clarification.options]
        self.assertTrue(labels)
        for label in labels:
            self.assertNotIn("{block}", label)
            self.assertNotIn("a block", label)
        self.assertIn("How many claims were filed in Baruasagar?", labels)

    def test_extraction_failure_degrades_to_placeholders(self):
        def broken_extract(user_query, slots, client, **kwargs):
            raise RuntimeError("LLM down")

        router.extract_entities = broken_extract
        result = self._run()
        labels = [chip.label for chip in result.clarification.options]
        self.assertIn("How many claims were filed in a block?", labels)


FARMER_TEMPLATE_MAP = {
    "F09": {"param_slots": [
        {"name": "farmer_name", "entity_type": "farmer_name"},
        {"name": "village", "entity_type": "village"},
    ]},
}

FARMER_SCORED = [
    ("F09", "Which schemes is {farmer_name} of {village} enrolled in?", 0.21),
]

AMBIGUOUS = [
    EntityCandidate(name="Venkateswarlu Gupta", districts=["Anantapur"]),
    EntityCandidate(name="Venkateswarlu Devi", districts=["Chittoor"]),
]


class RosterValidator:
    """'Rajesh Sri' is one person; 'Venkateswarlu G' is several; 'Zzyzx Kumar'
    is nobody. Nothing here is a district."""

    def validate(self, value, entity_type):
        text = str(value).strip().lower()
        if entity_type == "farmer_name":
            if text == "rajesh sri":
                return ExtractedEntity(
                    slot_name="farmer_name", raw_value=str(value),
                    resolved_value="Rajesh Sri", entity_type="farmer_name",
                    confidence="exact",
                )
            if text.startswith("venkateswarlu"):
                raise ClarificationNeeded(
                    "Several farmers match 'Venkateswarlu G': …",
                    entity_type="farmer_name", raw_value=str(value),
                    candidates=AMBIGUOUS,
                )
        raise EntityNotFound(entity_type, str(value), [])


class AmbiguousNameFillTests(unittest.TestCase):
    """Fix 4.1 — a name that matches several roster entries is ambiguous, not
    unknown. Dropping it put 'a farmer name' where the user's own words go."""

    def setUp(self):
        self._real_extract = router.extract_entities

        def fake_extract(user_query, slots, client, **kwargs):
            # The elicitation probe and the chip-fill probe are separate calls
            # with different slot sets, and they can disagree. Here elicitation
            # finds nothing, so the miss chips are what the user actually sees.
            if slots == ["district", "farmer_name"]:
                return {}
            found = {}
            if "farmer_name" in slots:
                found["farmer_name"] = "Venkateswarlu G"
            if "village" in slots:
                found["village"] = "Nowhere"      # EntityNotFound → dropped
            return found

        router.extract_entities = fake_extract

    def tearDown(self):
        router.extract_entities = self._real_extract

    def test_ambiguous_value_is_kept_raw_and_unknown_values_are_dropped(self):
        fill = router._extract_fill_values(
            "Tell me what we know about Venkateswarlu G",
            ["F09"], FARMER_TEMPLATE_MAP, RosterValidator(), object(),
        )
        self.assertEqual(fill.get("farmer_name"), "Venkateswarlu G")
        self.assertNotIn("village", fill, "a genuinely unknown value stays dropped")

    def test_the_users_name_reaches_the_chip(self):
        result = router._no_match(
            FARMER_SCORED,
            "Tell me what we know about Venkateswarlu G",
            "tell me what we know about venkateswarlu g",
            time.monotonic(),
            validator=RosterValidator(), openai_client=object(),
            template_map=FARMER_TEMPLATE_MAP,
        )
        labels = [chip.label for chip in result.clarification.options]
        self.assertIn(
            "Which schemes is Venkateswarlu G of a village enrolled in?", labels
        )
        for label in labels:
            self.assertNotIn("a farmer name", label)


class FarmerElicitationTests(unittest.TestCase):
    """Fix 4.5 — a bare name gets the measures we hold for that farmer, not a
    chip reading 'a farmer name of a village'. District keeps precedence."""

    def setUp(self):
        self._real_extract = router.extract_entities

    def tearDown(self):
        router.extract_entities = self._real_extract

    def _extract(self, **found):
        def fake_extract(user_query, slots, client, **kwargs):
            self.assertEqual(
                slots, ["district", "farmer_name"],
                "both probes must share ONE extraction call",
            )
            return {k: v for k, v in found.items() if v is not None}

        router.extract_entities = fake_extract

    def _run(self, query):
        return router._no_match(
            FARMER_SCORED, query, query.lower(), time.monotonic(),
            validator=RosterValidator(), openai_client=object(),
            template_map=FARMER_TEMPLATE_MAP,
        )

    def test_a_unique_farmer_gets_elicitation_chips(self):
        self._extract(farmer_name="Rajesh Sri")
        result = self._run("Tell me what we know about Rajesh Sri")
        self.assertEqual(result.clarification.reason, "broad_question")
        self.assertIn("Rajesh Sri", result.clarification.prompt)
        self.assertTrue(result.clarification.options)
        for chip in result.clarification.options:
            self.assertIn("Rajesh Sri", chip.send_text)
            self.assertNotIn("{", chip.send_text)

    def test_an_ambiguous_name_offers_the_query_with_each_candidate_substituted(self):
        """Substituted with a REFERENCE, not a bare name. Where the candidates
        are several people who share one name — four Lakshmi Devis — the name
        gives four identical chips and there is nothing to choose between."""
        self._extract(farmer_name="Venkateswarlu G")
        result = self._run("Tell me what we know about Venkateswarlu G")
        self.assertEqual(result.clarification.reason, "unknown_entity")
        sends = [chip.send_text for chip in result.clarification.options]
        self.assertEqual(len(set(sends)), len(sends), "chips must be distinguishable")
        self.assertIn(
            "Tell me what we know about Venkateswarlu Gupta of Anantapur", sends
        )
        self.assertIn(
            "Tell me what we know about Venkateswarlu Devi of Chittoor", sends
        )

    def test_district_wins_when_the_name_is_also_a_place(self):
        """'How is Krishna doing?' must stay a district elicitation — 'Krishna'
        fuzzy-matches farmer names too."""

        class DistrictAndFarmerValidator(RosterValidator):
            def validate(self, value, entity_type):
                if entity_type == "district" and str(value).lower() == "krishna":
                    return ExtractedEntity(
                        slot_name="district", raw_value=str(value),
                        resolved_value="Krishna", entity_type="district",
                        confidence="exact",
                    )
                return super().validate(value, entity_type)

        self._extract(district="Krishna", farmer_name="Krishna")
        result = router._no_match(
            FARMER_SCORED, "How is Krishna doing?", "how is krishna doing",
            time.monotonic(),
            validator=DistrictAndFarmerValidator(), openai_client=object(),
            template_map=FARMER_TEMPLATE_MAP,
        )
        self.assertEqual(result.clarification.reason, "broad_question")
        self.assertIn("What would you like to know about Krishna?",
                      result.clarification.prompt)
        for chip in result.clarification.options:
            self.assertIn("Krishna", chip.send_text)

    def test_an_unknown_name_falls_through_to_the_generic_miss(self):
        self._extract(farmer_name="Zzyzx Kumar")
        result = self._run("Tell me about Zzyzx Kumar")
        self.assertEqual(result.clarification.reason, "no_match")


if __name__ == "__main__":
    unittest.main()
