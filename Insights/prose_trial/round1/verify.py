#!/usr/bin/env python
"""WP-D4 T4 -- the AI verifier.

A DIFFERENT model from the writer. The writer is gpt-5.6-sol (pinned by D17);
the verifier is gpt-5.5 -- a different model generation, same vendor. Same
vendor is a disclosed limitation: Insights/.env serves one vendor's key, and
the brief permits same-vendor-only if disclosed.

The verifier never sees the writing task, the checks, or the other findings.
It sees the packet, Appendix A's background, and the rendering.
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prompts import APPENDIX_A, render_packet

VERIFIER_MODEL = "gpt-5.5"

_BACKGROUND = APPENDIX_A.split("Background to reflect where relevant:", 1)[1].strip()

TEMPLATE = """You are checking one short piece of writing against the source material it was written from. You are not judging its style, its tone, or the order it makes its points in. You are judging one thing only: whether it is supported.

SOURCE MATERIAL -- the finding and its reference figures:
{packet}

SOURCE MATERIAL -- background facts about how these records are known to be incomplete:
{background}

THE WRITING TO CHECK:
LEAD: {lead}
DETAIL: {detail}

Answer these two questions:
1. Does the writing claim anything that the source material above does not support -- a number, a place, a comparison, a cause, or a degree of certainty that is not in the sources?
2. Does the writing lose or weaken a limitation that the source material states -- for example presenting a figure as established when the background says the underlying records are partial?

Reply with JSON only, no other text, in exactly this shape:

{{"verdict": "pass", "claim_map": [{{"claim": "<a core claim from the writing, quoted>", "supported_by": "<the exact packet line or background bullet that supports it>"}}]}}

or

{{"verdict": "fail", "problems": [{{"drifted_claim": "<the unsupported or weakened claim, quoted exactly from the writing>", "missing_or_contradicted_fact": "<what the source says instead, or what is absent from it>"}}]}}

Rules for your reply:
- If you answer "pass", claim_map must list EVERY core claim the writing makes, each mapped to a specific source line. A pass with an empty or partial claim_map is not acceptable.
- If anything is unclear or you cannot map a claim, answer "fail" and say so in missing_or_contradicted_fact. Do not guess.
"""


def build_verifier_prompt(packet: dict, lead: str, detail: str) -> str:
    return TEMPLATE.format(packet=render_packet(packet), background=_BACKGROUND,
                           lead=lead, detail=detail)


def parse_verdict(text: str) -> dict:
    """Parse the verifier's JSON. Anything unparseable or vague is a
    FAIL-TO-VERIFY, never a pass (brief T4: 'Vague verdict = fail-to-verify')."""
    raw = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              "verifier returned no parseable JSON: " + raw[:200]}]}
    try:
        obj = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        return {"verdict": "fail_to_verify",
                "problems": [{"drifted_claim": "(none quoted)",
                              "missing_or_contradicted_fact":
                              f"verifier JSON did not parse ({e}): " + raw[:200]}]}

    v = str(obj.get("verdict", "")).lower().strip()
    if v == "pass":
        cm = obj.get("claim_map") or []
        if not cm or not all(c.get("claim") and c.get("supported_by") for c in cm):
            # Rubber-stamp guard: a pass without a real claim mapping is not a pass.
            return {"verdict": "fail_to_verify", "claim_map": cm,
                    "problems": [{"drifted_claim": "(none quoted)",
                                  "missing_or_contradicted_fact":
                                  "verifier passed without a complete claim mapping"}]}
        return {"verdict": "pass", "claim_map": cm}
    if v == "fail":
        probs = obj.get("problems") or []
        if not probs or not all(p.get("drifted_claim") for p in probs):
            return {"verdict": "fail_to_verify", "problems": probs or
                    [{"drifted_claim": "(none quoted)",
                      "missing_or_contradicted_fact": "verifier failed without quoting a claim"}]}
        return {"verdict": "fail", "problems": probs}
    return {"verdict": "fail_to_verify",
            "problems": [{"drifted_claim": "(none quoted)",
                          "missing_or_contradicted_fact": f"verifier gave no clear verdict: {v!r}"}]}


def verifier_reason(res: dict) -> str:
    bits = []
    for p in res.get("problems", []):
        bits.append(f"A reviewer flagged this claim: \"{p.get('drifted_claim')}\". "
                    f"The source says: {p.get('missing_or_contradicted_fact')}")
    return " ".join(bits)
