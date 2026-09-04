import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import { recordHref, type DiscoverCitation } from "@/services/discover-api";

/**
 * Hover-to-source: the figure an officer reads, bound to the record it came
 * from (WP-D7 ruling 4, WP-D8).
 *
 * The card is the validation mechanism, not decoration. An officer who cannot
 * see where a number came from has to take the answer on trust, and the whole
 * point of retrieving stored findings rather than computing new ones is that
 * they never have to. So the hover shows the engine's OWN sentence, the slice
 * of data it covers, where it stands in the analysis, when the run was, and a
 * link to the whole record.
 *
 * It renders through a portal because the report card clips its overflow, and
 * a card that is cut off at the edge of the report is worse than none.
 */

interface OpenState {
  citation: DiscoverCitation;
  /** The span the card belongs to. Identity is the ELEMENT, not the finding
   *  id: one finding is normally bound to several figures in the same answer,
   *  and keying on the id would open — and mark as expanded — all of them. */
  element: HTMLElement;
  anchor: DOMRect;
  /** A click pins the card open; a hover does not. */
  pinned: boolean;
}

interface CitationContextValue {
  open: OpenState | null;
  show: (
    citation: DiscoverCitation,
    element: HTMLElement,
    pinned: boolean
  ) => void;
  hide: () => void;
  /** Hovering the card itself must not let the leave-timer close it. */
  hold: () => void;
  releaseAfterDelay: () => void;
}

const CitationContext = createContext<CitationContextValue | null>(null);

/** How long the card survives the pointer leaving, so it can be moved onto. */
const LEAVE_DELAY_MS = 160;

export function CitationProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState<OpenState | null>(null);
  const timer = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const show = useCallback(
    (citation: DiscoverCitation, element: HTMLElement, pinned: boolean) => {
      clearTimer();
      // One card at a time: showing a new one replaces whatever was open,
      // including a pinned card, so a reader never has two overlapping.
      setOpen({
        citation,
        element,
        anchor: element.getBoundingClientRect(),
        pinned,
      });
    },
    [clearTimer]
  );

  const hide = useCallback(() => {
    clearTimer();
    setOpen(null);
  }, [clearTimer]);

  const hold = useCallback(() => clearTimer(), [clearTimer]);

  const releaseAfterDelay = useCallback(() => {
    clearTimer();
    timer.current = window.setTimeout(() => setOpen(null), LEAVE_DELAY_MS);
  }, [clearTimer]);

  useEffect(() => clearTimer, [clearTimer]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") hide();
    };
    // The card is anchored to a rect taken when it opened, so it has to go
    // when the page moves under it rather than float somewhere wrong.
    const onScroll = () => hide();
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open, hide]);

  const value = useMemo(
    () => ({ open, show, hide, hold, releaseAfterDelay }),
    [open, show, hide, hold, releaseAfterDelay]
  );

  return (
    <CitationContext.Provider value={value}>
      {children}
      <CitationCard />
    </CitationContext.Provider>
  );
}

const CARD_WIDTH = 340;
const GAP = 8;

function CitationCard() {
  const ctx = useContext(CitationContext);
  if (!ctx?.open) return null;
  const { citation, anchor } = ctx.open;

  // Clamped to the viewport so a span near the right edge does not push the
  // card off screen, and flipped above the line when there is no room below.
  const left = Math.min(
    Math.max(GAP, anchor.left),
    Math.max(GAP, window.innerWidth - CARD_WIDTH - GAP)
  );
  const below = anchor.bottom + GAP;
  const flip = below + 200 > window.innerHeight && anchor.top > 220;
  const style: React.CSSProperties = {
    position: "fixed",
    left,
    width: CARD_WIDTH,
    zIndex: 60,
    ...(flip ? { bottom: window.innerHeight - anchor.top + GAP } : { top: below }),
  };

  return createPortal(
    <div
      role="tooltip"
      id="discover-citation-card"
      style={style}
      onMouseEnter={ctx.hold}
      onMouseLeave={ctx.releaseAfterDelay}
      className="border border-line bg-white rounded-xl shadow-lg px-4 py-3.5"
    >
      <p className="text-[13px] leading-relaxed text-ink">
        {citation.display_sentence}
      </p>

      {citation.scope && (
        <p className="mt-2 text-[12px] leading-relaxed text-muted-design">
          <span className="text-ink/70">Covers:</span> {citation.scope}
        </p>
      )}

      {citation.standing && (
        <p className="mt-1 text-[12px] leading-relaxed text-muted-design">
          {citation.standing}
        </p>
      )}

      <div className="mt-3 pt-2.5 border-t border-line flex items-center justify-between gap-3">
        <span className="text-[11px] text-muted-design">
          {citation.view}
          {citation.view && citation.stamp ? " — " : ""}
          {citation.stamp}
        </span>
        <a
          href={recordHref(citation.url)}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-[12px] font-medium text-ink underline underline-offset-2 hover:text-accent-saffron transition-colors"
        >
          Open record&nbsp;&#8599;
        </a>
      </div>
    </div>,
    document.body
  );
}

/**
 * One bound span.
 *
 * The text wears the text tokens — a bound figure is not a link and must not
 * read as one, or an officer starts reading the colour as meaning. The dotted
 * underline is the whole affordance.
 */
export function CitationSpan({
  citation,
  children,
}: {
  citation: DiscoverCitation;
  children: ReactNode;
}) {
  const ctx = useContext(CitationContext);
  const ref = useRef<HTMLButtonElement>(null);
  const isOpen = !!ctx?.open && ctx.open.element === ref.current;

  if (!ctx) return <>{children}</>;

  const open = (pinned: boolean) => {
    if (ref.current) ctx.show(citation, ref.current, pinned);
  };

  return (
    <button
      ref={ref}
      type="button"
      // The same attribute the service's own render puts on a bound span, so
      // what the frontend bound can be read straight off the DOM and compared
      // with `answer_html` without a debugger.
      data-finding-id={citation.id}
      aria-expanded={isOpen}
      aria-describedby={isOpen ? "discover-citation-card" : undefined}
      onMouseEnter={() => open(false)}
      onMouseLeave={() => {
        if (!ctx.open?.pinned) ctx.releaseAfterDelay();
      }}
      onFocus={() => open(true)}
      onBlur={() => ctx.releaseAfterDelay()}
      onClick={() => {
        if (isOpen && ctx.open?.pinned) ctx.hide();
        else open(true);
      }}
      className="inline cursor-help bg-transparent p-0 m-0 text-left font-inherit text-inherit leading-inherit border-0 border-b border-dotted border-ink/50 hover:border-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-saffron/60 rounded-[2px]"
    >
      {children}
    </button>
  );
}
