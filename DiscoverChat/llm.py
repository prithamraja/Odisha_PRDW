# -*- coding: utf-8 -*-
"""One logged, capped call path. Every model call in DiscoverChat goes through
here so the budget guard and the usage record cannot be bypassed (WP-D4's llm.py
pattern, D17's budget discipline).

Three things this exists to make impossible:

  - an unlogged call. The routing decision must be logged per turn (D5.2), and
    a decision made by a call nobody recorded is not auditable.
  - an over-budget call. WP-D4's ceilings apply unchanged: 16k in, the D17
    completion budget for the writer, 4k for the verifier.
  - a silently starved verdict. A reasoning model can spend its whole completion
    budget on reasoning and return an empty string with finish_reason='length'
    and no error — that is how an executive report was once generated with every
    section blank. `starved()` names that case so callers handle it rather than
    reading it as a refusal. WP-D4b's D43 addition, retry-once-on-empty, is the
    caller's policy; this module only reports the condition.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from . import config

LOG_DIR = Path(os.getenv("DISCOVERCHAT_LOG_DIR", str(config.HERE / "logs")))
LOG_PATH = LOG_DIR / "calls.jsonl"


def _load_env() -> None:
    from dotenv import load_dotenv
    for candidate in (config.REPO / "Insights" / ".env",
                      Path("i:/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW/"
                           "Insights/.env")):
        if candidate.exists():
            load_dotenv(candidate)


_CLIENT = None


def client():
    global _CLIENT
    if _CLIENT is None:
        _load_env()
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("STOP: no OPENAI_API_KEY from Insights/.env")
        from openai import OpenAI
        _CLIENT = OpenAI()
    return _CLIENT


def count_tokens(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:
        return len(text) // 4


def starved(record: dict) -> bool:
    """The response is empty and the budget was spent. Not a refusal."""
    return (not record["response_text"].strip()
            and record["finish_reason"] == "length")


def call(model: str, prompt: str, max_completion: int, purpose: str,
         *, turn_id=None, attempt=None) -> dict:
    """One chat completion, capped and logged."""
    tokens_in = count_tokens(prompt)
    if tokens_in > config.MAX_PROMPT_TOKENS:
        raise ValueError(
            f"prompt is {tokens_in} tokens, over the {config.MAX_PROMPT_TOKENS} "
            f"cap ({purpose}). Assembly went wrong; the call is not sent."
        )

    started = time.time()
    response = client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_completion,
    )
    elapsed = time.time() - started

    choice = response.choices[0]
    usage = response.usage
    details = getattr(usage, "completion_tokens_details", None)

    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "turn_id": turn_id,
        "purpose": purpose,
        "attempt": attempt,
        "model": model,
        "max_completion_tokens": max_completion,
        "seconds": round(elapsed, 1),
        "input_tokens_estimated": tokens_in,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt": prompt,
        "finish_reason": choice.finish_reason,
        "response_text": choice.message.content or "",
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "reasoning_tokens": getattr(details, "reasoning_tokens", None)
            if details else None,
        },
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
