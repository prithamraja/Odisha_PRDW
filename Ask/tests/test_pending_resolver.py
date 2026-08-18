"""What a reply to a paused question means (query_router/pending_resolver.py).

Two defects live here. Both start the same way: `take_pending` is one-shot, so
by the time strict slot validation fails the paused question is already gone.

  Fix 1 — the roster disambiguation prompt names people BY DISTRICT, so a
          district reply is what it invited; it used to fail `farmer_name`
          validation and the farmer question was lost.
  Fix 3 — "all crops" is a scope-widening answer no slot can hold; it used to
          route standalone and confidently serve an unrelated template.
"""
import unittest

from query_router.models import (
    EntityCandidate,
    EntityNotFound,
    ExtractedEntity,
    PendingClarification,
)
from query_router.pending_resolver import (
    FALLTHROUGH,
    REASK,
    RESUME,
    SERVE_ALTERNATIVE,
    is_scope_widening_reply,
    resolve_pending_reply,
)

CANDIDATES = [
    EntityCandidate(name="Venkateswarlu Gupta", districts=["Anantapur"]),
    EntityCandidate(
        name="Venkateswarlu Babu",
        districts=["East Godavari", "Srikakulam", "Vizianagaram", "Chittoor"],
    ),
    EntityCandidate(
        name="Venkateswarlu Chowdary", districts=["Krishna", "Srikakulam", "Chittoor"]
    ),
    EntityCandidate(name="Venkateswarlu Devi", districts=["Visakhapatnam", "Chittoor"]),
]

CANDIDATE_NAMES = {c.name for c in CANDIDATES}


class StubValidator:
    """Only the roster names in CANDIDATES and a handful of districts/crops
    exist. Anything else raises, exactly as the real registry would."""

    KNOWN = {
        "district": ["Anantapur", "Chittoor", "Krishna", "Guntur", "Visakhapatnam"],
        "crop": ["Bengalgram", "Blackgram", "Chilli", "Paddy"],
        "farmer_name": sorted(CANDIDATE_NAMES),
    }

    def validate(self, raw, entity_type):
        for value in self.KNOWN.get(entity_type, []):
            if value.lower() == str(raw).strip().lower():
                return ExtractedEntity(
                    slot_name=entity_type, raw_value=str(raw), resolved_value=value,
                    entity_type=entity_type, confidence="exact",
                )
        raise EntityNotFound(entity_type, str(raw), [])

    def registry_values(self, entity_type):
        return list(self.KNOWN.get(entity_type, []))


TEMPLATE_MAP = {
    "Q125": {
        "abstract_question": "How many schemes is {farmer_name} enrolled in?",
        "param_slots": [{"name": "farmer_name", "entity_type": "farmer_name",
                         "position": 1}],
    },
    "Q098": {
        "abstract_question":
            "For {crop}, which farmers took input subsidy and also sold to MARKFED?",
        "param_slots": [{"name": "crop", "entity_type": "crop", "position": 1}],
        "scope_alternative": "Q118",
    },
    # Same shape as Q098 but with no broader question authored for it — the
    # branch that must re-ask rather than invent an alternative.
    "Q098X": {
        "abstract_question": "For {crop}, who did what?",
        "param_slots": [{"name": "crop", "entity_type": "crop", "position": 1}],
    },
    "Q118": {
        "abstract_question":
            "Which pairs of schemes overlap the most in the farmers they serve?",
        "param_slots": [],
    },
}


def farmer_pending(candidates=None) -> PendingClarification:
    return PendingClarification(
        query_id="Q125", missing_slot="farmer_name", slot_type="farmer_name",
        filled={}, original_query="How many schemes is Venkateswarlu G enrolled in?",
        candidates=CANDIDATES if candidates is None else candidates,
    )


def crop_pending(query_id="Q098") -> PendingClarification:
    return PendingClarification(
        query_id=query_id, missing_slot="crop", slot_type="crop", filled={},
        original_query="How many input-subsidy farmers also sold produce to MARKFED?",
    )


def resolve(reply, pending):
    return resolve_pending_reply(
        reply, pending, StubValidator(), template_map=TEMPLATE_MAP
    )


class CandidateResolutionTests(unittest.TestCase):
    """Fix 1 — the reply picks a candidate, by name or by district.

    A resume carries a REFERENCE, not a bare name: a name is not a person (71%
    of the roster's names are shared), so resuming with the name the user was
    just asked to disambiguate would re-raise the same clarify forever. Where
    the candidate has been pinned to one place, the reference says so.
    """

    def test_full_name_resumes(self):
        resolution = resolve("Venkateswarlu Gupta", farmer_pending())
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, "Venkateswarlu Gupta of Anantapur")

    def test_name_match_ignores_case_and_punctuation(self):
        resolution = resolve("  venkateswarlu devi? ", farmer_pending())
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, "Venkateswarlu Devi")

    def test_typo_in_a_candidate_name_still_resumes(self):
        resolution = resolve("Venkateswarlu Guptaa", farmer_pending())
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, "Venkateswarlu Gupta of Anantapur")

    def test_a_name_several_candidates_share_is_never_guessed(self):
        """Two people, one name, and a reply that says only the name: picking
        the first is the silent wrong-person merge in a new place."""
        shared = [
            EntityCandidate(name="Lakshmi Devi", districts=["Nellore"],
                            village="Sangam", aadhaar="113702637296"),
            EntityCandidate(name="Lakshmi Devi", districts=["Nellore"],
                            village="Bogole", aadhaar="186782992085"),
        ]
        self.assertNotEqual(
            resolve("Lakshmi Devi", farmer_pending(shared)).kind, RESUME
        )
        picked = resolve("Lakshmi Devi of Bogole", farmer_pending(shared))
        self.assertEqual(picked.kind, RESUME)
        self.assertEqual(picked.value, "Lakshmi Devi of Bogole")

    def test_district_naming_exactly_one_candidate_resumes_with_that_name(self):
        """The reproduced bug: 'Anantapur' answered the question we asked, and
        used to be discarded because it isn't a farmer_name."""
        resolution = resolve("Anantapur", farmer_pending())
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, "Venkateswarlu Gupta of Anantapur")

    def test_district_shared_by_several_narrows_and_keeps_the_pending(self):
        resolution = resolve("Chittoor", farmer_pending())
        self.assertEqual(resolution.kind, REASK)
        self.assertIn("Chittoor", resolution.prompt)
        narrowed = {c.name for c in resolution.pending.candidates}
        self.assertEqual(
            narrowed,
            {"Venkateswarlu Babu", "Venkateswarlu Chowdary", "Venkateswarlu Devi"},
        )
        self.assertEqual(resolution.pending.query_id, "Q125",
                         "the paused question must survive the narrowing")
        self.assertEqual({c.label.split(" (")[0] for c in resolution.options}, narrowed)
        # Every chip carries the district forward. Sending the bare name back
        # would throw the narrowing away — three of these names are several
        # people each, so the next round would re-offer the ones just ruled out.
        self.assertEqual(
            {c.send_text for c in resolution.options},
            {f"{name} of Chittoor" for name in narrowed},
        )

    def test_narrowed_reask_then_a_name_resumes(self):
        narrowed = resolve("Chittoor", farmer_pending())
        resolution = resolve("Venkateswarlu Devi", narrowed.pending)
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(
            resolution.value, "Venkateswarlu Devi of Chittoor",
            "the district the user already gave must survive into the resume",
        )

    def test_district_no_candidate_is_in_reasks_with_the_candidates(self):
        resolution = resolve("Guntur", farmer_pending())
        self.assertEqual(resolution.kind, REASK)
        self.assertEqual(
            {c.label.split(" (")[0] for c in resolution.options} - {'Ask "Guntur" instead'},
            CANDIDATE_NAMES,
            "a disambiguation re-ask should re-offer the people it listed",
        )


class ShortReplyRetryTests(unittest.TestCase):
    """A two-word fragment straight after a clarify is far more likely to be a
    bad answer than a new question, and routing it standalone is how an
    unrelated template captures it. Ask once more — but exactly once."""

    def test_a_short_unusable_reply_reasks_instead_of_routing(self):
        resolution = resolve("top 25", crop_pending())
        self.assertEqual(resolution.kind, REASK)
        self.assertEqual(resolution.reason, "missing_parameter")
        self.assertIn("still need a crop", resolution.prompt)
        self.assertIn(
            "How many input-subsidy farmers", resolution.prompt,
            "the re-ask must say which question is still waiting",
        )
        self.assertTrue(resolution.pending.retried)

    def test_the_escape_chip_resends_the_users_own_words(self):
        resolution = resolve("top 25", crop_pending())
        escape = resolution.options[-1]
        self.assertEqual(escape.send_text, "top 25")
        self.assertIn("instead", escape.label)

    def test_the_retry_happens_exactly_once(self):
        first = resolve("top 25", crop_pending())
        second = resolve("top 25", first.pending)
        self.assertEqual(second.kind, FALLTHROUGH,
                         "a second unusable reply must not trap the user")

    def test_a_longer_reply_is_taken_at_face_value(self):
        """Above the threshold we believe the user changed the subject — the
        retry is for fragments, not for sentences."""
        self.assertEqual(
            resolve("show me the crop pattern by district", crop_pending()).kind,
            FALLTHROUGH,
        )

    def test_a_valid_answer_is_unaffected(self):
        self.assertEqual(resolve("Paddy", crop_pending()).kind, RESUME)


class ScopeWideningVocabularyTests(unittest.TestCase):
    """Fix 3 — the closed vocabulary, with no LLM anywhere near it."""

    def test_scope_terms_with_and_without_the_slot_noun(self):
        for reply in (
            "all", "any", "every", "everything", "overall", "no filter",
            "doesn't matter", "doesnt matter", "all of them",
            "all crops", "any crop", "across all crops", "Every Crop!",
        ):
            self.assertTrue(is_scope_widening_reply(reply, "crop"), reply)

    def test_real_values_are_not_scope_widening(self):
        for reply in ("Paddy", "Anantapur", "top 25", "crops", "all paddy", ""):
            self.assertFalse(is_scope_widening_reply(reply, "crop"), reply)

    def test_geo_slots_accept_the_validators_state_level_terms(self):
        # WP-2 fixture swap: the state-level markers are PR&DW's now. Same
        # assertion, same shared `_STATE_LEVEL_TERMS` source.
        for reply in ("statewide", "state", "entire state", "odisha", "orissa",
                      "all districts"):
            self.assertTrue(is_scope_widening_reply(reply, "district"), reply)
        for reply in ("all gps", "whole state"):
            self.assertTrue(is_scope_widening_reply(reply, "gp"), reply)
        # Those are scope markers for geography only — 'odisha' is not a crop
        # answer.
        self.assertFalse(is_scope_widening_reply("statewide", "crop"))
        self.assertFalse(is_scope_widening_reply("odisha", "crop"))


class ScopeWideningResolutionTests(unittest.TestCase):
    def test_all_crops_serves_the_declared_broader_question(self):
        resolution = resolve("all crops", crop_pending())
        self.assertEqual(resolution.kind, SERVE_ALTERNATIVE)
        self.assertEqual(resolution.query_id, "Q118")

    def test_without_an_annotation_it_reasks_and_keeps_the_pending(self):
        resolution = resolve("all crops", crop_pending("Q098X"))
        self.assertEqual(resolution.kind, REASK)
        self.assertIn("one crop at a time", resolution.prompt)
        self.assertEqual(resolution.pending.query_id, "Q098X")

    def test_reask_chips_are_complete_catalog_questions(self):
        """A chip tap arrives with from_chip=True and no pending resume, so its
        send_text has to be routable on its own — a bare 'Paddy' would not be."""
        resolution = resolve("all crops", crop_pending("Q098X"))
        self.assertTrue(resolution.options)
        for chip in resolution.options:
            self.assertNotIn("{", chip.send_text)
            self.assertIn("For ", chip.send_text)
            self.assertNotEqual(chip.label, chip.send_text)

    def test_a_named_crop_still_resumes_normally(self):
        resolution = resolve("Paddy", crop_pending())
        self.assertEqual(resolution.kind, RESUME)
        self.assertEqual(resolution.value, "Paddy")

    def test_a_geo_pending_engages_the_scope_path(self):
        pending = PendingClarification(
            query_id="Q125", missing_slot="district", slot_type="district",
            filled={}, original_query="q",
        )
        resolution = resolve("statewide", pending)
        self.assertEqual(resolution.kind, REASK)
        self.assertIn("one district at a time", resolution.prompt)


if __name__ == "__main__":
    unittest.main()
