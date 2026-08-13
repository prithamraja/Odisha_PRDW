"""The extractor prompt must offer every status value the validator accepts.

The bug this pins: `_EXTRACTION_PROMPT` enumerates the legal values for each
status slot, so a value missing from that enumeration is a value the extractor
*cannot emit*, whatever the validator will accept. Two slots had drifted:

  * `beneficiary_status` allowed only Included/Excluded, so "whose beneficiary
    status is Pending?" bound `Excluded` and answered with the 9 excluded
    farmers instead of the 38 pending ones — plausible output, wrong rows, and
    it routed to the right template throughout. A query_id assertion would
    never have caught it.
  * `crop_status` allowed only Approved/Pending/Under Review, so "which crops
    are marked as Damaged?" returned `{"crop_status": null}` and stalled on a
    "For which crop status?" clarification.

The validator had already been fixed for both, with comments; nobody checked
that the prompt agreed, and nothing failed. `EnumAgreementTests` is that check.

The direction is prompt ⊇ validator, not equality: `crop_status` and
`approval_status` share one rule line, and only `crop_status` has `Damaged`, so
the line is legitimately wider than what `approval_status` accepts.

`LiveExtractionTests` closes the loop through the real model — it needs
OPENAI_API_KEY and skips cleanly without it.
"""
import os
import re
import unittest

from dotenv import load_dotenv

from pathlib import Path

from query_router.entity_extractor import _EXTRACTION_PROMPT
from query_router.entity_validator import REGISTRY_CONFIG, EntityValidator

_BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND / ".env")

# Slot -> the questions that should make the model emit each of its values.
# One phrasing per value; the value itself is the expected resolution.
_LIVE_QUESTIONS = {
    "crop_status": {
        "Approved": "Which registered crops are approved?",
        "Pending": "Which registered crops are pending?",
        "Under Review": "Which registered crops are under review?",
        "Damaged": "Which registered crops are marked as Damaged?",
    },
    "beneficiary_status": {
        "Included": "Whose beneficiary status is Included?",
        "Excluded": "Whose beneficiary status is Excluded?",
        "Pending": "Whose beneficiary status is Pending (not yet Included)?",
    },
}

# ekyc_status is checked for prompt/validator agreement but not driven live:
# 'Approved' matches zero rows in pm_kisan.ekyc_status, so it is accepted to
# answer truthfully rather than mis-bind. See its comment in entity_validator.
_AGREEMENT_SLOTS = ["ekyc_status", "beneficiary_status", "crop_status", "approval_status"]


def _rule_line(slot: str) -> str:
    """The '- For <slot>...' line of _EXTRACTION_PROMPT that governs `slot`."""
    pattern = re.compile(r"^- For .*\b" + re.escape(slot) + r"\b.*$", re.MULTILINE)
    match = pattern.search(_EXTRACTION_PROMPT)
    assert match, f"no rule line in _EXTRACTION_PROMPT mentions {slot}"
    return match.group(0)


class EnumAgreementTests(unittest.TestCase):
    """Every value the validator accepts is a value the prompt lets the model say."""

    def test_prompt_offers_every_validated_status_value(self):
        for slot in _AGREEMENT_SLOTS:
            line = _rule_line(slot)
            for value in REGISTRY_CONFIG[slot]["values"]:
                with self.subTest(slot=slot, value=value):
                    self.assertIn(
                        value, line,
                        f"_EXTRACTION_PROMPT cannot emit {slot}={value!r}; the "
                        f"validator accepts it. Rule line: {line}",
                    )

    def test_the_three_repaired_values_are_named(self):
        """Named explicitly so a rewrite of the loop above cannot lose them."""
        self.assertIn("Approved", _rule_line("ekyc_status"))
        self.assertIn("Pending", _rule_line("beneficiary_status"))
        self.assertIn("Damaged", _rule_line("crop_status"))

    def test_ekyc_aliases_do_not_remap_onto_approved(self):
        """'verified' and 'complete' mean Completed in pm_kisan.ekyc_status;
        remapping them would silently change the three templates that work."""
        for alias, target in REGISTRY_CONFIG["ekyc_status"]["aliases"].items():
            with self.subTest(alias=alias):
                self.assertNotEqual(target, "Approved")


class _NoDBConn:
    """Static-enum validation needs no registry; _load warns and moves on."""

    def execute(self, *_args, **_kwargs):
        raise RuntimeError("no database in this test")


class ValidatorAcceptsEveryLiveValueTests(unittest.TestCase):
    """The other half of the round trip, with no model in the loop."""

    @classmethod
    def setUpClass(cls):
        cls.validator = EntityValidator(_NoDBConn())

    def test_every_value_the_prompt_offers_validates_to_itself(self):
        for slot, questions in _LIVE_QUESTIONS.items():
            for value in questions:
                with self.subTest(slot=slot, value=value):
                    resolved = self.validator.validate(value, slot)
                    self.assertEqual(resolved.resolved_value, value)


_SKIP = None
if not os.environ.get("OPENAI_API_KEY"):
    _SKIP = "OPENAI_API_KEY not set — the live extractor cannot run without it"


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class LiveExtractionTests(unittest.TestCase):
    """The real model, asked for each value in turn, through the real validator."""

    @classmethod
    def setUpClass(cls):
        from openai import OpenAI

        from query_router.entity_extractor import extract_entities

        cls.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        cls.extract = staticmethod(extract_entities)
        cls.validator = EntityValidator(_NoDBConn())

    def test_extractor_emits_every_accepted_value(self):
        for slot, questions in _LIVE_QUESTIONS.items():
            for value, question in questions.items():
                with self.subTest(slot=slot, value=value):
                    raw = self.extract(question, [slot], self.client)
                    self.assertIsNotNone(
                        raw.get(slot),
                        f"extractor returned null for {slot} on {question!r} — the "
                        f"prompt enumeration probably omits {value!r}",
                    )
                    resolved = self.validator.validate(raw[slot], slot)
                    self.assertEqual(resolved.resolved_value, value, question)


if __name__ == "__main__":
    unittest.main()
