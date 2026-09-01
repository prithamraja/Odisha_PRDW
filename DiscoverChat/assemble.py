# -*- coding: utf-8 -*-
"""The three conversational moves (D42 "What v1 is").

  RETRIEVE   score the question; everything above the floor is the answer.
  NAVIGATE   follow-ups walk finding structure — an exception member, a shared
             measure, sibling findings. No free exploration.
  DECLINE    a number-lookup routes to Ask; a why-question gets the reframe.

Two invariants this module exists to hold, and both are structural rather than
instructed:

**Finding text is never model-written.** `_render_finding` reads the corpus.
There is no path by which model output reaches an officer as a finding sentence;
the model's words are only ever inserted around them.

**Every answer carries the run stamp.** Not as decoration: the corpus is a
snapshot of one mining run, and an answer that does not say when it was mined
invites an officer to read a stale pattern as today's.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import classifier, config, judge as judge_mod, navigate, writer as writer_mod
from .retrieval import Result


# A decomposition answers "where does this sit", and an officer who asked "who
# is DRIVING the shortfall" will read a split as the answer to the question they
# asked unless the difference is stated. Deterministic text, on the same footing
# as the why-reframe: it states a limit, it does not characterise the findings.
DECOMPOSE_SCOPE_NOTE = (
    "One thing to be clear about: the breakdown below shows where the amount "
    "sits — which parts add up to it, and in what proportion. It does not "
    "establish what produced it. This analysis finds patterns and does not "
    "measure what causes what."
)

ASK_ROUTE_MESSAGE = (
    "That is a question about the records themselves — a figure, a count or a "
    "list — and this system does not hold them. Ask, the question-answering "
    "chatbot for this database, is the one to put it to. This system only "
    "reports patterns the analysis has already found."
)


@dataclass
class Answer:
    move: str
    text: str
    findings: list = field(default_factory=list)
    routing: dict = field(default_factory=dict)
    prose: dict = field(default_factory=dict)
    retrieval: dict = field(default_factory=dict)
    stamp: str = ""

    def as_dict(self) -> dict:
        return {"move": self.move, "text": self.text,
                "findings": [f.id for f in self.findings],
                "routing": self.routing, "prose": self.prose,
                "retrieval": self.retrieval, "stamp": self.stamp}


# ── deterministic rendering ──────────────────────────────────────────────────

def render_finding(finding, *, bullet: bool = False) -> str:
    """One record, from the corpus, verbatim. No model touches this.

    Bulleted rather than numbered, and that is not a style choice: a numbered
    list puts digits into the answer that belong to no finding, and the gate's
    "every numeral traces to a corpus sentence" check would then have to carve
    out an exception for presentation. A check with an exception in it is a
    weaker check, and list markers are the cheaper thing to give up.

    `display_sentence()` rather than `sentence` (D6.1): the same string with its
    engine column names swapped for officer phrases by a dictionary. It is still
    the corpus's sentence -- no clause moves and no digit changes -- which is
    why `findings-verbatim` in the gate is still a real check after the swap.
    """
    head = "- " if bullet else ""
    return f"{head}{finding.display_sentence()}\n   ({finding.coverage_line()})"


def render_findings(findings: list) -> str:
    if len(findings) == 1:
        return render_finding(findings[0])
    return "\n\n".join(render_finding(f, bullet=True) for f in findings)


def nothing_found(result: Result) -> str:
    """The honest miss (D42 ruling 5). Never a stretched weak match."""
    lines = ["The current analysis has nothing on this."]
    if result.slots.has_geography or result.slots.measures:
        named = (result.slots.gp_names + result.slots.blocks
                 + result.slots.districts)
        if named:
            lines.append(
                f"It does hold findings that mention {', '.join(named)}, but "
                f"none of them is close enough to what you asked to be worth "
                f"showing you.")
    lines.append(
        "That is a statement about this analysis run, not about the data: the "
        "engine looks for particular shapes of pattern, and what you asked "
        "about is not one it found.")
    return "\n".join(lines)


def why_reframe(question: str, result: Result) -> str:
    """D41: a why-question gets a scope-honest reframe, never an answer.

    Three parts, and the third is what stops the reframe being a brush-off:
    what the data DOES show about the subject, that the readings are open, and
    what could actually be done next.
    """
    # Written to pass its own gate. An earlier draft said "not reliable enough
    # to carry a causal claim", and the ban fired on 'causal': the denial sat 66
    # characters back, outside the negation window. Widening that window to let
    # this sentence through would have loosened the guard for every real claim
    # too, so the sentence was reworded instead — which is what the ban is for.
    lines = [
        "This analysis finds patterns and associations. It cannot establish "
        "what causes what — the outcome measures in this data are not reliable "
        "enough for that — so I will not answer a 'why' with a reason.",
    ]
    if result.hits:
        lines.append("")
        lines.append("What the analysis does show about this:")
        lines.append("")
        lines.append(render_findings([h.finding for h in result.hits]))
        lines.append("")
        lines.append(
            "Those readings are open in both directions: a pattern like this "
            "can be a real difference in how places work, or a difference in "
            "what gets recorded, and nothing in the analysis separates the two.")
    else:
        lines.append("")
        lines.append("The analysis also holds nothing on the subject of your "
                     "question, so there is not even a pattern to point at.")
    lines.append("")
    lines.append(
        "What can be done next is describable rather than analytical: ask the "
        "places named here what they did differently, check whether the records "
        "behind the pattern are complete, and put the question to the officers "
        "who were there.")
    return "\n".join(lines)


# ── the moves ────────────────────────────────────────────────────────────────

class Assembler:
    def __init__(self, retriever, *, allow_model: bool = True,
                 use_judge: bool | None = None):
        self.retriever = retriever
        self.allow_model = allow_model
        # The judged path needs a model, so `allow_model=False` forces the
        # threshold path. That is what keeps the offline gate meaningful: the
        # behaviours it pins -- the Ask decline, the why-reframe, the causal
        # scan, numeral traceability, the run stamp -- are all independent of
        # which retrieval path ran, and none of them should go red because a
        # model phrased something differently on a replay.
        self.use_judge = (config.USE_JUDGE if use_judge is None else use_judge)
        self._roster = self._build_roster()

    def _retrieve(self, message: str, turn_id=None) -> tuple:
        """(Result, judge metadata). The judged path, or the threshold path.

        The judged path pools everything above `CANDIDATE_FLOOR`, hands the top
        `CANDIDATE_POOL` to the judge, and keeps what the judge selects. If the
        judge cannot be reached or cannot be parsed, this falls back to the
        THRESHOLD path rather than to the pool -- showing an officer 100
        candidates because a judge was unavailable would be the opposite of
        what the judge is for.
        """
        if not (self.use_judge and self.allow_model):
            return self.retriever.score(message), {"used": False,
                                                   "why": "threshold path"}

        pooled = self.retriever.pool(message)
        selection = judge_mod.select(message, [h.finding for h in pooled.hits],
                                     corpus_size=len(self.retriever.corpus),
                                     turn_id=turn_id)
        if selection.source != "judge":
            fallback = self.retriever.score(message)
            meta = selection.as_dict()
            meta["used"] = False
            meta["fell_back_to_threshold"] = True
            return fallback, meta

        keep = set(selection.kept_ids)
        hits = [h for h in pooled.hits if h.finding.id in keep]
        capped = len(hits) > config.ANSWER_CAP
        result = Result(slots=pooled.slots, hits=hits[:config.ANSWER_CAP],
                        considered=pooled.considered,
                        best_cosine=pooled.best_cosine,
                        threshold=config.CANDIDATE_FLOOR,
                        collapsed_count=pooled.collapsed_count, capped=capped)
        meta = selection.as_dict()
        meta["used"] = True
        meta["pool"] = len(pooled.hits)
        return result, meta

    def _build_roster(self) -> set:
        """Every place / category name the corpus knows — the (b) check's net."""
        roster = set()
        for finding in self.retriever.corpus.all():
            for name in finding.data.get("named_members", []):
                text = str(name).strip()
                if text and not text.isdigit() and len(text) > 2:
                    roster.add(text)
        return roster

    def _navigate(self, message, anchors, previous_question, routing, stamp):
        """One of the three structural walks, or None to fall through."""
        walk = navigate.walk(message, anchors, self.retriever)
        if walk is None:
            return None
        if not walk.findings:
            return Answer(move=classifier.NAVIGATE,
                          text=_stamped(walk.explanation, stamp),
                          routing=routing.as_dict(), stamp=stamp,
                          retrieval={"walk": walk.kind, "above_floor": 0})
        body = render_findings(walk.findings)
        return Answer(move=classifier.NAVIGATE,
                      text=_stamped(f"{walk.explanation}\n\n{body}", stamp),
                      findings=walk.findings, routing=routing.as_dict(),
                      stamp=stamp,
                      retrieval={"walk": walk.kind,
                                 "above_floor": len(walk.findings)})

    def answer(self, message: str, *, history=None, turn_id=None,
               anchors=None, previous_question: str = "") -> Answer:
        stamp = config.run_stamp_line()
        anchors = anchors or []
        routing = classifier.classify(message, history or [], turn_id=turn_id,
                                      allow_model=self.allow_model)

        if routing.move == classifier.LOOKUP:
            return Answer(move=routing.move, text=_stamped(ASK_ROUTE_MESSAGE, stamp),
                          routing=routing.as_dict(), stamp=stamp)

        if routing.move == classifier.NAVIGATE:
            answer = self._navigate(message, anchors, previous_question,
                                    routing, stamp)
            if answer is not None:
                return answer
            # No structural walk applies. The turn is still answered, but as a
            # SEARCH over a contextualised query, and the answer says so — a
            # navigate turn that silently became a fresh search would be the
            # free exploration D42 rules out.
            message = navigate.contextualise(message, previous_question, anchors)

        result, judge_meta = self._retrieve(message, turn_id=turn_id)
        retrieval_meta = {
            "judge": judge_meta,
            "considered": result.considered,
            "best_cosine": round(result.best_cosine, 4),
            "threshold": result.threshold,
            "above_floor": len(result.hits),
            "collapsed": result.collapsed_count,
            "capped": result.capped,
            "slots": result.slots.as_dict(),
        }

        if routing.move == classifier.WHY:
            return Answer(move=routing.move,
                          text=_stamped(why_reframe(message, result), stamp),
                          findings=[h.finding for h in result.hits],
                          routing=routing.as_dict(), retrieval=retrieval_meta,
                          stamp=stamp)

        if not result.hits:
            return Answer(move=routing.move,
                          text=_stamped(nothing_found(result), stamp),
                          routing=routing.as_dict(), retrieval=retrieval_meta,
                          stamp=stamp)

        findings = [h.finding for h in result.hits]
        body = render_findings(findings)

        # A small answer is rendered from its sentences and needs no prose at
        # all. Calling a model to introduce two findings would be spending a
        # verifier round on a sentence that adds nothing.
        if len(findings) <= config.FULL_RENDER_MAX or not self.allow_model:
            text = body
            prose_meta = {"used": False,
                          "why": "few enough findings to render directly"}
        else:
            prose = writer_mod.write(message, findings,
                                     corpus_roster=self._roster,
                                     turn_id=turn_id, fallback="")
            prose_meta = prose.as_dict()
            prose_meta["used"] = not prose.fell_back
            text = f"{prose.text}\n\n{body}" if prose.text else body

        # A causally-worded decompose turn gets the limit stated before the
        # numbers, not after them: an officer who reads the split first has
        # already taken it for the answer to "who is driving this".
        if (routing.move == classifier.DECOMPOSE
                and classifier.asked_causally(message)
                and any(f.is_decomposition for f in findings)):
            text = f"{DECOMPOSE_SCOPE_NOTE}\n\n{text}"

        if result.capped:
            text += (f"\n\nMore than {config.ANSWER_CAP} findings clear the "
                     f"relevance bar for this question; these are the "
                     f"{config.ANSWER_CAP} closest to what you asked.")

        return Answer(move=routing.move, text=_stamped(text, stamp),
                      findings=findings, routing=routing.as_dict(),
                      prose=prose_meta, retrieval=retrieval_meta, stamp=stamp)


def _stamped(text: str, stamp: str) -> str:
    return f"{text}\n\n({stamp})"
