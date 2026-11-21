import {
  recordHref,
  type LayoutBar,
  type LayoutBarsPanel,
  type LayoutComparePanel,
  type LayoutCompareRow,
  type LayoutPanel,
} from "@/services/discover-api";
import { ReportRecordLink } from "./ReportRecordLink";

/**
 * The small charts under the paragraphs that cite them (WP-D12).
 *
 * Plain elements, no chart library, as in the mock-up. Every string is the
 * service's (`DiscoverChat/layout.py`); `fraction` is used for geometry and
 * never printed. Each panel is a <figure> with a <figcaption>, and every bar
 * or part carries an accessible name with its member, value and share.
 */

/** Below this share a compare part is too narrow to print its label in. */
const MIN_LABELLED_PART = 0.15;
/** The longest bar's length, as a share of the track, so the value and share
 *  usually fit at its tip; when they do not, they wrap under the bar. */
const LONGEST_BAR = 0.72;

function directionNote(direction: string | null): string {
  return direction ? ` ${direction}` : "";
}

/** Two or three panels under one paragraph: side by side from 640px, stacked
 *  below; an odd last panel takes the whole row. */
export function ReportPanelGroup({ panels }: { panels: LayoutPanel[] }) {
  if (!panels.length) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-report-part="panels">
      {panels.map((panel, i) => (
        <div
          key={panel.ids.join(" ")}
          className={
            "min-w-0 " +
            (panels.length % 2 === 1 && i === panels.length - 1
              ? "sm:col-span-2"
              : "")
          }
        >
          <ReportPanel panel={panel} />
        </div>
      ))}
    </div>
  );
}

export function ReportPanel({ panel }: { panel: LayoutPanel }) {
  if (panel.kind === "compare") return <ComparePanel panel={panel} />;
  if (panel.kind === "ranked" || panel.kind === "time")
    return <BarsPanel panel={panel} />;
  return null;
}

const FIGURE =
  "m-0 min-w-0 rounded-[10px] border border-report-line bg-white px-[18px] py-4 flex flex-col gap-2.5";

// ---------------------------------------------------------------------------
// compare: one split bar per record, the same two members in every row
// ---------------------------------------------------------------------------

function ComparePanel({ panel }: { panel: LayoutComparePanel }) {
  return (
    <figure className={FIGURE} data-panel-kind="compare" data-panel-ids={panel.ids.join(" ")}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-report-ink-soft">
        <figcaption className="mr-auto min-w-0">
          <span className="font-semibold">Split by {panel.by}</span>
          <span className="block text-report-ink-muted">{panel.scope}</span>
        </figcaption>
        {panel.members.map((member, i) => (
          <div key={member} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={
                "w-2.5 h-2.5 rounded-[3px] " +
                (i === 0 ? "bg-report-cyan" : "bg-report-cyan-light")
              }
            />
            {member}
          </div>
        ))}
      </div>
      {panel.rows.map((row) => (
        <CompareRow key={row.id} row={row} />
      ))}
    </figure>
  );
}

function CompareRow({ row }: { row: LayoutCompareRow }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1.5">
      <div className="basis-full sm:basis-[190px] shrink-0 min-w-0 text-[13px] text-report-ink-soft">
        <a
          href={recordHrefOrNothing(row.url)}
          target="_blank"
          rel="noreferrer"
          className="first-letter:uppercase inline-block hover:underline underline-offset-2"
        >
          {row.label}
        </a>{" "}
        <span className="text-report-ink-muted">({row.total})</span>
      </div>
      <div className="flex-[1_1_12rem] min-w-0 flex gap-0.5 h-7 text-[13px] font-semibold">
        {row.parts.map((part, i) => (
          <div
            key={part.member}
            role="img"
            aria-label={`${part.member}: ${part.value}${directionNote(
              row.direction
            )}, ${part.share} of ${row.label}`}
            style={{ flexGrow: part.fraction, flexBasis: 0 }}
            className={
              "min-w-0 overflow-hidden rounded flex items-center pl-2 " +
              (i === 0
                ? "bg-report-cyan text-white"
                : "bg-report-cyan-light text-report-ink")
            }
          >
            {part.fraction >= MIN_LABELLED_PART ? part.share : null}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ranked / time: one bar per member, growing from a baseline
// ---------------------------------------------------------------------------

function caption(panel: LayoutBarsPanel): string {
  // Nothing to say when every member is drawn, or when none is (the only bar
  // is "Not recorded": every other member holds nothing).
  if (panel.of <= panel.shown || panel.shown === 0) return "";
  return panel.kind === "time"
    ? `the ${panel.shown} largest of ${panel.of}, in time order`
    : `the ${panel.shown} largest of ${panel.of}`;
}

function BarsPanel({ panel }: { panel: LayoutBarsPanel }) {
  const longest = Math.max(0, ...panel.bars.map((b) => b.fraction)) || 1;
  const leftOut = caption(panel);
  return (
    <figure className={FIGURE} data-panel-kind={panel.kind} data-panel-ids={panel.ids.join(" ")}>
      <figcaption className="text-[12px] text-report-ink-soft">
        <span className="block font-semibold first-letter:uppercase">
          {panel.label} by {panel.by}
        </span>
        <span className="block text-report-ink-muted">
          Total {panel.total}
          {panel.direction ? ` · all figures ${panel.direction}` : ""}
          {leftOut ? ` · ${leftOut}` : ""}
        </span>
        <span className="block text-report-ink-muted">{panel.scope}</span>
      </figcaption>
      <div className="flex flex-col gap-2">
        {panel.bars.map((bar) => (
          <BarRow
            key={bar.member}
            bar={bar}
            length={(bar.fraction / longest) * LONGEST_BAR}
            direction={panel.direction}
            measure={panel.label}
          />
        ))}
      </div>
      <ReportRecordLink url={panel.url} about={`this chart of ${panel.label}`} className="self-start" />
    </figure>
  );
}

function BarRow({
  bar,
  length,
  direction,
  measure,
}: {
  bar: LayoutBar;
  length: number;
  direction: string | null;
  measure: string;
}) {
  const grey = bar.role === "not_recorded";
  return (
    <div
      role="img"
      aria-label={`${bar.member}: ${bar.value}${directionNote(direction)}, ${
        bar.share
      } of ${measure}`}
      className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5"
    >
      <div
        className={
          "basis-full sm:basis-[8.5rem] shrink-0 min-w-0 break-words text-[13px] " +
          (grey ? "text-report-ink-muted" : "text-report-ink-soft")
        }
      >
        {bar.member}
      </div>
      <div className="flex-[1_1_10rem] min-w-0 flex flex-wrap items-center gap-x-2 gap-y-0.5 border-l border-report-axis">
        <div
          className={
            "h-4 rounded-r " + (grey ? "bg-report-grey" : "bg-report-cyan")
          }
          style={{
            width: `${(length * 100).toFixed(2)}%`,
            minWidth: bar.fraction > 0 ? 2 : 0,
          }}
        />
        <div className="whitespace-nowrap text-[12px] text-report-ink">
          <span className="font-semibold">{bar.value}</span>
          <span className="text-report-ink-muted"> · {bar.share}</span>
        </div>
      </div>
    </div>
  );
}

/** The same resolver the hover card uses; no link at all without a url. */
function recordHrefOrNothing(url: string): string | undefined {
  return url ? recordHref(url) : undefined;
}
