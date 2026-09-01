import { AlertTriangle, ArrowRight, Loader2, X } from "lucide-react";

import { parseAnswer, type AnswerBlock } from "@/lib/discover-answer";
import type { DiscoverChatResponse } from "@/services/discover-api";
import { RichText } from "./RichText";

export interface ReportState {
  question: string;
  status: "loading" | "done" | "error";
  response?: DiscoverChatResponse;
  error?: string;
}

interface InsightReportProps {
  state: ReportState;
  onDismiss: () => void;
  /** Send the question to Ask instead. Offered only on the decline. */
  onRouteToAsk?: (question: string) => void;
}

/**
 * How the answer was arrived at, said plainly.
 *
 * The service's own move names are internal vocabulary — an officer reading
 * "lookup" learns nothing — so each is captioned. The caption is shown, not the
 * move, but the move is what drives the branch, so a move the frontend has not
 * seen before still renders rather than blanking the card.
 */
const MOVE_CAPTIONS: Record<string, string> = {
  retrieve: "From the findings already mined",
  navigate: "Following on from what is on screen",
  decompose: "A breakdown of the recorded totals",
  lookup: "This one is for Ask",
  why: "Scope note",
};

function Block({ block }: { block: AnswerBlock }) {
  if (block.kind === "finding") {
    return (
      <div className="pl-4 border-l-2 border-accent-saffron/40">
        <p className="text-[14px] leading-relaxed text-ink">
          <RichText text={block.text} />
        </p>
        <p className="mt-1 text-[12px] text-muted-design">{block.coverage}</p>
      </div>
    );
  }
  return (
    <p className="text-[14px] leading-relaxed text-ink/80">
      <RichText text={block.text} />
    </p>
  );
}

export function InsightReport({
  state,
  onDismiss,
  onRouteToAsk,
}: InsightReportProps) {
  const { question, status, response, error } = state;
  const parsed = response ? parseAnswer(response.answer) : null;
  const caption = response ? MOVE_CAPTIONS[response.move] : undefined;
  const isAskRoute = response?.move === "lookup";

  return (
    <div className="mb-8 border border-line bg-white rounded-xl overflow-hidden">
      <div className="flex items-start gap-4 px-6 pt-5 pb-4 border-b border-line">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent-saffron mb-1.5">
            Insight report
          </div>
          <h2 className="font-display text-[19px] leading-snug text-ink">
            {question}
          </h2>
          {caption && (
            <div className="mt-2 text-[12px] text-muted-design">{caption}</div>
          )}
        </div>
        <button
          onClick={onDismiss}
          aria-label="Dismiss insight report"
          className="shrink-0 w-7 h-7 rounded-md border border-line text-muted-design hover:text-ink hover:border-ink/30 flex items-center justify-center transition-colors"
        >
          <X size={13} />
        </button>
      </div>

      <div className="px-6 py-5">
        {status === "loading" && (
          <div className="flex items-center gap-2.5 text-[13px] text-muted-design">
            <Loader2 size={14} className="animate-spin" />
            Searching the findings this analysis has already mined&hellip;
          </div>
        )}

        {status === "error" && (
          <div className="flex gap-3">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-accent-saffron" />
            <div className="min-w-0">
              <p className="text-[14px] text-ink">
                The report could not be generated.
              </p>
              <p className="mt-1 text-[13px] text-muted-design leading-relaxed">
                {error}
              </p>
            </div>
          </div>
        )}

        {status === "done" && parsed && (
          <>
            <div className="space-y-4">
              {parsed.blocks.map((block, i) => (
                <Block key={i} block={block} />
              ))}
            </div>

            {isAskRoute && onRouteToAsk && (
              <button
                onClick={() => onRouteToAsk(question)}
                className="mt-5 inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-ink hover:bg-ink/90 text-ivory text-[13px] font-medium transition-colors"
              >
                Put this question to Ask
                <ArrowRight size={13} strokeWidth={2.25} />
              </button>
            )}

            {/* The corpus is a snapshot of one mining run. An answer that did
                not say when it was mined would invite a stale pattern to be
                read as today's, which is why the service stamps every one. */}
            {parsed.stamp && (
              <p className="mt-5 pt-4 border-t border-line text-[12px] text-muted-design">
                {parsed.stamp}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
