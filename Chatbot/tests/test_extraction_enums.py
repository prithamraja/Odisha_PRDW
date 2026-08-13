"""The extractor prompt must offer every value the validator accepts.

The bug this pins: `_EXTRACTION_PROMPT` enumerates the legal values for each
enumerated slot, so a value missing from that enumeration is a value the
extractor *cannot emit*, whatever the validator will accept. In AP two slots had
drifted and nothing failed: `beneficiary_status` omitted 'Pending', so "whose
beneficiary status is Pending?" bound `Excluded` and answered with 9 farmers
instead of 38 — plausible output, wrong rows, right template throughout. A
query_id assertion would never have caught it.

For PR&DW the enums are **generated from the registry** at startup
(`entity_extractor.build_prompt`), which is meant to make that class of drift
impossible. These tests are what say "meant to" is actually true:

  * the generated prompt really does carry the DATABASE's values, not a
    hard-coded list that happens to look right today;
  * every value it offers validates back to itself, so the round trip closes;
  * every alias TARGET names a real registry value, which is the one way a
    hand-written table can still silently point at nothing;
  * the workbook's 19 bind names all map to an entity type that exists.

The direction is prompt ⊇ validator for the enumerated slots, and prompt ⊆
validator for the sampled ones (district and block are long lists whose rule
line shows examples — the validator's alias and fuzzy cascade covers the rest,
and an unresolvable place clarifies rather than mis-binding).

`LiveExtractionTests` closes the loop through the real model. It is **opt-in**:
it costs money and hits the network, and a suite that quietly does that whenever
a key happens to be in `.env` is not a suite you can run freely. Set
PRDW_LIVE_EXTRACTION=1 to include it.
"""
import os
import re
import unittest
from pathlib import Path

from query_router.entity_extractor import (
    _ENUM_SLOTS,
    _FULLY_ENUMERATED,
    build_prompt,
)
from query_router.entity_validator import (
    PARAM_ENTITY_TYPES,
    REGISTRY_CONFIG,
    EntityValidator,
    _collapse_ws,
    _resolve_config,
)

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

# The 19 bind names on the workbook's Parameter Registry sheet, verbatim. Kept
# here rather than re-parsed from the xlsx so the test needs no Excel reader and
# no open-file race with the operator's copy — but a mismatch with the sheet is
# exactly what it is meant to catch, so update BOTH together.
WORKBOOK_BIND_NAMES = [
    "date_range", "date_range_2", "district_name", "block_name", "block_name_2",
    "gp_name", "gp_name_2", "focus_area", "theme", "scheme", "scheme_2",
    "status", "asset_category", "asset_sub_category", "activity_code",
    "top_n", "threshold", "amount_threshold", "deadline",
]


_ADAPTER_CACHE: list = []


def _adapter():
    """The real database, READ-ONLY, or None when it is not present.

    Guarded rather than assumed: the suite must skip cleanly on a checkout
    without the sample data instead of erroring, which is the defect the AP
    collision suite's unguarded `_connect()` shipped with.

    Memoised because the skip decorator and setUpClass both ask, and the
    database sits on a Drive-synced path where a cold open is not free.

    Opened through `db_factory.open_analytical_db`, NOT `DuckDBFileAdapter`
    directly: three of the allowed-values queries read `v_activity`/`v_asset`,
    and a view-less adapter would fail them softly — `_query` logs and returns
    `[]`, leaving the status and asset registries empty and every assertion over
    them vacuously true. Which is the failure this whole module exists to catch.
    """
    if _ADAPTER_CACHE:
        return _ADAPTER_CACHE[0]
    adapter = None
    if _DB_PATH.exists():
        try:
            from db_factory import open_analytical_db
            adapter = open_analytical_db(_DB_PATH)
        except Exception:
            adapter = None
    _ADAPTER_CACHE.append(adapter)
    return adapter


class _NoDBConn:
    """Registry loading fails cleanly and logs; nothing raises."""

    def execute(self, *_args, **_kwargs):
        raise RuntimeError("no database in this test")


def _rule_line(prompt: str, slot: str) -> str:
    """The '- For <slot>…' line of the prompt that governs `slot`.

    The slot must appear in the HEAD of the line, before the first colon —
    otherwise 'status' matches the gp rule, which happens to say "GPDP status of
    Andhrua", and the assertion then checks the wrong line's contents.
    """
    pattern = re.compile(
        r"^- For [^:\n]*\b" + re.escape(slot) + r"\b[^:\n]*:.*$", re.MULTILINE
    )
    match = pattern.search(prompt)
    assert match, f"no rule line in the extraction prompt governs {slot}"
    return match.group(0)


class PromptIsGeneratedTests(unittest.TestCase):
    """The enums come from the registry that is passed in — not from prose.

    This runs without a database on purpose: if the prompt were hand-written,
    feeding it an invented registry would change nothing and these would fail.
    """

    def test_the_values_that_reach_the_prompt_are_the_ones_supplied(self):
        fake = {
            "status": ["FICTIONAL STATUS A", "FICTIONAL STATUS B"],
            "scheme": ["Fictional Commission"],
            "theme": ["Theme 99 - Fictional"],
            "district": ["Fictionalpur"],
        }
        prompt = build_prompt(lambda slot: fake.get(slot, []), warn=False)
        for slot, values in fake.items():
            for value in values:
                with self.subTest(slot=slot, value=value):
                    self.assertIn(value, _rule_line(prompt, slot))

    def test_no_ap_vocabulary_survives_in_the_prompt(self):
        """A leftover AP rule line is a slot the model will try to fill from a
        domain that no longer exists."""
        prompt = build_prompt(lambda _slot: [], warn=False)
        for word in ("farmer", "Aadhaar", "aadhaar", "Kharif", "Rabi", "mandal",
                     "PM-KISAN", "crop", "acre", "hectare"):
            with self.subTest(word=word):
                self.assertNotIn(word, prompt)

    def test_every_enumerated_slot_has_a_rule_line(self):
        prompt = build_prompt(lambda _slot: [], warn=False)
        for slot in _ENUM_SLOTS:
            with self.subTest(slot=slot):
                self.assertTrue(_rule_line(prompt, slot))


class RegistryStructureTests(unittest.TestCase):
    """Structural agreement that needs no database."""

    def test_every_workbook_bind_name_maps_to_an_entity_type(self):
        for bind in WORKBOOK_BIND_NAMES:
            with self.subTest(bind=bind):
                self.assertIn(
                    bind, PARAM_ENTITY_TYPES,
                    f"${bind} is on the Parameter Registry sheet but WP-3 has "
                    f"no entity type to declare for it",
                )

    def test_no_entity_type_is_promised_that_does_not_exist(self):
        for bind, etype in PARAM_ENTITY_TYPES.items():
            with self.subTest(bind=bind):
                self.assertIn(etype, REGISTRY_CONFIG,
                              f"${bind} maps to unknown entity type {etype!r}")

    def test_the_map_covers_the_sheet_and_nothing_else(self):
        self.assertEqual(sorted(PARAM_ENTITY_TYPES), sorted(WORKBOOK_BIND_NAMES))

    def test_every_mirror_points_at_a_real_base_type(self):
        for etype, cfg in REGISTRY_CONFIG.items():
            base = cfg.get("mirrors")
            if base:
                with self.subTest(etype=etype):
                    self.assertIn(base, REGISTRY_CONFIG)
                    self.assertNotIn("mirrors", REGISTRY_CONFIG[base],
                                     "a mirror of a mirror never resolves")


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class LoadedRegistryTests(unittest.TestCase):
    """The half that needs the real values. Read-only throughout."""

    @classmethod
    def setUpClass(cls):
        cls.adapter = _adapter()
        cls.validator = EntityValidator(cls.adapter)
        cls.prompt = build_prompt(cls.validator.registry_values)

    def test_the_prompt_carries_every_value_of_the_fully_enumerated_slots(self):
        """status, scheme, theme, fiscal_year: a value missing here is a value
        the model cannot say, and the answer is wrong without an error."""
        for slot in sorted(_FULLY_ENUMERATED & set(_ENUM_SLOTS)):
            line = _rule_line(self.prompt, slot)
            values = self.validator.registry_values(slot)
            self.assertTrue(values, f"{slot} registry is empty")
            for value in values:
                with self.subTest(slot=slot, value=value):
                    # Compared on the display form: 'Theme 5 - …Village ' and
                    # '\tWORK COMPLETED' are shown tidied (the validator matches
                    # whitespace-collapsed either way).
                    self.assertIn(" ".join(value.split()), line)

    def test_every_value_the_prompt_offers_validates_to_itself(self):
        """The other half of the round trip, with no model in the loop."""
        for slot in _ENUM_SLOTS:
            for value in self.validator.registry_values(slot):
                with self.subTest(slot=slot, value=value):
                    resolved = self.validator.validate(value, slot)
                    self.assertEqual(resolved.resolved_value, value)

    def test_the_tidied_display_form_also_validates(self):
        """The prompt shows 'WORK COMPLETED'; the column stores it with a
        leading tab. The model will echo what it was shown, so that form has to
        resolve onto the stored one or every completed-work question is empty."""
        for slot in ("status", "theme"):
            for value in self.validator.registry_values(slot):
                tidy = " ".join(value.split())
                with self.subTest(slot=slot, value=tidy):
                    self.assertEqual(
                        self.validator.validate(tidy, slot).resolved_value, value
                    )

    def test_every_alias_target_names_a_real_registry_value(self):
        """An alias pointing at a value that is not in the registry binds a
        string the column does not hold — zero rows, no error. The one way a
        hand-written table can still fail silently."""
        for etype, cfg in REGISTRY_CONFIG.items():
            base, resolved_cfg = _resolve_config(etype)
            aliases = resolved_cfg.get("aliases") or {}
            values = {_collapse_ws(v) for v in self.validator.registry_values(base)}
            if not values:
                continue
            for alias, target in aliases.items():
                with self.subTest(etype=etype, alias=alias):
                    self.assertIn(
                        _collapse_ws(target), values,
                        f"{etype} alias {alias!r} -> {target!r}, which is not a "
                        f"loaded value",
                    )

    def test_the_suspected_bad_status_decode_is_kept_out(self):
        """'Buildings' is an asset_category label that appears in the
        activity_status decode (dim_code code 173). Logged, not repaired, and
        never offered as a status."""
        self.assertNotIn("Buildings", self.validator.registry_values("status"))
        self.assertNotIn("Buildings", _rule_line(self.prompt, "status"))
        # …and it is still a perfectly real ASSET category.
        self.assertIn("Buildings", self.validator.registry_values("asset_category"))

    def test_the_six_fiscal_years_are_full_form(self):
        years = self.validator.registry_values("fiscal_year")
        self.assertEqual(len(years), 6)
        for year in years:
            with self.subTest(year=year):
                self.assertRegex(year, r"^\d{4}-\d{4}$")

    def test_an_abbreviated_year_never_binds_as_typed(self):
        """'2024-25' is the whole reason date_phrase exists: it would bind
        successfully and match nothing."""
        self.assertEqual(
            self.validator.validate("2024-25", "fiscal_year").resolved_value,
            "2024-2025",
        )

    def test_every_gp_binds_a_code_not_a_name(self):
        for name in self.validator.registry_values("gp"):
            with self.subTest(gp=name):
                entity = self.validator.validate(name, "gp")
                self.assertTrue(
                    entity.resolved_code,
                    f"{name} resolved to a name with no gp_lgd_code — a "
                    f"code-bound slot would fail on it",
                )


_LIVE = os.environ.get("PRDW_LIVE_EXTRACTION") == "1"
_LIVE_REASON = (
    "live extraction is opt-in: set PRDW_LIVE_EXTRACTION=1 (costs money, "
    "requires OPENAI_API_KEY)"
)

# One phrasing per value the model must be able to emit, for the slots where a
# missing enum silently mis-binds.
_LIVE_QUESTIONS = {
    "status": {
        "WORK ONGOING":   "Which activities are still ongoing in Andhrua?",
        "WORK COMPLETED": "Which activities are marked WORK COMPLETED?",
        "WORK ABANDONED": "List the abandoned works in Barpali block",
        "UNDER APPROVAL": "How many activities are under approval?",
    },
    "fiscal_year": {
        "2024-2025": "How much did Khordha spend in FY 24-25?",
        "2023-2024": "How many plans were approved in 2023-24?",
    },
}


@unittest.skipIf(not _LIVE, _LIVE_REASON)
class LiveExtractionTests(unittest.TestCase):
    """The real model, asked for each value in turn, through the real validator."""

    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv(_BACKEND / ".env")
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise unittest.SkipTest("OPENAI_API_KEY not set")
        adapter = _adapter()
        if adapter is None:
            raise unittest.SkipTest(f"no sample database at {_DB_PATH}")

        from openai import OpenAI
        from query_router.entity_extractor import (
            extract_entities,
            refresh_prompt_enums,
        )

        cls.client = OpenAI(api_key=key)
        cls.extract = staticmethod(extract_entities)
        cls.validator = EntityValidator(adapter)
        refresh_prompt_enums(cls.validator.registry_values)

    def test_extractor_emits_every_accepted_value(self):
        for slot, questions in _LIVE_QUESTIONS.items():
            for value, question in questions.items():
                with self.subTest(slot=slot, value=value):
                    raw = self.extract(question, [slot], self.client)
                    self.assertIsNotNone(
                        raw.get(slot),
                        f"extractor returned null for {slot} on {question!r} — "
                        f"the prompt enumeration probably omits {value!r}",
                    )
                    resolved = self.validator.validate(raw[slot], slot)
                    self.assertEqual(
                        " ".join(resolved.resolved_value.split()), value, question
                    )


if __name__ == "__main__":
    unittest.main()
