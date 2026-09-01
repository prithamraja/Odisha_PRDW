# -*- coding: utf-8 -*-
"""Per-conversation state: what is on screen, so a follow-up has an anchor.

Deliberately small and in-process. The only thing a follow-up needs is the
findings the officer can see and the question that produced them; anything more
would be state this product has no use for and a privacy surface it has no
reason to open. Nothing here is persisted — a restart loses the thread, which
for a read-only findings browser is a smaller cost than a store to maintain.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field

MAX_SESSIONS = 500
MAX_TURNS = 20


@dataclass
class Turn:
    question: str
    move: str
    finding_ids: list = field(default_factory=list)


@dataclass
class Session:
    session_id: str
    turns: list = field(default_factory=list)
    _anchors: list = field(default_factory=list)

    @property
    def previous_question(self) -> str:
        return self.turns[-1].question if self.turns else ""

    @property
    def anchors(self) -> list:
        """The findings currently on screen — what a follow-up may walk from."""
        return self._anchors

    def history_lines(self) -> list:
        return [f"{t.question} -> {t.move}, {len(t.finding_ids)} finding(s)"
                for t in self.turns]

    def record(self, question: str, move: str, findings: list) -> None:
        self.turns.append(Turn(question, move, [f.id for f in findings]))
        del self.turns[:-MAX_TURNS]
        if findings:
            self._anchors = list(findings)


class SessionStore:
    def __init__(self, max_sessions: int = MAX_SESSIONS):
        self._sessions: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_sessions

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            self._sessions.move_to_end(session_id)
            while len(self._sessions) > self._max:
                self._sessions.popitem(last=False)
            return session
