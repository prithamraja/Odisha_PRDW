import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "@/types/chat";

// The question already on screen, and the one the fragment actually got.
const ANCHOR = "What is the total actual expenditure incurred by each GP in 2024-25?";
const ANSWERED = "What is the total actual expenditure incurred by Khordha in 2024-25?";
const CONTROL = "Ask as a new question instead";

function bound(overrides: Partial<Message> = {}): Message {
  return {
    id: "a1",
    role: "assistant",
    content: ANSWERED,
    timestamp: 0,
    tier: "tier2",
    originalQuery: "in khordha?",
    interpretation: {
      kind: "fragment_reroute",
      anchor_question: ANCHOR,
      anchor_template_id: "EXP-001",
      detail: "district → Khordha",
    },
    ...overrides,
  };
}

describe("the follow-up marker", () => {
  it("stacks the question on screen above the question answered", () => {
    render(<MessageBubble message={bound()} onAskAsNewQuestion={() => {}} />);

    expect(screen.getByText(ANCHOR)).toBeInTheDocument();
    expect(screen.getByText(ANSWERED)).toBeInTheDocument();
    expect(screen.getByText(/read as a follow-up/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: CONTROL })).toBeInTheDocument();
  });

  it("does not print the detail — the two questions already show the difference", () => {
    render(<MessageBubble message={bound()} onAskAsNewQuestion={() => {}} />);
    expect(screen.queryByText(/district → Khordha/)).not.toBeInTheDocument();
  });

  it("re-sends WHAT THE USER TYPED, not the echoed catalogue phrasing", () => {
    const onAskAsNewQuestion = vi.fn();
    render(
      <MessageBubble message={bound()} onAskAsNewQuestion={onAskAsNewQuestion} />
    );

    fireEvent.click(screen.getByRole("button", { name: CONTROL }));

    expect(onAskAsNewQuestion).toHaveBeenCalledWith("in khordha?");
    expect(onAskAsNewQuestion).not.toHaveBeenCalledWith(ANSWERED);
  });

  it("keeps the marker but withdraws the control while a request is in flight", () => {
    render(<MessageBubble message={bound()} />);   // no callback = in flight

    expect(screen.getByText(/read as a follow-up/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: CONTROL })).not.toBeInTheDocument();
  });

  it("draws nothing at all when the answer was routed standalone", () => {
    render(
      <MessageBubble
        message={bound({
          interpretation: { kind: "new_question" },
        })}
        onAskAsNewQuestion={() => {}}
      />
    );

    expect(screen.getByText(ANSWERED)).toBeInTheDocument();
    expect(screen.queryByText(/read as a follow-up/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: CONTROL })).not.toBeInTheDocument();
  });

  it("draws nothing when the backend sends no interpretation at all", () => {
    render(
      <MessageBubble
        message={bound({ interpretation: undefined })}
        onAskAsNewQuestion={() => {}}
      />
    );
    expect(screen.getByText(ANSWERED)).toBeInTheDocument();
    expect(screen.queryByText(/read as a follow-up/)).not.toBeInTheDocument();
  });

  it("draws nothing when a bound kind arrives with nothing to anchor to", () => {
    render(
      <MessageBubble
        message={bound({ interpretation: { kind: "frame_edit" } })}
        onAskAsNewQuestion={() => {}}
      />
    );
    expect(screen.queryByText(/read as a follow-up/)).not.toBeInTheDocument();
  });

  it("leaves the user's own message alone", () => {
    render(
      <MessageBubble
        message={bound({ role: "user", content: "in khordha?" })}
        onAskAsNewQuestion={() => {}}
      />
    );

    expect(screen.getByText("in khordha?")).toBeInTheDocument();
    expect(screen.queryByText(ANCHOR)).not.toBeInTheDocument();
    expect(screen.queryByText(/read as a follow-up/)).not.toBeInTheDocument();
  });
});
