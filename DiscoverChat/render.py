# -*- coding: utf-8 -*-
"""Hover-to-source rendering for the consolidated narrative (WP-D7 D7.3/D7.2).

**The tags are plumbing and never appear on screen.** What appears is the
narrative, with every figure bound to the stored sentence it came from, so an
officer can put a cursor on a number and read the engine's own words, the slice
of data they describe, and when the analysis was run — then follow the link to
the whole record (D7.2).

**This is the operator's validation mechanism** (ruling 4), and that is why the
binding here is not a second implementation of the citation rule. It calls
`checks.bind_numerals`, the same function the blocking check calls, so the
number an officer hovers is bound by the rule the answer passed. A renderer that
matched numbers its own way could show a hover that the check never approved.

**The service ships this so the behaviour suite can exercise it end to end.**
The hover UI in the Discover tab is the operator's front-end side and will not
be this markup; what has to be shared is the DATA — the per-id record map the
API returns — and the fact that a checked binding exists for every numeral. This
module is the reference that proves both are sufficient to build the hover from.

NO STYLING BEYOND WHAT THE BEHAVIOUR NEEDS. `title=` carries the hover text so
the fragment works with no CSS and no JavaScript at all; the `data-` attributes
carry the same content in fields, for a front end that wants to render its own
panel. Both are populated from one dict so they cannot disagree.
"""
from __future__ import annotations

import html
import re

from . import checks, config


def citation_map(findings: list, *, run_date: str = "") -> dict:
    """Per cited id: everything a hover or a record link needs.

    Both sentences are carried. The STORED one is what the citation check
    matched against and what `/record/{id}` serves, so it is the auditable form;
    the DISPLAY one is what an officer can actually read. Showing the display
    sentence in the hover and holding the stored one beside it is not a
    contradiction — `findings-verbatim` in the gate proves every digit is the
    same in both.
    """
    out = {}
    for finding in findings:
        out[finding.id] = {
            "id": finding.id,
            "sentence": finding.sentence,
            "display_sentence": finding.display_sentence(),
            "scope": finding.data.get("subspace_phrase", ""),
            "standing": finding.coverage_line(),
            "view": finding.view_title,
            "is_decomposition": finding.is_decomposition,
            "stamp": run_date or config.run_stamp_line(),
            "url": config.record_url(finding.id),
        }
    return out


def _hover_text(entry: dict) -> str:
    bits = [entry["display_sentence"]]
    if entry["scope"]:
        bits.append(f"Covers: {entry['scope']}")
    # ASCII separator, not an em-dash: this line is our own scaffolding, and the
    # renderer must not be the thing that puts a non-ASCII byte into an
    # otherwise-ASCII answer. The corpus's own sentences may carry anything; the
    # frame we wrap around them stays ASCII so a cp1252 console can print it.
    bits.append(f"{entry['view']} - {entry['stamp']}")
    return "\n".join(bits)


def _wrap(text: str, entry: dict) -> str:
    return (
        '<span class="dc-cite" '
        f'data-finding-id="{html.escape(entry["id"], quote=True)}" '
        f'data-record-url="{html.escape(entry["url"], quote=True)}" '
        f'data-sentence="{html.escape(entry["display_sentence"], quote=True)}" '
        f'data-scope="{html.escape(entry["scope"], quote=True)}" '
        f'data-stamp="{html.escape(entry["stamp"], quote=True)}" '
        f'title="{html.escape(_hover_text(entry), quote=True)}">'
        f'{html.escape(text)}'
        # The glyph is written as an entity rather than as a literal so this
        # module stays pure ASCII: the gate and the tests print rendered
        # fragments to a Windows console that is cp1252 by default, and a
        # renderer that raises UnicodeEncodeError when someone looks at its
        # output is a renderer nobody will look at.
        f'<a class="dc-cite-link" href="{html.escape(entry["url"], quote=True)}">&#8599;</a>'
        "</span>"
    )


def _spans_for_sentence(sentence: str, findings: list, cites: dict,
                        run_date: str) -> list:
    """(start, end, replacement) for one sentence, non-overlapping, in order.

    Two passes, and the order between them is what keeps a claim-level hover
    from swallowing a figure that has its own:

      1. NUMERALS. Every numeral occurrence is bound to the first tag in this
         sentence whose STORED sentence contains it — `checks.bind_numerals`'s
         rule, applied here to positions rather than to tokens.
      2. CLAIMS. A tag that bound no numeral in this sentence is a non-numeric
         claim, and the hover target is "the phrase the tag follows": the run of
         text from the previous tag to this one. If a figure inside that run
         already carries its own hover, the claim span is shortened to the text
         after it rather than being dropped, so the claim is still reachable.
    """
    by_id = {f.id: f for f in findings}
    stored = {f.id: checks._stored_numerals(f) for f in findings}
    tags = list(re.finditer(r"\[([^\[\]\n]{1,60})\]", sentence))
    tag_ids = [t.group(1).strip() for t in tags]

    spans = []
    for tag in tags:                                   # the tags themselves go
        spans.append((tag.start(), tag.end(), ""))

    tag_bound = {i: False for i in range(len(tags))}
    for match in checks._NUM.finditer(sentence):
        if any(s <= match.start() < e for s, e, _ in spans):
            continue                                   # a digit inside a tag
        variants = checks._num_variants(match.group(0))
        for index, tag_id in enumerate(tag_ids):
            if tag_id in by_id and (variants & stored[tag_id]):
                spans.append((match.start(), match.end(),
                              _wrap(match.group(0), cites[tag_id])))
                tag_bound[index] = True
                break

    numeral_ends = [e for s, e, r in spans if r]
    previous_end = 0
    for index, tag in enumerate(tags):
        if not tag_bound[index] and tag_ids[index] in by_id:
            start = previous_end
            inner = [e for e in numeral_ends if start < e <= tag.start()]
            if inner:
                start = max(inner)
            phrase = sentence[start:tag.start()]
            stripped = phrase.strip()
            if stripped:
                offset = start + phrase.index(stripped)
                spans.append((offset, offset + len(stripped),
                              _wrap(stripped, cites[tag_ids[index]])))
        previous_end = tag.end()

    spans.sort(key=lambda s: s[0])
    cleaned, last = [], -1
    for start, end, replacement in spans:
        if start < last:
            continue
        cleaned.append((start, end, replacement))
        last = end
    return cleaned


def to_html(tagged_prose: str, findings: list, *, run_date: str = "") -> str:
    """The narrative as an HTML fragment, every citation a hover element."""
    cites = citation_map(findings, run_date=run_date)
    out = []
    for sentence in checks._tagged_sentences(tagged_prose or ""):
        spans = _spans_for_sentence(sentence, findings, cites, run_date)
        pieces, cursor = [], 0
        for start, end, replacement in spans:
            pieces.append(html.escape(sentence[cursor:start]))
            pieces.append(replacement)
            cursor = end
        pieces.append(html.escape(sentence[cursor:]))
        rendered = "".join(pieces).strip()
        if rendered:
            out.append(rendered)
    body = " ".join(out)
    body = re.sub(r"\s+([.,;:!?])", r"\1", body)
    stamp = run_date or config.run_stamp_line()
    return (f'<div class="dc-answer">\n  <p>{body}</p>\n'
            f'  <p class="dc-stamp">({html.escape(stamp)})</p>\n</div>')


CSS = """.dc-cite { border-bottom: 1px dotted #666; cursor: help; }
.dc-cite-link { text-decoration: none; font-size: 0.75em; padding-left: 2px; }
.dc-stamp { color: #666; font-size: 0.85em; }
.dc-answer { max-width: 42rem; line-height: 1.55; font-family: system-ui, sans-serif; }
"""


def to_page(tagged_prose: str, findings: list, *, question: str = "",
            run_date: str = "") -> str:
    """The same fragment as a standalone page — what the behaviour suite opens."""
    heading = f"<h2>{html.escape(question)}</h2>\n" if question else ""
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>DiscoverChat answer</title>\n<style>\n" + CSS +
            "</style></head>\n<body>\n" + heading
            + to_html(tagged_prose, findings, run_date=run_date)
            + "\n</body></html>\n")
