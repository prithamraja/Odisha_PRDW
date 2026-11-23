import { Download } from "lucide-react";

/** The caution line under every Insight report (WP-D13 Fix 6, D68). The
 *  operator's words, phrased by the PM: edit this one line to change them. */
const REPORT_CAUTION = "Produced with AI, so it may contain mistakes. It shows patterns in the records and cannot tell what caused them. Please check the source records before acting.";

/** Set on <html> only while a report's print box is open. Every print rule in
 *  `index.css` hangs off it, so Ctrl+P anywhere else prints as before. */
const PRINTING_ATTR = "data-report-printing";
/** Set on the one report card being printed. */
const PRINT_TARGET_ATTR = "data-print-target";

/** Characters a file name cannot hold on Windows, macOS or Linux. Each, and
 *  any control character, becomes a space. */
const NOT_FILE_SAFE = '\\/:*?"<>|';
const fileSafe = (ch: string) => {
  const code = ch.codePointAt(0) ?? 0;
  return code < 0x20 || code === 0x7f || NOT_FILE_SAFE.includes(ch) ? " " : ch;
};

/**
 * The name the browser suggests for the PDF (D72):
 * "Insight report - <the question, first 60 characters, file-safe> - YYYY-MM-DD".
 * The date is the day of the download, in the officer's own time zone.
 * Browsers take the name from the page title.
 */
function pdfFileName(question: string, today: Date): string {
  const first60 = Array.from(question.trim()).slice(0, 60);
  const safe = first60.map(fileSafe).join("").replace(/\s+/g, " ").trim();
  const date = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  return safe ? `Insight report - ${safe} - ${date}` : `Insight report - ${date}`;
}

/** Puts the page back after a print: set while a print box is open. */
let restorePage: (() => void) | null = null;

/**
 * Open the browser's own print box for one report card, where it is saved as
 * a PDF. Nothing is sent anywhere and nothing is written again: the PDF is the
 * report already on the screen.
 *
 * For the print only, <html> and the card are marked (the print rules in
 * `index.css` key on both) and the page title becomes the file name. All
 * three are put back on `afterprint`, which Chrome and Edge fire when the
 * print box closes.
 */
function printReport(card: HTMLElement, question: string): void {
  restorePage?.(); // a print box that never reported closing: tidy up first
  const root = document.documentElement;
  const title = document.title;
  const restore = () => {
    window.removeEventListener("afterprint", restore);
    root.removeAttribute(PRINTING_ATTR);
    card.removeAttribute(PRINT_TARGET_ATTR);
    document.title = title;
    if (restorePage === restore) restorePage = null;
  };
  restorePage = restore;
  card.setAttribute(PRINT_TARGET_ATTR, "");
  root.setAttribute(PRINTING_ATTR, "");
  document.title = pdfFileName(question, new Date());
  window.addEventListener("afterprint", restore);
  window.print();
}

/**
 * The report's footer (WP-D12 T2.4): the run stamp, as before, and a
 * "Download PDF" button (WP-D13 Fix 10, D72).
 *
 * Download opens the browser's print box on the report as it is on screen —
 * no PDF library, no call to the service. It replaced the WP-D12 Copy button,
 * and reverses that ruling's "No Download". No follow-up chips (WP-D12
 * ruling 4).
 *
 * WP-D13 Fix 6: a fixed caution line sits on its own row above the stamp, on
 * every report — with a layout, without one, and on a fall-back. Plain muted
 * text, no icon and no box, so it does not compete with "Needs checking". It
 * prints with the report; the button does not (`data-print-hide`).
 */
export function ReportFooter({
  stamp,
  question,
}: {
  stamp: string | null;
  question: string;
}) {
  return (
    <div data-report-part="footer" className="mt-5 pt-4 border-t border-report-line">
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
          onClick={(event) => {
            const card = event.currentTarget.closest<HTMLElement>("[data-report-card]");
            if (card) printReport(card, question);
          }}
          data-report-chrome=""
          data-print-hide=""
          className="h-11 px-3.5 rounded-lg border border-report-line-strong bg-white text-report-ink text-[13px] inline-flex items-center gap-2 hover:border-report-ink/40 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-report-cyan/60"
        >
          <Download size={14} aria-hidden="true" />
          <span>Download PDF</span>
        </button>
      </div>
    </div>
  );
}
