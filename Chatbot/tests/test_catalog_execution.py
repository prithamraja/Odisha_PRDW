"""The execution gate: all 346 templates, against the workbook's own answers.

WHAT THIS PROVES
    Every template in TEMPLATE_CATALOG executes against the sample database with
    the workbook's Test Report parameters and returns the row count the Test
    Report recorded. 325 return rows, 21 legitimately return none.

    SQL is deterministic. Unlike routing — which flips ~3% of questions on
    identical replays and must never be regressed on a single miss — a row-count
    mismatch here is a real defect every time: in the conversion from the
    workbook, in the D10 geography rewrite, or in the view wiring. There is no
    replay noise to allow for, so the assertion is exact.

    It is also the only end-to-end check that the geography rewrite is
    *semantically* neutral. Every `$gp_name` predicate was moved off `gp_name`
    onto `gp_lgd_code`, and the 13 v_asset ones onto a subquery through
    v_activity. Binding a name where a code is expected returns zero rows with no
    error anywhere — precisely the silent failure this catches, because the
    oracle says how many rows each query returned BEFORE the rewrite.

THE BINDS GO THROUGH THE REAL VALIDATOR
    The Test Report binds GP names ("Bandhpali"); the rewritten SQL wants LGD
    codes. Rather than translating with a lookup of its own, this test resolves
    every code-bound slot through `EntityValidator`, which is the machinery the
    router uses. So a break in name→code resolution fails here too, rather than
    being papered over by a test-only shortcut.
"""
import json
import unittest
from pathlib import Path

from query_router.template_catalog import TEMPLATE_CATALOG, bind

_BACKEND = Path(__file__).resolve().parents[1]
_DB_PATH = _BACKEND / "data" / "panchayat_1.duckdb"
_ORACLE_PATH = Path(__file__).parent / "data" / "workbook_test_report.json"

_ORACLE = json.loads(_ORACLE_PATH.read_text(encoding="utf-8"))

_STATE: dict = {}


def _open():
    """(adapter, validator) or None — memoised; the DB is on a synced path."""
    if _STATE:
        return _STATE.get("pair")
    pair = None
    if _DB_PATH.exists():
        try:
            from db_factory import open_analytical_db
            from query_router.entity_validator import EntityValidator
            adapter = open_analytical_db(_DB_PATH)
            pair = (adapter, EntityValidator(adapter))
        except Exception:                                    # pragma: no cover
            pair = None
    _STATE["pair"] = pair
    return pair


def tearDownModule():
    pair = _STATE.get("pair")
    if pair is not None:
        try:
            pair[0].close()
        except Exception:                                    # pragma: no cover
            pass


class CatalogueShapeTests(unittest.TestCase):
    """Checks that need no database."""

    def test_the_catalogue_holds_every_answerable_workbook_question(self):
        self.assertEqual(len(TEMPLATE_CATALOG), 346)
        self.assertEqual(set(TEMPLATE_CATALOG), set(_ORACLE))

    def test_the_oracle_binds_exactly_the_slots_each_template_declares(self):
        for qid, entry in TEMPLATE_CATALOG.items():
            with self.subTest(qid=qid):
                self.assertEqual(
                    {s["name"] for s in entry["param_slots"]},
                    set(_ORACLE[qid]["params"]),
                    "the Test Report's sample binds and the template's slots "
                    "have drifted apart",
                )

    def test_no_template_binds_a_gram_panchayat_by_name(self):
        """Decision D4/D10: a GP name is not an identity.

        Statewide ~6,800 GPs share names freely, so a surviving `gp_name = $…`
        predicate would silently aggregate every namesake into one answer — the
        AP name-collision defect transplanted into geography.
        """
        import re
        from tools.build_catalog import mask_literals
        offenders = sorted(
            qid for qid, entry in TEMPLATE_CATALOG.items()
            if re.search(r"\w+\.gp_name\s*(?:=|\bIN\b)\s*\(?\s*\$",
                         mask_literals(entry["sql_template"]), re.IGNORECASE)
        )
        self.assertEqual(offenders, [])

    def test_every_gp_slot_binds_a_code(self):
        for qid, entry in TEMPLATE_CATALOG.items():
            for slot in entry["param_slots"]:
                if slot["entity_type"] in ("gp", "gp_2"):
                    with self.subTest(qid=qid, slot=slot["name"]):
                        self.assertEqual(slot.get("bind"), "code")

    def test_no_entry_carries_a_date_filter(self):
        """Decision D9 — the fiscal year is an ordinary slot.

        `date_kind: "year"` compares INTEGERS, and this column holds the string
        '2024-2025'; a date_filter on it raises a binder error rather than
        answering wrongly, but only once someone asks.
        """
        for qid, entry in TEMPLATE_CATALOG.items():
            with self.subTest(qid=qid):
                self.assertIsNone(entry["date_filter"])
                self.assertIsNone(entry["date_kind"])

    def test_no_sql_uses_tagged_dollar_quoting(self):
        """`$tag$…$tag$` is genuinely ambiguous with `$name` parameters — an
        opening `$tag$` cannot be told from `$tag` followed by `$`. WP-1 report
        §8.4 asked WP-3 to keep it out of the catalogue."""
        import re
        offenders = sorted(
            qid for qid, entry in TEMPLATE_CATALOG.items()
            if re.search(r"\$[a-zA-Z_]\w*\$", entry["sql_template"])
        )
        self.assertEqual(offenders, [])

    def test_every_slot_type_matches_the_entity_registry(self):
        from query_router.entity_validator import PARAM_ENTITY_TYPES
        for qid, entry in TEMPLATE_CATALOG.items():
            for slot in entry["param_slots"]:
                with self.subTest(qid=qid, slot=slot["name"]):
                    self.assertEqual(
                        slot["entity_type"], PARAM_ENTITY_TYPES[slot["name"]],
                        "catalogue and entity registry disagree on what this "
                        "bind name validates as",
                    )

    def test_every_partial_answer_carries_its_caveat(self):
        """Decision D3. A Partial answer without its caveat is the
        confidently-wrong failure mode the whole caveat layer exists for."""
        missing = sorted(
            qid for qid, entry in TEMPLATE_CATALOG.items()
            if entry["answerable"] == "Partial" and not (entry.get("caveat") or "").strip()
        )
        self.assertEqual(missing, [])


@unittest.skipIf(_open() is None, f"no sample database at {_DB_PATH}")
class ExecutionGateTests(unittest.TestCase):
    """All 346, executed."""

    @classmethod
    def setUpClass(cls):
        cls.adapter, cls.validator = _open()
        # Executed ONCE for the whole class: 346 statements over 12,704
        # activities is ~45 seconds, and running them twice to assert two
        # different things about the same results would be paying it twice.
        cls.counts: dict[str, int] = {}
        cls.errors: dict[str, str] = {}
        for qid in sorted(TEMPLATE_CATALOG):
            try:
                sql, params = bind(qid, cls._binds_for(cls, qid))
                cls.counts[qid] = len(cls.adapter.execute(sql, params).fetchall())
            except Exception as exc:
                cls.errors[qid] = f"{type(exc).__name__}: {exc}"

    def _binds_for(self, qid: str) -> dict:
        """The Test Report's sample parameters, resolved the way the router does."""
        entry = TEMPLATE_CATALOG[qid]
        sample = _ORACLE[qid]["params"]
        code_bound = {s["name"] for s in entry["param_slots"] if s.get("bind") == "code"}
        values = {}
        for name, value in sample.items():
            if value is not None and name in code_bound:
                resolved = self.validator.validate(str(value), name.replace("_name", ""))
                assert resolved.resolved_code, f"{qid}: {value!r} resolved to no LGD code"
                value = resolved.resolved_code
            values[name] = value
        return values

    def test_every_template_executes(self):
        self.assertEqual(self.errors, {})

    def test_all_346_reproduce_the_test_report_row_counts(self):
        mismatches = [
            f"{qid}: got {self.counts[qid]} rows, Test Report says {_ORACLE[qid]['rows']}"
            for qid in sorted(self.counts)
            if self.counts[qid] != _ORACLE[qid]["rows"]
        ]
        for qid in sorted(self.counts):
            with self.subTest(qid=qid):
                self.assertEqual(self.counts[qid], _ORACLE[qid]["rows"])
        self.assertEqual(mismatches, [])

    def test_the_21_zero_row_queries_are_the_documented_ones(self):
        """Zero rows is a legitimate answer here — "which GPs uploaded no plan"
        is correctly empty when every loaded GP has one. Pinned as a SET so a NEW
        zero-row query (the shape a broken predicate produces) cannot hide among
        them by coincidence of count."""
        expected_empty = sorted(q for q, o in _ORACLE.items() if o["rows"] == 0)
        self.assertEqual(len(expected_empty), 21)
        self.assertEqual(sorted(q for q, n in self.counts.items() if n == 0),
                         expected_empty)


if __name__ == "__main__":
    unittest.main()
