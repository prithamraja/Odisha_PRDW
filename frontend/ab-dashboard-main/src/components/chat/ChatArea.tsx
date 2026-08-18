import { useRef, useEffect, useState } from "react";
import type { ContextFrame, Message } from "@/types/chat";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { ChatInput } from "./ChatInput";
import { ContextHistory } from "./ContextHistory";
import { Shield, Search, Send, ArrowUpRight } from "lucide-react";

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  onSend: (message: string, fromChip?: boolean, resetContext?: boolean) => void;
  // Re-sends a message that was read as a follow-up, with the context reset.
  onAskAsNewQuestion?: (text: string) => void;
  onDateRangeUpdate?: (messageId: string, startDate: string, endDate: string) => void;
  currentFrame?: ContextFrame | null;
  onContextJumpBack?: (steps: number) => void;
  onContextReset?: () => void;
}

// Every entry below is a WP-4a gold-set question carrying a PASS test status
// against the real drop, so it routes to the template id in the comment and
// returns the row count noted there. They are chosen to span the catalogue
// brackets rather than to sample it evenly, so a walkthrough hits something
// interesting on the first click. Re-fire these with from_chip=true against the
// live backend after any catalogue change.
const landingSuggestions = [
  { category: "PLANNING", q: "Which blocks achieved 100% GPDP submission in 2024-2025?" }, // PLN-006, 16 rows
  { category: "SPEND", q: "What is the total actual expenditure incurred by each GP in 2024-25?" }, // EXP-001, 20 rows
  { category: "FUNDING", q: "How much funding is recorded from each funding source in 2024-25?" }, // BUD-002, 3 rows
  { category: "PROGRESS", q: "What is the completion rate under each theme and focus area in 2024-2025?" }, // IMP-005, 25 rows
  { category: "SANCTIONS", q: "What is the total administratively sanctioned amount for each GP in 2024-25?" }, // SAN-003, 20 rows
  { category: "SANITATION", q: "How many Solid Waste Management activities have been planned in 2024-25?" }, // SBM-SWM-001, 1 row
  { category: "ASSETS", q: "How many assets were created in each GP during 2024-2025?" }, // AST-001, 20 rows
  { category: "TRENDS", q: "Compare the approved cost and expenditure theme-wise between 2023-24 and 2024-25." }, // TRD-002, 7 rows
];

function EmptyAskState({ onPick }: { onPick: (q: string) => void }) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    onPick(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-10 py-16">
      <div className="w-full max-w-[720px]">
        {/* Hero */}
        <div className="text-center mb-10">
          <h1 className="font-display text-[44px] leading-[1.05] tracking-tight text-ink mb-4">
            Ask anything about<br />
            <span className="italic text-muted-design" style={{ fontFamily: "'DM Sans', sans-serif" }}>Odisha panchayat data.</span>
          </h1>
          <p className="text-[15px] text-muted-design leading-relaxed max-w-md mx-auto">
            Get answers, insights, and visual analysis in seconds — across GPDP
            planning, sanctions, fund releases, expenditure, works and sanitation.
          </p>
        </div>

        {/* Hero input */}
        <div className="mb-12">
          <div className="flex items-center gap-2 bg-white border border-line rounded-xl px-5 py-3.5 focus-within:border-ink/40 transition-colors shadow-sm">
            <Search size={15} className="text-muted-design" />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about GPDP, expenditure, sanctions, blocks, districts…"
              className="flex-1 bg-transparent text-[15px] text-ink placeholder:text-muted-design outline-none"
              autoFocus
            />
            <button
              onClick={handleSubmit}
              className="ml-1 w-8 h-8 rounded-lg bg-ink hover:bg-ink/90 flex items-center justify-center transition-colors"
              aria-label="Send message"
            >
              <Send size={13} className="text-ivory" strokeWidth={2.25} />
            </button>
          </div>
        </div>

        {/* Suggestions */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-design">
              Try asking
            </span>
            <div className="flex-1 h-px bg-line" />
          </div>

          <div className="divide-y divide-line border-y border-line">
            {landingSuggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onPick(s.q)}
                className="w-full text-left py-3 px-1 flex items-center gap-4 group hover:bg-white/40 transition-colors"
              >
                <span className="text-[10px] uppercase tracking-[0.1em] text-muted-design w-20 shrink-0">
                  {s.category}
                </span>
                <span className="flex-1 text-[14px] text-ink">
                  {s.q}
                </span>
                <ArrowUpRight
                  size={14}
                  className="text-muted-design opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function ChatArea({
  messages,
  isLoading,
  onSend,
  onAskAsNewQuestion,
  onDateRangeUpdate,
  currentFrame,
  onContextJumpBack,
  onContextReset,
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Landing state — no messages yet
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="h-[calc(100vh-3.5rem)] bg-ivory overflow-y-auto">
        <EmptyAskState onPick={onSend} />
      </div>
    );
  }

  // Active conversation state
  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Context history — collapsed rail on the left, expands on click */}
      {currentFrame && (
        <ContextHistory
          frame={currentFrame}
          disabled={isLoading}
          onJumpBack={onContextJumpBack}
          onReset={onContextReset}
        />
      )}

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header strip */}
        <div className="border-b border-line bg-white px-10 py-5">
          <div className="max-w-[820px] mx-auto">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent-saffron mb-1">
              Ask
            </div>
            <h1 className="font-display text-[22px] tracking-tight text-ink">
              Query Odisha panchayat data in plain English
            </h1>
          </div>
        </div>

        {/* Conversation area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin px-10 py-8 bg-ivory">
          <div className="max-w-[820px] mx-auto space-y-6">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onDateRangeUpdate={onDateRangeUpdate}
                onSend={isLoading ? undefined : onSend}
                // The MARKER stays while a request is in flight; only the
                // control it offers is withdrawn.
                onAskAsNewQuestion={isLoading ? undefined : onAskAsNewQuestion}
              />
            ))}
            {isLoading && <TypingIndicator />}
          </div>
        </div>

        {/* Input bar */}
        <ChatInput onSend={onSend} disabled={isLoading} />
      </div>
    </div>
  );
}
