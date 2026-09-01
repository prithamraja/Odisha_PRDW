# -*- coding: utf-8 -*-
"""NAVIGATE: follow-ups that walk finding structure. No free exploration.

D42 names three walks and this module implements those three and nothing else:

  EXCEPTION MEMBER  the officer asks about one of the exceptions just named ->
                    the findings where that member is the subject in its own
                    right, not merely one of twenty following a pattern
  SHARED MEASURE    "and elsewhere?" / "what about the other blocks" -> other
                    findings mined on the same measure
  SIBLINGS          "anything similar?" -> findings with the same shape (view,
                    measure, breakdown, pattern type) over a different slice

"No free exploration" is a real constraint, not a slogan: a follow-up that
matches none of the three walks is NOT quietly turned into a fresh search of the
whole corpus. It is answered as a retrieve turn over a CONTEXTUALISED query, and
the answer says that is what happened, so the officer can tell a structural walk
from a new search.

CONTEXTUALISED, NEVER THE RAW FRAGMENT (D42 ruling 7). "What about Banking
Facilities?" embedded on its own retrieves findings about banking, which is not
what was asked. The rewrite is DETERMINISTIC — the fragment, the question it
follows, and the subject of the findings on screen — because a model-written
rewrite would put a second uninspectable step between the officer's words and
what was searched for.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Walk:
    kind: str                    # "exception" | "measure" | "sibling" | "search"
    findings: list
    explanation: str
    query: str = ""


_SIMILAR = re.compile(r"\b(?:similar|anything else like|same (?:kind|sort|thing)|"
                      r"others like|elsewhere|other (?:places|blocks|districts|gps))\b",
                      re.IGNORECASE)


def anchor_names(anchors: list) -> dict:
    """The exception members and measures the officer can legitimately walk to."""
    exceptions, measures = {}, set()
    for finding in anchors:
        for exception in finding.data.get("exceptions", []):
            label = str(exception.get("member_label", "")).strip()
            if label:
                exceptions.setdefault(label, []).append(finding)
        measures.update(finding.data.get("measures", []))
    return {"exceptions": exceptions, "measures": measures}


def contextualise(message: str, previous_question: str, anchors: list) -> str:
    """A self-contained rewrite of a fragment, built deterministically."""
    subjects = []
    for finding in anchors[:3]:
        for measure in finding.data.get("measures", [])[:2]:
            if measure not in subjects and measure != "(varies)":
                subjects.append(measure.replace("_", " "))
    parts = [message.strip()]
    if previous_question:
        parts.append(f"This follows the question: {previous_question.strip()}")
    if subjects:
        parts.append("The findings on screen are about " + ", ".join(subjects) + ".")
    return " ".join(parts)


def walk(message: str, anchors: list, retriever) -> Walk | None:
    """Try the three structural walks, in order. None if none applies."""
    if not anchors:
        return None
    names = anchor_names(anchors)

    # 1. An exception member the officer just saw named.
    for label, sources in names["exceptions"].items():
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(label) + r"(?![A-Za-z0-9])",
                     message, re.IGNORECASE):
            findings = _findings_about(retriever, label)
            if findings:
                return Walk("exception", findings,
                            f"{label} was named as an exception in what you were "
                            f"just shown. These are the findings where it is the "
                            f"subject in its own right.")
            return Walk("exception", [],
                        f"{label} was named as an exception in what you were just "
                        f"shown, but the analysis holds no finding where it is "
                        f"the subject in its own right.")

    # 2. The same measure, elsewhere.
    if _SIMILAR.search(message) and names["measures"]:
        findings = _findings_on_measures(retriever, names["measures"], anchors)
        if findings:
            measure_words = ", ".join(sorted(m.replace("_", " ")
                                             for m in names["measures"])[:3])
            return Walk("measure", findings,
                        f"Other findings the analysis holds on {measure_words}.")

    # 3. Siblings: the same shape over a different slice.
    if _SIMILAR.search(message):
        findings = _siblings(retriever, anchors)
        if findings:
            return Walk("sibling", findings,
                        "Findings of the same shape over a different slice of "
                        "the data.")
    return None


def _findings_about(retriever, label: str, limit: int = 6) -> list:
    """Findings where `label` is the subject: its slice, its highlight, or its
    exception — never merely one of the members following a pattern."""
    out = []
    for finding in retriever.corpus.all():
        geo = finding.geography
        keys = list(geo["gp_names"]) + list(geo["blocks"]) + list(geo["districts"])
        role_key = label
        if label in geo["gp_names"]:
            role_key = geo["gp_lgd_codes"][geo["gp_names"].index(label)]
        if label in keys and geo["roles"].get(role_key) != "follows_pattern":
            out.append((finding.score, finding))
            continue
        for filters in finding.data.get("base_subspace", []):
            if len(filters) == 2 and str(filters[1]) == label:
                out.append((finding.score, finding))
                break
        else:
            for exception in finding.data.get("exceptions", []):
                if str(exception.get("member_label", "")) == label:
                    out.append((finding.score, finding))
                    break
    out.sort(key=lambda pair: -pair[0])
    return [finding for _score, finding in out[:limit]]


def _findings_on_measures(retriever, measures: set, anchors: list,
                          limit: int = 6) -> list:
    seen = {f.id for f in anchors}
    out = []
    for finding in retriever.corpus.all():
        if finding.id in seen:
            continue
        if measures & set(finding.measures):
            out.append((finding.score, finding))
    out.sort(key=lambda pair: -pair[0])
    return [finding for _score, finding in out[:limit]]


def _siblings(retriever, anchors: list, limit: int = 6) -> list:
    shapes = {(f.view, f.data["measure"], f.data["breakdown"],
               f.data["pattern_type"]) for f in anchors}
    seen = {f.id for f in anchors}
    out = []
    for finding in retriever.corpus.all():
        if finding.id in seen:
            continue
        shape = (finding.view, finding.data["measure"],
                 finding.data["breakdown"], finding.data["pattern_type"])
        if shape in shapes:
            out.append((finding.score, finding))
    out.sort(key=lambda pair: -pair[0])
    return [finding for _score, finding in out[:limit]]
