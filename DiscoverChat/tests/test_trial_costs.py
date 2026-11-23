# -*- coding: utf-8 -*-
"""WP-D13 Fix 9 T4 (D70): a trial never reports $0 for a model it has no
price for.

Each trial script replaces `llm.call` with its own counter when it is
imported, so each is loaded in a separate process and handed a fake model
call -- no model is called. Run:
    python -m pytest DiscoverChat/tests/test_trial_costs.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = ("run_causal_log_trial", "run_headline_trial")

PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
trial = __import__(sys.argv[2])

def fake(model, prompt, max_completion, purpose, **kw):
    return {"usage": {"prompt_tokens": 1000, "completion_tokens": 500},
            "seconds": 1.0, "finish_reason": "stop", "response_text": "x"}

trial._real_call = fake

def run(models):
    trial.CALLS.clear()
    for model in models:
        trial._counted(model, "prompt", 10, "write")
    calls = [c for c in trial.CALLS if c]
    return {"calls": [c["usd"] for c in calls], "spend": trial.spend(calls)}

print(json.dumps({
    "prices": sorted(trial.PRICES),
    "unpriced": run(["gpt-6.2-sol", "gpt-6-luna"]),
    "priced": run(["gpt-5.6-sol"]),
    "mixed": run(["gpt-5.6-sol", "gpt-6.2-sol"]),
}))
"""


def _probe(script: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", PROBE, str(REPO / "DiscoverChat" / "experiments"),
         script], cwd=str(REPO), capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr[-2000:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TrialCostTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = {script: _probe(script) for script in SCRIPTS}

    def test_no_price_is_put_in_for_the_new_models(self):
        for script, r in self.results.items():
            with self.subTest(script=script):
                self.assertNotIn("gpt-6.2-sol", r["prices"])
                self.assertNotIn("gpt-6-luna", r["prices"])

    def test_an_unpriced_model_reports_tokens_and_no_cost(self):
        for script, r in self.results.items():
            with self.subTest(script=script):
                u = r["unpriced"]
                self.assertEqual(u["calls"], [None, None])
                self.assertIsNone(u["spend"]["usd"])
                self.assertEqual(u["spend"]["price_not_set"],
                                 ["gpt-6-luna", "gpt-6.2-sol"])
                text = u["spend"]["text"]
                self.assertIn("2,000 tokens in, 1,000 out", text)
                self.assertIn("price not set for gpt-6.2-sol", text)
                self.assertIn("price not set for gpt-6-luna", text)
                self.assertNotIn("$", text)

    def test_a_priced_model_is_costed_as_before(self):
        for script, r in self.results.items():
            with self.subTest(script=script):
                p = r["priced"]
                # 1,000 in at $4 and 500 out at $20 per 1M tokens
                self.assertEqual(p["calls"], [0.014])
                self.assertEqual(p["spend"]["usd"], 0.014)
                self.assertEqual(p["spend"]["text"], "$0.0140")

    def test_a_mixed_run_never_totals_to_a_dollar_figure(self):
        for script, r in self.results.items():
            with self.subTest(script=script):
                m = r["mixed"]
                self.assertIsNone(m["spend"]["usd"])
                self.assertIn("price not set for gpt-6.2-sol",
                              m["spend"]["text"])
                self.assertIn("$0.0140 for the 1 priced calls",
                              m["spend"]["text"])


if __name__ == "__main__":
    unittest.main()
