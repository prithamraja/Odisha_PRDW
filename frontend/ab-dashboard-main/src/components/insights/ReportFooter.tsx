import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

/** How long the button reads "Copied" after a copy. */
const COPIED_MS = 2000;

/**
 * The report's footer (WP-D12 T2.4): the run stamp, as before, and a Copy
 * button that puts the question and the plain answer on the clipboard.
 *
 * The plain `answer` is copied — the same text a plain client shows, with the
 * run stamp at its end — so a pasted report still says when it was mined.
 * No Download, and no follow-up chips (ruling 4).
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
      await navigator.clipboard.writeText(`${question}\n\n${answer}`);
    } catch {
      return; // no clipboard (an insecure origin, a denied permission): stay quiet
    }
    setCopied(true);
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), COPIED_MS);
  };

  return (
    <div className="mt-5 pt-4 border-t border-report-line flex flex-wrap items-center gap-2.5">
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
  );
}
