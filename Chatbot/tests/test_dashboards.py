"""The dashboard proposal: derived from ratified SQL, and provably still it.

`dashboard_catalog` builds each entry by substituting a signed-off template's
parameters with literals rather than by authoring new SQL, because a dashboard
answers with no user input to qualify it and unratified SQL is the last place
that should happen. These tests are what make "derived" a fact rather than an
intention: every proposed dashboard is executed and compared, row for row,
against its source template bound with the same values.

They run against the PROPOSAL regardless of whether it has been ratified — the
point is that the operator can see it working before deciding, and that it
cannot rot while it waits.
"""
import unittest
from pathlib import Path

from query_router.dashboard_catalog import (
    DASHBOARD_CATALOG,
    DASHBOARD_FISCAL_YEAR,
    DASHBOARD_TOP_N,
    DASHBOARDS_RATIFIED,
    PROPOSED_DASHBOARDS,
)
from query_router.template_catalog import TEMPLATE_CATALOG, bind

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"

_STATE: dict = {}


def _adapter():
    if _STATE:
        return _STATE.get("adapter")
    adapter = None
    if _DB_PATH.exists():
        try:
            from db_factory import open_analytical_db
            adapter = open_analytical_db(_DB_PATH)
        except Exception:                                    # pragma: no cover
            adapter = None
    _STATE["adapter"] = adapter
    return adapter


def tearDownModule():
    adapter = _STATE.get("adapter")
    if adapter is not None:
        try:
            adapter.close()
        except Exception:                                    # pragma: no cover
            pass


class DashboardProposalTests(unittest.TestCase):
    def test_the_proposal_is_within_the_briefed_range(self):
        self.assertTrue(15 <= len(PROPOSED_DASHBOARDS) <= 25)

    def test_it_ships_inactive_until_ratified(self):
        """The selection — which questions get answered without being asked — is
        the operator's call, so the live catalogue stays empty until they make
        it. Everything downstream already handles an empty one."""
        if not DASHBOARDS_RATIFIED:
            self.assertEqual(DASHBOARD_CATALOG, {})
        else:
            self.assertEqual(DASHBOARD_CATALOG, PROPOSED_DASHBOARDS)

    def test_every_dashboard_comes_from_a_real_template(self):
        for qid, entry in PROPOSED_DASHBOARDS.items():
            with self.subTest(qid=qid):
                self.assertIn(entry["source_template"], TEMPLATE_CATALOG)

    def test_no_dashboard_id_collides_with_a_template_id(self):
        """`_serve_query_id` dispatches on catalogue MEMBERSHIP, so a shared id
        would make one entry unreachable rather than merely confusing. Fifteen
        template ids already begin with D (DQY-*, DSS-*)."""
        self.assertEqual(set(PROPOSED_DASHBOARDS) & set(TEMPLATE_CATALOG), set())

    def test_no_parameter_survives_the_substitution(self):
        """A `$name` left in a dashboard is a statement that cannot execute —
        there is nothing to bind it with, and the seeder would log it as an
        ERROR row rather than fail."""
        import re
        for qid, entry in PROPOSED_DASHBOARDS.items():
            with self.subTest(qid=qid):
                masked = re.sub(r"'(?:[^']|'')*'", "", entry["sql"])
                self.assertNotIn("$", masked)

    def test_the_caveat_travels_with_the_dashboard(self):
        """Decision D3 does not stop applying because an answer was precomputed;
        if anything a tile is where a caveat is most easily read past."""
        for qid, entry in PROPOSED_DASHBOARDS.items():
            with self.subTest(qid=qid):
                self.assertEqual(
                    entry["caveat"],
                    TEMPLATE_CATALOG[entry["source_template"]].get("caveat"),
                )
        caveated = sum(1 for e in PROPOSED_DASHBOARDS.values() if e["caveat"])
        self.assertGreater(caveated, 0)


@unittest.skipIf(_adapter() is None, f"no sample database at {_DB_PATH}")
class DashboardExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = _adapter()

    def _template_rows(self, template_id: str) -> list[tuple]:
        """The source template, bound exactly as the substitution binds it."""
        template = TEMPLATE_CATALOG[template_id]
        values = {}
        for slot in template["param_slots"]:
            name = slot["name"]
            if name in ("date_range", "date_range_2"):
                values[name] = DASHBOARD_FISCAL_YEAR
            elif name == "top_n":
                values[name] = str(DASHBOARD_TOP_N)
            else:
                values[name] = None
        sql, params = bind(template_id, values)
        return self.adapter.execute(sql, params).fetchall()

    def test_every_dashboard_returns_what_its_template_returns(self):
        """The whole safety argument for deriving rather than authoring. If the
        substitution changed the meaning of a statement, this is where it shows.

        Compared as a MULTISET, not as an ordered list. Several of these
        questions rank on a column with heavy ties — PLN-004 sorts nine
        districts by an upload percentage that is 100.0 for most of them — and
        the SQL's own ORDER BY does not determine the order within a tie, so two
        executions of the SAME statement can return the same rows in different
        order. Asserting order would be asserting something neither query
        promises, and would fail at random.
        """
        for qid, entry in sorted(PROPOSED_DASHBOARDS.items()):
            with self.subTest(qid=qid, template=entry["source_template"]):
                dashboard_rows = self.adapter.execute(entry["sql"]).fetchall()
                template_rows = self._template_rows(entry["source_template"])
                self.assertEqual(len(dashboard_rows), len(template_rows))
                self.assertCountEqual(dashboard_rows, template_rows)

    # Two of the proposal return nothing on the 20-GP sample, and both are
    # correct to: they are absence questions ("which GPs filed no plan", "which
    # recorded no activity") and every loaded GP did file and did record. They
    # are kept in the proposal because statewide they are exactly the tiles a
    # review meeting wants. Declared here so a NEWLY empty dashboard — the shape
    # a broken substitution produces — still fails.
    EMPTY_ON_THE_SAMPLE = ["D02", "D20"]

    def test_only_the_documented_dashboards_are_empty(self):
        """An empty dashboard is seeded as status ERROR and renders a blank
        tile, so which ones are empty has to be a decision rather than a
        surprise."""
        empty = sorted(
            qid for qid, entry in PROPOSED_DASHBOARDS.items()
            if not self.adapter.execute(entry["sql"]).fetchall()
        )
        self.assertEqual(empty, self.EMPTY_ON_THE_SAMPLE)


if __name__ == "__main__":
    unittest.main()
