import { createElement } from "react";
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup, fireEvent } from "@testing-library/react";

import {
  READING_NOTE_MARKER,
  parseReport,
  splitBold,
} from "@/lib/insights-report";
import { AnomaliesView } from "@/components/insights/AnomaliesView";
import gamma05 from "@/data/insights/gamma_0.5_report.md?raw";

describe("parseReport", () => {
  it("assigns insights to the '## ' section currently in scope", () => {
    const { insights } = parseReport(`# Title

## Payments & DBT

**Pendency reaches 35% in two districts**

1. East Godavari carries the bulk.

## Targeting & Equity

**ST farmers receive 0.705 of the average**

1. The gap closes in ITDA mandals.
`);

    expect(insights).toHaveLength(2);
    expect(insights[0].section).toBe("Payments & DBT");
    expect(insights[0].leadline).toBe("Pendency reaches 35% in two districts");
    expect(insights[0].bullets).toEqual(["East Godavari carries the bulk."]);
    expect(insights[1].section).toBe("Targeting & Equity");
  });

  it("does not turn a '### ' sub-header into an insight when a leadline follows it", () => {
    const { insights } = parseReport(`## MARKFED Procurement

### MARKFED Procurement Findings

**ST farmers have the lowest per-purchase value at Rs 67,861**

1. ST farmers average Rs 67,861 per transaction.
`);

    // The sub-header must not appear, and must not swallow the real finding.
    expect(insights).toHaveLength(1);
    expect(insights[0].leadline).toBe(
      "ST farmers have the lowest per-purchase value at Rs 67,861"
    );
    expect(insights[0].bullets).toEqual(["ST farmers average Rs 67,861 per transaction."]);
  });

  it("still parses the '### ' heading + paragraph + dash-bullet shape", () => {
    const { insights } = parseReport(`## Overview

### Where the money went

Six programmes carry the spending.

- MARKFED procurement is the largest.
`);

    expect(insights).toHaveLength(1);
    expect(insights[0].leadline).toBe("Where the money went");
    expect(insights[0].bullets).toEqual([
      "Six programmes carry the spending.",
      "MARKFED procurement is the largest.",
    ]);
  });

  it("returns nothing for a report with no findings", () => {
    expect(parseReport("# Title\n\nJust prose, no findings.\n")).toEqual({
      insights: [],
      sections: [],
    });
  });

  it("promotes the generator's spaced '--' to an em dash, leaving hyphens alone", () => {
    const { insights } = parseReport(`## S

**MARKFED carries Rs 10.66 crore -- except Nellore**

1. The Backward-Caste share is 45.3% -- close to its roster share.
`);

    expect(insights[0].leadline).toBe("MARKFED carries Rs 10.66 crore — except Nellore");
    expect(insights[0].bullets[0]).toBe(
      "The Backward-Caste share is 45.3% — close to its roster share."
    );
  });

  it("keeps a leadline whole when it carries more than one bold span", () => {
    // Stripping the outer pair here would splice " holds " into a bold run.
    const { insights } = parseReport(`## S

**Chittoor** holds **Rs 36.67 lakh**

1. A bullet.
`);

    expect(insights[0].leadline).toBe("**Chittoor** holds **Rs 36.67 lakh**");
  });
});

describe("reading notes", () => {
  const md = `## Equity Cube

**ST farmers are reached at 62.0% against 71.0% for everyone else**

1. The statewide figure rests on 65 farmers.

${READING_NOTE_MARKER} These figures are **per farmer on the PM-KISAN roster**, not per farmer in the full farming population.

---

## MARKFED Procurement

**Paddy carries Rs 10.66 crore of procurement value**

1. Paddy is the largest crop by value.
`;

  const parsed = parseReport(md);

  it("attaches the note to its own section", () => {
    const equity = parsed.sections.find((s) => s.name === "Equity Cube")!;
    expect(equity.readingNote).toBe(
      "These figures are **per farmer on the PM-KISAN roster**, not per farmer in the full farming population."
    );
  });

  it("is not an insight, in the section or in the flat list", () => {
    expect(parsed.insights).toHaveLength(2);
    expect(parsed.insights.every((i) => !i.leadline.includes("Reading note"))).toBe(
      true
    );
    const equity = parsed.sections.find((s) => s.name === "Equity Cube")!;
    expect(equity.insights).toHaveLength(1);
  });

  it("leaves a section without one at null", () => {
    const markfed = parsed.sections.find((s) => s.name === "MARKFED Procurement")!;
    expect(markfed.readingNote).toBeNull();
  });

  it("joins a note wrapped over several blockquote lines into one paragraph", () => {
    const { sections } = parseReport(`## S

${READING_NOTE_MARKER} The base is the PM-KISAN roster.
> Tenant farmers are outside it.

**A finding**

1. A bullet.
`);

    expect(sections[0].readingNote).toBe(
      "The base is the PM-KISAN roster. Tenant farmers are outside it."
    );
    expect(sections[0].insights).toHaveLength(1);
  });
});

describe("splitBold", () => {
  it("splits the report's **bold** spans out of body text", () => {
    expect(splitBold("Chittoor holds **Rs 36.67 lakh** of the balance")).toEqual([
      { text: "Chittoor holds ", bold: false },
      { text: "Rs 36.67 lakh", bold: true },
      { text: " of the balance", bold: false },
    ]);
  });

  it("drops an unpaired marker rather than printing it", () => {
    expect(splitBold("Rs 36.67 lakh ** of the balance")).toEqual([
      { text: "Rs 36.67 lakh  of the balance", bold: false },
    ]);
  });

  it("leaves plain text alone", () => {
    expect(splitBold("no markers here")).toEqual([
      { text: "no markers here", bold: false },
    ]);
  });
});

describe("the bundled Odisha PR&DW gamma 0.5 report", () => {
  const { insights, sections } = parseReport(gamma05);

  // Discover renders whatever single .md sits in src/data/insights/. The feed
  // reads as this department's own findings either way, so a report from an
  // earlier deployment left in the folder is silently wrong rather than broken.
  // These assertions pin the bundled report to THIS programme.
  it("is the Odisha report, not a retired AP or UP one", () => {
    expect(gamma05).toContain("Odisha PR&DW Decision Aid");
    expect(gamma05).not.toContain("AP RTGS");
    expect(gamma05).not.toContain("PM-JAY");
  });

  it("parses every bold leadline in the file, and nothing else", () => {
    const leadlineCount = (gamma05.match(/^\*\*.*\*\*$/gm) ?? []).length;
    expect(insights).toHaveLength(leadlineCount);
  });

  it("discovers the report's three sections", () => {
    expect(sections).toHaveLength(3);
    expect(sections[0].name).toBe(
      "Activity Lifecycle - Every Planned Work and Its Money"
    );
    expect(sections.map((s) => s.name)).toContain(
      "Gram Panchayat Report Card by Year"
    );
  });

  it("leaves no insight stranded outside a section", () => {
    expect(insights.filter((i) => i.section === "General")).toHaveLength(0);
  });

  it("gives every insight supporting detail", () => {
    expect(insights.filter((i) => i.bullets.length === 0)).toHaveLength(0);
  });

  it("carries the generator's deterministic reading notes, and no insight is one", () => {
    const noted = sections.filter((s) => s.readingNote !== null);
    const markers = (gamma05.match(/^> \*\*Reading note:\*\*/gm) ?? []).length;

    expect(markers).toBeGreaterThan(0);
    expect(noted).toHaveLength(markers);
    // Every section's note has to be the one the generator wrote for THAT
    // view, not a note that happened to land in scope. The sanction-record
    // caveat is the one both the lifecycle and report-card views carry.
    expect(noted.map((s) => s.readingNote).join(" ")).toContain(
      "2,101 of the 12,704 activities"
    );
    // The old report had the caveat written by the model as a "### " heading,
    // which the feed then rendered as a numbered finding.
    expect(insights.map((i) => i.leadline)).not.toContain("Reading note for this view");
  });

  it("counts only insights, so the chip totals sum to the row count", () => {
    const perSection = sections.reduce((n, s) => n + s.insights.length, 0);
    expect(perSection).toBe(insights.length);
  });
});

describe("the rendered Discover feed", () => {
  it("shows no raw markdown markers anywhere on the page", () => {
    const { container, unmount } = render(createElement(AnomaliesView));
    expect(container.textContent).not.toContain("**");

    // Only one row is open at a time, so each body has to be looked at as it
    // opens. The bullets are where the generator's markers actually live.
    for (const button of container.querySelectorAll("[aria-expanded]")) {
      fireEvent.click(button);
      expect(container.textContent).not.toContain("**");
    }
    unmount();
  });

  it("renders each reading note as a callout, not as a row", () => {
    const { container, unmount } = render(createElement(AnomaliesView));
    const { insights, sections } = parseReport(gamma05);
    const noted = sections.filter((s) => s.readingNote !== null);

    // One toggle per insight and not one more: the notes are outside the list.
    expect(container.querySelectorAll("[aria-expanded]")).toHaveLength(
      insights.length
    );
    expect(container.textContent).toContain(
      "one row for each of the 12,704 activities"
    );
    expect(noted.length).toBeGreaterThan(0);
    unmount();
  });

  it("excludes the notes from the chip counts", () => {
    const { container, unmount } = render(createElement(AnomaliesView));
    const { insights } = parseReport(gamma05);

    const allChip = [...container.querySelectorAll('[role="group"] button')].find(
      (b) => b.textContent?.startsWith("All")
    )!;
    expect(allChip.textContent).toBe(`All${insights.length}`);
    unmount();
  });

  afterEach(() => cleanup());
});
