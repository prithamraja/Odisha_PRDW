import { AlertTriangle } from "lucide-react";

import type {
  LayoutCard,
  LayoutPatternCard,
  LayoutTotalCard,
  LayoutWarning,
} from "@/services/discover-api";
import { ReportRecordLink } from "./ReportRecordLink";

/**
 * The insight cards at the top of the report (WP-D12).
 *
 * Up to three, chosen and formatted by the service (`DiscoverChat/layout.py`):
 * the judge's findings in the service's own order, one card per measure. The
 * FIRST "Needs checking" warning is repeated as a last, tinted card so the
 * biggest records problem is seen before the prose, not only after it.
 *
 * The row wraps and stacks on a phone: every card has a 170px floor and grows.
 */
export function ReportCards({
  cards,
  warning,
}: {
  cards: LayoutCard[];
  warning?: LayoutWarning;
}) {
  if (!cards.length) return null;
  return (
    <div className="flex flex-wrap gap-3" data-report-part="cards">
      {cards.map((card) =>
        card.kind === "total" ? (
          <TotalCard key={card.id} card={card} />
        ) : (
          <PatternCard key={card.id} card={card} />
        )
      )}
      {warning && <WarningCard warning={warning} />}
    </div>
  );
}

const CARD =
  "min-w-0 rounded-[10px] border px-4 py-3.5 flex flex-col";

function TotalCard({ card }: { card: LayoutTotalCard }) {
  return (
    <div className={`${CARD} flex-[1_1_170px] border-report-line bg-white`}>
      <div className="text-[12px] text-report-ink-muted first-letter:uppercase">
        {card.label}
      </div>
      <div className="mt-1 text-[28px] font-semibold leading-[1.15] text-report-ink break-words">
        {card.value}
      </div>
      <div className="mt-1 text-[12px] text-report-ink-muted break-words">
        {card.scope}
      </div>
      <ReportRecordLink url={card.url} about={card.label} className="mt-2 self-start" />
    </div>
  );
}

function PatternCard({ card }: { card: LayoutPatternCard }) {
  return (
    <div className={`${CARD} flex-[2_1_240px] border-report-line bg-white`}>
      <p className="text-[14px] leading-relaxed text-report-ink-soft">
        {card.text}
      </p>
      <div className="mt-1.5 text-[12px] text-report-ink-muted break-words">
        {card.scope}
      </div>
      <ReportRecordLink url={card.url} about="this pattern" className="mt-2 self-start" />
    </div>
  );
}

function WarningCard({ warning }: { warning: LayoutWarning }) {
  return (
    <div
      className={`${CARD} flex-[1_1_170px] border-report-cyan-edge bg-report-cyan-wash`}
    >
      <div className="flex items-center gap-1.5 text-[12px] text-report-cyan-deep">
        <AlertTriangle size={13} aria-hidden="true" />
        Rows needing a check
      </div>
      <div className="mt-1 text-[28px] font-semibold leading-[1.15] text-report-ink">
        {warning.rows}
      </div>
      <div className="mt-1 text-[12px] text-report-cyan-deep">
        no {warning.missing} recorded
      </div>
      <ReportRecordLink
        url={warning.url}
        about={`the rows with no ${warning.missing}`}
        className="mt-2 self-start"
      />
    </div>
  );
}
