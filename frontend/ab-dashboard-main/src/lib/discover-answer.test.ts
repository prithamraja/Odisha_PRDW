import { describe, expect, it } from "vitest";
import { parseAnswer } from "./discover-answer";

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
