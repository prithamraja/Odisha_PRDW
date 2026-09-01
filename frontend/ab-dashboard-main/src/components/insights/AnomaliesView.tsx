import { useCallback, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, FileSearch, Info } from "lucide-react";

import {
  interleaveBySection,
  parseReport,
  rawReport,
  splitBold,
  type Insight,
  type ReportSection,
} from "@/lib/insights-report";
import { askDiscover } from "@/services/discover-api";
import { InsightReport, type ReportState } from "./InsightReport";
import { InsightSearchBar } from "./InsightSearchBar";
import { RichText } from "./RichText";

const ALL = "__all__";

// --- Formatted headline: the report's bold, plus every bare number ---
function FormattedHeadline({ text }: { text: string }) {
  return (
    <span>
      {splitBold(text).map((run, i) => {
        if (run.bold) {
          return (
            <strong key={i} className="font-semibold text-ink">
              {run.text}
            </strong>
          );
        }
        // Bold numbers that look like percentages, counts, or years
        const parts = run.text.split(/(\b\d[\d,.]*%?\b)/g);
        return (
          <span key={i}>
            {parts.map((part, j) =>
              /^\d[\d,.]*%?$/.test(part) ? (
                <span key={j} className="font-semibold text-ink">
                  {part}
                </span>
              ) : (
                <span key={j}>{part}</span>
              )
            )}
          </span>
        );
      })}
    </span>
  );
}

// --- Components ---

function PageHead() {
  return (
    <div className="mb-8 pb-6 border-b border-line">
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent-saffron mb-2">
        Discover
      </div>
      <h1 className="font-display text-[34px] leading-[1.1] tracking-tight text-ink">
        What the data tells us
      </h1>
      <p className="text-sm text-muted-design mt-2 max-w-xl">
        Priority findings across plans, works, funds and expenditure — generated
        from the department datasets rather than asked for.
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="border border-line bg-white rounded-xl px-8 py-12 text-center">
      <div className="w-10 h-10 rounded-lg bg-ivory border border-line flex items-center justify-center mx-auto mb-4">
        <FileSearch size={17} className="text-muted-design" />
      </div>
      <h2 className="font-display text-[20px] text-ink mb-2">No insights generated yet</h2>
      <p className="text-[14px] text-muted-design leading-relaxed max-w-sm mx-auto">
        Discover renders findings produced by the MetaInsights run over the Odisha
        PR&amp;DW datasets. That run has not been completed, so there is nothing to
        show — rather than display another programme&rsquo;s findings.
      </p>
      <p className="text-[13px] text-muted-design/80 leading-relaxed max-w-sm mx-auto mt-4">
        Ask is fully available in the meantime.
      </p>
    </div>
  );
}

function InsightRow({
  insight,
  isOpen,
  onToggle,
}: {
  insight: Insight;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="py-4 group">
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        className="w-full text-left flex items-start gap-3"
      >
        <div className="mt-1 text-muted-design group-hover:text-ink transition-colors">
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[15px] leading-snug text-ink">
            <FormattedHeadline text={insight.leadline} />
          </div>
        </div>
      </button>
      {isOpen && insight.bullets.length > 0 && (
        <div className="ml-7 mt-4 pl-4 border-l-2 border-accent-saffron/40 space-y-2">
          {insight.bullets.map((line, i) => (
            <div key={i} className="flex gap-3 text-[13px] text-ink/80 leading-relaxed">
              <span className="text-muted-design mt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>
                <RichText text={line} />
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * A section's reading note.
 *
 * Methodology, not a finding: the base a rate is quoted against, who is outside
 * it. It gets no chevron, no number and no place in the counts, because a
 * reader who has to open a row to find out what "per farmer" means has already
 * been misled by the rows above it. Pinned under the list it qualifies.
 */
function ReadingNoteCallout({
  note,
  section,
}: {
  note: string;
  /** Named only when several notes are stacked and each needs attributing. */
  section?: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-line bg-white/60 px-4 py-3">
      <Info size={14} className="mt-0.5 shrink-0 text-muted-design" />
      <div className="min-w-0">
        {/* The generator writes the note to follow a "Reading note:" lead-in, so
            the body opens lower-case. The label carries that lead-in. */}
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-design">
          Reading note
          {section && <span className="font-normal normal-case"> — {section}</span>}
        </div>
        <p className="text-[13px] leading-relaxed text-ink/75">
          <RichText text={note} />
        </p>
      </div>
    </div>
  );
}

const DISCOVER_SESSION_KEY = "discoverchat-session-id";

function getOrCreateDiscoverSessionId() {
  const existing = sessionStorage.getItem(DISCOVER_SESSION_KEY);
  if (existing) return existing;
  const sessionId = crypto.randomUUID();
  sessionStorage.setItem(DISCOVER_SESSION_KEY, sessionId);
  return sessionId;
}

interface AnomaliesViewProps {
  /** Hand the question to Ask. Offered when DiscoverChat declines a lookup. */
  onRouteToAsk?: (question: string) => void;
}

export function AnomaliesView({ onRouteToAsk }: AnomaliesViewProps = {}) {
  const [section, setSection] = useState<string>(ALL);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [report, setReport] = useState<ReportState | null>(null);
  const [sessionId] = useState(getOrCreateDiscoverSessionId);
  // Which request the card is currently showing. A turn can take a judge round
  // trip, and dismissing the card during one must not let the answer reopen it.
  const inFlight = useRef(0);

  // The card appears the moment the question is asked rather than when the
  // answer lands — a slow turn must still be visibly in flight, or the officer
  // asks it again.
  const handleSearch = useCallback(
    async (question: string) => {
      const request = ++inFlight.current;
      setReport({ question, status: "loading" });
      try {
        const response = await askDiscover(question, { session_id: sessionId });
        if (inFlight.current !== request) return;
        setReport({ question, status: "done", response });
      } catch (err) {
        if (inFlight.current !== request) return;
        setReport({
          question,
          status: "error",
          error:
            err instanceof Error
              ? err.message
              : "Something went wrong. Please try again.",
        });
      }
    },
    [sessionId]
  );

  const handleDismiss = useCallback(() => {
    inFlight.current++;
    setReport(null);
  }, []);

  const parsed = useMemo(
    () => (rawReport ? parseReport(rawReport) : { insights: [], sections: [] }),
    []
  );

  // Chips are the report's own sections, in the order they appear in it. The
  // counts are insight counts: a reading note is not a finding, so it does not
  // add to the number on a chip.
  const sectionNames = useMemo(
    () => parsed.sections.map((s) => s.name),
    [parsed]
  );

  const insights = useMemo(() => {
    if (section !== ALL) {
      return parsed.insights.filter((ins) => ins.section === section);
    }
    return interleaveBySection(parsed.insights, sectionNames);
  }, [parsed, sectionNames, section]);

  // In the All view the findings are interleaved across sections, so a note
  // pinned beside any one of them would read as qualifying its neighbours.
  // Every note is shown there instead, each named for the section it governs.
  const notes: ReportSection[] = useMemo(
    () =>
      parsed.sections.filter(
        (s) => s.readingNote !== null && (section === ALL || s.name === section)
      ),
    [parsed, section]
  );

  const chips = useMemo(
    () => [
      { key: ALL, label: "All", count: parsed.insights.length },
      ...parsed.sections.map((s) => ({
        key: s.name,
        label: s.name,
        count: s.insights.length,
      })),
    ],
    [parsed]
  );

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin bg-ivory">
      <div className="max-w-[860px] mx-auto px-10 py-10">
        <PageHead />

        {/* The question box. It runs DiscoverChat over the same mined findings
            the feed below is drawn from, so it sits above the feed's own
            filters rather than in a tab of its own — and it is offered even
            when no report has been dropped in, because the two are separate
            sources and an empty feed does not mean an empty corpus. */}
        <InsightSearchBar
          onSearch={handleSearch}
          isLoading={report?.status === "loading"}
        />

        {report && (
          <InsightReport
            state={report}
            onDismiss={handleDismiss}
            onRouteToAsk={onRouteToAsk}
          />
        )}

        {parsed.insights.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            {/* Section chips — derived from the report, not hardcoded. The
                section names are long sentences, so listing them all at once
                cost five stacked rows before the first finding. They now sit in
                a two-row grid that flows into columns and scrolls sideways,
                which keeps the feed itself above the fold. */}
            {sectionNames.length > 1 && (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-design">
                    Insight Categories
                  </span>
                  <div className="flex-1 h-px bg-line" />
                </div>
                <div
                  className="grid grid-rows-2 grid-flow-col auto-cols-max gap-1.5 overflow-x-auto scrollbar-thin pb-2"
                  role="group"
                  aria-label="Filter insights by category"
                >
                  {chips.map((chip) => {
                    const active = section === chip.key;
                    return (
                      <button
                        key={chip.key}
                        onClick={() => {
                          setSection(chip.key);
                          setExpanded(null);
                        }}
                        aria-pressed={active}
                        className={`px-3 py-1.5 rounded-full text-[13px] transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                          active
                            ? "bg-ink text-ivory"
                            : "bg-white border border-line text-ink hover:border-ink/30"
                        }`}
                      >
                        {chip.label}
                        <span className={active ? "text-ivory/60" : "text-muted-design"}>
                          {chip.count}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Insights list */}
            <div className="divide-y divide-line border-y border-line">
              {insights.map((insight, i) => (
                <InsightRow
                  key={`${section}-${i}`}
                  insight={insight}
                  isOpen={expanded === i}
                  onToggle={() => setExpanded(expanded === i ? null : i)}
                />
              ))}
            </div>

            {/* Reading notes — pinned under the findings they qualify, outside
                the list so they take no row and no number. */}
            {notes.length > 0 && (
              <div className="mt-6 space-y-2">
                {notes.map((s) => (
                  <ReadingNoteCallout
                    key={s.name}
                    note={s.readingNote!}
                    section={notes.length > 1 ? s.name : undefined}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
