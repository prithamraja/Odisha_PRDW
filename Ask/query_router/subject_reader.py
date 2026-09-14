"""The subject an officer names, read straight off the question (WP-6b T2).

THE DEFECT. "How many road construction activities are in progress?" was
answered, on ten of eleven phrasings in the 2026-09-14 Eval_1 replay, with the
count of EVERY ongoing activity — 400 for 2024-25, presented as road works.
`_FOCUS_AREA_ALIASES` already mapped "road construction" to Roads. The alias
never ran: the validator only resolves what the extractor hands it, and the
extractor returned no focus area at all. "Swachh Bharat" and "piped water"
bound only because the model happened to emit a value.

THE FIX IS THE ONE `$date_range` GOT (D33.13, the D30.4 pattern). The alias
tables become a deterministic PREFILL: the question is scanned for the
vocabulary of every subject slot the template offers, and what it names is
bound before the model is asked. The extractor stays the fallback for whatever
this cannot read. A reader with a narrow vocabulary that is right when it fires
beats a model that sometimes returns nothing.

WHAT IT READS. For each subject slot — focus area, work status, scheme, LSDG
theme, plan type — the loaded registry values and the alias keys, compared
case-folded, with runs of spaces and hyphens read as one space ("in-progress"
is "in progress"), word-bounded. Where two readings overlap the LONGEST wins,
across slots as well as within one: "water sufficient" is the LSDG theme, not
the water focus area; "GP office infrastructure" is a focus area, not Theme 6.
A slot is prefilled only when every mention agrees on ONE value — "water vs
sanitation" names two, which is a comparison for the extractor's list reading,
never a pick.

WHAT IT GUARDS. The same scan decides whether the question NAMED a subject at
all. A named subject whose slot is still unbound once extraction is over — the
reader stood aside for a comparison and the extractor then returned nothing —
is not answered as though it had never been said: `_fill_slots_or_clarify` asks,
reason `unbound_subject`. That is the general rule finding 1 was one instance
of: a question that names a subject must never be answered as if it had not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .entity_validator import LOSSY_ALIASES, _collapse_ws, _resolve_config

# The slots whose values an officer names in words. Geography has its own
# resolution path (fuzzy matching, the LGD collision guard) and is not read here;
# tied/untied is left to the extractor because "tied and untied" names BOTH
# halves of a split several statements report (WP-6 §8.1).
SUBJECT_TYPES = ("focus_area", "status", "scheme", "theme", "plan_type")

# How each reads in a question back to the officer.
NOUN = {
    "focus_area": "focus area",
    "status":     "work status",
    "scheme":     "scheme",
    "theme":      "LSDG theme",
    "plan_type":  "plan type",
}


def noun_for(entity_type: str) -> str:
    """'focus_area' -> 'focus area', following a mirrored type to its base."""
    base, _ = _resolve_config(entity_type)
    return NOUN.get(base, base.replace("_", " "))


# Words the tables carry that are too common in ordinary questions to be read as
# a subject without the model's judgement. Each was checked against every
# question in the WP-6 replays (WP6b_REPORT §3): "approved" is also "approved
# cost" and "plans approved"; "done" is also "work done"; "main" is also "the
# main reasons". The extractor still reads all three, exactly as before.
_NOT_READ: dict[str, frozenset[str]] = {
    "status":    frozenset({"approved", "done"}),
    "plan_type": frozenset({"main"}),
}


@dataclass(frozen=True)
class Mention:
    """One subject named in the question."""
    slot: str
    entity_type: str     # the base type, for the lossy-alias lookup
    phrase: str          # the table's own spelling — what the validator resolves
    value: str           # the registry value it names
    start: int
    end: int


def _key(text: str) -> str:
    """The comparison form: case-folded, every run of spaces/hyphens one space."""
    return re.sub(r"[\s\-–]+", " ", text or "").strip().lower()


_PATTERNS: dict[tuple, tuple[dict[str, tuple[str, str]], re.Pattern]] = {}


def _vocabulary(base_type: str, cfg: dict, registry: list[str]):
    """({key: (table phrase, value)}, one pattern matching any key)."""
    cache_key = (base_type, tuple(registry))
    cached = _PATTERNS.get(cache_key)
    if cached is not None:
        return cached
    vocab: dict[str, tuple[str, str]] = {}
    for phrase, target in cfg.get("aliases", {}).items():
        vocab[_key(phrase)] = (phrase, target)
    for value in registry:
        # A value named outright wins over an alias spelt the same way.
        vocab[_key(value)] = (value, value)
    for word in _NOT_READ.get(base_type, ()):
        vocab.pop(word, None)
    vocab.pop("", None)
    alternatives = sorted(vocab, key=len, reverse=True)
    body = "|".join(r"[\s\-–]+".join(map(re.escape, key.split(" ")))
                    for key in alternatives)
    pattern = re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.IGNORECASE)
    _PATTERNS[cache_key] = (vocab, pattern)
    return vocab, pattern


def named_subjects(text: str, slot_type: dict[str, str], validator) -> dict[str, list[Mention]]:
    """slot -> the subjects the question names for it, in the order written.

    Only slots of `SUBJECT_TYPES` the template offers. A type offered by two
    slots — a `$scheme` / `$scheme_2` comparison — is skipped: which mention
    belongs to which slot is a reading of the sentence, and that stays the
    extractor's job.
    """
    if validator is None or not hasattr(validator, "registry_values"):
        return {}
    by_base: dict[str, list[str]] = {}
    for slot, etype in slot_type.items():
        base, _ = _resolve_config(etype)
        if base in SUBJECT_TYPES:
            by_base.setdefault(base, []).append(slot)

    found: list[Mention] = []
    for base, slots in by_base.items():
        if len(slots) != 1:
            continue
        _, cfg = _resolve_config(base)
        vocab, pattern = _vocabulary(base, cfg, validator.registry_values(base))
        for match in pattern.finditer(text or ""):
            phrase, value = vocab[_key(match.group(0))]
            found.append(Mention(slots[0], base, phrase, value,
                                 match.start(), match.end()))

    # Longest first, across slots; keep what does not overlap a longer reading.
    kept: list[Mention] = []
    for mention in sorted(found, key=lambda m: (m.start - m.end, m.start)):
        if all(mention.end <= k.start or mention.start >= k.end for k in kept):
            kept.append(mention)

    named: dict[str, list[Mention]] = {}
    for mention in sorted(kept, key=lambda m: m.start):
        named.setdefault(mention.slot, []).append(mention)
    return named


def _distinct_values(mentions: list[Mention]) -> list[str]:
    seen: dict[str, str] = {}
    for mention in mentions:
        seen.setdefault(_collapse_ws(mention.value), mention.value.strip())
    return list(seen.values())


def prefill_phrase(mentions: list[Mention]) -> str | None:
    """The phrase to bind, when every mention names the SAME value; else None.

    The table's phrase, not the value: the validator resolves it, so an alias
    still binds with confidence "alias" and a lossy one ("Swachh Bharat") still
    owes the answer its caveat. Where several phrases name one value —
    "sanitation activities under Swachh Bharat" — the lossy one is bound,
    because that is the reading the caveat exists to disclose.
    """
    if not mentions or len(_distinct_values(mentions)) != 1:
        return None
    lossy = [m for m in mentions
             if (m.entity_type, _collapse_ws(m.phrase)) in LOSSY_ALIASES]
    pick = lossy[0] if lossy else max(mentions, key=lambda m: m.end - m.start)
    return pick.phrase


def unbound_subject(
    text: str, slot_type: dict[str, str], bound: set[str], validator,
) -> tuple[str, list[str]] | None:
    """(slot, the values named) for the first subject named but not bound."""
    for slot, mentions in named_subjects(text, slot_type, validator).items():
        if slot not in bound:
            return slot, _distinct_values(mentions)
    return None
