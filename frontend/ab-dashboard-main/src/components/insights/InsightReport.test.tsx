import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import { InsightReport, type ReportState } from "./InsightReport";
import { configureDiscoverApi, type DiscoverChatResponse } from "@/services/discover-api";

const STAMP = "as of 2026-08-17";

/**
 * A two-sentence answer with one bound figure, in exactly the shape
 * `DiscoverChat/render.py` emits — the `dc-cite` span, its `data-finding-id`,
 * and the `↗` anchor it always appends.
 */
const ANSWER =
  "Kalimela recorded the highest number of completed activities in 4 of 6 " +
  `fiscal years.\n\n(${STAMP})`;

const ANSWER_HTML =
  '<div class="dc-answer">\n  <p>Kalimela recorded the highest number of ' +
  'completed activities in <span class="dc-cite" data-finding-id="1-02147" ' +
  'data-record-url="/record/1-02147" title="t">4' +
  '<a class="dc-cite-link" href="/record/1-02147">&#8599;</a></span> of ' +
  '<span class="dc-cite" data-finding-id="1-02147" ' +
  'data-record-url="/record/1-02147" title="t">6' +
  '<a class="dc-cite-link" href="/record/1-02147">&#8599;</a></span> fiscal ' +
  `years.</p>\n  <p class="dc-stamp">(${STAMP})</p>\n</div>`;

const CITATIONS = {
  "1-02147": {
    id: "1-02147",
    sentence: "Across most fiscal_year values (4/6), Kalimela has the highest",
    display_sentence:
      "Across most fiscal years (4/6), Kalimela has the highest activities completed among Gram Panchayats",
    scope: "all records in this table",
    standing: "not in the ranked shortlist",
    view: "Activity Lifecycle",
    is_decomposition: false,
    stamp: STAMP,
    url: "/record/1-02147",
  },
};

function response(overrides: Partial<DiscoverChatResponse> = {}): DiscoverChatResponse {
  return {
    answer: ANSWER,
    move: "retrieve",
    session_id: "d1",
    turn_id: "t1",
    findings: [],
    routing: {},
    retrieval: { judge: { source: "judge" } },
    prose: {},
    stamp: STAMP,
    answer_tagged: "",
    citations: CITATIONS,
    answer_html: ANSWER_HTML,
    ...overrides,
  };
}

function done(overrides: Partial<DiscoverChatResponse> = {}): ReportState {
  return {
    question: "What should I know about Kalimela?",
    status: "done",
    response: response(overrides),
  };
}

const NOTICE = /selection step was unavailable/i;

describe("InsightReport hover-to-source", () => {
  it("makes each bound figure a focusable hover target, and nothing else", () => {
    const { container } = render(
      <InsightReport state={done()} onDismiss={() => {}} />
    );

    // The two numerals the service bound, and no other body text.
    const spans = container.querySelectorAll("button[data-finding-id]");
    expect([...spans].map((s) => s.textContent)).toEqual(["4", "6"]);
    expect([...spans].map((s) => s.getAttribute("data-finding-id"))).toEqual([
      "1-02147",
      "1-02147",
    ]);
  });

  it("keeps the sentence readable with the figures in place", () => {
    const { container } = render(
      <InsightReport state={done()} onDismiss={() => {}} />
    );
    expect(container.textContent).toContain(
      "Kalimela recorded the highest number of completed activities in 4 of 6 fiscal years."
    );
  });

  it("opens the card on hover with the finding's own sentence and a record link", () => {
    configureDiscoverApi({ baseUrl: "http://localhost:8100" });
    render(<InsightReport state={done()} onDismiss={() => {}} />);

    const figure = document.querySelector<HTMLElement>(
      'button[data-finding-id="1-02147"]'
    )!;
    fireEvent.mouseEnter(figure);

    const card = screen.getByRole("tooltip");
    expect(within(card).getByText(/Across most fiscal years \(4\/6\)/)).toBeTruthy();
    expect(within(card).getByText(/all records in this table/)).toBeTruthy();
    expect(within(card).getByText(/not in the ranked shortlist/)).toBeTruthy();
    expect(card.textContent).toContain(STAMP);

    const link = within(card).getByRole("link", { name: /Open record/ });
    // A path from the service is resolved against the DISCOVER base, and the
    // readable view is what an officer should land on.
    expect(link.getAttribute("href")).toBe(
      "http://localhost:8100/record/1-02147?format=html"
    );
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("opens on keyboard focus and closes on Escape", () => {
    render(<InsightReport state={done()} onDismiss={() => {}} />);

    const figure = document.querySelector<HTMLElement>(
      'button[data-finding-id="1-02147"]'
    )!;
    fireEvent.focus(figure);
    expect(screen.getByRole("tooltip")).toBeTruthy();
    expect(figure.getAttribute("aria-expanded")).toBe("true");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).toBeNull();
  });

  it("shows one card at a time", () => {
    render(<InsightReport state={done()} onDismiss={() => {}} />);

    const [first, second] = document.querySelectorAll<HTMLElement>(
      "button[data-finding-id]"
    );
    fireEvent.click(first);
    fireEvent.click(second);

    expect(screen.getAllByRole("tooltip")).toHaveLength(1);
    expect(second.getAttribute("aria-expanded")).toBe("true");
    expect(first.getAttribute("aria-expanded")).toBe("false");
  });

  it("renders plain text when the service sends no markup", () => {
    const { container } = render(
      <InsightReport
        state={done({ answer_html: undefined, citations: undefined })}
        onDismiss={() => {}}
      />
    );

    expect(container.querySelectorAll("button[data-finding-id]")).toHaveLength(0);
    expect(container.textContent).toContain(
      "Kalimela recorded the highest number of completed activities in 4 of 6 fiscal years."
    );
  });
});

describe("InsightReport fallback-selection notice", () => {
  it("appears when the judge was unreachable", () => {
    render(
      <InsightReport
        state={done({ retrieval: { judge: { source: "fallback-threshold" } } })}
        onDismiss={() => {}}
      />
    );
    expect(screen.getByText(NOTICE)).toBeTruthy();
  });

  it("does not appear when the judge ran", () => {
    render(<InsightReport state={done()} onDismiss={() => {}} />);
    expect(screen.queryByText(NOTICE)).toBeNull();
  });

  it("does not appear when the service says nothing about the judge", () => {
    render(
      <InsightReport state={done({ retrieval: {} })} onDismiss={() => {}} />
    );
    expect(screen.queryByText(NOTICE)).toBeNull();
  });

  it("is not shown while the answer is still loading", () => {
    render(
      <InsightReport
        state={{ question: "q", status: "loading" }}
        onDismiss={() => {}}
      />
    );
    expect(screen.queryByText(NOTICE)).toBeNull();
  });
});
