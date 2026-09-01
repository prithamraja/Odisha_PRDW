#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WP-D4 (v2) -- prompt construction.

The instantiated Appendix A goes in VERBATIM (context.CONTEXT). Nothing is added
to it, nothing is paraphrased, and no writing rule of any kind is appended: the
whole point of the v2 design is that the writer is unconstrained and every safety
check lives after it.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from context import CONTEXT

OUTPUT_FORMAT = """Give your answer for each finding below, in order. Delimit each one exactly like this:

===FINDING 1===
LEAD: <the lead>
DETAIL: <the detail paragraph>
===FINDING 2===
LEAD: ...
DETAIL: ...

...and so on, one block per finding."""


def render_packet(p):
    """One finding packet, exactly as the writer sees it."""
    L = []
    L.append("===FINDING %d===" % p["rank"])
    L.append("Engine sentence: %s" % p["feed_sentence"])
    L.append("Analysis table: %s -- %s" % (p["view_title"], p["view_row"]))
    L.append("Records covered: %s" % p["scope"])

    if p.get("definitions"):
        L.append("What the variables mean:")
        for d in p["definitions"]:
            L.append("  - %s (%s): %s" % (d["variable"], d["role"], d["definition"]))

    members = p.get("members_following_the_pattern") or []
    if members:
        L.append("Follows the pattern (%s of %s): %s"
                 % (p.get("members_count"), p.get("members_out_of"),
                    ", ".join(map(str, members))))
    if p["exceptions"]:
        L.append("Exceptions:")
        for e in p["exceptions"]:
            L.append("  - %s: %s -- %s" % (e["name"], e["kind"], e["in_words"]))
    else:
        L.append("Exceptions: none recorded.")

    if p["reference_figures"]:
        L.append("Reference figures:")
        for f in p["reference_figures"]:
            L.append("  - %s: %s" % (f["label"], f["display"]))
    elif p.get("grain_figures"):
        L.append("Reference figures. The engine cannot total this finding across "
                 "its three time units, so the figures below are for the "
                 "fiscal-year unit only, not for the finding as a whole:")
        for f in p["grain_figures"]:
            L.append("  - %s: %s" % (f["label"], f["display"]))
    else:
        L.append("Reference figures: none available for this finding.")

    if p.get("year_forms"):
        L.append("Year labels -- the same year in either form, both correct: "
                 + "; ".join("%s = %s" % (a, b) for a, b in p["year_forms"].items()))
    return "\n".join(L)


def build_writer_prompt(packets):
    return (CONTEXT + "\n\n" + OUTPUT_FORMAT + "\n\n"
            + "\n\n".join(render_packet(p) for p in packets))


def build_single_prompt(packet, reason):
    """T5 regeneration: the context + one packet + why the last attempt failed."""
    return (CONTEXT + "\n\n"
            + """Give your answer for this one finding only, delimited exactly like this:

===FINDING %d===
LEAD: <the lead>
DETAIL: <the detail paragraph>

A previous attempt at this finding was rejected. The reason given was:
%s

""" % (packet["rank"], reason) + render_packet(packet))
