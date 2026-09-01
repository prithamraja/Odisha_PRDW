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

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import assemble, config, corpus as corpus_mod
from .retrieval import Retriever
from .session import SessionStore

_log = logging.getLogger(__name__)

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    stamp = config.assert_pin_matches_corpus()
    retriever = Retriever()
    STATE["retriever"] = retriever
    STATE["assembler"] = assemble.Assembler(retriever)
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


@app.get("/health")
def health() -> dict:
    retriever = STATE.get("retriever")
    return {
        "status": "ok" if retriever else "starting",
        "findings": len(retriever.corpus) if retriever else 0,
        "candidate_set_id": STATE.get("stamp", {}).get("candidate_set_id"),
        "embedding_pin": STATE.get("stamp", {}).get("embedding_pin"),
        "knobs": config.knobs(),
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
    )


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
