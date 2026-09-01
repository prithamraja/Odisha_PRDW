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
 */

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

export function parseAnswer(answer: string): ParsedAnswer {
  const lines = (answer ?? "").replace(/\r\n/g, "\n").split("\n");

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

  const blocks: AnswerBlock[] = [];
  let paragraph: string[] = [];

  const flush = () => {
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
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
      blocks.push({
        kind: "finding",
        text: line.replace(/^\s*-\s+/, "").trim(),
        coverage: coverage[1].trim(),
      });
      i++; // the coverage line belongs to the finding, not to the prose
      continue;
    }

    paragraph.push(line.trim());
  }
  flush();

  return { blocks, stamp };
}

/** True when the answer is the route-to-Ask decline rather than a report. */
export function isAskRoute(move: string): boolean {
  return move === "lookup";
}
