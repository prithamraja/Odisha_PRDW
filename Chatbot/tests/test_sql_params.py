"""
WP-1: parameter-style detection and `$name` → pyformat translation.

The engine has to run two catalogues side by side — AP's positional `?` SQL and
the PR&DW catalogue's named `$name` SQL — and the cost of misreading which is
which is a silently wrong answer, not a crash. These tests pin the sniffer and
the translator on the cases that would do that damage.
"""
import unittest

from query_router.sql_params import (
    NAMED,
    POSITIONAL,
    mask_literals,
    named_params,
    param_style,
    positional_count,
    to_pyformat,
    uses_named_params,
)


class MaskingTests(unittest.TestCase):
    def test_mask_preserves_length(self):
        """Offsets found in the masked copy index straight into the original,
        so the translator can rewrite without re-scanning."""
        sql = "SELECT * FROM t WHERE note = 'costs $5' -- $comment\n AND x = $y"
        self.assertEqual(len(mask_literals(sql)), len(sql))

    def test_a_dollar_inside_a_string_literal_is_not_a_parameter(self):
        sql = "SELECT * FROM t WHERE note = 'costs $5 per $unit'"
        self.assertEqual(named_params(sql), [])
        self.assertFalse(uses_named_params(sql))

    def test_a_dollar_inside_a_comment_is_not_a_parameter(self):
        sql = "SELECT 1 -- filter by $district_name later\n"
        self.assertEqual(named_params(sql), [])

    def test_a_dollar_inside_a_block_comment_is_not_a_parameter(self):
        sql = "SELECT 1 /* was $district_name\n   before review */ FROM t"
        self.assertEqual(named_params(sql), [])

    def test_escaped_quote_does_not_end_the_literal_early(self):
        """'it''s $5' is ONE literal. Ending it at the doubled quote would leave
        `$5`... and then treat the rest of the statement as literal text."""
        sql = "SELECT * FROM t WHERE note = 'it''s $5' AND d = $district_name"
        self.assertEqual(named_params(sql), ["district_name"])


class DetectionTests(unittest.TestCase):
    def test_repeated_name_is_reported_once_in_order(self):
        """The optional-filter idiom repeats every parameter. The caller binds one
        value per NAME, so a repeat must not become a second slot."""
        sql = """SELECT count(*) FROM planned_activity pa
                 WHERE ($district_name IS NULL OR pa.district_name = $district_name)
                   AND ($fin_year IS NULL OR pa.fin_year = $fin_year)"""
        self.assertEqual(named_params(sql), ["district_name", "fin_year"])

    def test_positional_sql_has_no_named_params(self):
        sql = "SELECT * FROM pm_kisan WHERE district = ? AND mandal = ? LIMIT ?"
        self.assertEqual(named_params(sql), [])
        self.assertEqual(positional_count(sql), 3)

    def test_positional_count_ignores_a_question_mark_in_a_literal(self):
        sql = "SELECT * FROM t WHERE label = 'why?' AND d = ?"
        self.assertEqual(positional_count(sql), 1)

    def test_numeric_dollar_placeholders_are_not_named(self):
        """`$1` is positional-numeric, a different style — the regex requires an
        identifier so it is not mistaken for a name."""
        self.assertEqual(named_params("SELECT * FROM t WHERE d = $1"), [])

    def test_style_is_sniffed_from_the_sql(self):
        self.assertEqual(
            param_style({"sql_template": "SELECT 1 WHERE d = $district_name"}), NAMED
        )
        self.assertEqual(
            param_style({"sql_template": "SELECT 1 WHERE d = ?"}), POSITIONAL
        )

    def test_a_parameterless_entry_is_positional(self):
        """The 139 AP whole-of-state templates take no parameters at all. They
        must not accidentally land on the named path."""
        self.assertEqual(param_style({"sql_template": "SELECT count(*) FROM t"}), POSITIONAL)

    def test_an_explicit_param_style_overrules_the_sniffer(self):
        entry = {"sql_template": "SELECT 1 WHERE d = $district_name",
                 "param_style": POSITIONAL}
        self.assertEqual(param_style(entry), POSITIONAL)

    def test_a_bad_param_style_fails_loudly(self):
        with self.assertRaises(ValueError):
            param_style({"sql_template": "SELECT 1", "param_style": "dollar"})


class PyformatTranslationTests(unittest.TestCase):
    def test_named_params_become_pyformat(self):
        self.assertEqual(
            to_pyformat("SELECT * FROM t WHERE d = $district_name"),
            "SELECT * FROM t WHERE d = %(district_name)s",
        )

    def test_every_occurrence_of_a_repeated_name_is_rewritten(self):
        out = to_pyformat("WHERE ($d IS NULL OR col = $d)")
        self.assertEqual(out, "WHERE (%(d)s IS NULL OR col = %(d)s)")

    def test_a_literal_percent_is_doubled(self):
        """A pyformat driver scans the WHOLE statement for `%`. An un-doubled
        LIKE pattern raises 'unsupported format character' — and the SBM bracket
        is 86 keyword-matching queries, all of them full of them."""
        self.assertEqual(
            to_pyformat("WHERE activity_name LIKE '%toilet%' AND d = $district_name"),
            "WHERE activity_name LIKE '%%toilet%%' AND d = %(district_name)s",
        )

    def test_a_dollar_in_a_literal_survives_translation(self):
        self.assertEqual(
            to_pyformat("WHERE note = 'costs $5' AND d = $district_name"),
            "WHERE note = 'costs $5' AND d = %(district_name)s",
        )

    def test_positional_sql_is_left_alone(self):
        sql = "SELECT * FROM t WHERE d = ? LIMIT ?"
        self.assertEqual(to_pyformat(sql), sql)

    def test_the_output_is_a_valid_python_format_string(self):
        """psycopg2 binds pyformat through exactly this machinery, so if `%`
        escaping is wrong anywhere, this raises — the cheapest possible proxy for
        a real driver round trip."""
        sql = """SELECT count(*) FROM planned_activity
                 WHERE activity_name LIKE '%toilet%'
                   AND ($district_name IS NULL OR district_name = $district_name)
                   AND pct >= 50"""
        rendered = to_pyformat(sql) % {"district_name": "'Cuttack'"}
        self.assertIn("LIKE '%toilet%'", rendered)
        self.assertEqual(rendered.count("'Cuttack'"), 2)
        self.assertNotIn("$", rendered)


if __name__ == "__main__":
    unittest.main()
