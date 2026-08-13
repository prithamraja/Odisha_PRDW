"""Regression: templates that repeat a slot across several SQL placeholders
(Q098 filters both its subsidy and procurement subqueries by crop; F09 resolves
one farmer_name across all eight datasets) must receive one value per
placeholder, not one per logical entity. The normal route previously bound each
validated entity once, so every such template failed at the database despite
correct routing. Both execution paths (_serve_query_id and requery_template) now
share bind_param_values."""
import time
import unittest
from types import SimpleNamespace

from query_router import router
from query_router.models import ExtractedEntity, RouteTier
from query_router.template_catalog import TEMPLATE_CATALOG


def _entity(slot, resolved):
    return ExtractedEntity(
        slot_name=slot, raw_value=resolved.lower(),
        resolved_value=resolved, entity_type="social_category",
        confidence="high",
    )


class _CapturingConn:
    """Records every (sql, params) executed; returns one dummy row."""
    def __init__(self):
        self.captured = []

    def execute(self, sql, params):
        self.captured.append((sql, list(params)))
        return SimpleNamespace(
            description=["x"],
            fetchmany=lambda n: [(1,)],
        )


class _StubValidator:
    def validate(self, value, entity_type):
        return SimpleNamespace(resolved_value=value)


# Same shape as the Q024/Q032 comparison family: two logical categories, each
# bound at two interleaved positions.
_INTERLEAVED = {
    "abstract_question": "Compare {social_category} with {social_category_2}?",
    "date_filter": None,
    "date_kind": None,
    "sql_template": "SELECT ?, ?, ?, ?",
    "param_slots": [
        {"name": "social_category",   "entity_type": "social_category",   "position": 1},
        {"name": "social_category_2", "entity_type": "social_category_2", "position": 2},
        {"name": "social_category",   "entity_type": "social_category",   "position": 3},
        {"name": "social_category_2", "entity_type": "social_category_2", "position": 4},
    ],
    "result_ttl_seconds": 0,  # keep the router result cache out of these tests
}


class BindParamValuesTests(unittest.TestCase):
    def test_q098_binds_crop_twice(self):
        slots = TEMPLATE_CATALOG["Q098"]["param_slots"]
        self.assertEqual(
            router.bind_param_values(slots, {"crop": "Paddy"}),
            ["Paddy", "Paddy"],
        )

    def test_f09_binds_the_person_not_the_name(self):
        """F09 used to bind the name eight times, once per dataset, and so
        answered for everyone who shares it. It now binds one Aadhaar once."""
        slots = TEMPLATE_CATALOG["F09"]["param_slots"]
        self.assertEqual(
            router.bind_param_values(
                slots, {"farmer_name": "Ramesh Naidu"},
                person_ids={"farmer_name": "104002954660"},
            ),
            ["104002954660"],
        )

    def test_a_person_bound_slot_without_an_identity_fails_loudly(self):
        """Falling back to the name is what this whole change exists to stop:
        it would put a shared name back into the SQL with nothing to say so."""
        slots = TEMPLATE_CATALOG["F12"]["param_slots"]
        with self.assertRaises(ValueError) as ctx:
            router.bind_param_values(
                slots, {"farmer_name": "Lakshmi Devi"}, context=" for F12"
            )
        # WP-2 fixture swap: the message is domain-neutral now ("one record"),
        # because the same mechanism binds a gram panchayat's LGD code as well
        # as a farmer's Aadhaar. The behaviour asserted is unchanged.
        self.assertIn("did not resolve to one record", str(ctx.exception))

    def test_no_farmer_template_binds_a_name(self):
        """Every farmer_name slot in the catalog is person-bound — F14 is the
        one exception and declares entity_type name_search, because 'which
        farmers share this name' is asking about the collision itself."""
        offenders = [
            qid for qid, t in TEMPLATE_CATALOG.items()
            for s in t["param_slots"]
            if s.get("entity_type") == "farmer_name" and s.get("bind") != "aadhaar"
        ]
        self.assertEqual(offenders, [])
        self.assertEqual(
            [s.get("entity_type") for s in TEMPLATE_CATALOG["F14"]["param_slots"]],
            ["name_search"],
        )

    def test_interleaved_paired_category_template(self):
        self.assertEqual(
            router.bind_param_values(
                _INTERLEAVED["param_slots"],
                {"social_category": "SC", "social_category_2": "ST"},
            ),
            ["SC", "ST", "SC", "ST"],
        )

    def test_positions_win_over_declaration_order(self):
        slots = [
            {"name": "b", "position": 2},
            {"name": "a", "position": 1},
        ]
        self.assertEqual(
            router.bind_param_values(slots, {"a": "A", "b": "B"}),
            ["A", "B"],
        )

    def test_missing_parameter_raises(self):
        slots = TEMPLATE_CATALOG["Q098"]["param_slots"]
        with self.assertRaises(ValueError) as ctx:
            router.bind_param_values(slots, {}, context=" for Q098")
        self.assertIn("missing parameter(s) for Q098: crop", str(ctx.exception))

    def test_every_catalog_template_binds_all_placeholders(self):
        """One value per '?' for the whole catalog, with a value per slot name."""
        for qid, template in TEMPLATE_CATALOG.items():
            slots = template["param_slots"]
            params = {s["name"]: s["name"].upper() for s in slots}
            person_ids = {
                s["name"]: "104002954660"
                for s in slots if s.get("bind") == "aadhaar"
            }
            bound = router.bind_param_values(slots, params, person_ids=person_ids)
            self.assertEqual(
                len(bound), template["sql_template"].count("?"),
                f"{qid}: bound {len(bound)} values for "
                f"{template['sql_template'].count('?')} placeholders",
            )


class ExecutionPathParityTests(unittest.TestCase):
    """The normal route and the compare requery must bind identically."""

    def _serve(self, conn, entities):
        return router._serve_query_id(
            "TX_INTERLEAVED", entities, None,
            user_query="compare sc with st",
            normalized="compare sc with st",
            start=time.monotonic(),
            cache_conn=conn,
            dashboard_results={},
            template_map={"TX_INTERLEAVED": _INTERLEAVED},
            dashboard_questions={},
            start_date=None,
            end_date=None,
        )

    def test_serve_query_id_repeats_values_per_slot(self):
        conn = _CapturingConn()
        result = self._serve(
            conn, [_entity("social_category", "SC"), _entity("social_category_2", "ST")]
        )
        self.assertEqual(result.tier, RouteTier.TIER2_TEMPLATE)
        self.assertEqual(len(conn.captured), 1)
        self.assertEqual(conn.captured[0][1], ["SC", "ST", "SC", "ST"])

    def test_serve_query_id_missing_slot_falls_back_without_executing(self):
        conn = _CapturingConn()
        result = self._serve(conn, [_entity("social_category", "SC")])
        self.assertEqual(result.tier, RouteTier.FALLBACK)
        self.assertEqual(conn.captured, [])

    def test_requery_binds_identically_to_normal_route(self):
        serve_conn = _CapturingConn()
        self._serve(
            serve_conn,
            [_entity("social_category", "SC"), _entity("social_category_2", "ST")],
        )

        requery_conn = _CapturingConn()
        router.requery_template(
            "TX_INTERLEAVED",
            template_map={"TX_INTERLEAVED": _INTERLEAVED},
            cache_conn=requery_conn,
            validator=_StubValidator(),
            bound_params={"social_category": "SC", "social_category_2": "BC"},
            swap_slot="social_category_2",
            swap_value="ST",
            start_date=None,
            end_date=None,
        )

        self.assertEqual(serve_conn.captured[0][1], requery_conn.captured[0][1])


class DateFilterInjectionTests(unittest.TestCase):
    """The AP catalog's date_filters differ from PM-JAY's in two ways the
    injector has to handle: most carry an EMPTY alias (single-table SQL), and
    Agriculture can only be filtered by cropyear, which is a number."""

    def test_empty_alias_omits_the_dot_and_quotes_the_column(self):
        sql, offset, params = router._inject_date_filter(
            'SELECT * FROM ryss WHERE "district" = ?;', "", "SurveyDate", "iso",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertIn('AND "SurveyDate"::DATE BETWEEN ? AND ?', sql)
        self.assertNotIn('."SurveyDate"', sql)   # no broken leading dot
        self.assertNotIn(";", sql)               # appended inside the statement
        self.assertEqual(params, ["2024-01-01", "2024-12-31"])
        self.assertEqual(offset, 1)

    def test_non_empty_alias_still_qualifies_the_column(self):
        sql, _, _ = router._inject_date_filter(
            'SELECT * FROM markfed m WHERE m."DIST_NAME" = ?', "m", "PAYMENT_DATE", "iso",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertIn('m."PAYMENT_DATE"::DATE BETWEEN ? AND ?', sql)

    def test_year_kind_compares_years_numerically(self):
        sql, _, params = router._inject_date_filter(
            'SELECT * FROM agriculture a WHERE a."cropname" = ?', "a", "cropyear", "year",
            start_date="2024-03-01", end_date="2025-02-28",
        )
        self.assertIn('a."cropyear" >= ? AND a."cropyear" <= ?', sql)
        self.assertNotIn("::DATE", sql)
        self.assertEqual(params, [2024, 2025])

    def test_predicate_lands_before_group_by(self):
        sql, _, _ = router._inject_date_filter(
            'SELECT "district", COUNT(*)\nFROM ryss\nWHERE "district" = ?\n'
            'GROUP BY "district"\nORDER BY 2 DESC;',
            "", "SurveyDate", "iso",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertLess(sql.index('"SurveyDate"'), sql.index("GROUP BY"))

    def test_missing_where_starts_one(self):
        sql, _, _ = router._inject_date_filter(
            'SELECT COUNT(*) FROM ryss', "", "SurveyDate", "iso",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertIn('WHERE "SurveyDate"::DATE BETWEEN ? AND ?', sql)

    def test_date_params_are_spliced_ahead_of_a_later_placeholder(self):
        """R03-shaped: 'LIMIT ?' sits AFTER the injection point, so appending the
        date values to the end would bind them to the wrong placeholders."""
        sql, offset, date_params = router._inject_date_filter(
            'SELECT * FROM markfed\nWHERE "DIST_NAME" = ?\nORDER BY 1\nLIMIT ?;',
            "", "PROCUREMENT_DATE", "iso",
            start_date="2024-01-01", end_date="2024-12-31",
        )
        self.assertEqual(offset, 1)
        self.assertEqual(
            router.merge_date_params(["Krishna", 10], offset, date_params),
            ["Krishna", "2024-01-01", "2024-12-31", 10],
        )

    def test_serial_kind_refuses_rather_than_guessing(self):
        with self.assertRaises(router.DateFilterUnsupported):
            router._inject_date_filter(
                'SELECT * FROM fisheries WHERE "district" = ?',
                "", "fcs_registration_date", "serial",
                start_date="2024-01-01", end_date="2024-12-31",
            )

    def test_no_catalog_template_still_declares_serial(self):
        """The data contract is real dates — nothing should need the serial branch."""
        self.assertEqual(
            [tid for tid, t in TEMPLATE_CATALOG.items() if t.get("date_kind") == "serial"],
            [],
        )

    def test_every_dated_template_composes_and_binds(self):
        """Arity holds once the date predicate is appended, for all 83 of them."""
        for tid, template in TEMPLATE_CATALOG.items():
            date_filter = template.get("date_filter")
            if not date_filter:
                continue
            sql, offset, date_params = router._inject_date_filter(
                template["sql_template"], date_filter["alias"], date_filter["column"],
                template.get("date_kind"),
                start_date="2024-01-01", end_date="2024-12-31",
            )
            slots = template["param_slots"]
            bound = router.merge_date_params(
                router.bind_param_values(
                    slots, {s["name"]: s["name"].upper() for s in slots},
                    person_ids={
                        s["name"]: "104002954660"
                        for s in slots if s.get("bind") == "aadhaar"
                    },
                ),
                offset, date_params,
            )
            self.assertEqual(
                len(bound), sql.count("?"),
                f"{tid}: bound {len(bound)} values for {sql.count('?')} placeholders",
            )


if __name__ == "__main__":
    unittest.main()
