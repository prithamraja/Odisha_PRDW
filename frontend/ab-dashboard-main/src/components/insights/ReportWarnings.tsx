import { AlertTriangle } from "lucide-react";

import type { LayoutWarning } from "@/services/discover-api";
import { ReportRecordLink } from "./ReportRecordLink";

/**
 * The "Needs checking" box (WP-D12): records whose "not recorded" share is
 * large, one line each, worded from the service's own formatted strings.
 *
 * Labelled in words and marked with an icon — never by its tint alone. The
 * numbering is the list's own marker, not text, so no digit appears on screen
 * that neither the prose nor the layout holds.
 */
export function ReportWarnings({ warnings }: { warnings: LayoutWarning[] }) {
  if (!warnings.length) return null;
  return (
    <section
      aria-labelledby="report-needs-checking"
      data-report-part="warnings"
      className="rounded-[10px] border border-report-cyan-edge bg-report-cyan-wash px-5 py-[18px] flex flex-col gap-3"
    >
      <h3
        id="report-needs-checking"
        className="m-0 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-report-cyan-deep"
      >
        <AlertTriangle size={14} aria-hidden="true" />
        Needs checking
      </h3>
      <ol className="m-0 pl-5 list-decimal marker:font-semibold marker:text-report-ink flex flex-col gap-2.5 text-[14px] leading-relaxed text-report-ink-soft">
        {warnings.map((warning) => (
          <li key={warning.id} className="pl-1">
            <span className="font-semibold text-report-ink">
              {warning.rows} rows have no {warning.missing} on file.
            </span>{" "}
            They account for {warning.share} of {warning.measure} (
            {warning.amount}).{" "}
            <span className="text-[12px] text-report-ink-muted">
              · {warning.scope}
            </span>{" "}
            <ReportRecordLink
              url={warning.url}
              about={`the rows with no ${warning.missing}`}
            />
          </li>
        ))}
      </ol>
    </section>
  );
}
