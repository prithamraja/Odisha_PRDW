"""A gram panchayat name is not a gram panchayat.

This is the AP name-collision defect ported to geography. There, joining farmers
by name silently merged four different Lakshmi Devis and reported ₹259,181 as
one woman's MARKFED payments — right template, right routing, wrong answer, no
error anywhere. PR&DW is worse positioned for it: the sample holds 20 gram
panchayats whose names all happen to be distinct, while production holds ~6,800
across 314 blocks, where names repeat freely. A test written against the sample
would pass for the wrong reason and go on passing right up to the statewide
load.

So the fixture here is **synthetic and deliberately colliding** (decision D4):
two 'Naugaon's in different districts, two 'Rampur's in different blocks of the
SAME district, two 'Sundarpur's in the same block distinguishable only by LGD
code, and three names that are unique. What is asserted is the contract every
template depends on:

  * an ambiguous name clarifies, listing each candidate with its block and
    district — never a silent pick;
  * each candidate is separately selectable, and each selection binds its own
    distinct `gp_lgd_code`;
  * a unique name resolves silently, with its code;
  * no template can ever be handed an unresolved ambiguous name — the binder
    fails loudly rather than falling back to the name string.

Replaces `test_name_collisions.py` (the AP farmer roster), per the bootstrap's
"port the concept, not the file".
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from query_router.entity_validator import EntityValidator, describe_gp
from query_router.models import ClarificationNeeded, EntityNotFound
from query_router.router import bind_named_params, bind_param_values
from query_router.zones import candidate_chips, candidate_label

# (gp_lgd_code, gp_name, block_name, zp_name)
#
# Codes are six digits like the real ones but deliberately outside the sample's
# range, so nothing here can be confused with a real panchayat.
FIXTURE_GPS = [
    # Same name, different DISTRICTS — the commonest statewide collision.
    ("900001", "Naugaon",   "Barpali",     "Bargarh"),
    ("900002", "Naugaon",   "Bhubaneswar", "Khordha"),
    # Same name, SAME district, different blocks — the one a district-only
    # qualifier cannot separate.
    ("900003", "Rampur",    "Attabira",    "Bargarh"),
    ("900004", "Rampur",    "Barpali",     "Bargarh"),
    # Same name, SAME block — only the LGD code tells them apart.
    ("900005", "Sundarpur", "Khallikote",  "Ganjam"),
    ("900006", "Sundarpur", "Khallikote",  "Ganjam"),
    # Unique.
    ("900007", "Andhrua",   "Bhubaneswar", "Khordha"),
    ("900008", "Chikilli",  "Khallikote",  "Ganjam"),
    ("900009", "Haldikudar", "Lahunipara", "Sundargarh"),
]

SHARED_NAMES = ("Naugaon", "Rampur", "Sundarpur")
UNIQUE_NAMES = ("Andhrua", "Chikilli", "Haldikudar")

_tmpdir: str | None = None
_adapter = None
_skip_reason: str | None = None


def _build_fixture():
    """A throwaway .duckdb holding only the colliding roster.

    Built under the system temp directory — never in the repo and never on the
    Drive-synced path, where DuckDB cannot create its temp files. Returns a
    reason string when it cannot be built, so the suite SKIPS rather than
    erroring: an unguarded connect is what made the AP collision suite
    contribute 17 errors to every baseline run.
    """
    global _tmpdir, _adapter
    try:
        import duckdb

        _tmpdir = tempfile.mkdtemp(prefix="prdw_gp_collisions_")
        path = Path(_tmpdir) / "collisions.duckdb"
        con = duckdb.connect(str(path))
        con.execute(
            "CREATE TABLE gram_panchayat ("
            "  gp_lgd_code VARCHAR, gp_name VARCHAR,"
            "  state_code VARCHAR, state_name VARCHAR, district_code VARCHAR,"
            "  zp_name VARCHAR, block_code VARCHAR, block_name VARCHAR)"
        )
        con.executemany(
            "INSERT INTO gram_panchayat "
            "(gp_lgd_code, gp_name, state_code, state_name, district_code,"
            " zp_name, block_code, block_name) "
            "VALUES (?, ?, '21', 'Odisha', '000', ?, '000', ?)",
            [(code, name, district, block)
             for code, name, block, district in FIXTURE_GPS],
        )
        # Enough of the rest of the schema that registry loading is quiet.
        con.execute(
            "CREATE TABLE planned_activity (activity_code VARCHAR, "
            "gp_lgd_code VARCHAR, fiscal_year VARCHAR, activity_status BIGINT, "
            "focus_area BIGINT)"
        )
        con.execute(
            "INSERT INTO planned_activity VALUES "
            "('A1', '900001', '2024-2025', 176, 56)"
        )
        con.close()

        from db_adapters import DuckDBFileAdapter
        _adapter = DuckDBFileAdapter(path)
        return None
    except Exception as exc:                                 # pragma: no cover
        return f"could not build the synthetic collision fixture: {exc}"


_skip_reason = _build_fixture()


def tearDownModule():
    if _adapter is not None:
        try:
            _adapter.close()
        except Exception:
            pass
    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)


@unittest.skipIf(_skip_reason is not None, _skip_reason or "")
class GPCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = EntityValidator(_adapter)

    def resolve(self, text):
        return self.validator.validate(text, "gp")

    # ── The fixture is doing its job ─────────────────────────────────────────

    def test_the_fixture_actually_collides(self):
        """Guards the guard: if the roster ever loads without duplicates, every
        assertion below would pass vacuously."""
        names = self.validator.registry_values("gp")
        self.assertEqual(len(names), 6, names)          # 9 rows, 6 distinct names
        for name in SHARED_NAMES:
            self.assertIn(name, names)

    # ── A shared name clarifies ──────────────────────────────────────────────

    def test_a_shared_name_clarifies_instead_of_merging(self):
        for name in SHARED_NAMES:
            with self.subTest(name=name):
                with self.assertRaises(ClarificationNeeded):
                    self.resolve(name)

    def test_the_prompt_names_the_block_and_district_of_each_candidate(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Naugaon")
        message = str(ctx.exception)
        for block, district in (("Barpali", "Bargarh"),
                                ("Bhubaneswar", "Khordha")):
            self.assertIn(block, message)
            self.assertIn(district, message)

    def test_a_district_qualifier_alone_cannot_separate_a_within_district_pair(self):
        """Both Rampurs are in Bargarh. The district is not the qualifier —
        which is exactly why the candidate carries the block."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Rampur")
        districts = {d for c in ctx.exception.candidates for d in c.districts}
        self.assertEqual(districts, {"Bargarh"})
        blocks = {c.parent_place for c in ctx.exception.candidates}
        self.assertEqual(blocks, {"Attabira", "Barpali"})

    def test_every_candidate_carries_its_own_code(self):
        for name in SHARED_NAMES:
            with self.subTest(name=name):
                with self.assertRaises(ClarificationNeeded) as ctx:
                    self.resolve(name)
                codes = [c.code for c in ctx.exception.candidates]
                self.assertTrue(all(codes), codes)
                self.assertEqual(len(set(codes)), len(codes), "candidates share a code")

    def test_every_candidate_is_listed_none_are_truncated_away(self):
        """A candidate the user cannot see is a panchayat they can never ask
        about."""
        for name, expected in (("Naugaon", 2), ("Rampur", 2), ("Sundarpur", 2)):
            with self.subTest(name=name):
                with self.assertRaises(ClarificationNeeded) as ctx:
                    self.resolve(name)
                self.assertEqual(len(ctx.exception.candidates), expected)

    def test_candidate_labels_are_distinguishable(self):
        """Two identical chips would leave the user unable to choose — the
        failure the LGD-code tiebreak exists for."""
        for name in SHARED_NAMES:
            with self.subTest(name=name):
                with self.assertRaises(ClarificationNeeded) as ctx:
                    self.resolve(name)
                chips = candidate_chips(ctx.exception.candidates)
                labels = [c.label for c in chips]
                sends = [c.send_text for c in chips]
                self.assertEqual(len(set(labels)), len(labels), labels)
                self.assertEqual(len(set(sends)), len(sends), sends)

    def test_same_block_candidates_fall_back_to_the_lgd_code(self):
        """Both Sundarpurs are in Khallikote block of Ganjam, so name + block
        is not enough and the public code has to do the separating."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Sundarpur")
        chips = candidate_chips(ctx.exception.candidates)
        for chip in chips:
            self.assertRegex(chip.send_text, r"9000\d\d")
            self.assertRegex(chip.label, r"9000\d\d")

    # ── Each candidate is separately selectable ──────────────────────────────

    def test_each_candidate_resolves_to_exactly_one_panchayat(self):
        for name in SHARED_NAMES:
            with self.assertRaises(ClarificationNeeded) as ctx:
                self.resolve(name)
            for reply in (c.send_text for c in candidate_chips(ctx.exception.candidates)):
                with self.subTest(reply=reply):
                    entity = self.resolve(reply)
                    self.assertTrue(entity.resolved_code)

    def test_the_candidates_of_one_name_bind_distinct_codes(self):
        """The whole defect in one assertion: two panchayats called the same
        thing must not end up filtering on the same value."""
        for name in SHARED_NAMES:
            with self.subTest(name=name):
                with self.assertRaises(ClarificationNeeded) as ctx:
                    self.resolve(name)
                replies = [c.send_text
                           for c in candidate_chips(ctx.exception.candidates)]
                codes = {self.resolve(r).resolved_code for r in replies}
                self.assertEqual(len(codes), len(replies), codes)

    def test_a_chip_resolves_to_the_panchayat_it_names(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Naugaon")
        by_code = {c.code: c for c in ctx.exception.candidates}
        for chip in candidate_chips(ctx.exception.candidates):
            with self.subTest(chip=chip.send_text):
                entity = self.resolve(chip.send_text)
                candidate = by_code[entity.resolved_code]
                self.assertIn(candidate.parent_place, chip.label)

    def test_a_resolved_panchayat_survives_a_second_round_trip(self):
        """A chained clarify re-validates everything already filled. If the
        resolved value did not itself resolve back to the same GP, the pause
        would repeat forever."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Rampur")
        for chip in candidate_chips(ctx.exception.candidates):
            first = self.resolve(chip.send_text)
            second = self.resolve(first.resolved_value)
            with self.subTest(chip=chip.send_text):
                self.assertEqual(second.resolved_code, first.resolved_code)

    def test_the_lgd_code_itself_resolves(self):
        for code, name, _block, _district in FIXTURE_GPS:
            with self.subTest(code=code):
                self.assertEqual(self.resolve(code).resolved_code, code)

    def test_a_name_with_its_block_resolves_without_asking(self):
        entity = self.resolve("Rampur of Attabira")
        self.assertEqual(entity.resolved_code, "900003")

    def test_a_name_with_its_district_resolves_when_that_is_enough(self):
        entity = self.resolve("Naugaon of Khordha")
        self.assertEqual(entity.resolved_code, "900002")

    # ── Unique names are untouched ───────────────────────────────────────────

    def test_a_unique_name_answers_directly(self):
        for name in UNIQUE_NAMES:
            with self.subTest(name=name):
                entity = self.resolve(name)
                self.assertEqual(entity.resolved_value, name)
                self.assertTrue(entity.resolved_code)

    def test_a_unique_name_is_not_dressed_up_with_a_block(self):
        """'Andhrua of Bhubaneswar' as the echoed value would read as a
        correction the user did not make."""
        self.assertEqual(self.resolve("Andhrua").resolved_value, "Andhrua")

    def test_a_misspelling_of_a_unique_name_still_lands(self):
        self.assertEqual(self.resolve("Andhroa").resolved_code, "900007")

    def test_an_unknown_name_is_refused_with_suggestions(self):
        with self.assertRaises(EntityNotFound) as ctx:
            self.resolve("Nowhereabad")
        self.assertTrue(ctx.exception.suggestions)

    # ── No template ever sees an unresolved ambiguous name ───────────────────

    def test_a_code_bound_slot_refuses_to_bind_a_bare_name(self):
        """The last line of defence. Even if something upstream handed the
        binder a raw name, a {"bind": "code"} slot fails loudly instead of
        filtering on a string that several panchayats answer to."""
        slots = [{"name": "gp_name", "entity_type": "gp", "bind": "code",
                  "position": 1}]
        with self.assertRaises(ValueError):
            bind_named_params(slots, {"gp_name": "Naugaon"}, person_ids={})
        with self.assertRaises(ValueError):
            bind_param_values(slots, {"gp_name": "Naugaon"}, person_ids={})

    def test_a_code_bound_slot_binds_the_code_not_the_name(self):
        entity = self.resolve("Naugaon of Barpali")
        slots = [{"name": "gp_name", "entity_type": "gp", "bind": "code",
                  "position": 1}]
        bound = bind_named_params(
            slots, {"gp_name": entity.resolved_value},
            person_ids={"gp_name": entity.resolved_code},
        )
        self.assertEqual(bound, {"gp_name": "900001"})
        self.assertNotIn("Naugaon", str(bound))

    def test_an_optional_code_bound_slot_still_binds_null_when_absent(self):
        """Decision D2's optional geography must survive the code binding."""
        slots = [{"name": "gp_name", "entity_type": "gp", "bind": "code",
                  "optional": True, "position": 1}]
        self.assertEqual(bind_named_params(slots, {}, person_ids={}),
                         {"gp_name": None})

    # ── Presentation ─────────────────────────────────────────────────────────

    def test_describe_gp_reads_as_a_place_a_person_would_say(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Naugaon")
        self.assertIn(
            "Naugaon (Barpali block, Bargarh district)", str(ctx.exception)
        )

    def test_candidate_label_leads_with_the_block(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Naugaon")
        label = candidate_label(ctx.exception.candidates[0])
        self.assertTrue(label.startswith("Naugaon ("), label)

    def test_no_lgd_code_is_ever_masked(self):
        """A code is public. The AP path masked its identifier to the last four
        digits; doing that here would make the chip unresolvable."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Sundarpur")
        for chip in candidate_chips(ctx.exception.candidates):
            self.assertNotIn("XXXX", chip.label)
            self.assertNotIn("XXXX", chip.send_text)


@unittest.skipIf(_skip_reason is not None, _skip_reason or "")
class RosterScaleTests(unittest.TestCase):
    """What the roster looks like when names repeat — the shape the statewide
    load will have, in miniature."""

    @classmethod
    def setUpClass(cls):
        cls.validator = EntityValidator(_adapter)

    def test_every_shared_name_clarifies_and_no_unique_one_does(self):
        for name in SHARED_NAMES:
            with self.subTest(name=name, shared=True):
                with self.assertRaises(ClarificationNeeded):
                    self.validator.validate(name, "gp")
        for name in UNIQUE_NAMES:
            with self.subTest(name=name, shared=False):
                self.assertTrue(self.validator.validate(name, "gp").resolved_code)

    def test_the_scale_of_the_collision_is_what_the_roster_sees(self):
        """Six distinct names over nine panchayats: three of the six are shared.
        Binding names would silently merge six rows into three."""
        names = self.validator.registry_values("gp")
        self.assertEqual(len(names), 6)
        self.assertEqual(len(FIXTURE_GPS), 9)

    def test_the_paired_slot_resolves_the_same_way(self):
        """$gp_name_2 mirrors $gp_name — a GP-vs-GP comparison must not have a
        weaker collision guard on its second operand."""
        with self.assertRaises(ClarificationNeeded):
            self.validator.validate("Naugaon", "gp_2")
        entity = self.validator.validate("Naugaon of Khordha", "gp_2")
        self.assertEqual(entity.resolved_code, "900002")


if __name__ == "__main__":
    unittest.main()
