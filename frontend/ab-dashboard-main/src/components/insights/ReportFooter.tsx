import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

/** How long the button reads "Copied" after a copy. */
const COPIED_MS = 2000;

/** The caution line under every Insight report (WP-D13 Fix 6, D68). The
 *  operator's words, phrased by the PM: edit this one line to change them. */
const REPORT_CAUTION = "Produced with AI, so it may contain mistakes. It shows patterns in the records and cannot tell what caused them. Please check the source records before acting.";

/**
 * The report's footer (WP-D12 T2.4): the run stamp, as before, and a Copy
 * button that puts the question and the plain answer on the clipboard.
 *
 * The plain `answer` is copied — the same text a plain client shows, with the
 * run stamp at its end — so a pasted report still says when it was mined.
 * No Download, and no follow-up chips (ruling 4).
 *
 * WP-D13 Fix 6: a fixed caution line sits on its own row above the stamp, on
 * every report — with a layout, without one, and on a fall-back. Plain muted
 * text, no icon and no box, so it does not compete with "Needs checking".
 * Copy carries it: question, answer, caution, each a blank line apart.
 */
export function ReportFooter({
  stamp,
  question,
  answer,
}: {
  stamp: string | null;
  question: string;
  answer: string;
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    []
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(
        `${question}\n\n${answer}\n\n${REPORT_CAUTION}`
      );
    } catch {
      return; // no clipboard (an insecure origin, a denied permission): stay quiet
    }
    setCopied(true);
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), COPIED_MS);
  };

  return (
    <div className="mt-5 pt-4 border-t border-report-line">
      <p
        data-report-chrome=""
        data-report-caution=""
        className="m-0 mb-2.5 text-[12px] leading-snug text-report-ink-muted"
      >
        {REPORT_CAUTION}
      </p>
      <div className="flex flex-wrap items-center gap-2.5">
        {/* The corpus is a snapshot of one mining run. An answer that did not
            say when it was mined would invite a stale pattern to be read as
            today's, which is why the service stamps every one. */}
        <p className="m-0 flex-[1_1_240px] text-[12px] text-report-ink-muted">
          {stamp}
        </p>
        <button
          type="button"
          onClick={copy}
          data-report-chrome=""
          className="h-11 px-3.5 rounded-lg border border-report-line-strong bg-white text-report-ink text-[13px] inline-flex items-center gap-2 hover:border-report-ink/40 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-report-cyan/60"
        >
          {copied ? (
            <Check size={14} aria-hidden="true" />
          ) : (
            <Copy size={14} aria-hidden="true" />
          )}
          <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
    </div>
  );
}
