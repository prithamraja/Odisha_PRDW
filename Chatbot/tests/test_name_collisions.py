"""A name is not a person.

316 of the 446 distinct names in pm_kisan are held by more than one Aadhaar —
71%, the worst reaching seven people. Every per-farmer template used to filter
on the name string, so all of them silently answered for everyone who shares
it. F12 reported the four different Lakshmi Devis' MARKFED payments as one
farmer's total: ₹259,181.42, which is two real people added together.

These tests assert on the FIGURE THAT CAME BACK, never on query_id. A
query_id-only assertion passes throughout the entire bug: the routing was
always right, and so was the template — the number was wrong.

Everything here is deterministic: DuckDB, the registry and the pending
resolver. No LLM, so no replay budget and no flake.
"""
import os
import re
import unittest

import duckdb

from query_router.entity_validator import EntityValidator, mask_aadhaar
from query_router.models import ClarificationNeeded
from query_router.pending_resolver import (
    RESUME,
    resolve_pending_reply,
    PendingClarification,
)
from query_router.router import bind_param_values
from query_router.template_catalog import TEMPLATE_CATALOG
from query_router.zones import candidate_chips

_TABLES = [
    "pm_kisan", "agriculture", "markfed", "ryss",
    "fisheries", "sericulture", "horticulture_apmip", "survey_land_records",
]

# The four people the defect merged, and what each is actually owed by MARKFED.
LAKSHMI_DEVIS = {
    "Lakshmi Devi of Rambilli": 128833.64,
    "Lakshmi Devi of Sangam":   130347.78,
    "Lakshmi Devi of Chapadu":  None,       # no MARKFED row at all
    "Lakshmi Devi of Bogole":   None,
}
MERGED_TOTAL = 128833.64 + 130347.78       # 259181.42 — the figure that was reported

# What each dataset calls the farmer's name. None of them may be compared to a
# bound parameter any more; the Aadhaar is.
_NAME_COLUMNS = (
    "name", "farmername", "Farmer_Name", "FARMER_NAME",
    "farmer_name", "FarmerName", "pattadar_name",
)


def _connect():
    data_dir = os.environ.get("DATA_DIR", "RTGS_Data/flat")
    conn = duckdb.connect()
    for table in _TABLES:
        conn.execute(
            f"CREATE VIEW {table} AS "
            f"SELECT * FROM read_parquet('{data_dir}/{table}.parquet')"
        )
    return conn


class NameCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()
        cls.validator = EntityValidator(cls.conn)

    def resolve(self, text):
        return self.validator.validate(text, "farmer_name")

    def f12_markfed(self, farmer_value):
        """F12's MARKFED figure for whoever `farmer_value` resolves to."""
        entity = self.resolve(farmer_value)
        template = TEMPLATE_CATALOG["F12"]
        values = bind_param_values(
            template["param_slots"],
            {"farmer_name": entity.resolved_value},
            person_ids={"farmer_name": entity.person_aadhaar},
        )
        rows = self.conn.execute(template["sql_template"], values).fetchall()
        markfed = [r for r in rows if r[2] == "MARKFED"]
        return float(markfed[0][3]) if markfed else None

    # ── The defect ────────────────────────────────────────────────────────────

    def test_a_shared_name_clarifies_instead_of_merging(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Lakshmi Devi")
        self.assertEqual(len(ctx.exception.candidates), 4)

    def test_each_of_the_four_returns_her_own_figure(self):
        for reference, expected in LAKSHMI_DEVIS.items():
            with self.subTest(reference):
                self.assertEqual(self.f12_markfed(reference), expected)

    def test_the_merged_total_is_returned_to_nobody(self):
        """The specific wrong number, checked against every path into F12."""
        for reference in LAKSHMI_DEVIS:
            self.assertNotEqual(self.f12_markfed(reference), MERGED_TOTAL)

    def test_the_two_nellore_candidates_are_separately_selectable(self):
        """District alone does not disambiguate: two of the four are both in
        Nellore, so a district-only chip offered the same thing twice."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Lakshmi Devi")
        nellore = [c for c in ctx.exception.candidates if c.districts == ["Nellore"]]
        self.assertEqual(len(nellore), 2)
        chips = candidate_chips(nellore)
        self.assertEqual(len({c.send_text for c in chips}), 2)
        self.assertEqual(len({c.label for c in chips}), 2)
        self.assertNotEqual(
            self.f12_markfed(chips[0].send_text),
            self.f12_markfed(chips[1].send_text),
        )

    # ── The tap has to reach a person ─────────────────────────────────────────

    def test_every_chip_resolves_to_exactly_one_person(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Lakshmi Devi")
        aadhaars = set()
        for chip in candidate_chips(ctx.exception.candidates):
            entity = self.resolve(chip.send_text)   # must not raise: no loop
            self.assertIsNotNone(entity.person_aadhaar)
            aadhaars.add(entity.person_aadhaar)
        self.assertEqual(len(aadhaars), 4)

    def test_a_tap_resumes_on_the_person_it_names(self):
        """The likeliest way to get this wrong: a chip that sends the ambiguous
        name back, which clarifies again on the next turn, forever."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Lakshmi Devi")
        candidates = ctx.exception.candidates
        pending = PendingClarification(
            query_id="F12", missing_slot="farmer_name", slot_type="farmer_name",
            filled={}, original_query="total benefits for Lakshmi Devi",
            candidates=candidates,
        )
        for chip in candidate_chips(candidates):
            resolution = resolve_pending_reply(
                chip.send_text, pending, self.validator, template_map={}
            )
            self.assertEqual(resolution.kind, RESUME, chip.send_text)
            self.assertEqual(resolution.value, chip.send_text)
            self.resolve(resolution.value)   # resolves, so the pause ends here

    def test_a_resolved_person_survives_a_second_round_trip(self):
        """Q125 asks for a village after the farmer, and re-validates what is
        already filled. If the identity did not survive, that re-validation
        would raise the same clarify and the question could never finish."""
        first = self.resolve("Lakshmi Devi of Sangam")
        second = self.resolve(first.resolved_value)
        self.assertEqual(second.person_aadhaar, first.person_aadhaar)

    # ── What must not change ─────────────────────────────────────────────────

    def test_a_unique_name_still_answers_directly(self):
        for name in ["Anil Babu", "Anjamma Chowdary", "Anil Rao",
                     "Anjamma Sri", "Venkateswarlu Gupta"]:
            with self.subTest(name):
                entity = self.resolve(name)
                self.assertEqual(entity.resolved_value, name,
                                 "a unique name must read back exactly as typed")
                self.assertIsNotNone(entity.person_aadhaar)

    def test_a_partial_name_still_clarifies_by_name(self):
        """The guard that already worked: several DIFFERENT names match, and
        the user picks a surname before anyone picks a person."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Anjamma")
        surnames = {c.name for c in ctx.exception.candidates}
        self.assertGreater(len(surnames), 1)
        self.assertTrue(all(s.startswith("Anjamma ") for s in surnames))

    def test_picking_a_shared_surname_cascades_into_the_person_choice(self):
        """'Anjamma Babu' is four people. Stage one picks the name, stage two
        the person — neither stage may resolve on its own."""
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Anjamma Babu")
        self.assertEqual(len(ctx.exception.candidates), 4)
        self.assertTrue(all(c.village for c in ctx.exception.candidates))

    def test_f14_still_answers_the_collision_itself(self):
        """F14 asks how many farmers share a name — resolving to one person
        would answer a different question, so it uses name_search."""
        entity = self.validator.validate("Ramesh Naidu", "name_search")
        self.assertEqual(entity.resolved_value, "Ramesh Naidu")
        template = TEMPLATE_CATALOG["F14"]
        rows = self.conn.execute(
            template["sql_template"],
            bind_param_values(template["param_slots"], {"farmer_name": "Ramesh Naidu"}),
        ).fetchall()
        self.assertEqual(len(rows), 4)

    # ── Catalog-wide invariants ──────────────────────────────────────────────

    def test_no_farmer_template_filters_or_groups_by_name(self):
        for qid, template in TEMPLATE_CATALOG.items():
            farmer_slots = [
                s for s in template["param_slots"]
                if s.get("entity_type") == "farmer_name"
            ]
            if not farmer_slots:
                continue
            with self.subTest(qid):
                for slot in farmer_slots:
                    self.assertEqual(slot.get("bind"), "aadhaar")
                sql = template["sql_template"]
                for column in _NAME_COLUMNS:
                    self.assertNotRegex(
                        sql, rf'"{column}"\)*\s*=\s*UPPER\(TRIM\(\?',
                        f"{qid} still filters {column} by the bound value",
                    )
                # A name may still be grouped ALONGSIDE the Aadhaar — that is
                # the key doing the work and the name is along for the ride.
                # Grouping on the name alone is what added the people together.
                for clause in re.findall(r"GROUP BY[^;]*", sql):
                    if '"name"' in clause:
                        self.assertIn(
                            "aadhaar", clause.lower(),
                            f"{qid} groups by name without the Aadhaar keying it",
                        )

    def test_every_farmer_template_executes_on_one_person(self):
        person = self.resolve("Lakshmi Devi of Rambilli")
        for qid, template in TEMPLATE_CATALOG.items():
            if not any(s.get("bind") == "aadhaar" for s in template["param_slots"]):
                continue
            with self.subTest(qid):
                params = {
                    s["name"]: person.resolved_value if s["name"] == "farmer_name"
                    else "Rambilli"
                    for s in template["param_slots"]
                }
                values = bind_param_values(
                    template["param_slots"], params,
                    person_ids={"farmer_name": person.person_aadhaar},
                )
                self.conn.execute(template["sql_template"], values).fetchall()

    def test_no_full_aadhaar_reaches_a_user_visible_string(self):
        with self.assertRaises(ClarificationNeeded) as ctx:
            self.resolve("Lakshmi Devi")
        visible = [str(ctx.exception)]
        for chip in candidate_chips(ctx.exception.candidates):
            visible += [chip.label, chip.send_text]
        for text in visible:
            self.assertNotRegex(text, r"(?<!\d)\d{12}(?!\d)", text)

    def test_a_masked_aadhaar_breaks_a_tie_name_and_village_cannot(self):
        """Name + village is unique across this whole drop, so the tiebreak
        never fires on it — which is exactly why it needs its own test."""
        from query_router.models import EntityCandidate
        twins = [
            EntityCandidate(name="Ramesh Naidu", districts=["Guntur"],
                            village="Chebrolu", aadhaar="104002954660"),
            EntityCandidate(name="Ramesh Naidu", districts=["Guntur"],
                            village="Chebrolu", aadhaar="113702637296"),
        ]
        chips = candidate_chips(twins)
        self.assertEqual(len({c.send_text for c in chips}), 2)
        self.assertEqual(len({c.label for c in chips}), 2)
        for chip, twin in zip(chips, twins):
            self.assertIn(mask_aadhaar(twin.aadhaar), chip.send_text)
            self.assertNotRegex(chip.send_text, r"(?<!\d)\d{12}(?!\d)")
            self.assertLessEqual(
                len(chip.send_text.split()), 6,
                "a longer reply stops reading as a slot answer and routes away",
            )


class RosterIdentityTests(unittest.TestCase):
    """The registry itself, rather than what it is used for."""

    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()
        cls.validator = EntityValidator(cls.conn)

    def test_the_scale_of_the_collision_is_what_the_index_sees(self):
        shared = [
            name for name, people in self.validator._farmer_people.items()
            if len(people) > 1
        ]
        self.assertEqual(len(self.validator._farmer_people), 446)
        self.assertEqual(len(shared), 316)

    def test_every_shared_name_clarifies_and_none_of_the_unique_ones_do(self):
        clarified = resolved = 0
        for people in self.validator._farmer_people.values():
            name = people[0].name
            try:
                self.validator.validate(name, "farmer_name")
            except ClarificationNeeded:
                clarified += 1
                self.assertGreater(len(people), 1, f"{name} is one person")
            else:
                resolved += 1
                self.assertEqual(len(people), 1, f"{name} is {len(people)} people")
        self.assertEqual((clarified, resolved), (316, 130))
