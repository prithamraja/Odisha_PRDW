#!/usr/bin/env python
"""WP-D4 -- prompt construction. Appendix A is embedded VERBATIM (brief T2);
nothing is added to it and nothing is paraphrased."""

# ---------------------------------------------------------------------------
# Appendix A of handoffs/WPD4_prose_trial.md, verbatim. Do not edit.
# ---------------------------------------------------------------------------
APPENDIX_A = """You are writing for a decision-aid system used by government officials in
Odisha's Department of Panchayati Raj & Drinking Water. The system
automatically analyses village-level planning and spending records --
development plans, sanctions, payments, works and photo evidence from
Gram Panchayats, blocks, and districts -- and surfaces patterns worth an official's attention.

Your readers are busy block-, district- and state-level officials, not data
analysts. They read these insights to decide where to direct attention:
which districts to question, which records to reconcile, which local
practices to check at the next review.

Below are 15 findings from the analysis engine, each written in the engine's
internal style -- accurate but full of database language -- along with
reference figures for each. Rewrite each finding as an insight a senior
officer would find clear and actionable:
- a one-to-two-sentence lead the officer sees first;
- a short detail paragraph explaining what was found, which places are
  exceptions and in what way, and what is worth checking or asking at the
  next review.

Write naturally, in plain English. Use the reference figures where they
strengthen the point; use no number that is not provided. Be direct about
what the data can and cannot establish -- these records are incomplete in
known ways described below, and an insight that overstates certainty could
send an official after the wrong problem.

Background to reflect where relevant:
- Sanction records exist for only about one work in six, so figures on a
  sanctioned basis describe that subset, and a falling sanctioned value can
  mean fewer sanctions or fewer sanctions being entered.
- Cost-free activities (training, campaigns, services) began being recorded
  only in 2023-24, so activity counts jump at that boundary for a reporting
  reason, not a real one.
- Total cashbook spending has not grown across these years, while the share
  of spending linked to a planned activity rose from 2.7% to 53.2% -- a rise
  in "linked spending" is mostly better record-keeping.
- March concentrates payments every year; it is the fiscal year-end and this
  is normal government cash flow.
- Output categories "Code 101" to "Code 110" have no descriptions on file;
  nothing can be concluded about what they contain until the department
  supplies the decode.
- "Uncategorised" assets are works with no asset category recorded -- about
  two-thirds of all works; it is not itself a kind of asset.
- Only 17 works in the whole sample are marked completed, so completion
  figures measure recording practice, not delivery.
- Voucher and payment counts are workload, not a performance rating.
- This is a 20-Gram-Panchayat sample; percentages describe the sample, not
  the state."""

# Figures that appear in Appendix A's background, for the T3 numeral check.
APPENDIX_A_NUMERALS = ["2023-24", "2.7", "53.2", "101", "110", "17", "20"]

OUTPUT_FORMAT = """Give your answer for all 15 findings, in order. Delimit each one exactly like this:

===FINDING 1===
LEAD: <the lead>
DETAIL: <the detail paragraph>
===FINDING 2===
LEAD: ...
DETAIL: ...

...and so on through ===FINDING 15===."""


def render_packet(p: dict) -> str:
    """One finding packet, as the writer sees it."""
    L = []
    L.append(f"===FINDING {p['rank']}===")
    L.append(f"Engine sentence: {p['feed_sentence']}")
    L.append(f"Records covered: {p['scope']}")
    members = p.get("members_following_the_pattern") or []
    if members:
        L.append(f"Follows the pattern ({p.get('members_count')} of "
                 f"{p.get('members_out_of')}): " + ", ".join(map(str, members)))
    if p["exceptions"]:
        L.append("Exceptions:")
        for e in p["exceptions"]:
            L.append(f"  - {e['name']}: {e['kind']} -- {e['in_words']}")
    else:
        L.append("Exceptions: none recorded.")
    if p["reference_figures"]:
        L.append("Reference figures:")
        for f in p["reference_figures"]:
            L.append(f"  - {f['label']}: {f['display']}")
    else:
        L.append("Reference figures: none available for this finding "
                 "(the engine could not compute them because the finding spans "
                 "members measured on different scales).")
    return "\n".join(L)


def build_writer_prompt(packets: list) -> str:
    return (APPENDIX_A + "\n\n" + OUTPUT_FORMAT + "\n\n"
            + "\n\n".join(render_packet(p) for p in packets))


def build_single_prompt(packet: dict, reason: str) -> str:
    """T5 regeneration: Appendix A + one packet + why the last attempt failed."""
    return (APPENDIX_A + "\n\n"
            + f"""Give your answer for this one finding only, delimited exactly like this:

===FINDING {packet['rank']}===
LEAD: <the lead>
DETAIL: <the detail paragraph>

A previous attempt at this finding was rejected. The reason given was:
{reason}

""" + render_packet(packet))
