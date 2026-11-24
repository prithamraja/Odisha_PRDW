# -*- coding: utf-8 -*-
"""DiscoverChat — the FastAPI service (WP-D5, stage D5.2).

Mirrors Ask's conventions: read-only data access, `.env` config, everything
runnable by module name.

    python -m uvicorn DiscoverChat.main:app --host 127.0.0.1 --port 8100

It is a SEPARATE PRODUCT from Ask (D42 ruling 1). Nothing here imports Ask's
router, changes Ask's gates, or answers a database question; the one thing it
takes from Ask is the entity registry, read-only, so the two cannot disagree
about what a place is called. The user-facing routing between the two products
is the user's to own, and `/ask-route` exists so a front end can be told where
to send a question rather than having to guess.

STARTUP IS FAIL-LOUD. The corpus pin, the vector shapes and Ask's registry are
all checked before the first request. This project's own history is the reason:
a view-less adapter loads its registries empty and every test then passes
vacuously, and a report was once generated with every section blank because
nothing failed noisily.
"""
from __future__ import annotations

import html
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import assemble, config, corpus as corpus_mod, place as place_mod, render
from .retrieval import Retriever
from .session import SessionStore

_log = logging.getLogger(__name__)

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    stamp = config.assert_pin_matches_corpus()
    retriever = Retriever()
    STATE["retriever"] = retriever
    # WP-D15 T5.7: the profile sheet store is opened ONCE, here. Missing or
    # refused, the service runs without sheets and says why in /health; it
    # never fails to start because of them.
    if config.PROFILE_SHEETS:
        sheets, why = place_mod.open_store()
    else:
        sheets, why = None, "switched off (DISCOVERCHAT_PROFILE_SHEETS=0)"
    STATE["profile"], STATE["profile_status"] = sheets, why
    if sheets is None:
        _log.warning("DiscoverChat runs without profile sheets: %s", why)
    STATE["assembler"] = assemble.Assembler(retriever, sheets=sheets)
    STATE["sessions"] = SessionStore()
    STATE["stamp"] = stamp
    _log.info("DiscoverChat up: %d findings, candidate set %s",
              len(retriever.corpus), stamp.get("candidate_set_id"))
    yield
    STATE.clear()


app = FastAPI(title="DiscoverChat",
              description="Conversational access to pre-mined MetaInsight "
                          "findings. Computes nothing; retrieves and frames.",
              lifespan=lifespan)

# The Discover tab calls this from the browser, on a different port from Ask's
# backend, so every request is cross-origin. Open like Ask's, and for the same
# reason: the service is read-only over already-published findings and holds no
# per-user data. `allow_credentials` stays FALSE — no cookie or auth header is
# ever sent, and a wildcard origin WITH credentials is the one combination
# browsers reject outright, so turning it on would break the tab rather than
# secure it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    move: str
    session_id: str
    turn_id: str
    findings: list
    routing: dict
    retrieval: dict
    prose: dict
    stamp: str
    # WP-D7 D7.3. `answer` is the display text with the [id] tags stripped;
    # these three are what a hover UI is built from. `answer_tagged` keeps the
    # tags, `citations` resolves each id to its stored sentence, scope, run
    # stamp and record URL, and `answer_html` is the REFERENCE render -- the
    # front end will build its own, but shipping one means the behaviour suite
    # can exercise hover-to-source end to end rather than asserting on a dict.
    answer_tagged: str = ""
    citations: dict = {}
    answer_html: str = ""
    # WP-D12. Cards, charts and the "Needs checking" list, built by code from
    # the stored records (`layout.build`). Every string an officer reads is
    # formatted here; the front end decides no number and no ranking. {} when
    # there is nothing to lay out or DISCOVERCHAT_LAYOUT=0.
    layout: dict = {}
    # WP-D15 T5.4. Which place was answered, its alternatives and note, how
    # many sheet lines were handed and which the answer used, in the order
    # first used (`lines_used` -- what WP-D16 will highlight). {} when no
    # sheet was used.
    place: dict = {}


@app.get("/health")
def health() -> dict:
    retriever = STATE.get("retriever")
    return {
        "status": "ok" if retriever else "starting",
        "findings": len(retriever.corpus) if retriever else 0,
        "candidate_set_id": STATE.get("stamp", {}).get("candidate_set_id"),
        "embedding_pin": STATE.get("stamp", {}).get("embedding_pin"),
        "knobs": config.knobs(),
        "profile_sheets": {"available": STATE.get("profile") is not None,
                           "why": STATE.get("profile_status", "not opened")},
    }


@app.post("/chat", response_model=AskResponse)
def chat(request: AskRequest) -> AskResponse:
    sessions: SessionStore = STATE["sessions"]
    session_id = request.session_id or uuid.uuid4().hex
    session = sessions.get(session_id)
    turn_id = uuid.uuid4().hex[:12]

    answer = STATE["assembler"].answer(
        request.message, history=session.history_lines(), turn_id=turn_id,
        anchors=session.anchors, previous_question=session.previous_question,
    )
    session.record(request.message, answer.move, answer.findings)

    return AskResponse(
        answer=answer.text, move=answer.move, session_id=session_id,
        turn_id=turn_id,
        findings=[{"id": f.id, "sentence": f.sentence,
                   "coverage": f.coverage_line(), "view": f.view_title}
                  for f in answer.findings],
        routing=answer.routing, retrieval=answer.retrieval,
        prose=answer.prose, stamp=answer.stamp,
        answer_tagged=answer.tagged_text, citations=answer.citations,
        answer_html=_answer_html(answer),
        layout=answer.layout,
        place=answer.place,
    )


def _answer_html(answer) -> str:
    """The reference render. A place turn's facts are wrapped like findings,
    and its note leads the render as it leads `answer` (WP-D15 T5.3, T5.5)."""
    if not answer.tagged_text:
        return ""
    if not answer.place:
        return render.to_html(answer.tagged_text, answer.findings,
                              run_date=answer.stamp)
    return render.to_html(answer.tagged_text, answer.findings,
                          run_date=answer.stamp,
                          place_facts=answer.place_facts,
                          lead=answer.lead)


@app.get("/finding/{finding_id}")
def finding(finding_id: str) -> dict:
    """One finding, as the corpus holds it. Read-only; nothing is computed."""
    record = STATE["retriever"].corpus.get(finding_id)
    if record is None:
        return {"found": False, "finding_id": finding_id}
    return {"found": True, "finding_id": finding_id,
            "sentence": record.sentence, "view": record.view_title,
            "coverage": record.coverage_line(),
            "in_feed": record.in_feed, "view_rank": record.view_rank,
            "measures": record.measures, "geography": record.geography,
            "stamp": config.run_stamp_line()}


@app.get("/ask-route")
def ask_route() -> dict:
    """What this product does NOT answer, for whoever owns the routing."""
    return {
        "this_product": "patterns the analysis has already found",
        "not_this_product": "figures, counts, lists and records from the database",
        "message": assemble.ASK_ROUTE_MESSAGE,
    }


# ═════════════════════════════════════════════════════════════════════════════
# WP-D7 D7.2 — provenance: the record endpoint
# ═════════════════════════════════════════════════════════════════════════════
# This is what makes a citation checkable BY THE OFFICER rather than only by the
# citation check. Ruling 4: hover-to-source on every datapoint is the user's
# validation mechanism, and a hover that cannot be followed to the record it
# claims to come from is decoration.
#
# READ-ONLY, SAME CORPUS THE CHATBOT SERVES. Nothing is computed and nothing is
# looked up anywhere else, so a record cannot disagree with the answer that
# cited it. Both corpora resolve through one map (`1-...` findings and `d1-...`
# decompositions), because `corpus.load` concatenates them into one id space.
#
# NO AUTH QUESTION IS OPENED HERE, per the brief. The service already serves
# these same sentences through `/chat` and `/finding/{id}` with no auth, so an
# endpoint that returns them addressed by id adds no exposure. If auth arrives
# it arrives for the whole service; `deploy/RAILWAY.md` already records the
# no-auth-on-/query note for Ask.


def _record_payload(record) -> dict:
    """The stored record, in the terms the brief names.

    `sentence` and `display_sentence` are both returned and the difference is
    the point: the first is what the citation check matched a numeral against
    and what a labelling sheet or an audit compares to, the second is what an
    officer can read. `findings-verbatim` in the gate proves the digits are the
    same in both, so an officer reading the second is not reading a different
    claim.
    """
    data = record.data
    payload = {
        "found": True,
        "id": record.id,
        "record_type": "decomposition" if record.is_decomposition else "finding",
        "sentence": record.sentence,
        "display_sentence": record.display_sentence(),
        # ── coordinates: which slice of which table this is about ──
        "coordinates": {
            "view": record.view,
            "view_title": record.view_title,
            "subspace": data.get("base_subspace", data.get("subspace", [])),
            "subspace_phrase": data.get("subspace_phrase", ""),
            "measure": data.get("measure"),
            "measures": data.get("measures", []),
            "breakdown": data.get("breakdown") or data.get("dimension"),
            "geography": data.get("geography", {}),
            "rows_in_scope": data.get("rows_in_scope"),
            "hdp_size": data.get("hdp_size"),
        },
        # ── values: the figures the sentence is built from ──
        "values": {
            "named_members": data.get("named_members", []),
            "exceptions": data.get("exceptions", []),
            "commonness_sets": data.get("commonness_sets", []),
            "total": data.get("total"),
            "total_display": data.get("total_display"),
            "members": corpus_mod.members_of(data),
            "shape": data.get("shape"),
            "reconciles": data.get("reconciles"),
        },
        # ── engine score and standing ──
        "engine_score": data.get("score"),
        "conciseness": data.get("conciseness"),
        "impact": data.get("impact"),
        "standing": record.coverage_line(),
        "in_feed": data.get("in_feed"),
        "feed_rank": data.get("feed_rank"),
        "view_rank": data.get("view_rank"),
        # ── the run stamp: which mining run this record is from ──
        "run_stamp": config.run_stamp_line(),
        "candidate_set_id": data.get("candidate_set_id")
                            or STATE.get("stamp", {}).get("candidate_set_id"),
        "url": config.record_url(record.id),
    }
    return payload


def _record_html(payload: dict) -> str:
    """A minimal readable view. Deliberately plain: this is what an officer sees
    when they follow a hover, and it has one job — show the record the number
    came from, with its scope and its run stamp, in words rather than JSON."""
    def row(label, value):
        if value in (None, "", [], {}):
            return ""
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False, indent=2)
            return (f"<tr><th>{html.escape(label)}</th>"
                    f"<td><pre>{html.escape(str(value))}</pre></td></tr>")
        return (f"<tr><th>{html.escape(label)}</th>"
                f"<td>{html.escape(str(value))}</td></tr>")

    coordinates = payload["coordinates"]
    rows = "".join([
        row("Reads as", payload["display_sentence"]),
        row("Stored sentence", payload["sentence"]),
        row("Kind", payload["record_type"]),
        row("Analysis table", coordinates["view_title"]),
        row("Covers", coordinates["subspace_phrase"]),
        row("Broken down by", coordinates["breakdown"]),
        row("Measure", coordinates["measure"]),
        row("Rows in scope", coordinates["rows_in_scope"]),
        row("Engine score", payload["engine_score"]),
        row("Standing in the analysis", payload["standing"]),
        row("Run stamp", payload["run_stamp"]),
        row("Candidate set", payload["candidate_set_id"]),
        row("Places named", coordinates["geography"].get("gp_names")),
        row("Members", payload["values"]["members"][:25]
            if payload["values"]["members"] else None),
        row("Exceptions", payload["values"]["exceptions"]),
    ])
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>Record {html.escape(payload['id'])}</title><style>"
        "body{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;"
        "padding:0 1rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}"
        "th{text-align:left;vertical-align:top;width:14rem;padding:.4rem .6rem;"
        "border-bottom:1px solid #eee;color:#444;font-weight:600}"
        "td{padding:.4rem .6rem;border-bottom:1px solid #eee}"
        "pre{margin:0;white-space:pre-wrap;font-size:.85em}"
        "p.note{color:#666;font-size:.9em}"
        "</style></head><body>"
        f"<h1>{html.escape(payload['id'])}</h1>"
        "<p class=\"note\">One record from the analysis, exactly as it is "
        "stored. Nothing on this page is computed at request time.</p>"
        f"<table>{rows}</table>"
        "</body></html>"
    )


@app.get("/record/{finding_id}")
def record(finding_id: str, format: str = "json"):
    """The stored record behind a citation. `?format=html` for the reader view.

    An UNKNOWN ID 404s rather than returning `{"found": false}`, which is where
    this differs from `/finding/{id}` above and why it is a new endpoint rather
    than a widening of that one. `/finding` is an internal lookup whose caller
    already knows the id is real; `/record` is the target of a link in an
    officer's answer, and a link that returns 200 with a "not found" body is a
    link that looks like it worked. `/finding` keeps its shape so nothing that
    calls it changes.
    """
    found = STATE["retriever"].corpus.get(finding_id)
    if found is None:
        # WP-D15 T5.2: a place fact (`p-...`) resolves through the sheet store.
        place_payload = _place_record_payload(finding_id)
        if place_payload is None:
            raise HTTPException(status_code=404,
                                detail=f"no record {finding_id} in this corpus")
        if format == "html":
            return HTMLResponse(_place_record_html(place_payload))
        return place_payload
    payload = _record_payload(found)
    if format == "html":
        return HTMLResponse(_record_html(payload))
    return payload


# ── WP-D15 T5.2: a place fact behind a citation ──────────────────────────────
def _place_record_payload(fact_id: str) -> dict | None:
    """One sheet sentence: the sentence, the place's label, the row, the
    stored figures of that row exactly as the sheet holds them, the note and
    the run stamp. None for an id that is not a sheet sentence (-> 404).

    Layout (my decision, report §7): `figures` is the sheet's own entry for the
    row -- `rows[row]` for a main-row line (plus G2 for the G1 line, which
    states both), `lists[row][key]` for a list line -- copied, not
    re-computed. Built in `place.record_payload`: every read of the sheet
    store goes through `place.py`."""
    return place_mod.record_payload(STATE.get("profile"), fact_id)


def _place_record_html(payload: dict) -> str:
    """The reader view of a place fact, in the plain style of `_record_html`."""
    def row(label, value):
        if value in (None, "", [], {}):
            return ""
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False, indent=2)
            return (f"<tr><th>{html.escape(label)}</th>"
                    f"<td><pre>{html.escape(str(value))}</pre></td></tr>")
        return (f"<tr><th>{html.escape(label)}</th>"
                f"<td>{html.escape(str(value))}</td></tr>")

    rows = "".join([
        row("Place", payload["label"]),
        row("Stored sentence", payload["sentence"]),
        row("Note", payload["note"]),
        row("Kind", "place profile sheet line"),
        row("Row", payload["row"] + (f" / {payload['key']}"
                                     if payload["key"] else "")),
        row("Stored figures", payload["figures"]),
        row("Run stamp", payload["run_stamp"]),
        row("Candidate set", payload["candidate_set_id"]),
    ])
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>Record {html.escape(payload['id'])}</title><style>"
        "body{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;"
        "padding:0 1rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}"
        "th{text-align:left;vertical-align:top;width:14rem;padding:.4rem .6rem;"
        "border-bottom:1px solid #eee;color:#444;font-weight:600}"
        "td{padding:.4rem .6rem;border-bottom:1px solid #eee}"
        "pre{margin:0;white-space:pre-wrap;font-size:.85em}"
        "p.note{color:#666;font-size:.9em}"
        "</style></head><body>"
        f"<h1>{html.escape(payload['id'])}</h1>"
        "<p class=\"note\">One line of a place's profile sheet, exactly as it "
        "is stored. Nothing on this page is computed at request time.</p>"
        f"<table>{rows}</table>"
        "</body></html>"
    )
