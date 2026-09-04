import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  parseAnswer,
  parseCitedAnswer,
  resetCitationWarnings,
  usedFallbackSelection,
  type CitedBlock,
} from "./discover-answer";
import type { DiscoverCitation } from "@/services/discover-api";
import FIXTURES from "./discover-answers.fixtures.json";

// The fixtures below are the shapes DiscoverChat/assemble.py actually emits:
// `render_finding` (bulleted and bare), `_stamped`, and the why-reframe.
const STAMP = "mined from the 2026-08-30 analysis run, candidate set cs-7";

describe("parseAnswer", () => {
  it("reads a single finding and its coverage", () => {
    const { blocks, stamp } = parseAnswer(
      `Expenditure per GP in Khordha is 2.4x the state median.\n` +
        `   (12 GPs, 2024-25)\n\n(${STAMP})`
    );

    expect(stamp).toBe(STAMP);
    expect(blocks).toEqual([
      {
        kind: "finding",
        text: "Expenditure per GP in Khordha is 2.4x the state median.",
        coverage: "12 GPs, 2024-25",
      },
    ]);
  });

  it("strips the list marker from bulleted findings", () => {
    const { blocks } = parseAnswer(
      `- First finding.\n   (a, b)\n\n- Second finding.\n   (c, d)\n\n(${STAMP})`
    );

    expect(blocks.map((b) => b.kind)).toEqual(["finding", "finding"]);
    expect(blocks[0]).toMatchObject({ text: "First finding." });
    expect(blocks[1]).toMatchObject({ text: "Second finding.", coverage: "c, d" });
  });

  it("keeps the writer's prose separate from the findings it introduces", () => {
    const { blocks } = parseAnswer(
      `Three blocks account for most of the gap.\n\n` +
        `- A finding.\n   (cov)\n\n(${STAMP})`
    );

    expect(blocks[0]).toEqual({
      kind: "paragraph",
      text: "Three blocks account for most of the gap.",
    });
    expect(blocks[1].kind).toBe("finding");
  });

  it("joins a wrapped paragraph into one block", () => {
    const { blocks } = parseAnswer(
      `This analysis finds patterns and associations.\nIt cannot establish what causes what.\n\n(${STAMP})`
    );

    expect(blocks).toEqual([
      {
        kind: "paragraph",
        text:
          "This analysis finds patterns and associations. It cannot establish what causes what.",
      },
    ]);
  });

  // The decline and the honest miss are prose only. They still carry a stamp,
  // and losing it would let a stale run read as today's.
  it("keeps the stamp on an answer that has no findings at all", () => {
    const { blocks, stamp } = parseAnswer(
      `The current analysis has nothing on this.\n\n(${STAMP})`
    );

    expect(stamp).toBe(STAMP);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("paragraph");
  });

  it("does not read a stamp as the coverage of the finding above it", () => {
    const { blocks, stamp } = parseAnswer(
      `A finding.\n   (real coverage)\n\n(${STAMP})`
    );

    expect(stamp).toBe(STAMP);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toMatchObject({ coverage: "real coverage" });
  });

  it("survives an answer with no stamp rather than dropping the text", () => {
    const { blocks, stamp } = parseAnswer("Just prose.");
    expect(stamp).toBeNull();
    expect(blocks).toEqual([{ kind: "paragraph", text: "Just prose." }]);
  });

  it("returns nothing for an empty answer", () => {
    expect(parseAnswer("")).toEqual({ blocks: [], stamp: null });
  });
});

// Recorded from a live turn against DiscoverChat on 2026-09-01 (candidate set
// a7f991c1df3771f9). Hand-written fixtures agree with whatever the parser does;
// this one does not, and it carries the case that broke a naive parse — a
// finding SENTENCE with parentheses of its own, on the line above the coverage.
const LIVE_TURN = "- Across most measure values (6/9), Bheden has the highest (varies) among block_name values. Exception: activity_linked_expenditure (Barpali has the highest (varies) among block_name values); sanctions_count (Barpali has the highest (varies) among block_name values); sanctioned_amount (Barpali has the highest (varies) among block_name values)\n   (ranked 31 of 32 in the current feed)\n\n- Across most fiscal_year values (4/6), Bhubaneswar has the highest payment_amount among block_name values. Exception: 2024-2025 (no clear pattern); 2025-2026 (different pattern)\n   (not in the ranked shortlist \u2014 one of the wider set of patterns the analysis found but did not promote)\n\n(as of 2026-08-17)";

describe("a recorded live turn", () => {
  it("splits into its two findings, coverage and stamp", () => {
    const { blocks, stamp } = parseAnswer(LIVE_TURN);

    expect(blocks.map((b) => b.kind)).toEqual(["finding", "finding"]);
    expect(stamp).toBe("as of 2026-08-17");
  });

  it("keeps parentheses inside a finding sentence out of the coverage", () => {
    const { blocks } = parseAnswer(LIVE_TURN);
    const first = blocks[0];

    expect(first.kind).toBe("finding");
    if (first.kind !== "finding") return;
    // "(varies)" belongs to the sentence, not to the coverage line under it.
    expect(first.text).toContain("(varies)");
    expect(first.text.startsWith("-")).toBe(false);
    expect(first.coverage).toBe("ranked 31 of 32 in the current feed");
  });

  it("carries the unranked-coverage label through verbatim", () => {
    const { blocks } = parseAnswer(LIVE_TURN);
    const second = blocks[1];

    expect(second.kind).toBe("finding");
    if (second.kind !== "finding") return;
    expect(second.coverage).toBe(
      "not in the ranked shortlist — one of the wider set of patterns the " +
        "analysis found but did not promote"
    );
  });
});

// Recorded after WP-D6 landed (question decomposition + the render-time
// glossary). The sentences now carry officer phrases rather than column names,
// and a decomposition record's coverage line reads differently from a mined
// finding's — the STRUCTURE the parser keys on is unchanged, and this fixture
// is what proves that rather than assumes it.
const LIVE_TURN_D6 = "- Within the whole of Gram Panchayat Report Card by Year, spending totals Rs 25.35 crore across 16 blocks. It is spread across them without one standing out: the largest is Bhubaneswar at 13.1% (Rs 3.33 crore), then Rangeilunda at 10.8% (Rs 2.73 crore). The remaining 14 together account for Rs 19.29 crore. For size: Bhubaneswar holds 10.4% of the 12,704 activities behind these totals, against 13.1% of spending -- a group's total grows with how much of the work it holds.\n   (a breakdown of the recorded totals, not a mined pattern \u2014 the parts add up to the whole)\n\n- Within focus area Rural housing, spending measured against plan totals Rs -2.23 crore across 16 blocks. This measure is signed: a positive figure is spending above plan and a negative figure is spending below plan. It is concentrated: Boipariguda accounts for 95.7% of it (Rs -2.13 crore). The remaining 15 together account for Rs -9.50 lakh. For size: Boipariguda holds 2.0% of the 305 activities behind these totals, against 95.7% of spending measured against plan -- a group's total grows with how much of the work it holds. As a ratio rather than an amount, Boipariguda is 0.0%.\n   (a breakdown of the recorded totals, not a mined pattern \u2014 the parts add up to the whole)\n\n(as of 2026-08-17)";

describe("a recorded live turn after WP-D6", () => {
  it("still splits into findings, coverage and stamp", () => {
    const { blocks, stamp } = parseAnswer(LIVE_TURN_D6);

    expect(blocks.every((b) => b.kind === "finding")).toBe(true);
    expect(blocks).toHaveLength(2);
    expect(stamp).toBe("as of 2026-08-17");
  });

  it("keeps a decomposition's coverage line intact", () => {
    const first = parseAnswer(LIVE_TURN_D6).blocks[0];

    expect(first.kind).toBe("finding");
    if (first.kind !== "finding") return;
    expect(first.coverage).toBe(
      "a breakdown of the recorded totals, not a mined pattern — the parts " +
        "add up to the whole"
    );
    // Rupee figures and percentages belong to the sentence, not the coverage.
    expect(first.text).toContain("Rs 25.35 crore");
  });
});

// ---------------------------------------------------------------------------
// Hover-to-source (WP-D8)
// ---------------------------------------------------------------------------

/**
 * Recorded from the running WP-D7 DiscoverChat on 2026-09-04 (candidate set
 * a7f991c1df3771f9) over the 15 questions of
 * `DiscoverChat/experiments/answer_compare.json`, plus the brief's two manual
 * cases. Real turns, not hand-written: a hand-written fixture would agree with
 * whatever the parser does, and the point of these is to disagree when the
 * parser and the service's own render disagree.
 */
interface Fixture {
  question: string;
  answer: string;
  answer_tagged: string;
  citations: Record<string, DiscoverCitation>;
  answer_html: string;
  judge_source: string | null;
}

const fixtures = FIXTURES as unknown as Fixture[];
const cited = fixtures.filter((f) => f.answer_html.trim() !== "");

/** The bound spans the SERVICE produced: id and text, in document order. */
function oracleSpans(answerHtml: string): { id: string; text: string }[] {
  const body = /<p>([\s\S]*?)<\/p>/.exec(answerHtml);
  if (!body) return [];
  const out: { id: string; text: string }[] = [];
  const span =
    /<span class="dc-cite"[^>]*\sdata-finding-id="([^"]*)"[^>]*>([\s\S]*?)<\/span>/g;
  let m: RegExpExecArray | null;
  while ((m = span.exec(body[1])) !== null) {
    out.push({
      id: m[1],
      text: m[2]
        .replace(/<a class="dc-cite-link"[\s\S]*?<\/a>/g, "")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&#x27;/g, "'")
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, "&"),
    });
  }
  return out;
}

/** The bound spans OUR render produced, in the same shape and order. */
function renderedSpans(blocks: CitedBlock[]): { id: string; text: string }[] {
  return blocks.flatMap((b) =>
    b.segments
      .filter((s) => s.citation)
      .map((s) => ({ id: s.citation!.id, text: s.text }))
  );
}

describe("parseCitedAnswer, against the service's own render", () => {
  beforeEach(() => resetCitationWarnings());

  it("has the recorded turns to check against", () => {
    expect(fixtures.length).toBeGreaterThanOrEqual(15);
    expect(cited.length).toBeGreaterThan(0);
  });

  // (a) The hard invariant. Our segments are slices of `answer` itself, so
  // this is exact — no whitespace drift, every numeral in place and in order.
  it.each(cited.map((f) => [f.question, f] as const))(
    "reassembles the answer byte for byte: %s",
    (_q, fixture) => {
      const { blocks } = parseCitedAnswer(
        fixture.answer,
        fixture.answer_html,
        fixture.citations
      );
      const plain = parseAnswer(fixture.answer);

      expect(blocks).toHaveLength(plain.blocks.length);
      blocks.forEach((block, i) => {
        // Segments concatenate back to exactly the block's own text...
        expect(block.segments.map((s) => s.text).join("")).toBe(block.text);
        // ...and that text is byte for byte what the untagged parse gives.
        expect(block.text).toBe(plain.blocks[i].text);
        expect(block.kind).toBe(plain.blocks[i].kind);
      });
    }
  );

  // (b) The oracle. Every span the service bound is a bound span here, with
  // the same text, in the same order — and there are no extra ones.
  it.each(cited.map((f) => [f.question, f] as const))(
    "binds exactly the spans answer_html binds: %s",
    (_q, fixture) => {
      const { blocks } = parseCitedAnswer(
        fixture.answer,
        fixture.answer_html,
        fixture.citations
      );

      const expected = oracleSpans(fixture.answer_html);
      expect(expected.length).toBeGreaterThan(0);
      expect(renderedSpans(blocks)).toEqual(expected);
      // The ids as a set too, so a reordering cannot pass by coincidence.
      expect(new Set(renderedSpans(blocks).map((s) => s.id))).toEqual(
        new Set(expected.map((s) => s.id))
      );
    }
  );

  it("never emits an empty segment", () => {
    for (const fixture of cited) {
      const { blocks } = parseCitedAnswer(
        fixture.answer,
        fixture.answer_html,
        fixture.citations
      );
      for (const block of blocks) {
        for (const segment of block.segments) {
          expect(segment.text.length).toBeGreaterThan(0);
        }
      }
    }
  });

  it("reports that it found citations", () => {
    const fixture = cited[0];
    const parsed = parseCitedAnswer(
      fixture.answer,
      fixture.answer_html,
      fixture.citations
    );
    expect(parsed.hasCitations).toBe(true);
  });
});

describe("parseCitedAnswer when the payload cannot carry a binding", () => {
  beforeEach(() => resetCitationWarnings());

  // (d) An older service, or a turn that fell back to bare sentences.
  it("renders exactly as the untagged parse when there is no answer_html", () => {
    for (const fixture of fixtures) {
      const parsed = parseCitedAnswer(fixture.answer);
      const plain = parseAnswer(fixture.answer);

      expect(parsed.stamp).toBe(plain.stamp);
      expect(parsed.hasCitations).toBe(false);
      expect(parsed.blocks.map((b) => b.text)).toEqual(
        plain.blocks.map((b) => b.text)
      );
      // One plain segment per block: nothing is hoverable.
      for (const block of parsed.blocks) {
        expect(block.segments.every((s) => s.citation === null)).toBe(true);
      }
    }
  });

  it("falls back rather than mangling when the markup is not this answer's", () => {
    const fixture = cited[0];
    const parsed = parseCitedAnswer(
      "A completely unrelated answer.\n\n(as of 2026-08-17)",
      fixture.answer_html,
      fixture.citations
    );

    expect(parsed.hasCitations).toBe(false);
    expect(parsed.blocks[0].text).toBe("A completely unrelated answer.");
  });

  // (c) An id in the markup with no entry in the citations map.
  it("renders an unknown id as plain text and warns once per id", () => {
    const fixture = cited[0];
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    // Every id in the markup is now unknown.
    const parsed = parseCitedAnswer(fixture.answer, fixture.answer_html, {});

    // The words are still there, in full, and none of them is hoverable.
    const plain = parseAnswer(fixture.answer);
    expect(parsed.blocks.map((b) => b.text)).toEqual(
      plain.blocks.map((b) => b.text)
    );
    expect(parsed.hasCitations).toBe(false);
    for (const block of parsed.blocks) {
      expect(block.segments.every((s) => s.citation === null)).toBe(true);
    }

    // Once per id, not once per occurrence.
    const ids = new Set(oracleSpans(fixture.answer_html).map((s) => s.id));
    expect(warn).toHaveBeenCalledTimes(ids.size);

    warn.mockRestore();
  });

  it("survives an empty answer with markup attached", () => {
    expect(parseCitedAnswer("", '<div class="dc-answer"><p>x</p></div>', {})).toEqual(
      { blocks: [], stamp: null, hasCitations: false }
    );
  });
});

// (e) The fallback notice, at the level the notice is decided.
describe("usedFallbackSelection", () => {
  it("is true only when the judge fell back to the threshold", () => {
    expect(
      usedFallbackSelection({ judge: { source: "fallback-threshold" } })
    ).toBe(true);
    expect(usedFallbackSelection({ judge: { source: "judge" } })).toBe(false);
    expect(usedFallbackSelection({ judge: {} })).toBe(false);
    expect(usedFallbackSelection({})).toBe(false);
    expect(usedFallbackSelection(undefined)).toBe(false);
  });

  it("agrees with the recorded turns", () => {
    for (const fixture of fixtures) {
      expect(
        usedFallbackSelection({ judge: { source: fixture.judge_source } })
      ).toBe(fixture.judge_source === "fallback-threshold");
    }
  });
});
