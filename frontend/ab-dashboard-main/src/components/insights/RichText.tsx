import { splitBold } from "@/lib/insights-report";

/**
 * Body text with the report's own `**bold**` rendered as emphasis.
 *
 * Shared by the generated feed and the DiscoverChat report, so a marker is
 * never shown to an officer as a pair of asterisks in either of them.
 */
export function RichText({ text }: { text: string }) {
  return (
    <>
      {splitBold(text).map((run, i) =>
        run.bold ? (
          <strong key={i} className="font-semibold text-ink">
            {run.text}
          </strong>
        ) : (
          <span key={i}>{run.text}</span>
        )
      )}
    </>
  );
}
