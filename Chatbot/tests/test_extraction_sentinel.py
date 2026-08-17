"""An API failure must never masquerade as "the user named nothing" (D30.2).

THE DEFECT. `extract_entities` ended:

    except Exception:
        return {s: None for s in slots}

so a timeout, a 429, an auth failure, a truncated reasoning response and a
malformed JSON body were all returned as the same all-null dict the model
produces when it reads the question and finds nothing in it. The officer was
then asked "For which date range?" about a sentence in which they had stated the
year, and nothing in the logs said a call had failed. WP-4 §5.1 found this
sitting beside F1; F1's deterministic fallback landed at `e3e70ff` and this did
not, so D30.2 keeps it as a task in its own right.

WHAT THE FIX IS NOT. It is not a behaviour change. The sentinel is still a dict
of nulls, so every caller reads it exactly as before — and the deterministic
`$date_range` fallback still runs on it, which is precisely right: a year the
user typed is recoverable from the question whether the extractor timed out or
merely declined. What changes is that the CAUSE is attributable, in three
places: the warning log, the usage meter (so the eval can count causes), and
`extraction_failed()` for any caller that wants to branch.

No API key and no network: the client is a stub.
"""
import json
import logging
import unittest

import httpx
import openai

from query_router import entity_extractor as ex
from query_router.entity_extractor import (
    ExtractionUnavailable,
    extract_entities,
    extraction_failed,
)
from query_router.llm_usage import meter

SLOTS = ["date_range", "district_name"]
QUERY = "Which GPs have not uploaded their GPDP in 2024-2025?"

_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content, finish_reason="stop"):
        self.message = _Message(content)
        self.finish_reason = finish_reason


class _Usage:
    def __init__(self, reasoning=0):
        self.prompt_tokens = 500
        self.completion_tokens = 20
        self.total_tokens = 520
        self.completion_tokens_details = type(
            "D", (), {"reasoning_tokens": reasoning})()
        self.prompt_tokens_details = type("D", (), {"cached_tokens": 0})()


class _Response:
    def __init__(self, content, finish_reason="stop", reasoning=0):
        self.choices = [_Choice(content, finish_reason)]
        self.usage = _Usage(reasoning)


class _Client:
    """Whatever `create` is set to: a response to return or an error to raise."""

    def __init__(self, outcome):
        self._outcome = outcome
        parent = self

        class _Completions:
            def create(self, **kwargs):
                if isinstance(parent._outcome, BaseException):
                    raise parent._outcome
                return parent._outcome

        self.chat = type("C", (), {"completions": _Completions()})()


def _call(outcome, slots=SLOTS, query=QUERY):
    return extract_entities(query, slots, _Client(outcome))


class ExtractionSentinelTests(unittest.TestCase):

    def setUp(self):
        meter().reset()

    # ── The discriminator ─────────────────────────────────────────────────────

    def test_an_honest_empty_answer_is_not_the_sentinel(self):
        """The whole point. "How many gram panchayats are there?" names no year
        and no district, and the model saying so is a correct answer, not a
        failure — it must stay distinguishable from one."""
        raw = _call(_Response(json.dumps({})))
        self.assertEqual(raw, {"date_range": None, "district_name": None})
        self.assertFalse(extraction_failed(raw))
        self.assertNotIsInstance(raw, ExtractionUnavailable)

    def test_a_failure_is_the_sentinel_and_still_all_none(self):
        """Callers read `raw.get(slot)` and must not change behaviour."""
        raw = _call(openai.APITimeoutError(request=_REQUEST))
        self.assertEqual(dict(raw), {"date_range": None, "district_name": None})
        self.assertTrue(extraction_failed(raw))
        self.assertEqual(raw.cause, "timeout")

    # ── Every cause the router can be handed ──────────────────────────────────

    def test_each_transport_failure_gets_its_own_cause(self):
        cases = [
            (openai.APITimeoutError(request=_REQUEST), "timeout"),
            (openai.APIConnectionError(request=_REQUEST), "connection"),
            (openai.RateLimitError(
                "slow down", response=httpx.Response(429, request=_REQUEST),
                body=None), "rate_limit"),
            (openai.AuthenticationError(
                "bad key", response=httpx.Response(401, request=_REQUEST),
                body=None), "auth"),
            (openai.InternalServerError(
                "boom", response=httpx.Response(500, request=_REQUEST),
                body=None), "server_error"),
            (RuntimeError("something nobody predicted"), "unexpected_error"),
        ]
        for exc, expected in cases:
            with self.subTest(cause=expected):
                raw = _call(exc)
                self.assertTrue(extraction_failed(raw))
                self.assertEqual(raw.cause, expected)

    def test_an_unknown_provider_subclass_lands_on_its_family(self):
        """The cause map is walked over the MRO precisely so a class we have
        never seen still reports something better than 'unexpected_error'."""
        class SomeFutureRateLimit(openai.RateLimitError):
            pass

        raw = _call(SomeFutureRateLimit(
            "429", response=httpx.Response(429, request=_REQUEST), body=None))
        self.assertEqual(raw.cause, "rate_limit")

    def test_malformed_json_is_bad_json_not_a_timeout(self):
        raw = _call(_Response('{"date_range": "2024-2025"'))
        self.assertEqual(raw.cause, "bad_json")

    def test_a_json_array_is_bad_json(self):
        """Valid JSON, wrong shape — `parsed.get` used to raise AttributeError
        inside the same bare except and read as an empty question."""
        raw = _call(_Response('["2024-2025"]'))
        self.assertEqual(raw.cause, "bad_json")

    def test_an_empty_body_is_reported_as_empty_not_as_an_answer(self):
        raw = _call(_Response(""))
        self.assertEqual(raw.cause, "empty_response")

    def test_a_reasoning_model_that_spent_its_budget_reads_as_truncated(self):
        """`finish_reason='length'` with no content is the D17 failure mode —
        the model thought until the completion budget was gone. Calling that
        'the user named nothing' is how a budget problem hides for a release."""
        raw = _call(_Response("", finish_reason="length"))
        self.assertEqual(raw.cause, "truncated")

    def test_truncated_json_is_truncated_rather_than_malformed(self):
        raw = _call(_Response('{"date_range": "2024-', finish_reason="length"))
        self.assertEqual(raw.cause, "truncated")

    # ── The log has to say which ──────────────────────────────────────────────

    def test_the_log_attributes_the_cause(self):
        """D30.2's actual requirement: 'the log must attribute the cause'."""
        with self.assertLogs("query_router.entity_extractor", level="WARNING") as cm:
            _call(openai.APITimeoutError(request=_REQUEST))
        message = "\n".join(cm.output)
        self.assertIn("UNAVAILABLE", message)
        self.assertIn("timeout", message)
        self.assertIn("date_range", message)

    def test_a_successful_call_logs_no_warning(self):
        logger = logging.getLogger("query_router.entity_extractor")
        with self.assertNoLogs(logger, level="WARNING"):
            _call(_Response(json.dumps({"date_range": "2024-2025"})))

    # ── The meter tells the two apart, which is what T4 counts ────────────────

    def test_the_meter_separates_a_failure_from_an_empty_answer(self):
        _call(openai.APITimeoutError(request=_REQUEST))
        _call(_Response(json.dumps({})))
        _call(_Response(json.dumps({"date_range": "2024-2025"}), reasoning=140))

        stats = meter().extraction_stats()
        self.assertEqual(stats["extraction_calls"], 3)
        self.assertEqual(stats["unavailable_calls"], 1)
        self.assertEqual(stats["unavailable_causes"], {"timeout": 1})
        # Of the two calls the model actually ANSWERED, one was all-None.
        self.assertEqual(stats["all_none_answered"], 1)
        self.assertEqual(stats["all_none_rate_answered"], 0.5)

    def test_reasoning_tokens_are_recorded_per_extraction_call(self):
        """The F1 telltale: nulls at 40/49/52 reasoning tokens, reads at
        80–201. WP-4 could only see that in a hand-run diagnostic."""
        _call(_Response(json.dumps({}), reasoning=45))
        _call(_Response(json.dumps({"date_range": "2024-2025",
                                    "district_name": "Khordha"}), reasoning=150))
        stats = meter().extraction_stats()
        self.assertEqual(stats["reasoning_tokens_when_all_none"]["max"], 45)
        self.assertEqual(stats["reasoning_tokens_when_read"]["min"], 150)
        self.assertEqual(meter().totals()["reasoning_tokens"], 195)

    def test_null_rates_are_reported_per_slot_family(self):
        """D30.1 shelved the retry on condition that the CATEGORICAL rate be
        measured — `$date_range` has a deterministic reader behind it and a
        theme has nothing."""
        _call(_Response(json.dumps({"date_range": "2024-2025"})),
              slots=["date_range", "theme", "top_n"])
        stats = meter().extraction_stats()
        families = stats["by_slot_family"]
        self.assertEqual(families["date"]["null_rate"], 0.0)
        self.assertEqual(families["categorical"]["null_rate"], 1.0)
        self.assertEqual(families["numeric"]["null_rate"], 1.0)

    # ── Blast radius ──────────────────────────────────────────────────────────

    def test_no_slots_still_costs_nothing(self):
        raw = extract_entities(QUERY, [], _Client(RuntimeError("must not be called")))
        self.assertEqual(raw, {})
        self.assertEqual(meter().extraction_stats()["extraction_calls"], 0)

    def test_the_sentinel_carries_the_detail_for_a_human(self):
        raw = _call(openai.APITimeoutError(request=_REQUEST))
        self.assertIn("APITimeoutError", raw.detail)

    def test_extraction_failed_is_false_for_a_plain_dict(self):
        self.assertFalse(extraction_failed({"date_range": None}))
        self.assertFalse(extraction_failed(None))


if __name__ == "__main__":
    unittest.main()
