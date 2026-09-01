#!/usr/bin/env python
"""WP-D4 -- one logged, capped call path. Every call in the trial goes through
here so the spend guard and the usage record cannot be bypassed."""
import os, sys, json, time, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
LOG = os.path.join(HERE, "logs", "calls.jsonl")

# Spend guard, from the brief. Hard limits, enforced here in code.
MAX_CALLS = 60
MAX_INPUT_TOKENS = 16000
WRITER_MAX_COMPLETION = 8000
VERIFIER_MAX_COMPLETION = 4000

# The key lives in the Drive .env and is loaded FROM THERE, in place. It is
# never copied into the mirror, printed, or written. (WPD3 §4.4 bug 1 was this
# path being wrong and the load silently doing nothing.)
DRIVE_ENV = ("i:/My Drive/ASC Lab/LMIC AI Code repo/Odisha_PRDW/Insights/.env")


def _client():
    from dotenv import load_dotenv
    load_dotenv(DRIVE_ENV)
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("STOP: no OPENAI_API_KEY from Insights/.env")
    from openai import OpenAI
    return OpenAI()


def count_tokens(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:
        return len(text) // 4


def calls_so_far() -> int:
    if not os.path.exists(LOG):
        return 0
    with open(LOG, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def call(model: str, prompt: str, max_completion: int, purpose: str,
         rank=None, attempt=None) -> dict:
    """One chat completion. Enforces the caps, logs request/response/usage."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    n = calls_so_far()
    if n >= MAX_CALLS:
        raise SystemExit(f"STOP: spend guard -- {n} calls already made, cap is {MAX_CALLS}")

    tok_in = count_tokens(prompt)
    if tok_in > MAX_INPUT_TOKENS:
        # Brief: "a packet overflow means T1 went wrong -- STOP, don't send".
        raise SystemExit(f"STOP: input {tok_in} tokens > {MAX_INPUT_TOKENS} cap ({purpose})")

    client = _client()
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_completion,
    )
    dt = time.time() - t0

    choice = resp.choices[0]
    text = choice.message.content or ""
    u = resp.usage
    details = getattr(u, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details else None

    rec = {
        "call_index": n + 1,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "purpose": purpose,
        "rank": rank,
        "attempt": attempt,
        "model": model,
        "max_completion_tokens": max_completion,
        "seconds": round(dt, 1),
        "input_tokens_estimated": tok_in,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt": prompt,
        "finish_reason": choice.finish_reason,
        "response_text": text,
        "response_chars": len(text),
        "usage": {
            "prompt_tokens": u.prompt_tokens,
            "completion_tokens": u.completion_tokens,
            "total_tokens": u.total_tokens,
            "reasoning_tokens": reasoning,
        },
    }
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return rec
