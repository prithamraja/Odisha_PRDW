import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Index from "./Index";
import * as api from "@/services/api";
import type { ChatResponse } from "@/services/api";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>(
    "@/services/api"
  );
  return { ...actual, sendMessage: vi.fn() };
});

const STATEWIDE = "What is the total actual expenditure incurred by each GP in 2024-25?";
const NARROWED = "What is the total actual expenditure incurred by Khordha in 2024-25?";
const CONTROL = "Ask as a new question instead";

function response(overrides: Partial<ChatResponse>): ChatResponse {
  return {
    session_id: "s1",
    context_frame: null,
    tier: "tier2",
    answer: "",
    result: null,
    query_id: "EXP-001",
    query_description: null,
    intent: null,
    entities: [],
    latency_ms: 1,
    ...overrides,
  };
}

/** Ask the statewide question, then the fragment that gets read as a follow-up. */
async function askThenFollowUp() {
  const sendMessage = vi.mocked(api.sendMessage);
  sendMessage.mockResolvedValueOnce(response({ answer: STATEWIDE }));
  render(<Index />);

  fireEvent.change(screen.getByPlaceholderText(/Ask about GPDP/), {
    target: { value: "how much was spent by each GP in 2024-25?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await screen.findByText(STATEWIDE);

  sendMessage.mockResolvedValueOnce(
    response({
      answer: NARROWED,
      interpretation: {
        kind: "fragment_reroute",
        anchor_question: STATEWIDE,
        anchor_template_id: "EXP-001",
        detail: "district → Khordha",
      },
    })
  );
  // The landing hero is gone once the conversation has messages; this is the
  // composer at the foot of the thread.
  const composer = screen.getByPlaceholderText(/Ask about GPDP/);
  fireEvent.change(composer, { target: { value: "in khordha?" } });
  fireEvent.keyDown(composer, { key: "Enter" });
  await screen.findByText(NARROWED);
  return sendMessage;
}

describe("the escape from a follow-up reading", () => {
  beforeEach(() => {
    vi.mocked(api.sendMessage).mockReset();
    sessionStorage.clear();
  });

  it("re-sends the user's own words with the context reset", async () => {
    const sendMessage = await askThenFollowUp();
    sendMessage.mockResolvedValueOnce(
      response({ answer: "Some entirely different answer." })
    );

    fireEvent.click(screen.getByRole("button", { name: CONTROL }));

    await waitFor(() =>
      expect(sendMessage).toHaveBeenCalledTimes(3)
    );
    const [text, options] = sendMessage.mock.calls[2];
    expect(text).toBe("in khordha?");            // not the echoed phrasing
    expect(options?.reset_context).toBe(true);
    expect(options?.from_chip).toBeFalsy();
  });

  it("appends the correction and leaves the exchange it corrects on screen", async () => {
    const sendMessage = await askThenFollowUp();
    sendMessage.mockResolvedValueOnce(
      response({ answer: "Some entirely different answer." })
    );

    fireEvent.click(screen.getByRole("button", { name: CONTROL }));

    // The follow-up reading it corrects is still there, marker and all — that
    // is what makes the correction auditable.
    await screen.findByText("Some entirely different answer.");
    expect(screen.getByText(NARROWED)).toBeInTheDocument();
    expect(screen.getByText(/read as a follow-up/)).toBeInTheDocument();
    expect(screen.getAllByText("in khordha?").length).toBeGreaterThan(1);
  });

  it("marks nothing when the answer was routed standalone", async () => {
    const sendMessage = vi.mocked(api.sendMessage);
    sendMessage.mockResolvedValueOnce(response({ answer: STATEWIDE }));
    render(<Index />);

    fireEvent.change(screen.getByPlaceholderText(/Ask about GPDP/), {
      target: { value: "how much was spent by each GP in 2024-25?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await screen.findByText(STATEWIDE);
    expect(screen.queryByText(/read as a follow-up/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: CONTROL })).not.toBeInTheDocument();
  });
});
