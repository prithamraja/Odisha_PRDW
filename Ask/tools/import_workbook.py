"""
Import the ARCHIVED workbook into a FRESH directory. Never onto the live files.

    python tools/import_workbook.py --out-dir <new directory> [--workbook PATH]

WHAT THIS IS FOR, NOW. Until WP-6 this was `tools/build_catalog.py`, and the
workbook `AI_Chatbot_Questions.xlsx` was the catalogue's source of truth. Since
WP-6 T0 (operator decision, 2026-09-12) the committed
`query_router/template_catalog.py` is the source of truth and is edited by
hand; the workbook is archived in `handoffs/archive/` as the record of the
2026-08-13 sign-off. This script is kept for one purpose: to show what that
sign-off said, as catalogue files, so a question like "what did the workbook
have for PLN-031?" can be answered by a diff rather than by opening Excel.

IT CAN ONLY CREATE. It refuses an output directory that already holds any of its
outputs, refuses the live `query_router/` and `tests/data/` directories
outright, and opens every output with exclusive-create. No gate and no test
runs it.

The derivation half it used to share — the D10 geography rewrite, the paraphrase
rules, the reranker descriptions — lives in `tools/derive_catalog.py` and is
imported from there, so a fresh import is marked up exactly the way the live
file is.

DEPENDENCY: openpyxl, a manual-use requirement only; deliberately NOT in
requirements.txt.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from tools.derive_catalog import (  # noqa: E402
    CODE_BOUND,
    DEFAULTED_SLOTS,
    PARAM_ENTITY_TYPES,
    QUESTION_TOKENS,
    SCOPE_NOUN,
    SCOPE_SUFFIX,
    TEMPLATE_PATH,
    TOKEN_PROSE,
    _GEO_RUN,
    adopt_markers,
    code_mixed_question,
    derived_template_paraphrases,
    derived_unanswerable_paraphrases,
    emit_entry,
    grouped_geo_slots,
    is_optional,
    load_catalog,
    rewrite_geography,
    scope_free_question,
    to_prose,
)

DEFAULT_WORKBOOK = REPO / "handoffs" / "archive" / "AI_Chatbot_Questions.xlsx"


# ── The workbook, as records ──────────────────────────────────────────────────

def read_workbook(path: Path) -> dict[str, list[dict]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out: dict[str, list[dict]] = {}
    for name in wb.sheetnames:
        rows = list(wb[name].iter_rows(values_only=True))
        if not rows:
            out[name] = []
            continue
        header = [("" if h is None else str(h).strip()) for h in rows[0]]
        records = []
        for row in rows[1:]:
            if all(c is None or str(c).strip() == "" for c in row):
                continue
            records.append(dict(zip(header, row)))
        out[name] = records
    return out


def text(value) -> str:
    return "" if value is None else str(value).strip()

def declared_params(row: dict) -> list[str]:
    return re.findall(r"\$(\w+)", text(row["Parameters (bind order)"]))


def build_slots(row: dict, sql: str) -> list[dict]:
    slots = []
    for name in declared_params(row):
        entity_type = PARAM_ENTITY_TYPES.get(name)
        if entity_type is None:
            raise ValueError(f"{row['Question ID']}: unknown bind name ${name}")
        slot = {"name": name, "entity_type": entity_type}
        if is_optional(sql, name) or name in DEFAULTED_SLOTS:
            slot["optional"] = True
        if name in DEFAULTED_SLOTS:
            # Optional here means "the router supplies it", NOT "bind NULL" —
            # `LIMIT NULL` is unbounded, the opposite of a page size. The
            # default is declared on the slot so every serving path reads it
            # from one place; see router.slot_defaults().
            slot["default"] = DEFAULTED_SLOTS[name]
        if name in CODE_BOUND:
            slot["bind"] = "code"
        slots.append(slot)
    return slots


def to_abstract(parameterised: str, slot_names: set[str], qid: str) -> str:
    """'…in {District}…' -> '…in {district_name}…', formattable by slot name."""
    def sub(m):
        token = m.group(1)
        slot = QUESTION_TOKENS.get(token)
        if slot is None:
            raise ValueError(f"{qid}: unknown question placeholder {{{token}}}")
        if slot not in slot_names:
            # A placeholder naming a slot the template does not have would make
            # .format() raise inside suggestions._chip_for. Write it as prose.
            return TOKEN_PROSE[token]
        return "{" + slot + "}"
    return re.sub(r"\{([^}]*)\}", sub, parameterised or "")


def build_paraphrases(row: dict, abstract: str, slots: list[dict]) -> list[str]:
    """Extra retrieval surface for one template, deduplicated.

    Three sources, in descending order of how much they help:
      * the Example Question — real values, the shape a user actually types;
      * the Original Question — the officer's own abstract wording, which is
        often phrased quite differently from the parameterised one;
      * one scope line per geography tier this template can filter on (D2).
    """
    out: list[str] = []
    seen = {to_prose(abstract).lower()}

    def add(candidate: str) -> None:
        candidate = re.sub(r"\s+", " ", candidate or "").strip()
        if not candidate or candidate.lower() in seen:
            return
        seen.add(candidate.lower())
        out.append(candidate)

    add(text(row["Example Question"]))
    add(to_prose(text(row["Original Question"])))
    add(to_prose(text(row["Parameterized Question"])))

    optional_geo = [s["name"] for s in slots
                    if s.get("optional") and s["name"] in SCOPE_NOUN]
    if optional_geo:
        source = text(row["Parameterized Question"]) or text(row["Original Question"])
        has_geo_run = bool(_GEO_RUN.search(source))
        for slot in optional_geo:
            if has_geo_run:
                # The question names its own scope — swap that run for this tier
                # so the variant reads as a real question rather than a list of
                # every tier at once.
                add(to_prose(_GEO_RUN.sub(SCOPE_NOUN[slot], source)))
            else:
                # A naturally state-wide question ("how many SWM activities were
                # planned in 2024-25?"), which D2 says the same template must
                # also answer for one district / block / GP.
                add(f"{to_prose(source).rstrip('?. ')}, {SCOPE_SUFFIX[slot]}?")
    return out


GENERATED_BANNER = '''# ── FRESH IMPORT of the archived workbook — NOT the live catalogue ───────────
# Written by tools/import_workbook.py. The live catalogue is
# query_router/template_catalog.py, edited by hand since WP-6 (2026-09-12).
'''

TEMPLATE_HEADER = '''"""
Odisha Panchayati Raj & Drinking Water — the query catalogue.

346 templates: every question on the workbook's Questions sheet that the
database can answer (95 "Yes", 251 "Partial"). The 17 "No" rows and the 13
dropped beneficiary questions are NOT here — they live in
`unanswerable_catalog.py`, so that a question the database genuinely cannot
answer is retrieved and refused with its reason instead of missing.

ONE TEMPLATE PER QUESTION, SLOTS OPTIONAL (decision D2)
    The filter idiom is `($p IS NULL OR col = $p)`: an absent optional slot
    binds SQL NULL, which reads as "do not filter on this". So ONE entry answers
    a question state-wide, for a district, for a block or for a single GP,
    instead of the AP catalogue's -S/-D/-M sibling variants. Absent optional
    slots must never stall on a clarification — "how many activities are
    planned?" is a complete question state-wide.

    Because the scope is no longer visible in the id, it has to be visible to
    RETRIEVAL: each geography-optional entry carries scope-phrased paraphrases
    ("district-wise…", "block-wise…", "GP-wise…") that all resolve to the one
    entry. The vector retriever keeps the MAX score over a template's vectors and
    counts distinct query_ids toward k, so these can never crowd the candidate
    list.

NAMED PARAMETERS (decision D1)
    Every statement uses `$name` placeholders and binds a DICT, one entry per
    slot name however often the name occurs — which the optional-filter idiom
    makes the normal case, since each parameter appears twice. `param_style` is
    sniffed from the SQL by query_router/sql_params.py; no entry sets it.

GEOGRAPHY BINDS A CODE, NOT A NAME (decisions D4/D10)
    Every `$gp_name` slot is `{"bind": "code"}` and binds the resolved
    `gp_lgd_code`. The SQL predicate was rewritten to match: `v.gp_name =
    $gp_name` became `v.gp_lgd_code = $gp_name`. THE SLOT KEEPS ITS NAME AND ITS
    VALUE IS NOW A CODE — the name is the workbook's, the value is the
    validator's. Statewide there are ~6,800 GPs and names repeat freely, so a
    name predicate would silently merge every namesake into one answer.

    `v_asset` carries geography but not `gp_lgd_code`, so its 13 GP predicates
    resolve through the parent activity
    (`activity_code IN (SELECT … FROM v_activity WHERE gp_lgd_code = $gp_name)`),
    which is exactly equivalent. Blocks and districts still bind their validated
    NAME, because no view exposes their codes — see WP3_REPORT for the
    view-change request that would finish the job.

CAVEATS ARE FIRST-CLASS (decision D3)
    296 of these 346 entries carry a `caveat`, verbatim from the workbook's
    Answerability Note. 251 questions are only PARTIALLY answerable — a proxy
    column, a coverage gap, a denominator that is the 20 loaded GPs rather than
    the roster — and a Partial answer served without its caveat is the
    confidently-wrong failure mode this whole layer exists to prevent. The
    caveat reaches the user as `QueryResponse.caveat` AND appended verbatim to
    the rendered answer; it is never passed through an LLM prompt, where it
    could be paraphrased away.

DATES ARE ORDINARY SLOTS (decision D9)
    `date_filter` is None on every entry and `date_kind` is never set. The
    fiscal year is a normal `$date_range` slot binding the full `'2024-2025'`
    string; `date_phrase.py` maps "FY 24-25" / "last year" onto it. The engine's
    date-injection machinery stays dormant for PR&DW — its `year` kind compares
    integers and would raise a binder error on this column.

THE VIEWS
    Every statement reads the `v_*` analytical views, which are created at
    adapter startup from `sql/create_views.sql` into the writable in-memory
    catalog (`db_factory._seed_views`). Seventeen queries also touch a base
    table — `gram_panchayat` mostly, for the LEFT-JOIN-from-the-roster shape
    that keeps zero-activity GPs in the answer, which is the finding a review
    meeting wants.

ENTRY KEYS
    abstract_question   the parameterised question, placeholders renamed to slot
                        names so `.format()` works in suggestions.
    sql_template        the workbook's SQL, verbatim but for the geography
                        rewrite above.
    param_slots         [{name, entity_type, optional?, bind?}] in the
                        workbook's bind order. `entity_type` matches
                        entity_validator.PARAM_ENTITY_TYPES (a test asserts it).
    caveat              the Answerability Note, when there is one.
    bracket / module / submodule / question_type / answerable
                        the workbook's own classification. Bracket+Module+
                        Submodule is the family structure rerank_context.py
                        groups by.
    paraphrases         extra retrieval surface; see D2 above.

VALIDATION
    tests/test_catalog_execution.py executes all 346 against the sample database
    with the workbook's own sample parameters and compares row counts against
    the Test Report sheet. SQL is deterministic, so any mismatch is a real
    defect rather than replay noise.
"""
'''

UNANSWERABLE_HEADER = '''"""
The questions this database CANNOT answer, and why.

Thirty of them: the 17 rows the workbook marks "Answerable from DB = No", and
the 13 beneficiary questions on its Dropped sheet.

WHY THEY ARE IN THE CATALOGUE AT ALL
    Officers will ask these. Beneficiary questions especially — "how many
    beneficiaries got a pension in this GP" is an obvious thing to want, and the
    only beneficiary table in the database is empty. Left out of the catalogue,
    such a question retrieves nothing, scores below the no-match threshold and
    gets the generic "I'm not sure I can answer that specific question yet"
    fallback, which is indistinguishable from the bot merely failing. The
    officer is left unsure whether to rephrase, and a bot that looks unreliable
    on an answerable-sounding question is worse than one that says plainly what
    it does not hold.

    So these are RETRIEVABLE but NOT EXECUTABLE. They carry no SQL and no slots.
    `router` serves a matched id from here as an honest refusal built from the
    workbook's own reason — "the database cannot answer this because …" — and
    offers the nearest answerable questions where the note names one.

    They are a SEPARATE dict from TEMPLATE_CATALOG deliberately. Everything that
    iterates TEMPLATE_CATALOG assumes an entry has SQL and slots — the binder,
    the execution gate, `validate_catalog`, `_accepted_filters`. Merging the two
    would mean teaching every one of those about a third kind of entry; keeping
    them apart means the retriever indexes both and only the router has to know.

KEYS
    question    the workbook's Original Question, placeholders written out.
    reason      the Answerability Note / drop reason, VERBATIM. This is what the
                user is told; it is the whole value of the entry.
    alternative a query_id that answers the nearest answerable question, where
                the workbook's note names one. Offered as a chip, never
                substituted silently.
"""
'''

TEMPLATE_FOOTER = '''

ALL_TEMPLATES: dict[str, dict] = TEMPLATE_CATALOG


def bind(template_id: str, values: dict):
    """Return (sql, params) for a template and a {slot_name: value} dict.

    Every PR&DW template is NAMED, so this returns a DICT with one entry per
    slot name however often that name occurs in the statement — which is the
    normal case here, since `($p IS NULL OR col = $p)` writes each parameter
    twice. The positional branch is kept because `sql_params.param_style` still
    detects positional SQL and the engine must not silently mis-bind it.

    Slots marked {"optional": True} may be absent from `values`; they bind None
    (SQL NULL). Missing REQUIRED slots still raise.
    """
    from .sql_params import NAMED, param_style

    t = ALL_TEMPLATES[template_id]
    slots = t['param_slots']
    optional = {s['name'] for s in slots if s.get('optional')}
    missing = {s['name'] for s in slots} - set(values) - optional
    if missing:
        raise KeyError(f'{template_id} missing slot values: {sorted(missing)}')

    if param_style(t) == NAMED:
        return t['sql_template'], {s['name']: values.get(s['name']) for s in slots}

    ordered = sorted(slots, key=lambda s: s['position'])
    return t['sql_template'], [values.get(s['name']) for s in ordered]


def required_entities(template_id: str) -> list[str]:
    """Distinct entity types the extractor must resolve for this template."""
    return sorted({s['entity_type'] for s in ALL_TEMPLATES[template_id]['param_slots']})


def retrieval_corpus():
    """(text, template_id) pairs for embedding — abstract question plus paraphrases."""
    pairs = []
    for tid, t in ALL_TEMPLATES.items():
        pairs.append((t['abstract_question'], tid))
        for p in t.get('paraphrases', []):
            pairs.append((p, tid))
    return pairs


def family_of(template_id: str) -> tuple[str, str, str]:
    """(bracket, module, submodule) — the grouping rerank_context.py families on."""
    t = ALL_TEMPLATES[template_id]
    return (t['bracket'], t['module'], t['submodule'])
'''

# ── Build ─────────────────────────────────────────────────────────────────────

def build_templates(sheets: dict) -> tuple[str, list[str], dict]:
    rows = [r for r in sheets["Questions"]
            if text(r["Answerable from DB"]) in ("Yes", "Partial")]
    registry_optional = {
        text(r["Bind name"]).lstrip("$"): text(r["NULL skips filter"]) == "Yes"
        for r in sheets["Parameter Registry"]
    }

    findings: list[str] = []
    entries: list[str] = []
    stats = Counter()
    disagreements: list[str] = []
    asset_rewrites: list[str] = []

    for row in rows:
        qid = text(row["Question ID"])
        sql = text(row["Parameterized SQL"])
        if not sql:
            raise ValueError(f"{qid}: answerable but has no SQL")

        sql, notes = rewrite_geography(qid, sql)
        if any("v_asset" in n for n in notes):
            asset_rewrites.append(qid)
        stats["rewritten"] += 1 if notes or "gp_lgd_code = $gp_name" in sql else 0

        slots = build_slots(row, sql)
        slot_names = {s["name"] for s in slots}
        abstract = to_abstract(text(row["Parameterized Question"]), slot_names, qid)

        for slot in slots:
            name = slot["name"]
            if name in DEFAULTED_SLOTS:
                # D18.P1 overrides both sources for these; counting them as
                # disagreements would bury the 12 real ones under 91 noisy rows.
                stats["defaulted"] += 1
                continue
            declared = registry_optional.get(name)
            if declared is not None and declared != bool(slot.get("optional")):
                disagreements.append(
                    f"{qid} ${name}: SQL guard says "
                    f"{'optional' if slot.get('optional') else 'required'}, "
                    f"Parameter Registry says "
                    f"{'optional' if declared else 'required'}"
                )

        entry = {
            "abstract_question": abstract,
            "date_filter": None,        # decision D9 — never a date_filter
            "date_kind": None,
            "sql_template": sql,
            "param_slots": slots,
            "result_ttl_seconds": 600,
            "bracket": text(row["Bracket"]),
            "module": text(row["Module"]),
            "submodule": text(row["Submodule"]),
            "question_type": text(row["Question Type"]),
            "answerable": text(row["Answerable from DB"]),
            "paraphrases": build_paraphrases(row, abstract, slots),
        }
        grouped = grouped_geo_slots(sql, slots)
        if grouped:
            entry["grouped_geo"] = grouped
            stats["grouped_geo"] += 1
        note = text(row["Answerability Note"])
        if note:
            entry["caveat"] = note
            stats["caveated"] += 1
        stats["templates"] += 1
        entries.append(emit_entry(qid, entry))

    body = (
        TEMPLATE_HEADER
        + GENERATED_BANNER
        + "\n\nTEMPLATE_CATALOG: dict[str, dict] = {\n\n"
        + "\n\n".join(entries)
        + "\n}\n"
        + TEMPLATE_FOOTER
    )

    findings.append(f"templates: {stats['templates']}, caveated: {stats['caveated']}")
    findings.append(
        f"v_asset GP predicates resolved through v_activity ({len(asset_rewrites)}): "
        + ", ".join(asset_rewrites)
    )
    findings.append(
        f"optional-slot disagreements with the Parameter Registry "
        f"({len(disagreements)}) — the SQL guard wins:\n    "
        + "\n    ".join(disagreements)
    )
    findings.append(
        f"optional-with-default slots (D18.P1, {stats['defaulted']} occurrences): "
        + ", ".join(f"${n} = {v!r}" for n, v in sorted(DEFAULTED_SLOTS.items()))
    )
    findings.append(
        f"templates reporting one row per geography (grouped_geo): "
        f"{stats['grouped_geo']}"
    )
    return body, findings, stats


def _unanswerable_paraphrases(
    question: str, extra: list[str], *, code_mixed: bool = False
) -> list[str]:
    """Index surface for one unanswerable entry, deduplicated, order stable.

    The workbook's own alternative wordings first where it has any, then the
    scope-free line (see `scope_free_question` for why it exists and what it
    measured), then the code-mixed line where it is asked for.

    `code_mixed` IS GATED TO THE DROPPED SHEET, which is the scope D31.5 rules
    on: the beneficiary refusals are the entries whose gold questions are typed
    in that register, and BEN-003 is the one measured stuck outside the window
    because of it. The frame table itself is general and would fire on most of
    the 17 "No" rows — on several of them producing a line that differs from the
    English by one word, which is index weight for no retrieval gain. Widening
    the gate is a one-line change and should be made the way this one was: on a
    rank measurement from `refusal_recall.py`, not on the argument that more
    surface cannot hurt.
    """
    out: list[str] = []
    # The code-mixed line is built from the SCOPE-FREE form, so the place and
    # the year are already gone before the frame is switched (D31.5).
    scope_free = scope_free_question(question)
    candidates = [*extra, scope_free]
    if code_mixed:
        candidates.append(code_mixed_question(scope_free or question))
    for candidate in candidates:
        if not candidate:
            continue
        if candidate.strip().lower() == (question or "").strip().lower():
            continue
        if any(candidate.strip().lower() == seen.strip().lower() for seen in out):
            continue
        out.append(candidate.strip())
    return out


def build_unanswerable(sheets: dict) -> tuple[str, int]:
    """The 17 'No' rows plus the 13 Dropped beneficiary questions."""
    entries: list[str] = []
    count = 0

    # A workbook note that names its own answerable alternative, e.g. PLN-022's
    # "PLN-010 with a user-supplied $deadline is the closest answerable form."
    ref = re.compile(r"\b([A-Z]{3}(?:-[A-Z]{2,3})?-\d{3})\b")

    for row in sheets["Questions"]:
        if text(row["Answerable from DB"]) != "No":
            continue
        qid = text(row["Question ID"])
        reason = text(row["Answerability Note"])
        alternatives = [m for m in ref.findall(reason) if m != qid]
        entry = {
            "question": to_prose(text(row["Original Question"])),
            "reason": reason,
            "bracket": text(row["Bracket"]),
            "module": text(row["Module"]),
            "submodule": text(row["Submodule"]),
            "source": "No",
        }
        if alternatives:
            entry["alternative"] = alternatives[0]
        entry["paraphrases"] = _unanswerable_paraphrases(
            entry["question"],
            [to_prose(text(row["Parameterized Question"])),
             text(row["Example Question"])])
        entries.append(emit_unanswerable(qid, entry))
        count += 1

    for row in sheets["Dropped"]:
        qid = text(row["Question ID"])
        entry = {
            "question": to_prose(text(row["Original Question"])),
            "reason": text(row["Why it was dropped"]),
            "bracket": text(row["Bracket"]),
            "module": text(row["Module"]),
            "submodule": text(row["Module"]),
            "source": "Dropped",
            # The Dropped sheet has five columns and none of them is a
            # Parameterized or Example question, so the scope-free line is the
            # only extra surface available — and it is the one that mattered.
            "paraphrases": _unanswerable_paraphrases(
                to_prose(text(row["Original Question"])), [], code_mixed=True),
        }
        entries.append(emit_unanswerable(qid, entry))
        count += 1

    body = (
        UNANSWERABLE_HEADER
        + GENERATED_BANNER
        + "\n\nUNANSWERABLE_CATALOG: dict[str, dict] = {\n\n"
        + "\n\n".join(entries)
        + "\n}\n"
        + '''

def retrieval_corpus():
    """(text, query_id) pairs for embedding, same shape as the template catalogue."""
    pairs = []
    for qid, entry in UNANSWERABLE_CATALOG.items():
        pairs.append((entry["question"], qid))
        for p in entry.get("paraphrases", []):
            pairs.append((p, qid))
    return pairs


def refusal_for(query_id: str) -> str | None:
    """The sentence an officer is shown, built from the workbook's own reason.

    Verbatim, for the same reason a caveat is verbatim: the reason IS the
    answer to "why not", and a paraphrase of it is a worse answer.
    """
    entry = UNANSWERABLE_CATALOG.get(query_id)
    if entry is None:
        return None
    return (
        f"I can't answer that from this database. {entry['reason']}"
    )
'''
    )
    return body, count


def emit_unanswerable(qid: str, entry: dict) -> str:
    lines = [f"    {qid!r}: {{"]
    for key in ("question", "reason", "bracket", "module", "submodule",
                "source", "alternative"):
        if key in entry:
            lines.append(f'        "{key}": {entry[key]!r},')
    lines.append('        "paraphrases": [')
    for p in entry["paraphrases"]:
        lines.append(f"            {p!r},")
    lines.append("        ],")
    lines.append("    },")
    return "\n".join(lines)


def build_oracle(sheets: dict) -> tuple[str, int]:
    """The Test Report sheet as JSON: the row counts the execution gate checks."""
    oracle = {}
    for row in sheets["Test Report"]:
        qid = text(row["Question ID"])
        if text(row["Answerable"]) == "No":
            continue
        params = text(row["Parameters used"])
        oracle[qid] = {
            "answerable": text(row["Answerable"]),
            "status": text(row["Test Status"]),
            "rows": int(row["Rows"]),
            "params": json.loads(params) if params else {},
        }
    return json.dumps(oracle, indent=1, sort_keys=True) + "\n", len(oracle)


OUTPUTS = ("template_catalog.py", "unanswerable_catalog.py", "workbook_test_report.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    ap.add_argument("--out-dir", type=Path, required=True,
                    help="a directory holding none of the outputs yet")
    args = ap.parse_args()

    out = args.out_dir.resolve()
    live = {TEMPLATE_PATH.parent.resolve(), (BACKEND / "tests" / "data").resolve()}
    if out in live:
        print(f"refusing to import into the live catalogue directory {out}",
              file=sys.stderr)
        return 2
    existing = [name for name in OUTPUTS if (out / name).exists()]
    if existing:
        print(f"refusing: {out} already holds {', '.join(existing)} — this script "
              "only ever creates files", file=sys.stderr)
        return 2
    if not args.workbook.exists():
        print(f"workbook not found: {args.workbook}", file=sys.stderr)
        return 2
    lock = args.workbook.parent / ("~$" + args.workbook.name)
    if lock.exists():
        print(f"{args.workbook.name} is open in Excel ({lock.name} present). "
              "Close it so the saved file is current.", file=sys.stderr)
        return 2

    sheets = read_workbook(args.workbook)
    template_src, findings, _ = build_templates(sheets)
    unanswerable_src, n_unanswerable = build_unanswerable(sheets)
    oracle_src, n_oracle = build_oracle(sheets)

    template_src, unsplit_t = adopt_markers(
        template_src, load_catalog(template_src, "TEMPLATE_CATALOG"),
        derived_template_paraphrases)
    unanswerable_src, unsplit_u = adopt_markers(
        unanswerable_src, load_catalog(unanswerable_src, "UNANSWERABLE_CATALOG"),
        derived_unanswerable_paraphrases)

    for line in findings:
        print(line)
    print(f"unanswerable: {n_unanswerable}   oracle rows: {n_oracle}")
    if unsplit_t or unsplit_u:
        print(f"paraphrase lists left all-hand (no derived split found): "
              f"{unsplit_t + unsplit_u}")

    out.mkdir(parents=True, exist_ok=True)
    for name, source in zip(OUTPUTS, (template_src, unanswerable_src, oracle_src)):
        with open(out / name, "x", encoding="utf-8") as handle:
            handle.write(source)
        print(f"created {out / name}  ({len(source):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
