"""What every paid call actually cost, and what the extractor actually returned.

WHY THIS EXISTS (WP-4 §4, D28.8). WP-4 spent ~1,878 API calls and could not
state a token figure, because none of the three harnesses recorded `resp.usage`.
Worse, the ONE number that identified F1 — reasoning tokens per extraction call —
was only ever seen in a hand-run diagnostic: the three null extractions spent
40/49/52 reasoning tokens where every success spent 80–201. That signal is a
field on every response the router already receives and was being thrown away.

So this module is a passive meter. Every LLM call site hands it the response; it
keeps a record and nothing else. Two properties are load-bearing:

  IT NEVER RAISES. Instrumentation that can break a call is worse than no
  instrumentation. Every entry point is wrapped; a provider that renames a usage
  field costs a zero in a report, never a failed route.

  IT IS ALWAYS ON. Recording an integer per call is free next to the call
  itself, and a meter you have to remember to enable is a meter that is off on
  the run you needed it for.

The harnesses call `meter().reset()` before a replay and read `snapshot()`
after, so per-replay totals are per-replay rather than cumulative.

THE EXTRACTION LEDGER is the second half. `record_extraction` notes, per call,
which slots were asked for and which came back null, so a run can report the
all-None rate BY SLOT FAMILY (D30.1: the deterministic fallback covers
`$date_range`, and nothing covers a theme or a scheme — if the wobble moves to a
categorical slot there is no backstop, and this is what would show it).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Slot families, keyed on the WORKBOOK'S BIND NAMES — the same strings
# `param_slots` carries and `extract_entities` is asked for. The split exists
# because the slots differ in what happens when extraction returns null:
# `date` has a deterministic reader behind it (router._fiscal_year_from_text),
# `place` clarifies visibly, `numeric` mostly carries a default, and
# `categorical` has NO backstop at all — which is why D30.1 shelved the retry on
# condition that this rate be measured.
_DATE_SLOTS = {"date_range", "date_range_2"}
_PLACE_SLOTS = {"district_name", "block_name", "block_name_2",
                "gp_name", "gp_name_2"}
_CATEGORICAL_SLOTS = {"theme", "scheme", "scheme_2", "status", "focus_area",
                      "asset_category", "asset_sub_category", "activity_code"}
_NUMERIC_SLOTS = {"top_n", "threshold", "amount_threshold"}

SLOT_FAMILIES = ("date", "place", "categorical", "numeric", "other")


def slot_family(slot: str) -> str:
    """Which backstop, if any, covers this slot when extraction returns null."""
    if slot in _DATE_SLOTS:
        return "date"
    if slot in _PLACE_SLOTS:
        return "place"
    if slot in _CATEGORICAL_SLOTS:
        return "categorical"
    if slot in _NUMERIC_SLOTS:
        return "numeric"
    return "other"


@dataclass
class CallUsage:
    """One billed call. Token counts are 0 where the provider reported none."""
    site: str                    # extraction | rerank | classify | followup | embed
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str | None = None


@dataclass
class ExtractionOutcome:
    """One `extract_entities` call, as the router saw it come back."""
    slots: tuple[str, ...]
    null_slots: tuple[str, ...]
    cause: str | None            # None = the model answered; else the sentinel's cause
    reasoning_tokens: int | None = None
    query: str = ""              # truncated — this is a log, not a transcript

    @property
    def all_none(self) -> bool:
        return bool(self.slots) and len(self.null_slots) == len(self.slots)


def _int(value) -> int:
    try:
        return int(value or 0)
    except Exception:                                        # pragma: no cover
        return 0


def _usage_fields(usage) -> tuple[int, int, int, int, int]:
    """(prompt, completion, reasoning, cached, total) off an SDK usage object.

    Reasoning and cached tokens live in nested `*_details` objects that older
    responses and the embeddings endpoint do not carry at all, so every read is
    defended individually rather than the block as a whole — a missing
    `cached_tokens` must not cost us the prompt count next to it.
    """
    prompt = _int(getattr(usage, "prompt_tokens", 0))
    completion = _int(getattr(usage, "completion_tokens", 0))
    total = _int(getattr(usage, "total_tokens", 0)) or (prompt + completion)
    reasoning = _int(getattr(
        getattr(usage, "completion_tokens_details", None), "reasoning_tokens", 0))
    cached = _int(getattr(
        getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0))
    return prompt, completion, reasoning, cached, total


@dataclass
class UsageMeter:
    calls: list[CallUsage] = field(default_factory=list)
    extractions: list[ExtractionOutcome] = field(default_factory=list)

    # ── recording ─────────────────────────────────────────────────────────────

    def record_call(self, site: str, model: str, resp, *,
                    finish_reason: str | None = None) -> CallUsage | None:
        """Note one response's usage. Returns the record, for a caller that
        wants the reasoning-token count it just produced."""
        try:
            usage = getattr(resp, "usage", None)
            prompt, completion, reasoning, cached, total = (
                _usage_fields(usage) if usage is not None else (0, 0, 0, 0, 0))
            if finish_reason is None:
                choices = getattr(resp, "choices", None) or []
                if choices:
                    finish_reason = getattr(choices[0], "finish_reason", None)
            record = CallUsage(
                site=site, model=str(model),
                prompt_tokens=prompt, completion_tokens=completion,
                reasoning_tokens=reasoning, cached_tokens=cached,
                total_tokens=total, finish_reason=finish_reason,
            )
            self.calls.append(record)
            return record
        except Exception:                                    # pragma: no cover
            return None

    def record_extraction(self, slots, parsed: dict | None, *,
                          cause: str | None = None,
                          reasoning_tokens: int | None = None,
                          query: str = "") -> None:
        """Note what one extraction call returned, null slots and all."""
        try:
            slots = tuple(slots or ())
            if parsed is None:
                nulls = slots
            else:
                nulls = tuple(s for s in slots if parsed.get(s) in (None, ""))
            self.extractions.append(ExtractionOutcome(
                slots=slots, null_slots=nulls, cause=cause,
                reasoning_tokens=reasoning_tokens, query=(query or "")[:160],
            ))
        except Exception:                                    # pragma: no cover
            pass

    # ── reading ───────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.calls.clear()
        self.extractions.clear()

    def totals(self) -> dict:
        return {
            "calls": len(self.calls),
            "prompt_tokens": sum(c.prompt_tokens for c in self.calls),
            "completion_tokens": sum(c.completion_tokens for c in self.calls),
            "reasoning_tokens": sum(c.reasoning_tokens for c in self.calls),
            "cached_prompt_tokens": sum(c.cached_tokens for c in self.calls),
            "total_tokens": sum(c.total_tokens for c in self.calls),
        }

    def by_site(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for call in self.calls:
            row = out.setdefault(call.site, {
                "calls": 0, "model": call.model, "prompt_tokens": 0,
                "completion_tokens": 0, "reasoning_tokens": 0,
                "cached_prompt_tokens": 0, "total_tokens": 0,
            })
            row["calls"] += 1
            row["prompt_tokens"] += call.prompt_tokens
            row["completion_tokens"] += call.completion_tokens
            row["reasoning_tokens"] += call.reasoning_tokens
            row["cached_prompt_tokens"] += call.cached_tokens
            row["total_tokens"] += call.total_tokens
        return out

    def extraction_stats(self) -> dict:
        """The F1 telltales: all-None rates by slot family, and the reasoning-
        token distribution that separated a null from a read in WP-4 §5.1."""
        asked = {f: 0 for f in SLOT_FAMILIES}
        null = {f: 0 for f in SLOT_FAMILIES}
        for outcome in self.extractions:
            for slot in outcome.slots:
                family = slot_family(slot)
                asked[family] += 1
                if slot in outcome.null_slots:
                    null[family] += 1

        by_family = {
            family: {
                "asked": asked[family],
                "null": null[family],
                "null_rate": round(null[family] / asked[family], 4)
                             if asked[family] else 0.0,
            }
            for family in SLOT_FAMILIES if asked[family]
        }

        answered = [o for o in self.extractions if o.cause is None]
        all_none = [o for o in answered if o.all_none]
        causes: dict[str, int] = {}
        for outcome in self.extractions:
            if outcome.cause:
                causes[outcome.cause] = causes.get(outcome.cause, 0) + 1

        def _reasoning(records) -> dict | None:
            values = sorted(r.reasoning_tokens for r in records
                            if r.reasoning_tokens is not None)
            if not values:
                return None
            return {"n": len(values), "min": values[0], "max": values[-1],
                    "median": values[len(values) // 2],
                    "mean": round(sum(values) / len(values), 1)}

        return {
            "extraction_calls": len(self.extractions),
            # An "unavailable" call is an API/parse failure, NOT the model
            # answering "nothing was named" — keeping them apart is the whole
            # point of the sentinel (D30.2).
            "unavailable_calls": len(self.extractions) - len(answered),
            "unavailable_causes": causes,
            "all_none_answered": len(all_none),
            "all_none_rate_answered": round(len(all_none) / len(answered), 4)
                                      if answered else 0.0,
            "by_slot_family": by_family,
            "reasoning_tokens_when_all_none": _reasoning(all_none),
            "reasoning_tokens_when_read": _reasoning(
                [o for o in answered if not o.all_none]),
        }

    def snapshot(self) -> dict:
        """Everything, JSON-serialisable, for writing next to a results file."""
        return {"totals": self.totals(), "by_site": self.by_site(),
                "extraction": self.extraction_stats()}

    def report(self, title: str = "token spend") -> str:
        """The printable block the harnesses end on."""
        totals = self.totals()
        lines = [f"\n── {title} ──"]
        if not self.calls:
            lines.append("  no instrumented calls recorded "
                         "(cached run, or nothing was sent)")
        else:
            head = f"  {'site':<12} {'calls':>6} {'prompt':>10} {'cached':>9} " \
                   f"{'completion':>11} {'reasoning':>10} {'total':>11}"
            lines.append(head)
            for site, row in sorted(self.by_site().items()):
                lines.append(
                    f"  {site:<12} {row['calls']:>6} {row['prompt_tokens']:>10,} "
                    f"{row['cached_prompt_tokens']:>9,} "
                    f"{row['completion_tokens']:>11,} "
                    f"{row['reasoning_tokens']:>10,} {row['total_tokens']:>11,}")
            lines.append(
                f"  {'TOTAL':<12} {totals['calls']:>6} "
                f"{totals['prompt_tokens']:>10,} "
                f"{totals['cached_prompt_tokens']:>9,} "
                f"{totals['completion_tokens']:>11,} "
                f"{totals['reasoning_tokens']:>10,} {totals['total_tokens']:>11,}")

        stats = self.extraction_stats()
        if stats["extraction_calls"]:
            lines.append(f"\n── extraction outcomes "
                         f"({stats['extraction_calls']} calls) ──")
            lines.append(
                f"  all-None (model answered): {stats['all_none_answered']} "
                f"({stats['all_none_rate_answered']:.1%})")
            if stats["unavailable_calls"]:
                causes = ", ".join(f"{k}×{v}" for k, v in
                                   sorted(stats["unavailable_causes"].items()))
                lines.append(f"  UNAVAILABLE (API/parse failure, not an empty "
                             f"question): {stats['unavailable_calls']} — {causes}")
            else:
                lines.append("  UNAVAILABLE (API/parse failure): 0")
            lines.append("  null rate by slot family:")
            for family, row in stats["by_slot_family"].items():
                lines.append(f"    {family:<12} {row['null']:>5}/{row['asked']:<5} "
                             f"{row['null_rate']:>7.1%}")
            for label, key in (("when all-None", "reasoning_tokens_when_all_none"),
                               ("when read    ", "reasoning_tokens_when_read")):
                dist = stats[key]
                if dist:
                    lines.append(
                        f"  reasoning tokens {label}: n={dist['n']} "
                        f"min={dist['min']} median={dist['median']} "
                        f"mean={dist['mean']} max={dist['max']}")
        return "\n".join(lines)


_METER = UsageMeter()


def meter() -> UsageMeter:
    """The process-wide meter. The eval harnesses run the router in-process, so
    this is the same object the call sites write to."""
    return _METER


def record_call(site: str, model: str, resp, *,
                finish_reason: str | None = None) -> CallUsage | None:
    return _METER.record_call(site, model, resp, finish_reason=finish_reason)


def record_extraction(slots, parsed: dict | None, *, cause: str | None = None,
                      reasoning_tokens: int | None = None,
                      query: str = "") -> None:
    _METER.record_extraction(slots, parsed, cause=cause,
                             reasoning_tokens=reasoning_tokens, query=query)
