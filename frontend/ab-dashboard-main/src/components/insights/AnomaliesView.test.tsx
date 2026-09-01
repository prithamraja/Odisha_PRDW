import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AnomaliesView } from "./AnomaliesView";
import * as discoverApi from "@/services/discover-api";
import type { DiscoverChatResponse } from "@/services/discover-api";

vi.mock("@/services/discover-api", async () => {
  const actual = await vi.importActual<typeof import("@/services/discover-api")>(
    "@/services/discover-api"
  );
  return { ...actual, askDiscover: vi.fn() };
});

const PLACEHOLDER = "Ask a question to generate an insight report";
const STAMP = "mined from the 2026-08-30 analysis run";

function response(overrides: Partial<DiscoverChatResponse> = {}): DiscoverChatResponse {
  return {
    answer: `A finding sentence.\n   (12 GPs, 2024-25)\n\n(${STAMP})`,
    move: "retrieve",
    session_id: "d1",
    turn_id: "t1",
    findings: [],
    routing: {},
    retrieval: {},
    prose: {},
    stamp: STAMP,
    ...overrides,
  };
}

function ask(question: string) {
  fireEvent.change(screen.getByPlaceholderText(PLACEHOLDER), {
    target: { value: question },
  });
  fireEvent.click(screen.getByRole("button", { name: /Generate/ }));
}

beforeEach(() => {
  vi.mocked(discoverApi.askDiscover).mockReset();
  sessionStorage.clear();
});

// Each case mounts the whole 32-row feed as well as the report card, which
// runs close to vitest's 5s default in jsdom. The feed size is the point, so
// the budget is raised rather than the render trimmed.
describe("AnomaliesView question box", { timeout: 20000 }, () => {
  it("replaces the category chips, which are gone", () => {
    render(<AnomaliesView />);

    expect(screen.getByPlaceholderText(PLACEHOLDER)).toBeInTheDocument();
    expect(screen.queryByText("Insight Categories")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("group", { name: "Filter insights by category" })
    ).not.toBeInTheDocument();
  });

  // The chips went, the sections did not: the feed is still interleaved by
  // them so no one section monopolises the top of the list.
  it("still shows the whole feed under the question box", () => {
    render(<AnomaliesView />);
    expect(screen.getAllByRole("button", { expanded: false }).length).toBeGreaterThan(1);
  });

  it("renders the finding and its coverage, with the run stamp", async () => {
    vi.mocked(discoverApi.askDiscover).mockResolvedValueOnce(response());
    render(<AnomaliesView />);

    ask("Where does spending diverge most?");

    await screen.findByText("A finding sentence.");
    expect(screen.getByText("12 GPs, 2024-25")).toBeInTheDocument();
    expect(screen.getByText(STAMP)).toBeInTheDocument();
    // The question is echoed back so the report says what it answers.
    expect(
      screen.getByText("Where does spending diverge most?")
    ).toBeInTheDocument();
  });

  it("passes one session id, so a follow-up has an anchor", async () => {
    vi.mocked(discoverApi.askDiscover).mockResolvedValue(response());
    render(<AnomaliesView />);

    ask("first question");
    await screen.findByText("A finding sentence.");
    ask("second question");
    await waitFor(() =>
      expect(discoverApi.askDiscover).toHaveBeenCalledTimes(2)
    );

    const calls = vi.mocked(discoverApi.askDiscover).mock.calls;
    expect(calls[0][1]?.session_id).toBeTruthy();
    expect(calls[1][1]?.session_id).toBe(calls[0][1]?.session_id);
  });

  // D42 ruling 1: a records question is declined, never proxied. The handover
  // is the frontend's, and it must carry the officer's own words.
  it("offers the handover to Ask on a declined lookup", async () => {
    const onRouteToAsk = vi.fn();
    vi.mocked(discoverApi.askDiscover).mockResolvedValueOnce(
      response({
        move: "lookup",
        answer: `That is a question about the records themselves.\n\n(${STAMP})`,
      })
    );
    render(<AnomaliesView onRouteToAsk={onRouteToAsk} />);

    ask("How much did Khordha spend in 2024-25?");

    const handover = await screen.findByRole("button", {
      name: /Put this question to Ask/,
    });
    fireEvent.click(handover);
    expect(onRouteToAsk).toHaveBeenCalledWith(
      "How much did Khordha spend in 2024-25?"
    );
  });

  it("does not offer the handover on an ordinary report", async () => {
    vi.mocked(discoverApi.askDiscover).mockResolvedValueOnce(response());
    render(<AnomaliesView onRouteToAsk={vi.fn()} />);

    ask("Which blocks stand out?");
    await screen.findByText("A finding sentence.");
    expect(
      screen.queryByRole("button", { name: /Put this question to Ask/ })
    ).not.toBeInTheDocument();
  });

  it("says the report failed rather than showing an empty card", async () => {
    vi.mocked(discoverApi.askDiscover).mockRejectedValueOnce(
      new Error("Server error: 503")
    );
    render(<AnomaliesView />);

    ask("Which blocks stand out?");

    expect(await screen.findByText(/could not be generated/)).toBeInTheDocument();
    expect(screen.getByText("Server error: 503")).toBeInTheDocument();
  });

  // Dismissing during a slow turn must not let the answer reopen the card.
  it("does not reopen a dismissed report when its answer lands", async () => {
    let resolve!: (r: DiscoverChatResponse) => void;
    vi.mocked(discoverApi.askDiscover).mockReturnValueOnce(
      new Promise<DiscoverChatResponse>((r) => {
        resolve = r;
      })
    );
    render(<AnomaliesView />);

    ask("Where does spending diverge most?");
    fireEvent.click(screen.getByRole("button", { name: "Dismiss insight report" }));
    resolve(response());

    await waitFor(() =>
      expect(screen.queryByText("A finding sentence.")).not.toBeInTheDocument()
    );
  });

  it("dismisses the report without touching the feed", async () => {
    vi.mocked(discoverApi.askDiscover).mockResolvedValueOnce(response());
    render(<AnomaliesView />);

    ask("Which blocks stand out?");
    await screen.findByText("A finding sentence.");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss insight report" }));
    expect(screen.queryByText("A finding sentence.")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(PLACEHOLDER)).toBeInTheDocument();
  });
});
