/**
 * Parsing for a DiscoverChat answer.
 *
 * The service hands back one plain-text block. Its shape is fixed by
 * `DiscoverChat/assemble.py`, which is what makes it parseable at all:
 *
 *   - a finding is a sentence followed by an indented `(coverage)` line, and
 *     carries a leading `- ` when more than one is shown;
 *   - everything else is prose the writer put AROUND the findings;
 *   - the last block is always the run stamp, in parentheses.
 *
 * Split out from the view so it can be tested without React, matching
 * `insights-report.ts`. The parse is presentational only — no sentence is
 * rewritten, reordered or dropped, so what the officer reads is still the
 * service's own text.
 *
 * ## Hover-to-source (WP-D8)
 *
 * `parseCitedAnswer` adds the second layer: the same blocks, but with each
 * block's text cut into segments, some of which are bound to the finding they
 * came from. Those bindings are NOT computed here. They are computed server
 * side by `DiscoverChat/checks.bind_numerals` — the same function the blocking
 * citation check calls — and serialised into `answer_html`. We read the span
 * boundaries back out of that markup and drop everything else about it: its
 * styling, its `title=` tooltips, its `↗` links. The number an officer hovers
 * is therefore bound by the rule the answer actually passed, and there is no
 * second numeral-matching implementation in TypeScript to drift away from it.
 */

import type { DiscoverCitation } from "@/services/discover-api";

export interface AnswerFinding {
  kind: "finding";
  /** The corpus sentence, verbatim, minus the list marker. */
  text: string;
  /** The coverage line, minus its surrounding parentheses. */
  coverage: string;
}

export interface AnswerParagraph {
  kind: "paragraph";
  text: string;
}

export type AnswerBlock = AnswerFinding | AnswerParagraph;

export interface ParsedAnswer {
  blocks: AnswerBlock[];
  /** The run stamp — when the analysis behind these findings was mined. */
  stamp: string | null;
}

/** An indented parenthesised line: the coverage that follows a finding. */
const COVERAGE_LINE = /^\s{2,}\((.+)\)\s*$/;
/** The stamp: a whole block that is nothing but parentheses. */
const STAMP_BLOCK = /^\((.+)\)$/s;

/**
 * One contiguous slice of the original answer that a block's text is built
 * from. A paragraph that wrapped over three lines has three runs, joined by a
 * single space; a finding has one. Keeping the offsets is what lets the cited
 * layer map a span in the answer back to a position in a block's text without
 * re-finding it by string search, which on a short numeral like "4" would be a
 * guess.
 */
interface Run {
  /** Offset of this run's first character in the original answer. */
  start: number;
  text: string;
}

interface RawBlock {
  kind: "finding" | "paragraph";
  runs: Run[];
  coverage: string;
}

function runsToText(runs: Run[]): string {
  return runs.map((r) => r.text).join(" ");
}

/**
 * The block split, with offsets. `parseAnswer` projects the offsets away; the
 * cited path keeps them. One implementation so the two can never disagree
 * about where a block starts or what counts as a finding.
 */
function parseRawBlocks(answer: string): {
  blocks: RawBlock[];
  stamp: string | null;
} {
  const normalised = (answer ?? "").replace(/\r\n/g, "\n");
  const lines = normalised.split("\n");

  // Offset of the first character of each line in `normalised`.
  const offsets: number[] = [];
  let cursor = 0;
  for (const line of lines) {
    offsets.push(cursor);
    cursor += line.length + 1;
  }

  // The stamp is the trailing block. Taken off first so a stamp that happens
  // to sit on the line after a finding is never read as its coverage.
  let stamp: string | null = null;
  let end = lines.length;
  while (end > 0 && lines[end - 1].trim() === "") end--;
  if (end > 0) {
    const match = STAMP_BLOCK.exec(lines[end - 1].trim());
    if (match) {
      stamp = match[1];
      end--;
    }
  }

  const blocks: RawBlock[] = [];
  let paragraph: Run[] = [];

  const flush = () => {
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", runs: paragraph, coverage: "" });
      paragraph = [];
    }
  };

  for (let i = 0; i < end; i++) {
    const line = lines[i];
    if (line.trim() === "") {
      flush();
      continue;
    }

    const next = i + 1 < end ? lines[i + 1] : "";
    const coverage = COVERAGE_LINE.exec(next);
    if (coverage) {
      flush();
      // The marker and the surrounding space are not part of the sentence, so
      // the run starts after them — otherwise every finding's first bound span
      // would be offset by the width of "- ".
      const body = line.replace(/^\s*-\s+/, "");
      const lead = line.length - body.length;
      const trimmed = body.trim();
      blocks.push({
        kind: "finding",
        runs: [{ start: offsets[i] + lead + body.indexOf(trimmed), text: trimmed }],
        coverage: coverage[1].trim(),
      });
      i++; // the coverage line belongs to the finding, not to the prose
      continue;
    }

    const trimmed = line.trim();
    paragraph.push({ start: offsets[i] + line.indexOf(trimmed), text: trimmed });
  }
  flush();

  return { blocks, stamp };
}

export function parseAnswer(answer: string): ParsedAnswer {
  const { blocks, stamp } = parseRawBlocks(answer);
  return {
    stamp,
    blocks: blocks.map((b) =>
      b.kind === "finding"
        ? { kind: "finding", text: runsToText(b.runs), coverage: b.coverage }
        : { kind: "paragraph", text: runsToText(b.runs) }
    ),
  };
}

/** True when the answer is the route-to-Ask decline rather than a report. */
export function isAskRoute(move: string): boolean {
  return move === "lookup";
}

// ---------------------------------------------------------------------------
// Hover-to-source
// ---------------------------------------------------------------------------

/**
 * A slice of a block's text. `citation` is set when the service bound this
 * slice to a finding — that slice is the hover target, and it is what WP-D7
 * ruling 4 means by "the number itself".
 */
export interface CitedSegment {
  text: string;
  citation: DiscoverCitation | null;
}

export interface CitedFinding extends AnswerFinding {
  segments: CitedSegment[];
}

export interface CitedParagraph extends AnswerParagraph {
  segments: CitedSegment[];
}

export type CitedBlock = CitedFinding | CitedParagraph;

export interface ParsedCitedAnswer {
  blocks: CitedBlock[];
  stamp: string | null;
  /** True when at least one segment carries a citation. */
  hasCitations: boolean;
}

/** A span the service bound, as an offset range into the plain answer. */
interface BoundSpan {
  start: number;
  end: number;
  id: string;
}

const CITE_SPAN =
  /<span class="dc-cite"[^>]*\sdata-finding-id="([^"]*)"[^>]*>([\s\S]*?)<\/span>/g;
/** The `↗` anchor the reference render appends inside every bound span. */
const CITE_LINK = /<a class="dc-cite-link"[\s\S]*?<\/a>/g;

function unescapeHtml(text: string): string {
  return text
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

/** The body paragraph of the reference render, without the stamp paragraph. */
function answerBody(answerHtml: string): string | null {
  const match = /<p>([\s\S]*?)<\/p>/.exec(answerHtml);
  return match ? match[1] : null;
}

const isSpace = (ch: string) => ch === " " || ch === "\n" || ch === "\t" || ch === "\r";

/**
 * The bound spans, as offsets into the PLAIN answer.
 *
 * The reference render and the plain answer are the same characters with
 * different whitespace: `render.to_html` strips each sentence, joins them with
 * a single space, and closes the gap before `.,;:!?`. So the two are walked in
 * step, with any whitespace run on either side allowed to match any whitespace
 * run on the other, including an empty one. Nothing is searched for, so a span
 * whose text is "4" cannot land on the wrong "4".
 *
 * Returns null if the two streams ever disagree on a non-space character. That
 * is not an error to recover from cleverly — it means this markup did not come
 * from this answer, and the caller falls back to the plain render.
 */
function spansFromHtml(answer: string, answerHtml: string): BoundSpan[] | null {
  const body = answerBody(answerHtml ?? "");
  if (body === null) return null;

  // Tokenise the body into plain chunks and bound chunks, in document order.
  const chunks: { text: string; id: string | null }[] = [];
  let last = 0;
  CITE_SPAN.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = CITE_SPAN.exec(body)) !== null) {
    chunks.push({ text: unescapeHtml(body.slice(last, match.index)), id: null });
    chunks.push({
      text: unescapeHtml(match[2].replace(CITE_LINK, "")),
      id: match[1],
    });
    last = match.index + match[0].length;
  }
  chunks.push({ text: unescapeHtml(body.slice(last)), id: null });

  const spans: BoundSpan[] = [];
  let ai = 0;

  for (const chunk of chunks) {
    let start = -1;
    let end = -1;
    for (let ci = 0; ci < chunk.text.length; ci++) {
      const ch = chunk.text[ci];
      if (isSpace(ch)) {
        while (ci + 1 < chunk.text.length && isSpace(chunk.text[ci + 1])) ci++;
        while (ai < answer.length && isSpace(answer[ai])) ai++;
        continue;
      }
      // Whitespace the render dropped (before punctuation, or a paragraph
      // break it flattened) is skipped on the answer side.
      while (ai < answer.length && isSpace(answer[ai])) ai++;
      if (ai >= answer.length || answer[ai] !== ch) return null;
      if (start === -1) start = ai;
      ai++;
      end = ai;
    }
    if (chunk.id !== null && start !== -1) {
      spans.push({ start, end, id: chunk.id });
    }
  }

  return spans;
}

/**
 * The answer as blocks of segments, with every span the service bound marked.
 *
 * Falls back to the uncited blocks — byte for byte what `parseAnswer` gives —
 * whenever the payload cannot carry a binding: an older service that sends no
 * `answer_html`, a turn whose narrative fell back to bare sentences, or markup
 * that does not line up with the answer it came with.
 */
export function parseCitedAnswer(
  answer: string,
  answerHtml?: string,
  citations?: Record<string, DiscoverCitation>
): ParsedCitedAnswer {
  const { blocks: raw, stamp } = parseRawBlocks(answer);
  const normalised = (answer ?? "").replace(/\r\n/g, "\n");

  const plain = (): ParsedCitedAnswer => ({
    stamp,
    hasCitations: false,
    blocks: raw.map((b) => {
      const text = runsToText(b.runs);
      const segments: CitedSegment[] = text ? [{ text, citation: null }] : [];
      return b.kind === "finding"
        ? { kind: "finding", text, coverage: b.coverage, segments }
        : { kind: "paragraph", text, segments };
    }),
  });

  if (!answerHtml || !citations) return plain();

  const spans = spansFromHtml(normalised, answerHtml);
  if (spans === null || spans.length === 0) return plain();

  let hasCitations = false;
  const blocks: CitedBlock[] = raw.map((b) => {
    const segments: CitedSegment[] = [];

    const push = (text: string, citation: DiscoverCitation | null) => {
      if (!text) return;
      const previous = segments[segments.length - 1];
      // Plain text either side of a joiner is one segment, so a wrapped
      // paragraph does not render as a pile of adjacent spans.
      if (previous && previous.citation === null && citation === null) {
        previous.text += text;
        return;
      }
      segments.push({ text, citation });
    };

    b.runs.forEach((run, index) => {
      if (index > 0) push(" ", null); // the joiner `runsToText` uses
      const runEnd = run.start + run.text.length;
      let cursor = run.start;
      for (const span of spans) {
        if (span.end <= cursor || span.start >= runEnd) continue;
        const from = Math.max(span.start, cursor);
        const to = Math.min(span.end, runEnd);
        push(normalised.slice(cursor, from), null);
        const citation = citations[span.id];
        if (citation) {
          push(normalised.slice(from, to), citation);
          hasCitations = true;
        } else {
          // An id in the markup with no entry in the map. Show the words —
          // never blank the block — and say so once, because it means the two
          // halves of one payload disagree.
          warnUnknownId(span.id);
          push(normalised.slice(from, to), null);
        }
        cursor = to;
      }
      push(normalised.slice(cursor, runEnd), null);
    });

    const text = runsToText(b.runs);
    return b.kind === "finding"
      ? { kind: "finding", text, coverage: b.coverage, segments }
      : { kind: "paragraph", text, segments };
  });

  return { blocks, stamp, hasCitations };
}

const warnedIds = new Set<string>();

function warnUnknownId(id: string) {
  if (warnedIds.has(id)) return;
  warnedIds.add(id);
  console.warn(
    `[discover] answer cites ${id}, which is missing from the citations map; ` +
      `rendering it as plain text`
  );
}

/** Test seam: the warn-once set is module state and would leak between cases. */
export function resetCitationWarnings() {
  warnedIds.clear();
}

/**
 * True when the selection step did not run for this answer.
 *
 * The judge picks which findings an answer is built from. When it is
 * unreachable the service falls back to a similarity threshold, and the answer
 * is narrower than it should be — on 2026-09-03 a dead API key rendered as
 * "Bhubaneswar has no findings". An officer cannot tell that from the prose,
 * so the tab says it.
 */
export function usedFallbackSelection(
  retrieval: Record<string, unknown> | undefined
): boolean {
  const judge = retrieval?.judge as { source?: unknown } | undefined;
  return judge?.source === "fallback-threshold";
}
