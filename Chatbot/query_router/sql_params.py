"""
SQL parameter styles — detection, inspection and translation.

WHY THIS EXISTS
    The AP catalog binds POSITIONALLY: ``?`` placeholders plus ``param_slots``
    giving the ordered, always-required entities. The Odisha PR&DW catalogue is
    authored the other way round — DuckDB NAMED placeholders (``$district_name``),
    each often repeated inside one query by the optional-filter idiom

        ($district_name IS NULL OR gp.district_name = $district_name)

    where binding NULL disables the filter. That SQL is execution-tested and
    signed off, so the engine executes it VERBATIM rather than rewriting it to
    positional: a repeated ``$name`` expands to several ``?`` at different
    positions, and getting that expansion wrong is a silently-wrong-answer bug,
    not a crash.

DETECTION
    ``param_style(entry)`` decides how one catalogue entry binds:

      1. an explicit ``"param_style": "named" | "positional"`` key on the entry
         always wins — an escape hatch for SQL the sniffer would misread;
      2. otherwise: NAMED if the SQL contains at least one ``$name``
         placeholder outside string literals and comments, else POSITIONAL.

    Auto-detection is what keeps this additive: all 278 AP entries carry no
    ``param_style`` key and contain no ``$`` placeholders, so every one of them
    resolves to POSITIONAL and takes the byte-identical path it took before.

LITERAL AND COMMENT MASKING
    Every function here works on a MASKED copy of the SQL in which string
    literals ``'...'`` (with ``''`` escapes), ``--`` line comments, ``/*...*/``
    block comments and ``$$...$$`` dollar-quoted blocks are blanked to
    same-length filler. Offsets therefore still line up with the original, and
    a ``$`` inside a literal — ``WHERE note = 'costs $5'`` — is neither counted
    as a parameter nor rewritten.

KNOWN EDGE CASE — tagged dollar quoting
    ``$tag$ ... $tag$`` is genuinely ambiguous with this parameter syntax (the
    opening delimiter is indistinguishable from a ``$tag`` placeholder followed
    by a ``$``), so it is NOT masked. No catalogue SQL uses it; if any ever
    does, ``to_pyformat`` logs a warning rather than mangling it in silence.
"""
from __future__ import annotations

import logging
import re

_log = logging.getLogger(__name__)

NAMED = "named"
POSITIONAL = "positional"

# A DuckDB named placeholder. Deliberately conservative: `$` followed by an
# identifier. Does not match `$1` (positional-numeric) or `$$` (dollar quoting).
NAMED_PARAM_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")

_MASKABLE = re.compile(
    r"'(?:[^']|'')*'"        # single-quoted string literal, '' escape
    r"|--[^\n]*"             # line comment
    r"|/\*.*?\*/"            # block comment
    r"|\$\$.*?\$\$",         # untagged dollar-quoted block
    re.DOTALL,
)

# `$tag$ ... $tag$`. Detected only to warn — see the module docstring.
_TAGGED_DOLLAR_QUOTE = re.compile(r"\$(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\$.*?\$(?P=tag)\$", re.DOTALL)

_FILLER = "\x00"


def mask_literals(sql: str) -> str:
    """A same-length copy of `sql` with literals and comments blanked out.

    Same length is the point: match offsets found here index straight into the
    original string, so callers can rewrite the original without re-scanning.
    """
    return _MASKABLE.sub(lambda m: _FILLER * (m.end() - m.start()), sql)


def named_params(sql: str) -> list[str]:
    """Distinct `$name` parameter names, in first-seen order.

    A name repeated by the optional-filter idiom appears ONCE — the caller binds
    one value per name, not one per occurrence, which is the whole reason named
    binding is worth having here.
    """
    return list(dict.fromkeys(NAMED_PARAM_RE.findall(mask_literals(sql))))


def uses_named_params(sql: str) -> bool:
    return bool(NAMED_PARAM_RE.search(mask_literals(sql)))


def positional_count(sql: str) -> int:
    """Number of `?` placeholders outside literals and comments."""
    return mask_literals(sql).count("?")


def param_style(entry: dict) -> str:
    """NAMED or POSITIONAL for one catalogue entry. See module docstring."""
    explicit = entry.get("param_style")
    if explicit is not None:
        if explicit not in (NAMED, POSITIONAL):
            raise ValueError(
                f"param_style must be {NAMED!r} or {POSITIONAL!r}, got {explicit!r}"
            )
        return explicit
    return NAMED if uses_named_params(entry.get("sql_template", "")) else POSITIONAL


def to_pyformat(sql: str) -> str:
    """Rewrite DuckDB `$name` placeholders to DB-API pyformat `%(name)s`.

    For a driver whose paramstyle is pyformat (psycopg2 and friends), which
    binds from the same `{name: value}` dict DuckDB takes natively — so only
    the SQL text needs changing, never the parameters.

    Every other `%` in the statement is doubled to `%%`, including inside string
    literals: pyformat drivers scan the whole statement for `%`, so an
    un-doubled `LIKE '%toilet%'` raises "unsupported format character" (or worse,
    silently consumes the next characters as a format spec). This is the step
    that is easy to forget and impossible to miss once a keyword query runs.
    """
    if _TAGGED_DOLLAR_QUOTE.search(mask_literals(sql)):
        _log.warning(
            "SQL appears to use tagged dollar quoting ($tag$...$tag$), which is "
            "ambiguous with $name parameters — translation may be wrong. "
            "Rewrite the literal with ordinary single quotes."
        )

    masked = mask_literals(sql)
    spans = {m.start(): m for m in NAMED_PARAM_RE.finditer(masked)}

    out: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        match = spans.get(i)
        if match is not None:
            out.append(f"%({match.group(1)})s")
            i = match.end()
            continue
        ch = sql[i]
        out.append("%%" if ch == "%" else ch)
        i += 1
    return "".join(out)
