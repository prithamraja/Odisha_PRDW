"""Regression: templates that repeat a slot across several SQL placeholders must
receive one value per placeholder, not one per logical entity. The normal route
previously bound each validated entity once, so every such template failed at
the database despite correct routing. Both execution paths (_serve_query_id and
requery_template) share the binders.

That defect was found on the AP catalogue, where repetition was occasional
(Q098's twice-filtered crop). It is the NORM here: decision D2's optional-filter
idiom `($p IS NULL OR col = $p)` writes every geography parameter twice, so all
346 PR&DW templates repeat at least one slot and most repeat three."""
import time
import unittest
from types import SimpleNamespace

from query_router import router
from query_router.models import ExtractedEntity, RouteTier
from query_router.template_catalog import TEMPLATE_CATALOG, bind as bind_template


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
    """WP-3 fixture swap. The AP catalogue these named (Q098's twice-bound crop,
    F09's eight-dataset farmer lookup) is gone; the MECHANISM they pin is not,
    and the PR&DW catalogue exercises it harder — the optional-filter idiom
    `($p IS NULL OR col = $p)` writes every geography parameter twice, in all
    346 entries."""

    def test_a_repeated_slot_binds_once_per_occurrence(self):
        """The named path binds a DICT with one entry per slot NAME, however many
        times the name occurs — which is the whole point, since PLN-001 writes
        `$gp_name` twice and would otherwise need two values for one entity."""
        sql, params = bind_template("PLN-001", {
            "date_range": "2024-2025", "district_name": None,
            "block_name": None, "gp_name": "116350",
        })
        self.assertEqual(sql.count("$gp_name"), 2)
        self.assertEqual(params["gp_name"], "116350")
        self.assertEqual(len(params), 4)

    def test_a_code_bound_slot_binds_the_code_not_the_name(self):
        """Decision D4/D10: a GP name is not an identity. This is the AP
        name-collision defect (four Lakshmi Devis reported as one farmer's
        ₹259,181) transplanted into geography — statewide ~6,800 panchayats share
        names freely, so binding 'Naugaon' would merge every namesake."""
        slots = TEMPLATE_CATALOG["PLN-001"]["param_slots"]
        bound = router.bind_named_params(
            slots,
            {"date_range": "2024-2025", "gp_name": "Naugaon"},
            person_ids={"gp_name": "116350"},
        )
        self.assertEqual(bound["gp_name"], "116350")

    def test_a_code_bound_slot_without_an_identity_fails_loudly(self):
        """Falling back to the name is what this whole mechanism exists to stop:
        it would put a shared name back into the SQL with nothing to say so."""
        slots = TEMPLATE_CATALOG["TRD-010"]["param_slots"]
        with self.assertRaises(ValueError) as ctx:
            router.bind_named_params(
                slots,
                {"date_range": "2024-2025", "gp_name": "Naugaon",
                 "gp_name_2": "Rampur"},
                context=" for TRD-010",
            )
        self.assertIn("did not resolve to one record", str(ctx.exception))

    def test_every_gp_slot_in_the_catalogue_is_code_bound(self):
        """The catalogue-wide version of the same rule: not one template may
        filter a gram panchayat by name."""
        offenders = sorted(
            qid for qid, t in TEMPLATE_CATALOG.items()
            for s in t["param_slots"]
            if s.get("entity_type") in ("gp", "gp_2") and s.get("bind") != "code"
        )
        self.assertEqual(offenders, [])

    def test_an_absent_optional_slot_binds_null_rather_than_stalling(self):
        """Decision D2. 'How many activities are planned?' is a complete question
        state-wide; demanding a district would invent a requirement it never had."""
        _, params = bind_template("PLN-001", {"date_range": "2024-2025"})
        self.assertEqual(params["district_name"], None)
        self.assertEqual(params["block_name"], None)
        self.assertEqual(params["gp_name"], None)

    def test_every_top_n_slot_is_optional_with_the_default_page_size(self):
        """Decision D18.P1. `$top_n` is the LIMIT on 91 of the 346 templates and
        no officer says "top 10" — generated as REQUIRED, every ranking question
        stalls on a "how many rows?" chip (WP-4a §5.2)."""
        offenders = sorted(
            f"{qid} ${s['name']}"
            for qid, t in TEMPLATE_CATALOG.items()
            for s in t["param_slots"]
            if s["name"] == "top_n"
            and not (s.get("optional") and s.get("default") == "10")
        )
        self.assertEqual(offenders, [])
        self.assertEqual(
            sum(1 for t in TEMPLATE_CATALOG.values()
                for s in t["param_slots"] if s["name"] == "top_n"),
            91,
        )

    def test_the_declared_default_and_the_runtime_table_agree(self):
        """Two places name a default and they must not drift: the catalogue
        declares it per slot (the authority since D18.P1) while
        `_DEFAULT_ENTITY_VALUES` keeps the entity-type fallback the AP fixtures
        still use."""
        from tools.build_catalog import DEFAULTED_SLOTS
        for name, value in DEFAULTED_SLOTS.items():
            with self.subTest(slot=name):
                self.assertEqual(router._DEFAULT_ENTITY_VALUES.get(name), value)

    def test_a_ranking_template_binds_the_default_rather_than_null(self):
        """The one thing optionality must NOT mean here: `LIMIT NULL` is
        unbounded, so a `$top_n` that fell through to NULL would dump the whole
        result set instead of a page — the opposite of what the slot is for."""
        qid = next(q for q, t in TEMPLATE_CATALOG.items()
                   if any(s["name"] == "top_n" for s in t["param_slots"]))
        slots = TEMPLATE_CATALOG[qid]["param_slots"]
        bound = router.bind_named_params(
            slots,
            {s["name"]: "x" for s in slots
             if s["name"] != "top_n" and not s.get("optional")},
            person_ids={s["name"]: "116350"
                        for s in slots if s.get("bind") == "code"},
        )
        self.assertEqual(bound["top_n"], "10")

    def test_judgement_thresholds_stay_required_and_undefaulted(self):
        """Decision D18.P2, the counterpart to P1: `$threshold` (13 templates)
        and `$amount_threshold` (2) change the POPULATION under study — a
        completion-rate league table topped by a focus area with two activities
        is the confidently-wrong output the threshold exists to prevent. They
        clarify; they never default."""
        bearing = sorted({
            qid for qid, t in TEMPLATE_CATALOG.items()
            for s in t["param_slots"]
            if s["name"] in ("threshold", "amount_threshold")
        })
        self.assertEqual(len(bearing), 15)
        for qid in bearing:
            for slot in TEMPLATE_CATALOG[qid]["param_slots"]:
                if slot["name"] in ("threshold", "amount_threshold"):
                    with self.subTest(qid=qid, slot=slot["name"]):
                        self.assertNotIn("default", slot)
                        self.assertFalse(slot.get("optional"))

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
        """A REQUIRED slot with no value still stops, on the named path too —
        optional slots binding NULL must not have made every slot optional."""
        slots = TEMPLATE_CATALOG["PLN-001"]["param_slots"]
        with self.assertRaises(ValueError) as ctx:
            router.bind_named_params(slots, {}, context=" for PLN-001")
        self.assertIn("missing parameter(s) for PLN-001: date_range",
                      str(ctx.exception))

    def test_every_catalog_template_binds_every_placeholder_it_contains(self):
        """The structural gate, for all 346: every `$name` in a statement has a
        slot to bind it, and every slot appears in its statement.

        A `$name` with no slot is an unbound-parameter error at execution; a slot
        with no placeholder is a value the user was asked for and then ignored,
        which is worse because it answers.
        """
        import re
        from tools.build_catalog import mask_literals
        for qid, template in TEMPLATE_CATALOG.items():
            with self.subTest(qid=qid):
                declared = {s["name"] for s in template["param_slots"]}
                in_sql = set(re.findall(
                    r"\$(\w+)", mask_literals(template["sql_template"])))
                self.assertEqual(declared, in_sql)

    def test_every_template_is_detected_as_named(self):
        """Decision D1 — the workbook's `$name` SQL executes verbatim. A template
        mis-sniffed as positional would bind a LIST against `$name` placeholders
        and fail at the database."""
        from query_router.sql_params import NAMED, param_style
        for qid, template in TEMPLATE_CATALOG.items():
            with self.subTest(qid=qid):
                self.assertEqual(param_style(template), NAMED)


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
