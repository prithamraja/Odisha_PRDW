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


# WP-3 fixture swap. AP's roster was PEOPLE, so the bare-name path probed
# `farmer_name`; PR&DW's roster is PLACES and the same machinery — one
# extraction call, roster disambiguation, reference chips — answers "what about
# Naugaon?". The behaviour asserted is unchanged; only the roster is.
GP_TEMPLATE_MAP = {
    "GPX": {"param_slots": [
        {"name": "gp_name", "entity_type": "gp", "bind": "code"},
        {"name": "date_range", "entity_type": "fiscal_year"},
    ]},
}

GP_SCORED = [
    ("GPX", "What is the GPDP status for {gp_name} in {date_range}?", 0.21),
]

# Three panchayats called Naugaon. The BLOCK is what tells them apart — a
# district holds ~10 blocks and a GP name can repeat inside one, so the district
# alone is not the qualifier.
AMBIGUOUS = [
    EntityCandidate(name="Naugaon", districts=["Bargarh"],
                    parent_place="Barpali", code="900001"),
    EntityCandidate(name="Naugaon", districts=["Khordha"],
                    parent_place="Bhubaneswar", code="900002"),
]


class RosterValidator:
    """'Andhrua' is one panchayat; 'Naugaon' is several; 'Zzyzx' is nobody.
    Nothing here is a district or a block."""

    def validate(self, value, entity_type):
        text = str(value).strip().lower()
        if entity_type == "gp":
            if text == "andhrua":
                entity = ExtractedEntity(
                    slot_name="gp_name", raw_value=str(value),
                    resolved_value="Andhrua", entity_type="gp",
                    confidence="exact",
                )
                entity.resolved_code = "116350"
                return entity
            if text.startswith("naugaon"):
                raise ClarificationNeeded(
                    "2 different gram panchayats are called 'Naugaon': …",
                    entity_type="gp", raw_value=str(value),
                    candidates=AMBIGUOUS,
                )
        raise EntityNotFound(entity_type, str(value), [])

    @staticmethod
    def fiscal_years():
        return ["2023-2024", "2024-2025"]


class AmbiguousNameFillTests(unittest.TestCase):
    """Fix 4.1 — a name that matches several roster entries is ambiguous, not
    unknown. Dropping it put 'a gram panchayat' where the user's own words go."""

    def setUp(self):
        self._real_extract = router.extract_entities

        def fake_extract(user_query, slots, client, **kwargs):
            # The elicitation probe and the chip-fill probe are separate calls
            # with different slot sets, and they can disagree. Here elicitation
            # finds nothing, so the miss chips are what the user actually sees.
            if slots == ["district_name", "block_name", "gp_name"]:
                return {}
            found = {}
            if "gp_name" in slots:
                found["gp_name"] = "Naugaon"
            if "date_range" in slots:
                found["date_range"] = "nonesuch"   # EntityNotFound → dropped
            return found

        router.extract_entities = fake_extract

    def tearDown(self):
        router.extract_entities = self._real_extract

    def test_ambiguous_value_is_kept_raw_and_unknown_values_are_dropped(self):
        fill = router._extract_fill_values(
            "Tell me what we know about Naugaon",
            ["GPX"], GP_TEMPLATE_MAP, RosterValidator(), object(),
        )
        self.assertEqual(fill.get("gp_name"), "Naugaon")
        self.assertNotIn("date_range", fill,
                         "a genuinely unknown value stays dropped")

    def test_the_users_name_reaches_the_chip(self):
        result = router._no_match(
            GP_SCORED,
            "Tell me what we know about Naugaon",
            "tell me what we know about naugaon",
            time.monotonic(),
            validator=RosterValidator(), openai_client=object(),
            template_map=GP_TEMPLATE_MAP,
        )
        labels = [chip.label for chip in result.clarification.options]
        self.assertIn(
            "What is the GPDP status for Naugaon in a year?", labels
        )
        for label in labels:
            self.assertNotIn("a gram panchayat", label)


class GramPanchayatElicitationTests(unittest.TestCase):
    """Fix 4.5 — a bare place name gets the measures we hold for it, not a chip
    reading 'a gram panchayat in a year'. The WIDEST tier keeps precedence."""

    def setUp(self):
        self._real_extract = router.extract_entities

    def tearDown(self):
        router.extract_entities = self._real_extract

    def _extract(self, **found):
        def fake_extract(user_query, slots, client, **kwargs):
            self.assertEqual(
                slots, ["district_name", "block_name", "gp_name"],
                "all three tier probes must share ONE extraction call",
            )
            return {k: v for k, v in found.items() if v is not None}

        router.extract_entities = fake_extract

    def _run(self, query, validator=None):
        return router._no_match(
            GP_SCORED, query, query.lower(), time.monotonic(),
            validator=validator or RosterValidator(), openai_client=object(),
            template_map=GP_TEMPLATE_MAP,
        )

    def test_a_unique_panchayat_gets_elicitation_chips(self):
        self._extract(gp_name="Andhrua")
        result = self._run("Tell me what we know about Andhrua")
        self.assertEqual(result.clarification.reason, "broad_question")
        self.assertIn("Andhrua", result.clarification.prompt)
        self.assertTrue(result.clarification.options)
        for chip in result.clarification.options:
            self.assertIn("Andhrua", chip.send_text)
            self.assertNotIn("{", chip.send_text)

    def test_the_elicitation_chips_carry_a_year_so_they_execute(self):
        """Every one of these templates requires $date_range. Without a default
        the chip list would be EMPTY and a known panchayat would look like one
        the bot holds nothing about.

        The year is asserted only where the question NAMES one. EXP-002 ("how
        has expenditure changed over the years") is a trend across all of them
        and deliberately has no year in its wording — it still binds
        `$date_range`, which is what makes it offerable at all.
        """
        self._extract(gp_name="Andhrua")
        result = self._run("Tell me what we know about Andhrua")
        sends = [chip.send_text for chip in result.clarification.options]
        self.assertTrue(sends, "a known panchayat got no elicitation chips")
        self.assertTrue(
            any("2024-2025" in s for s in sends),
            "no chip named the year — the default was not applied",
        )
        for send in sends:
            self.assertNotIn("a year", send, "an unfilled year reached a chip")

    def test_an_ambiguous_name_offers_the_query_with_each_candidate_substituted(self):
        """Substituted with a REFERENCE, not a bare name. Where the candidates
        are several panchayats that share one name, the name gives identical
        chips and there is nothing to choose between."""
        self._extract(gp_name="Naugaon")
        result = self._run("Tell me what we know about Naugaon")
        self.assertEqual(result.clarification.reason, "unknown_entity")
        sends = [chip.send_text for chip in result.clarification.options]
        self.assertEqual(len(set(sends)), len(sends), "chips must be distinguishable")
        self.assertIn("Tell me what we know about Naugaon of Barpali", sends)
        self.assertIn("Tell me what we know about Naugaon of Bhubaneswar", sends)

    def test_the_district_reading_wins_when_a_name_is_both(self):
        """'How is Bhubaneswar doing?' must stay a DISTRICT elicitation.
        Bhubaneswar is a block as well, and several Odisha place names repeat
        across tiers, so the tiers are probed widest-first."""

        class AllTiersValidator(RosterValidator):
            def validate(self, value, entity_type):
                if entity_type == "district" and str(value).lower() == "bhubaneswar":
                    return ExtractedEntity(
                        slot_name="district_name", raw_value=str(value),
                        resolved_value="Khordha", entity_type="district",
                        confidence="alias",
                    )
                return super().validate(value, entity_type)

        self._extract(district_name="Bhubaneswar", block_name="Bhubaneswar")
        result = self._run("How is Bhubaneswar doing?", AllTiersValidator())
        self.assertEqual(result.clarification.reason, "broad_question")
        self.assertIn("What would you like to know about Khordha?",
                      result.clarification.prompt)
        for chip in result.clarification.options:
            self.assertIn("Khordha", chip.send_text)

    def test_an_unknown_name_falls_through_to_the_generic_miss(self):
        self._extract(gp_name="Zzyzx")
        result = self._run("Tell me about Zzyzx")
        self.assertEqual(result.clarification.reason, "no_match")


if __name__ == "__main__":
    unittest.main()
