import { recordHref } from "@/services/discover-api";

/**
 * "Open record ↗" for one layout item (WP-D12).
 *
 * The link comes from the item's OWN `url`, never from the citations map: on
 * the bare-sentence fallback that map is empty, and a card or a warning whose
 * link silently vanished on exactly the answers where the writer failed would
 * be the opposite of what the layout is for. `about` names what the record is
 * behind, so a screen reader can tell several "Open record" links apart.
 */
export function ReportRecordLink({
  url,
  about,
  className = "",
}: {
  url: string;
  about: string;
  className?: string;
}) {
  if (!url) return null;
  return (
    <a
      href={recordHref(url)}
      target="_blank"
      rel="noreferrer"
      aria-label={`Open the record behind ${about}`}
      className={`inline-flex items-center text-[12px] font-medium text-report-cyan-deep underline underline-offset-2 hover:text-report-ink transition-colors ${className}`}
    >
      Open record&nbsp;&#8599;
    </a>
  );
}
