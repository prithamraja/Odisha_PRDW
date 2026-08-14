/**
 * Loading and parsing for the Discover insights report.
 *
 * Kept out of the view so the parser can be unit-tested directly without
 * dragging React in, and so the component file only exports components.
 */

// The report is a drop-in: whatever MetaInsights writes into src/data/insights/
// gets picked up at build time. Globbing rather than a fixed import means the
// folder can legitimately be empty, and Discover then says so rather than
// rendering another programme's findings.
const reportModules = import.meta.glob("../data/insights/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

// The folder's own README documents the drop-in contract; it is not a report,
// and without this filter its worked example renders as a real finding.
const reportPaths = Object.keys(reportModules)
  .filter((p) => !/(^|\/)readme\.md$/i.test(p))
  .sort();

/** The report to render, or null when the folder holds no report. */
export const rawReport: string | null =
  reportPaths.length > 0 ? reportModules[reportPaths[0]] : null;

export interface Insight {
  leadline: string;
  bullets: string[];
  /** The report's own "## " section heading. Sections are discovered, not mapped. */
  section: string;
}

export interface ReportSection {
  /** The "## " heading, verbatim. */
  name: string;
  insights: Insight[];
  /** The section's methodology caveat, or null. Never an insight. */
  readingNote: string | null;
}

export interface ParsedReport {
  /** Every insight, in report order. Reading notes are NOT in here. */
  insights: Insight[];
  /** The report's sections, in the order they appear in it. */
  sections: ReportSection[];
}

export const UNSECTIONED = "General";

/**
 * The generator's contract for a methodology caveat: a blockquote whose first
 * line opens with this marker, sitting at the end of a view's section.
 *
 * The text behind it is fixed content emitted by
 * Metainsights_anomalies/src/phase5b_report.py (READING_NOTES /
 * reading_note_block), not written by the model — a paraphrased caveat is worse
 * than no caveat. It is methodology, not a finding, so it must never take a
 * feed row, a chevron, a number or a slot in a chip count. If the marker
 * changes on the generator side, change it here too.
 */
export const READING_NOTE_MARKER = "> **Reading note:**";

/**
 * The generator writes an ASCII double hyphen where an em dash is meant
 * ("Rs 20.22 crore -- except Nellore"). Normalise it for display; only the
 * spaced form is touched, so ranges and hyphenated names are left alone.
 */
function tidy(text: string): string {
  return text.replace(/ -- /g, " — ");
}

/**
 * Strip the bold markers that wrap a leadline.
 *
 * Only when the line is ONE bold span. A line carrying several spans
 * ("**A** then **B**") would otherwise lose its first and last markers and
 * splice the middle two together into a bold run of the text between them —
 * so it is left whole for the renderer, which handles inline bold anyway.
 */
function stripOuterBold(line: string): string {
  const trimmed = line.trim();
  const inner = trimmed.slice(2, -2).trim();
  return inner.includes("**") ? trimmed : inner;
}

/**
 * Parse a MetaInsights report.
 *
 * Three shapes are recognised, because the generator emits all three:
 *   1. a bold leadline (**...**) followed by numbered bullets — an insight
 *   2. a "### " heading followed by a paragraph and/or dash bullets — an insight
 *   3. a blockquote opening with READING_NOTE_MARKER — the section's reading
 *      note, which is not an insight and is not counted as one
 *
 * Section membership comes from whichever "## " heading is currently in scope,
 * so the filter chips always reflect the report actually supplied.
 */
export function parseReport(md: string): ParsedReport {
  const insights: Insight[] = [];
  const sections: ReportSection[] = [];
  const byName = new Map<string, ReportSection>();

  const sectionFor = (name: string): ReportSection => {
    let section = byName.get(name);
    if (!section) {
      section = { name, insights: [], readingNote: null };
      byName.set(name, section);
      sections.push(section);
    }
    return section;
  };

  let currentSection = UNSECTIONED;

  const lines = md.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Section header (## level, but not ###)
    if (line.startsWith("## ") && !line.startsWith("### ")) {
      currentSection = line.replace(/^## /, "").trim() || UNSECTIONED;
      sectionFor(currentSection);
      i++;
      continue;
    }

    // Reading note: a blockquote opening with the marker. Later "> " lines
    // belong to the same note, so a wrapped note reads as one paragraph.
    if (line.startsWith(READING_NOTE_MARKER)) {
      const parts = [line.slice(READING_NOTE_MARKER.length).trim()];
      i++;
      while (i < lines.length && lines[i].startsWith(">")) {
        parts.push(lines[i].replace(/^>\s?/, "").trim());
        i++;
      }
      const note = tidy(parts.join(" ").trim());
      if (note) {
        sectionFor(currentSection).readingNote = note;
      }
      continue;
    }

    // Bold leadline: **...**
    if (line.startsWith("**") && line.trimEnd().endsWith("**")) {
      const leadline = stripOuterBold(line);
      const bullets: string[] = [];
      i++;

      // Collect numbered bullets
      while (i < lines.length) {
        const bLine = lines[i].trim();
        if (/^\d+\.\s/.test(bLine)) {
          bullets.push(tidy(bLine.replace(/^\d+\.\s*/, "")));
          i++;
        } else if (bLine === "") {
          i++;
          if (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
            continue;
          }
          break;
        } else {
          break;
        }
      }

      if (leadline) {
        const insight = { leadline: tidy(leadline), bullets, section: currentSection };
        insights.push(insight);
        sectionFor(currentSection).insights.push(insight);
      }
      continue;
    }

    // "### " heading + paragraph + dash-bullet format (overview style)
    if (line.startsWith("### ")) {
      const heading = line.replace(/^### /, "").trim();
      i++;

      // A "### " line that just introduces bold leadlines is a sub-header, not a
      // finding — e.g. "### MARKFED Procurement Findings" sitting above the
      // section's first insight. Treating it as one would manufacture an empty
      // row AND swallow the real insight underneath it as its own body.
      const next = lines.slice(i).find((l) => l.trim() !== "");
      if (next && next.startsWith("**")) {
        continue;
      }

      const bullets: string[] = [];
      let paragraph = "";

      while (i < lines.length) {
        const bLine = lines[i].trim();
        if (bLine.startsWith("## ") || bLine.startsWith("### ") || bLine.startsWith("---")) {
          break;
        }
        if (bLine.startsWith("- ")) {
          bullets.push(tidy(bLine.replace(/^- /, "")));
          i++;
        } else if (/^\d+\.\s/.test(bLine)) {
          bullets.push(tidy(bLine.replace(/^\d+\.\s*/, "")));
          i++;
        } else if (bLine !== "" && !paragraph) {
          paragraph = tidy(bLine);
          i++;
        } else {
          i++;
        }
      }

      const allBullets: string[] = [];
      if (paragraph) allBullets.push(paragraph);
      allBullets.push(...bullets);

      if (heading) {
        const insight = {
          leadline: tidy(heading),
          bullets: allBullets,
          section: currentSection,
        };
        insights.push(insight);
        sectionFor(currentSection).insights.push(insight);
      }
      continue;
    }

    i++;
  }

  // A "## " heading the writer left empty is not a filter anyone can use.
  const populated = sections.filter(
    (s) => s.insights.length > 0 || s.readingNote !== null
  );
  return { insights, sections: populated };
}

/** Interleave sections so the unfiltered list reads across themes, not down one. */
export function interleaveBySection(insights: Insight[], sections: string[]): Insight[] {
  const buckets = new Map<string, Insight[]>(sections.map((s) => [s, []]));
  for (const ins of insights) {
    buckets.get(ins.section)?.push(ins);
  }

  const ordered: Insight[] = [];
  const cursors = new Map<string, number>(sections.map((s) => [s, 0]));
  let progressed = true;
  while (progressed) {
    progressed = false;
    for (const section of sections) {
      const bucket = buckets.get(section)!;
      const cursor = cursors.get(section)!;
      if (cursor < bucket.length) {
        ordered.push(bucket[cursor]);
        cursors.set(section, cursor + 1);
        progressed = true;
      }
    }
  }
  return ordered;
}

/**
 * Split text into runs, marking the ones the report wants emphasised.
 *
 * The generator writes `**bold**` inside bullet and note bodies as well as
 * around headlines. Only headlines were ever unwrapped, so every other body
 * rendered its asterisks literally. This is the one place that knows the
 * convention; the renderer turns a `bold` run into whatever the design system
 * calls emphasis.
 */
export function splitBold(text: string): { text: string; bold: boolean }[] {
  const runs: { text: string; bold: boolean }[] = [];
  const pattern = /\*\*(.+?)\*\*/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  // An unpaired marker has nothing to emphasise, and showing it to a programme
  // officer as "**" would be a generator bug leaking into the briefing. Drop it.
  const plain = (s: string) => ({ text: s.replace(/\*\*/g, ""), bold: false });

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      runs.push(plain(text.slice(cursor, match.index)));
    }
    runs.push({ text: match[1], bold: true });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    runs.push(plain(text.slice(cursor)));
  }
  return runs.filter((run) => run.text !== "");
}
