import { Fragment } from "react";
import { AlertTriangle, ArrowRight, Loader2, X } from "lucide-react";

import {
  parseCitedAnswer,
  usedFallbackSelection,
  type CitedBlock,
} from "@/lib/discover-answer";
import { placePanels, usableLayout } from "@/lib/discover-answer-layout";
import type { DiscoverChatResponse } from "@/services/discover-api";
import { CitationProvider, CitationSpan } from "./CitationSpan";
import { ReportCards } from "./ReportCards";
import { ReportFooter } from "./ReportFooter";
import { ReportPanelGroup } from "./ReportPanel";
import { ReportWarnings } from "./ReportWarnings";
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

/**
 * A block's text, with the bound figures made hoverable.
 *
 * `**bold**` is still the report's own marker, so an unbound segment goes
 * through `RichText` exactly as before. A bound segment is a figure the
 * service cited and never carries a marker, so it does not.
 */
function BlockText({ block }: { block: CitedBlock }) {
  return (
    <>
      {block.segments.map((segment, i) =>
        segment.citation ? (
          <CitationSpan key={i} citation={segment.citation}>
            {segment.text}
          </CitationSpan>
        ) : (
          <RichText key={i} text={segment.text} />
        )
      )}
    </>
  );
}

function Block({ block }: { block: CitedBlock }) {
  if (block.kind === "finding") {
    return (
      <div data-report-part="finding" className="pl-4 border-l-2 border-report-cyan/40">
        <p className="text-[14px] leading-relaxed text-report-ink">
          <BlockText block={block} />
        </p>
        <p className="mt-1 text-[12px] text-report-ink-muted">{block.coverage}</p>
      </div>
    );
  }
  return (
    <p className="text-[14px] leading-relaxed text-report-ink-soft">
      <BlockText block={block} />
    </p>
  );
}

/**
 * The Insight report (WP-D8 hover-to-source; WP-D12 layout).
 *
 * Order inside the card: header → cards → prose with its charts → the "Needs
 * checking" box → footer. The cards, charts and warnings come whole from the
 * service's `layout` field; without a usable one (absent, `{}`, another
 * version) the report renders exactly as it did before WP-D12. The prose is
 * the service's, untouched: the layout sits AROUND it and changes no word.
 */
export function InsightReport({
  state,
  onDismiss,
  onRouteToAsk,
}: InsightReportProps) {
  const { question, status, response, error } = state;
  const parsed = response
    ? parseCitedAnswer(response.answer, response.answer_html, response.citations)
    : null;
  const caption = response ? MOVE_CAPTIONS[response.move] : undefined;
  const isAskRoute = response?.move === "lookup";
  const fallbackSelection = usedFallbackSelection(response?.retrieval);
  const layout = response ? usableLayout(response.layout) : null;
  const placement =
    layout && parsed ? placePanels(parsed.blocks, layout.panels) : null;

  return (
    <CitationProvider>
      {/* data-report-card: what "Download PDF" prints (WP-D13 Fix 10). */}
      <div
        data-report-card=""
        className="mb-8 border border-report-line bg-white rounded-xl overflow-hidden"
      >
        <div className="flex items-start gap-4 px-6 pt-5 pb-4 border-b border-report-line">
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-report-cyan-deep mb-1.5">
              Insight report
            </div>
            <h2 className="font-display text-[19px] leading-snug text-report-ink">
              {question}
            </h2>
            {caption && (
              <div className="mt-2 text-[12px] text-report-ink-muted">
                {caption}
                {/* The dotted underline shows only on hover or focus where a
                    pointer can hover, so the report has to say the figures
                    are live. Two wordings, one shown per device by CSS. */}
                {status === "done" && parsed?.hasCitations && (
                  <span data-report-chrome="" data-print-hide="">
                    {" · "}
                    <span className="hidden [@media(hover:hover)]:inline">point at</span>
                    <span className="[@media(hover:hover)]:hidden">tap</span>
                    {" any number to see its source"}
                  </span>
                )}
              </div>
            )}
          </div>
          <button
            onClick={onDismiss}
            data-print-hide=""
            aria-label="Dismiss insight report"
            className="shrink-0 w-7 h-7 rounded-md border border-report-line text-report-ink-muted hover:text-report-ink hover:border-report-ink/30 flex items-center justify-center transition-colors"
          >
            <X size={13} />
          </button>
        </div>

        <div className="px-6 py-5">
          {status === "loading" && (
            <div className="flex items-center gap-2.5 text-[13px] text-report-ink-muted">
              <Loader2 size={14} className="animate-spin" />
              Searching the findings this analysis has already mined&hellip;
            </div>
          )}

          {status === "error" && (
            <div className="flex gap-3">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-report-cyan-deep" />
              <div className="min-w-0">
                <p className="text-[14px] text-report-ink">
                  The report could not be generated.
                </p>
                <p className="mt-1 text-[13px] text-report-ink-muted leading-relaxed">
                  {error}
                </p>
              </div>
            </div>
          )}

          {status === "done" && parsed && (
            <>
              {/* The step that picks WHICH findings an answer is built from was
                  unreachable. The prose cannot say so on its own — a narrower
                  answer reads exactly like a real absence of findings — so the
                  tab does, and an infrastructure failure stops looking like a
                  data finding. */}
              {fallbackSelection && (
                <p className="mb-4 text-[12px] leading-relaxed text-report-ink-muted">
                  The selection step was unavailable for this answer; only exact
                  matches are shown.
                </p>
              )}

              {layout && layout.cards.length > 0 && (
                <div className="mb-6">
                  <ReportCards cards={layout.cards} warning={layout.warnings[0]} />
                </div>
              )}

              <div className="space-y-4" data-report-part="prose">
                {parsed.blocks.map((block, i) => (
                  <Fragment key={i}>
                    <Block block={block} />
                    {placement && <ReportPanelGroup panels={placement.byBlock[i]} />}
                  </Fragment>
                ))}
                {placement && <ReportPanelGroup panels={placement.trailing} />}
              </div>

              {layout && layout.warnings.length > 0 && (
                <div className="mt-6">
                  <ReportWarnings warnings={layout.warnings} />
                </div>
              )}

              {isAskRoute && onRouteToAsk && (
                <button
                  onClick={() => onRouteToAsk(question)}
                  data-print-hide=""
                  className="mt-5 inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-report-ink hover:bg-report-ink/90 text-ivory text-[13px] font-medium transition-colors"
                >
                  Put this question to Ask
                  <ArrowRight size={13} strokeWidth={2.25} />
                </button>
              )}

              <ReportFooter stamp={parsed.stamp} question={question} />
            </>
          )}
        </div>
      </div>
    </CitationProvider>
  );
}
