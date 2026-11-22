# -*- coding: utf-8 -*-
"""WP-D13 Fix 6 (D68): the cause-and-effect check behind a switch.

DISCOVERCHAT_CAUSAL_CHECK = block | log | off, default log. Offline -- the
writer is a stub, no model calls. Run:
    python -m pytest DiscoverChat/tests/test_causal_mode.py -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from DiscoverChat import config  # noqa: F401  -- first, puts Insights/src on the path
from DiscoverChat import causal_gate, checks, llm, writer
from DiscoverChat.tests.test_citations import CLEAN, FINDINGS, RUN_DATE

REPO = Path(__file__).resolve().parents[2]

# Correct prose with the two words the writer actually used (D66 §6.2): a
# reason for a recommendation, and "therefore" joining a fact to one.
CAUSAL_WORDED = (CLEAN + " Activity records need attention because the "
                 "untied grant is concentrated [1-00987]. Attention should "
                 "therefore cover all 20 Gram Panchayats [d1-00042].")


def _stub(replies):
    """A writer that hands back `replies` in turn and counts its calls."""
    calls = []

    def fake_call(model, prompt, max_completion, purpose, **kw):
        calls.append({"purpose": purpose, "attempt": kw.get("attempt"),
                      "prompt": prompt})
        return {"response_text": replies[min(len(calls), len(replies)) - 1],
                "finish_reason": "stop", "usage": {}}
    return fake_call, calls


class CitationModeTests(unittest.TestCase):
    """Step 3_causal of check_citations, the live path."""

    def run_mode(self, mode, prose=CAUSAL_WORDED):
        return checks.check_citations(prose, FINDINGS, run_date=RUN_DATE,
                                      causal_mode=mode)

    def test_log_passes_and_records_the_scan(self):
        r = self.run_mode("log")
        self.assertTrue(r["all_pass"], checks.citation_failure_reason(r))
        causal = r["3_causal"]
        self.assertFalse(causal["pass"])
        self.assertFalse(causal["counts"])
        self.assertEqual([p["surface"] for p in causal["problems"]],
                         ["because", "therefore"])
        self.assertEqual(len(causal["sentences"]), 2)
        self.assertEqual(causal["sentences"][0]["words"], ["because"])
        self.assertIn("Attention should therefore cover",
                      causal["sentences"][1]["sentence"])
        self.assertEqual(checks.citation_failure_reason(r), "")

    def test_block_is_todays_behaviour(self):
        r = self.run_mode("block")
        self.assertFalse(r["all_pass"])
        # byte for byte what the scan returns -- no extra keys
        self.assertEqual(r["3_causal"],
                         causal_gate.check(checks.strip_tags(CAUSAL_WORDED)))
        self.assertIn("causal wording", checks.citation_failure_reason(r))

    def test_off_omits_the_key(self):
        r = self.run_mode("off")
        self.assertNotIn("3_causal", r)
        self.assertTrue(r["all_pass"])
        self.assertEqual(checks.citation_failure_reason(r), "")

    def test_log_does_not_hide_another_failure(self):
        r = self.run_mode("log", CAUSAL_WORDED + " There were 7 exceptions.")
        self.assertFalse(r["all_pass"])
        reason = checks.citation_failure_reason(r)
        self.assertIn("7 (no finding cited in this sentence)", reason)
        self.assertNotIn("causal wording", reason)

    def test_the_configured_mode_is_read_at_call_time(self):
        with mock.patch.object(config, "CAUSAL_CHECK", "block"):
            self.assertFalse(checks.check_citations(
                CAUSAL_WORDED, FINDINGS, run_date=RUN_DATE)["all_pass"])
        with mock.patch.object(config, "CAUSAL_CHECK", "off"):
            self.assertNotIn("3_causal", checks.check_citations(
                CAUSAL_WORDED, FINDINGS, run_date=RUN_DATE))

    def test_an_unknown_override_raises(self):
        with self.assertRaises(ValueError):
            self.run_mode("warn")


class ConnectiveModeTests(unittest.TestCase):
    """Check e_causal of check_prose, the DISCOVERCHAT_CONSOLIDATE=0 path."""

    PROSE = "Attention should therefore go to these blocks."

    def test_log(self):
        r = checks.check_prose(self.PROSE, [], causal_mode="log")
        self.assertTrue(r["all_pass"])
        self.assertFalse(r["e_causal"]["pass"])
        self.assertFalse(r["e_causal"]["counts"])
        self.assertEqual(checks.failure_reason(r), "")

    def test_block(self):
        r = checks.check_prose(self.PROSE, [], causal_mode="block")
        self.assertFalse(r["all_pass"])
        self.assertEqual(r["e_causal"], causal_gate.check(self.PROSE))
        self.assertIn("causal wording", checks.failure_reason(r))

    def test_off(self):
        r = checks.check_prose(self.PROSE, [], causal_mode="off")
        self.assertNotIn("e_causal", r)
        self.assertTrue(r["all_pass"])


class WriterModeTests(unittest.TestCase):
    """`writer.consolidate` with a stub writer: what the switch does to the
    retry and the fall-back."""

    def setUp(self):
        self.logdir = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(llm, "LOG_DIR",
                                          Path(self.logdir.name))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.logdir.cleanup()

    def log_lines(self):
        path = Path(self.logdir.name) / "citation_failures.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def consolidate(self, mode, replies):
        fake, calls = _stub(replies)
        with mock.patch.object(config, "CAUSAL_CHECK", mode), \
                mock.patch.object(llm, "call", fake):
            out = writer.consolidate("Where should attention go?", FINDINGS,
                                     run_date=RUN_DATE, turn_id="t-fix6")
        return out, calls

    def test_log_keeps_the_narrative_on_attempt_1(self):
        out, calls = self.consolidate("log", [CAUSAL_WORDED])
        self.assertEqual(len(calls), 1)
        self.assertFalse(out.fell_back)
        self.assertEqual(out.attempts, 1)
        self.assertEqual(out.tagged, CAUSAL_WORDED)
        lines = self.log_lines()
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["kind"], "causal_words_shown")
        self.assertFalse(line["fell_back"])
        self.assertEqual(line["turn_id"], "t-fix6")
        self.assertEqual(line["question"], "Where should attention go?")
        self.assertEqual(line["words"], ["because", "therefore"])
        self.assertEqual([s["words"] for s in line["sentences"]],
                         [["because"], ["therefore"]])
        self.assertNotIn("reason", line)

    def test_log_writes_nothing_for_a_clean_answer(self):
        out, calls = self.consolidate("log", [CLEAN])
        self.assertFalse(out.fell_back)
        self.assertEqual(self.log_lines(), [])

    def test_log_still_retries_and_falls_back_on_another_step(self):
        untagged = CAUSAL_WORDED + " There were 7 exceptions."
        out, calls = self.consolidate("log", [untagged, untagged])
        self.assertEqual(len(calls), 2)
        self.assertTrue(out.fell_back)
        self.assertIn("7 (no finding cited", out.reason)
        self.assertNotIn("causal wording", out.reason)
        # the retry prompt carries the other step's reason, not the causal one
        self.assertIn("7 (no finding cited", calls[1]["prompt"])
        self.assertNotIn("causal wording", calls[1]["prompt"])
        lines = self.log_lines()
        self.assertEqual(len(lines), 2)          # the two failed attempts
        self.assertTrue(all("kind" not in line for line in lines))

    def test_block_retries_then_falls_back(self):
        out, calls = self.consolidate("block", [CAUSAL_WORDED, CAUSAL_WORDED])
        self.assertEqual(len(calls), 2)
        self.assertTrue(out.fell_back)
        self.assertIn("causal wording", out.reason)
        self.assertIn("causal wording", calls[1]["prompt"])
        self.assertTrue(all("kind" not in line for line in self.log_lines()))

    def test_off_keeps_the_narrative_and_logs_nothing(self):
        out, calls = self.consolidate("off", [CAUSAL_WORDED])
        self.assertEqual(len(calls), 1)
        self.assertFalse(out.fell_back)
        self.assertEqual(self.log_lines(), [])


class StartupTests(unittest.TestCase):
    def test_an_unknown_value_raises_at_startup(self):
        env = dict(os.environ, DISCOVERCHAT_CAUSAL_CHECK="warn")
        proc = subprocess.run(
            [sys.executable, "-c", "import DiscoverChat.config"],
            cwd=str(REPO), env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("DISCOVERCHAT_CAUSAL_CHECK", proc.stderr)

    def test_the_default_is_log_and_is_in_the_settings_dump(self):
        env = {k: v for k, v in os.environ.items()
               if k != "DISCOVERCHAT_CAUSAL_CHECK"}
        proc = subprocess.run(
            [sys.executable, "-c",
             "from DiscoverChat import config; k = config.knobs(); "
             "print(k['causal_check'], k['direction_check'])"],
            cwd=str(REPO), env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.split()[0], "log")


if __name__ == "__main__":
    unittest.main()
