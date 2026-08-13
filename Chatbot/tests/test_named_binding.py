"""
WP-1: named-parameter execution, optional slots, and caveat passthrough.

Executes against a REAL DuckDB file built fresh in a temp directory, through the
real DuckDBFileAdapter — not a stub connection. The three things being checked
here only fail for real against a real engine:

  - a repeated `$name` binds one value at every occurrence;
  - binding NULL into `($p IS NULL OR col = $p)` disables that filter, which is
    the entire mechanism behind one-template-per-question;
  - the read-only attachment refuses writes.

The fixture is built in tempfile.mkdtemp(), never in the repo: the shipped
`data/panchayat_1.duckdb` lives in a Google Drive-synced folder and must only
ever be opened read-only.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import duckdb

from db_adapters import DuckDBFileAdapter
from query_router import router
from query_router.models import EntityNotFound, ExtractedEntity, RouteTier

# ── Fixture: a miniature of the PR&DW shape (GP → block → district) ───────────

_ROWS = [
    # gp_lgd_code, gp_name, block_name, district_name, fin_year, activities, created_on
    # fin_year is the full '2024-2025' STRING the data dictionary insists on, not
    # a number — a bare 2024 matches nothing.
    ("101", "Alpha",   "Balianta",  "Khordha",  "2024-2025", 12, "2024-05-10"),
    ("102", "Beta",    "Balianta",  "Khordha",  "2024-2025", 7,  "2024-06-15"),
    ("103", "Gamma",   "Nimapara",  "Puri",     "2024-2025", 20, "2024-08-01"),
    ("104", "Delta",   "Nimapara",  "Puri",     "2023-2024", 5,  "2023-11-20"),
]


def _build_fixture(directory: Path) -> Path:
    path = directory / "fixture.duckdb"
    conn = duckdb.connect(str(path))
    conn.execute(
        """CREATE TABLE planned_activity (
               gp_lgd_code   VARCHAR,
               gp_name       VARCHAR,
               block_name    VARCHAR,
               district_name VARCHAR,
               fin_year      VARCHAR,
               activities    INTEGER,
               created_on    DATE
           )"""
    )
    conn.executemany(
        "INSERT INTO planned_activity VALUES (?, ?, ?, ?, ?, ?, ?)", _ROWS
    )
    # The catalogue's SQL reads v_* views, absent from the shipped sample. Prove
    # the adapter resolves a VIEW through the read-only attachment too.
    conn.execute(
        "CREATE VIEW v_activity_summary AS "
        "SELECT district_name, fin_year, sum(activities) AS total "
        "FROM planned_activity GROUP BY 1, 2"
    )
    conn.close()
    return path


# The consolidated-template shape from decision D2: ONE entry, every geography
# slot optional, each parameter repeated by the optional-filter idiom.
CONSOLIDATED_SQL = """
SELECT gp_name, activities
FROM planned_activity
WHERE ($district_name IS NULL OR district_name = $district_name)
  AND ($block_name    IS NULL OR block_name    = $block_name)
  AND ($fin_year      IS NULL OR fin_year      = $fin_year)
ORDER BY gp_name
"""

CAVEAT = (
    "Counts cover only the Gram Panchayats loaded in this sample, not the full "
    "state roster."
)

TEMPLATE_MAP = {
    "P001": {
        "abstract_question": "How many activities are planned?",
        "date_filter": None,
        "sql_template": CONSOLIDATED_SQL,
        "caveat": CAVEAT,
        "param_slots": [
            {"name": "district_name", "entity_type": "district_name", "optional": True},
            {"name": "block_name",    "entity_type": "block_name",    "optional": True},
            {"name": "fin_year",      "entity_type": "fin_year",      "optional": True},
        ],
    },
    # A named template with a REQUIRED slot — optionality must be per-slot, not
    # a property of the named style.
    "P002": {
        "abstract_question": "Activities in {district_name}?",
        "date_filter": None,
        "sql_template": (
            "SELECT gp_name FROM planned_activity WHERE district_name = $district_name "
            "AND ($fin_year IS NULL OR fin_year = $fin_year) ORDER BY gp_name"
        ),
        "param_slots": [
            {"name": "district_name", "entity_type": "district_name"},
            {"name": "fin_year",      "entity_type": "fin_year", "optional": True},
        ],
    },
    # Positional, no caveat — the AP shape, for the "unchanged" assertions.
    "T001": {
        "abstract_question": "Activities in {district_name}?",
        "date_filter": None,
        "sql_template": (
            "SELECT gp_name FROM planned_activity WHERE district_name = ? ORDER BY gp_name"
        ),
        "param_slots": [
            {"name": "district_name", "entity_type": "district_name", "position": 1},
        ],
    },
}


class StubValidator:
    """Resolves anything in `known`, raises EntityNotFound otherwise."""

    known = {
        "district_name": ["Khordha", "Puri"],
        "block_name":    ["Balianta", "Nimapara"],
        "fin_year":      ["2024-2025", "2023-2024"],
    }

    def validate(self, raw, entity_type):
        for value in self.known.get(entity_type, []):
            if value.lower() == str(raw).strip().lower():
                return ExtractedEntity(
                    slot_name=entity_type, raw_value=str(raw), resolved_value=value,
                    entity_type=entity_type, confidence="exact",
                )
        raise EntityNotFound(entity_type, str(raw), self.known.get(entity_type, [])[:3])


def _entities(**slots) -> list[ExtractedEntity]:
    return [
        ExtractedEntity(slot_name=name, raw_value=value, resolved_value=value,
                        entity_type=name, confidence="exact")
        for name, value in slots.items()
    ]


class _AdapterFixture(unittest.TestCase):
    """Shared fresh-temp-file adapter."""

    @classmethod
    def setUpClass(cls):
        cls._dir = Path(tempfile.mkdtemp(prefix="wp1_named_"))
        cls.db_path = _build_fixture(cls._dir)
        cls.adapter = DuckDBFileAdapter(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.adapter.close()
        shutil.rmtree(cls._dir, ignore_errors=True)

    def setUp(self):
        router._result_cache.clear()   # results are cached per bind set


class AdapterTests(_AdapterFixture):
    def test_tables_and_views_resolve_unqualified(self):
        self.assertEqual(
            self.adapter.execute("SELECT count(*) FROM planned_activity").fetchone(), (4,)
        )
        self.assertEqual(
            self.adapter.execute("SELECT count(*) FROM v_activity_summary").fetchone(), (3,)
        )
        self.assertIn("v_activity_summary", self.adapter.data_relations())

    def test_the_attached_file_refuses_writes(self):
        """The whole reason the attachment is inverted: DuckDB, not our own
        care, is what stops a write reaching a Drive-synced database."""
        for stmt in (
            f"CREATE TABLE {DuckDBFileAdapter.DATA_ALIAS}.scratch (x INT)",
            f"DELETE FROM {DuckDBFileAdapter.DATA_ALIAS}.planned_activity",
        ):
            with self.assertRaises(Exception):
                self.adapter.execute(stmt)
        self.assertEqual(
            self.adapter.execute("SELECT count(*) FROM planned_activity").fetchone(), (4,)
        )

    def test_cache_tables_are_writable_beside_the_read_only_file(self):
        self.adapter.execute_ddl(
            "CREATE TABLE IF NOT EXISTS dashboard_cache (query_id VARCHAR, result TEXT)"
        )
        self.adapter.execute("INSERT INTO dashboard_cache VALUES ('D01', '[]')")
        self.assertEqual(
            self.adapter.execute("SELECT count(*) FROM dashboard_cache").fetchone(), (1,)
        )
        self.assertEqual(self.adapter.check_cache_table_collisions(), [],
                         "no cache table may shadow a relation in the data file")

    def test_a_missing_database_file_fails_with_a_usable_message(self):
        with self.assertRaises(RuntimeError) as caught:
            DuckDBFileAdapter(self._dir / "does_not_exist.duckdb")
        self.assertIn("DB_PATH", str(caught.exception))

    def test_named_dict_binding_is_native(self):
        rows = self.adapter.execute(
            "SELECT gp_name FROM planned_activity "
            "WHERE ($d IS NULL OR district_name = $d) ORDER BY gp_name",
            {"d": "Puri"},
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["Delta", "Gamma"])


class NamedBindingTests(unittest.TestCase):
    def test_a_repeated_name_binds_one_value_per_name(self):
        bound = router.bind_named_params(
            TEMPLATE_MAP["P001"]["param_slots"],
            {"district_name": "Puri", "block_name": "Nimapara", "fin_year": "2024-2025"},
        )
        self.assertEqual(
            bound, {"district_name": "Puri", "block_name": "Nimapara", "fin_year": "2024-2025"}
        )

    def test_named_slots_need_no_position_key(self):
        """A named bind has no position to get wrong, so param_slots for named
        entries are not required to carry one. bind_param_values would KeyError."""
        for slot in TEMPLATE_MAP["P001"]["param_slots"]:
            self.assertNotIn("position", slot)
        router.bind_named_params(TEMPLATE_MAP["P001"]["param_slots"], {})

    def test_style_dispatch_returns_a_dict_for_named_and_a_list_for_positional(self):
        named = router.bind_for_template(TEMPLATE_MAP["P002"], {"district_name": "Puri"})
        self.assertIsInstance(named, dict)
        positional = router.bind_for_template(TEMPLATE_MAP["T001"], {"district_name": "Puri"})
        self.assertIsInstance(positional, list)
        self.assertEqual(positional, ["Puri"])


class OptionalSlotTests(unittest.TestCase):
    def test_an_absent_optional_slot_binds_null(self):
        bound = router.bind_named_params(TEMPLATE_MAP["P001"]["param_slots"], {})
        self.assertEqual(
            bound, {"district_name": None, "block_name": None, "fin_year": None}
        )

    def test_an_absent_required_slot_still_raises(self):
        with self.assertRaises(ValueError) as caught:
            router.bind_named_params(
                TEMPLATE_MAP["P002"]["param_slots"], {}, context=" for P002"
            )
        message = str(caught.exception)
        self.assertIn("district_name", message)
        self.assertNotIn("fin_year", message,
                         "an optional slot must never be reported missing")

    def test_optional_slots_are_named_from_the_slot_dicts(self):
        self.assertEqual(
            router.optional_slots(TEMPLATE_MAP["P001"]["param_slots"]),
            {"district_name", "block_name", "fin_year"},
        )
        self.assertEqual(
            router.optional_slots(TEMPLATE_MAP["T001"]["param_slots"]), set(),
            "AP slots carry no optional key and must all stay required",
        )

    def test_an_absent_optional_slot_does_not_stall_on_a_clarification(self):
        """The point of D2: 'how many activities are planned?' is a complete
        question state-wide. Asking 'for which district?' invents a requirement
        the question never had."""
        validated, clarify = router._fill_slots_or_clarify(
            "P001",
            {"district_name": "district_name", "block_name": "block_name",
             "fin_year": "fin_year"},
            {"district_name": None, "block_name": None, "fin_year": None},
            StubValidator(), "how many activities are planned?", "normalized", 0.0,
            optional=router.optional_slots(TEMPLATE_MAP["P001"]["param_slots"]),
        )
        self.assertIsNone(clarify, "an absent optional slot must not clarify")
        self.assertEqual(validated, [])

    def test_an_absent_required_slot_still_stalls(self):
        _, clarify = router._fill_slots_or_clarify(
            "P002",
            {"district_name": "district_name", "fin_year": "fin_year"},
            {"district_name": None, "fin_year": None},
            StubValidator(), "how many activities are planned?", "normalized", 0.0,
            optional=router.optional_slots(TEMPLATE_MAP["P002"]["param_slots"]),
        )
        self.assertIsNotNone(clarify)
        self.assertEqual(clarify.tier, RouteTier.CLARIFY)
        self.assertEqual(clarify.clarification.reason, "missing_parameter")
        self.assertEqual(clarify.pending.missing_slot, "district_name")

    def test_a_supplied_optional_value_is_still_validated(self):
        """Optional means 'may be absent', NOT 'accept anything'. A district the
        registry doesn't know is a mistake to surface — silently binding NULL
        would answer state-wide and call it the district the user asked for."""
        _, clarify = router._fill_slots_or_clarify(
            "P001",
            {"district_name": "district_name"},
            {"district_name": "Kendrapara"},     # real district, not in the stub registry
            StubValidator(), "activities in Kendrapara?", "normalized", 0.0,
            optional={"district_name"},
        )
        self.assertIsNotNone(clarify, "an unknown optional value must clarify")
        self.assertEqual(clarify.clarification.reason, "unknown_entity")


class NamedExecutionTests(_AdapterFixture):
    """End-to-end through _serve_query_id against the real temp database."""

    def _serve(self, query_id, **slots):
        return router._serve_query_id(
            query_id, _entities(**slots), None,
            user_query="q", normalized="q", start=0.0,
            cache_conn=self.adapter,
            dashboard_results={}, template_map=TEMPLATE_MAP, dashboard_questions={},
            start_date=None, end_date=None,
        )

    def test_all_slots_null_answers_state_wide(self):
        result = self._serve("P001")
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE)
        self.assertEqual([r["gp_name"] for r in result.result],
                         ["Alpha", "Beta", "Delta", "Gamma"])

    def test_one_optional_slot_narrows_and_the_rest_stay_off(self):
        result = self._serve("P001", district_name="Khordha")
        self.assertEqual([r["gp_name"] for r in result.result], ["Alpha", "Beta"])

    def test_several_optional_slots_compose(self):
        result = self._serve("P001", district_name="Puri", fin_year="2024-2025")
        self.assertEqual([r["gp_name"] for r in result.result], ["Gamma"])

    def test_the_positional_path_still_executes_unchanged(self):
        result = self._serve("T001", district_name="Puri")
        self.assertEqual([r["gp_name"] for r in result.result], ["Delta", "Gamma"])

    def test_a_missing_required_named_slot_falls_back_rather_than_executing(self):
        result = self._serve("P002")
        self.assertEqual(result.tier, RouteTier.FALLBACK)
        self.assertIn("district_name", result.fallback_message)

    def test_two_different_binds_do_not_share_a_cache_entry(self):
        """The named binds are a DICT, and iterating a dict yields its KEYS — a
        fingerprint over the iteration would be identical for every district, so
        the second district asked would be served the first one's rows."""
        first  = self._serve("P001", district_name="Khordha")
        second = self._serve("P001", district_name="Puri")
        self.assertEqual([r["gp_name"] for r in first.result],  ["Alpha", "Beta"])
        self.assertEqual([r["gp_name"] for r in second.result], ["Delta", "Gamma"])

    def test_the_same_bind_is_served_from_cache(self):
        self._serve("P001", district_name="Puri")
        self.assertTrue(
            any(k.startswith("tmpl:P001:") for k in router._result_cache),
            "named execution must still populate the result cache",
        )


class NamedDateFilterTests(_AdapterFixture):
    """DuckDB will not mix `?` and `$name` in one prepared statement, so an
    injected date predicate has to match the style of the SQL it is spliced into.
    """

    def test_named_injection_emits_named_placeholders_and_a_dict(self):
        sql, offset, binds = router._inject_date_filter(
            "SELECT * FROM planned_activity WHERE district_name = $district_name",
            "", "created_on", "iso",
            start_date="2024-04-01", end_date="2025-03-31", named=True,
        )
        self.assertIn(f"${router.DATE_START_PARAM}", sql)
        self.assertIn(f"${router.DATE_END_PARAM}", sql)
        self.assertNotIn("?", sql)
        self.assertEqual(binds, {router.DATE_START_PARAM: "2024-04-01",
                                 router.DATE_END_PARAM: "2025-03-31"})
        self.assertEqual(offset, 0, "offset is meaningless for named binds")

    def test_positional_injection_is_unchanged(self):
        sql, offset, binds = router._inject_date_filter(
            "SELECT * FROM planned_activity WHERE district_name = ? ORDER BY gp_name LIMIT ?",
            "", "created_on", "iso",
            start_date="2024-04-01", end_date="2025-03-31",
        )
        self.assertEqual(binds, ["2024-04-01", "2025-03-31"])
        self.assertEqual(offset, 1, "the predicate lands ahead of the LIMIT ?")
        self.assertNotIn("$", sql)

    def test_merge_is_style_aware(self):
        self.assertEqual(
            router._merge_date_binds({"d": "Puri"}, 0, {"__date_start": "a", "__date_end": "b"}),
            {"d": "Puri", "__date_start": "a", "__date_end": "b"},
        )
        self.assertEqual(
            router._merge_date_binds(["Puri", 10], 1, ["a", "b"]),
            ["Puri", "a", "b", 10],
        )

    def test_an_injected_named_predicate_actually_executes(self):
        template = {
            "abstract_question": "Activities by year?",
            "sql_template": (
                "SELECT gp_name FROM planned_activity "
                "WHERE ($district_name IS NULL OR district_name = $district_name) "
                "ORDER BY gp_name"
            ),
            "date_filter": {"alias": "", "column": "created_on"},
            "date_kind": "iso",
            "param_slots": [
                {"name": "district_name", "entity_type": "district_name", "optional": True},
            ],
        }
        result = router._serve_query_id(
            "P003", [], None,
            user_query="q", normalized="q", start=0.0,
            cache_conn=self.adapter, dashboard_results={},
            template_map={"P003": template}, dashboard_questions={},
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE, result.fallback_message)
        self.assertTrue(result.date_filter_applied)
        # Delta is 2023-11-20 and drops out; the optional district stays NULL, so
        # the injected predicate is the only filter doing any work.
        self.assertEqual([r["gp_name"] for r in result.result], ["Alpha", "Beta", "Gamma"])


class CaveatPassthroughTests(_AdapterFixture):
    def _serve(self, query_id, **slots):
        return router._serve_query_id(
            query_id, _entities(**slots), None,
            user_query="q", normalized="q", start=0.0,
            cache_conn=self.adapter,
            dashboard_results={}, template_map=TEMPLATE_MAP, dashboard_questions={},
            start_date=None, end_date=None,
        )

    def test_a_caveated_entry_carries_its_note_into_the_result(self):
        self.assertEqual(self._serve("P001", district_name="Puri").caveat, CAVEAT)

    def test_an_entry_without_a_caveat_is_none(self):
        """Additive: every AP entry lacks the key and must behave as before."""
        self.assertIsNone(self._serve("T001", district_name="Puri").caveat)
        self.assertIsNone(self._serve("P002", district_name="Puri").caveat)

    def test_the_caveat_survives_an_empty_result(self):
        """Zero rows is exactly when a reader starts inventing reasons, so the
        note has to be there too."""
        result = self._serve("P001", district_name="Khordha", fin_year="2023-2024")
        self.assertEqual(result.result, [])
        self.assertEqual(result.caveat, CAVEAT)

    def test_the_caveat_is_a_separate_field_not_glued_onto_the_answer(self):
        from query_router.echo import echo_answer
        result = self._serve("P001", district_name="Puri")
        self.assertNotIn(CAVEAT, echo_answer(result))
        self.assertEqual(result.caveat, CAVEAT)


if __name__ == "__main__":
    unittest.main()
