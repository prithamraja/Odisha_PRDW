import { describe, expect, it } from "vitest";

import type { CitedBlock } from "./discover-answer";
import { citedIds, placePanels, usableLayout } from "./discover-answer-layout";
import type { DiscoverCitation, LayoutPanel } from "@/services/discover-api";

function citation(id: string): DiscoverCitation {
  return {
    id,
    sentence: "s",
    display_sentence: "s",
    scope: "",
    standing: "",
    view: "v",
    is_decomposition: true,
    stamp: "as of 2026-11-21",
    url: `/record/${id}`,
  };
}

function block(...ids: string[]): CitedBlock {
  return {
    kind: "paragraph",
    text: "t",
    segments: [
      { text: "plain ", citation: null },
      ...ids.map((id) => ({ text: "12", citation: citation(id) })),
    ],
  };
}

function panel(...ids: string[]): LayoutPanel {
  return {
    kind: "ranked",
    id: ids[0],
    ids,
    url: `/record/${ids[0]}`,
    label: "planned cost",
    by: "block",
    scope: "district Cuttack",
    total: "Rs 5.35 crore",
    direction: null,
    shown: 1,
    of: 1,
    bars: [],
  };
}

const CARD = {
  id: "d1-1",
  url: "/record/d1-1",
  kind: "total",
  value: "Rs 5.35 crore",
  label: "planned cost",
  scope: "district Cuttack",
};

describe("usableLayout", () => {
  it("is null for an absent, empty or other-version layout", () => {
    expect(usableLayout(undefined)).toBeNull();
    expect(usableLayout({})).toBeNull();
    expect(usableLayout({ version: 2, cards: [CARD] })).toBeNull();
    expect(usableLayout({ version: 1, cards: [], warnings: [], panels: [] })).toBeNull();
  });

  it("drops a panel or card of an unknown kind and keeps the rest", () => {
    const usable = usableLayout({
      version: 1,
      cards: [CARD, { ...CARD, id: "x", kind: "hologram" }],
      panels: [{ kind: "sankey", ids: ["d1-2"] }, panel("d1-3")],
    });
    expect(usable?.cards.map((c) => c.id)).toEqual(["d1-1"]);
    expect(usable?.panels.map((p) => p.ids)).toEqual([["d1-3"]]);
    expect(usable?.warnings).toEqual([]);
  });

  it("is null when only unknown panels were sent", () => {
    expect(usableLayout({ version: 1, panels: [{ kind: "sankey", ids: [] }] })).toBeNull();
  });
});

describe("placePanels", () => {
  it("puts a panel under the first block citing any of its records", () => {
    const blocks = [block("a"), block("b", "c"), block("c")];
    const placed = placePanels(blocks, [panel("c"), panel("z", "a"), panel("b")]);
    expect(placed.byBlock.map((ps) => ps.map((p) => p.ids[0]))).toEqual([
      ["z"],
      ["c", "b"],
      [],
    ]);
    expect(placed.trailing).toEqual([]);
  });

  it("sends a panel no block cites after the last block", () => {
    const placed = placePanels([block("a")], [panel("q")]);
    expect(placed.byBlock).toEqual([[]]);
    expect(placed.trailing.map((p) => p.ids)).toEqual([["q"]]);
  });

  it("puts every panel after the last block when nothing is cited (the fallback)", () => {
    const blocks = [block(), block()];
    const placed = placePanels(blocks, [panel("a"), panel("b")]);
    expect(placed.byBlock).toEqual([[], []]);
    expect(placed.trailing.map((p) => p.ids[0])).toEqual(["a", "b"]);
  });

  it("reads a block's cited ids off its bound segments", () => {
    expect([...citedIds(block("a", "b", "a"))]).toEqual(["a", "b"]);
  });
});
