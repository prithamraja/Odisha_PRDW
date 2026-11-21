import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { InsightReport } from "./InsightReport";
import FIXTURES from "@/lib/discover-layout.fixtures.json";
import BASELINE from "@/lib/discover-layout-baseline.fixtures.json";
import type {
  DiscoverChatResponse,
  DiscoverLayout,
  LayoutPanel,
} from "@/services/discover-api";

/**
 * WP-D12 T2.6, on the payloads the service actually returned (T1's live
 * turns, `discover-layout.fixtures.json`): Cuttack, Chikilli and the mostly-
 * patterns answer carry a narrative; Kalimela and the small answer fell back to
 * bare sentences; the out-of-scope question went to Ask with no layout.
 */

interface Entry {
  question: string;
  response: DiscoverChatResponse;
}

const ENTRIES = Object.entries(
  FIXTURES.answers as unknown as Record<string, Entry>
);
const BASE = (BASELINE as { text: Record<string, string> }).text;
const entry = (name: string) =>
  (FIXTURES.answers as unknown as Record<string, Entry>)[name];

function show(question: string, response: DiscoverChatResponse) {
  return render(
    <InsightReport
      state={{ question, status: "done", response }}
      onDismiss={() => {}}
      onRouteToAsk={() => {}}
    />
  );
}

/** The report's text without the two additions that are not about the
 *  answer: the "point at any number" hint and the Copy button. */
function answerText(container: HTMLElement): string {
  const copy = container.cloneNode(true) as HTMLElement;
  copy.querySelectorAll("[data-report-chrome]").forEach((n) => n.remove());
  return copy.textContent ?? "";
}

/** Everything a reader or a screen reader gets: text plus accessible names. */
function everything(container: HTMLElement): string {
  const labels = [...container.querySelectorAll("[aria-label]")].map(
    (n) => n.getAttribute("aria-label") ?? ""
  );
  return [container.textContent ?? "", ...labels].join("\n");
}

/** Every string in a layout an officer reads (not ids, urls, kinds, roles). */
function layoutStrings(layout: DiscoverLayout): string[] {
  const out: string[] = [];
  const add = (...values: Array<string | null | undefined>) =>
    values.forEach((v) => v && out.push(v));
  for (const card of layout.cards ?? []) {
    if (card.kind === "total") add(card.value, card.label, card.scope);
    else add(card.text, card.scope);
  }
  for (const w of layout.warnings ?? [])
    add(w.rows, w.missing, w.measure, w.share, w.amount, w.scope);
  for (const panel of (layout.panels ?? []) as LayoutPanel[]) {
    add(panel.by, panel.scope);
    if (panel.kind === "compare") {
      add(...panel.members);
      for (const row of panel.rows) {
        add(row.label, row.total, row.direction);
        for (const part of row.parts) add(part.member, part.share, part.value);
      }
    } else {
      add(panel.label, panel.total, panel.direction);
      for (const bar of panel.bars) add(bar.member, bar.share, bar.value);
    }
  }
  return out;
}

const NUMERAL = /\d{4}-\d{2,4}|\d+(?:[.,]\d+)*/g;
const numerals = (text: string) => text.match(NUMERAL) ?? [];
const squash = (text: string) => text.replace(/\s+/g, " ");

afterEach(() => {
  vi.useRealTimers();
});

describe("the fixtures are what T1 saved", () => {
  it("has the layouts the report describes", () => {
    const kinds = (name: string) =>
      ((entry(name).response.layout as DiscoverLayout).panels ?? []).map(
        (p) => p.kind
      );
    expect((entry("cuttack").response.layout as DiscoverLayout).warnings).toHaveLength(1);
    expect(kinds("cuttack").length).toBeGreaterThan(0);
    expect(entry("kalimela").response.answer_html).toBe("");
    expect(kinds("kalimela").length).toBeGreaterThan(0);
    expect(entry("out_of_scope").response.layout).toEqual({});
  });
});

describe("1. no usable layout renders exactly as before", () => {
  it.each(ENTRIES)("%s, layout removed", (name, { question, response }) => {
    const { container } = show(question, { ...response, layout: undefined });
    expect(answerText(container)).toBe(BASE[name]);
  });

  it.each(ENTRIES)("%s, layout version 2", (name, { question, response }) => {
    const layout = response.layout as DiscoverLayout;
    const { container } = show(question, {
      ...response,
      layout: { ...layout, version: 2 },
    });
    expect(answerText(container)).toBe(BASE[name]);
  });
});

describe("2. every layout string is on screen, and no other figure", () => {
  it.each(ENTRIES)("%s", (_name, { question, response }) => {
    const { container } = show(question, response);
    const seen = squash(everything(container));
    const layout = response.layout as DiscoverLayout;
    for (const text of layoutStrings(layout)) {
      expect(seen).toContain(squash(text));
    }

    const allowed = new Set<string>([
      ...numerals(response.answer),
      ...numerals(question),
      ...layoutStrings(layout).flatMap(numerals),
      ...((layout.panels ?? []) as LayoutPanel[]).flatMap((p) =>
        p.kind === "compare" ? [] : [String(p.shown), String(p.of)]
      ),
    ]);
    const stray = numerals(everything(container)).filter((n) => !allowed.has(n));
    expect(stray).toEqual([]);
  });

  it("draws the cards, the warning card, the charts and the box for Cuttack", () => {
    const { question, response } = entry("cuttack");
    const layout = response.layout as DiscoverLayout;
    const { container } = show(question, response);
    const cards = container.querySelector('[data-report-part="cards"]')!;
    // The cards, then the first warning repeated as a last, tinted card.
    expect(cards.children).toHaveLength((layout.cards ?? []).length + 1);
    expect(cards.textContent).toContain("Rows needing a check");
    expect(container.querySelectorAll("figure")).toHaveLength(
      (layout.panels ?? []).length
    );
    expect(screen.getByRole("region", { name: "Needs checking" })).toBeTruthy();
    // Every item links to its own record, without the citations map.
    const links = [...container.querySelectorAll("a[href*='/record/']")].map(
      (a) => a.getAttribute("href")
    );
    for (const card of layout.cards ?? []) {
      expect(links.some((href) => href?.includes(card.url))).toBe(true);
    }
  });

  it("gives every bar and part an accessible name with member, value and share", () => {
    const { question, response } = entry("cuttack");
    const { container } = show(question, response);
    const named = [...container.querySelectorAll("figure [role='img']")];
    expect(named.length).toBeGreaterThan(0);
    for (const node of named) {
      expect(node.getAttribute("aria-label")).toMatch(/^.+: .+, \d+(\.\d)?% of .+$/);
    }
  });
});

describe("3. each chart sits under the first paragraph citing its records", () => {
  const cited = ENTRIES.filter(([, e]) => e.response.answer_html);

  it.each(cited)("%s", (_name, { question, response }) => {
    const { container } = show(question, response);
    const prose = container.querySelector('[data-report-part="prose"]')!;
    const children = [...prose.children];
    const groups = children.filter((c) => c.matches('[data-report-part="panels"]'));
    const blocks = children.filter((c) => !c.matches('[data-report-part="panels"]'));
    const ids = (el: Element) =>
      new Set(
        [...el.querySelectorAll("[data-finding-id]")].map((b) =>
          b.getAttribute("data-finding-id")
        )
      );
    for (const group of groups) {
      for (const figure of group.querySelectorAll("figure")) {
        const panelIds = (figure.getAttribute("data-panel-ids") ?? "").split(" ");
        const first = blocks.findIndex((b) =>
          panelIds.some((id) => ids(b).has(id))
        );
        const before = children.slice(0, children.indexOf(group)).filter(
          (c) => !c.matches('[data-report-part="panels"]')
        );
        if (first === -1) {
          expect(before.length).toBe(blocks.length); // after the last block
        } else {
          expect(before[before.length - 1]).toBe(blocks[first]);
        }
      }
    }
  });

  it("puts every chart after the last block on the bare-sentence fallback", () => {
    const { question, response } = entry("kalimela");
    const { container } = show(question, response);
    const prose = container.querySelector('[data-report-part="prose"]')!;
    const last = prose.lastElementChild!;
    expect(last.matches('[data-report-part="panels"]')).toBe(true);
    expect(last.querySelectorAll("figure")).toHaveLength(
      ((response.layout as DiscoverLayout).panels ?? []).length
    );
    expect(prose.querySelectorAll('[data-report-part="panels"]')).toHaveLength(1);
  });
});

describe("4. an unknown panel kind is skipped", () => {
  it("draws the rest", () => {
    const { question, response } = entry("cuttack");
    const layout = response.layout as DiscoverLayout;
    const { container } = show(question, {
      ...response,
      layout: {
        ...layout,
        panels: [{ kind: "sankey", ids: ["d1-14417"] }, ...(layout.panels ?? [])],
      },
    });
    expect(container.querySelectorAll("figure")).toHaveLength(
      (layout.panels ?? []).length
    );
    expect(container.textContent).toContain(question);
  });
});

describe("5. Copy", () => {
  it("puts the question and the answer on the clipboard, then reads Copied", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
    const { question, response } = entry("cuttack");
    show(question, response);

    const button = screen.getByRole("button", { name: "Copy" });
    await act(async () => {
      fireEvent.click(button);
    });
    expect(writeText).toHaveBeenCalledWith(`${question}\n\n${response.answer}`);
    expect(button.textContent).toBe("Copied");

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(button.textContent).toBe("Copy");
  });
});

describe("the source underline and its hint", () => {
  it("shows the hint only when figures are bound", () => {
    const cuttack = show(entry("cuttack").question, entry("cuttack").response);
    expect(cuttack.container.textContent).toContain("any number to see its source");
    cuttack.unmount();
    const kalimela = show(entry("kalimela").question, entry("kalimela").response);
    expect(kalimela.container.textContent).not.toContain("any number to see its source");
  });

  it("hides the underline at rest only where the device can hover", () => {
    const { container } = show(entry("cuttack").question, entry("cuttack").response);
    const figure = container.querySelector("button[data-finding-id]")!;
    expect(figure.className).toContain("border-dotted");
    expect(figure.className).toContain("[@media(hover:hover)]:border-transparent");
    expect(figure.className).toContain("hover:border-report-ink");
    expect(figure.className).toContain("focus-visible:border-report-ink");
  });
});
