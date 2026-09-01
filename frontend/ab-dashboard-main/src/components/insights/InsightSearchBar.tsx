import { useState } from "react";
import { CornerDownLeft, Loader2, Search } from "lucide-react";

interface InsightSearchBarProps {
  onSearch: (question: string) => void;
  isLoading?: boolean;
}

/**
 * The question box above the feed.
 *
 * It runs DiscoverChat, not Ask: what comes back is a report assembled from
 * findings the analysis has already mined, never a figure looked up in the
 * database. The examples underneath say so by demonstration — every one of them
 * asks about a pattern, so the first question an officer tries is the kind this
 * product can actually answer.
 */
// Each one was run against the live corpus and returns findings. A "Try:" chip
// that answers "the analysis has nothing on this" would teach an officer the
// wrong lesson on their first use, so a miss is not allowed to sit here — when
// the corpus is rebuilt, re-run these three and replace any that stop hitting.
const EXAMPLES = [
  "Which blocks stand out on expenditure?",
  "What patterns show up in sanctions across districts?",
  "What is unusual about water supply works?",
];

export function InsightSearchBar({ onSearch, isLoading }: InsightSearchBarProps) {
  const [value, setValue] = useState("");

  const submit = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    onSearch(trimmed);
  };

  return (
    <div className="mb-8">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="flex items-center gap-3 bg-white border border-line rounded-xl px-4 py-3 focus-within:border-ink/40 transition-colors"
      >
        <Search size={16} className="text-muted-design shrink-0" />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask a question to generate an insight report"
          disabled={isLoading}
          aria-label="Ask a question to generate an insight report"
          className="flex-1 min-w-0 bg-transparent text-[14px] text-ink placeholder:text-muted-design outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !value.trim()}
          className="shrink-0 h-8 px-3 rounded-lg bg-ink hover:bg-ink/90 text-ivory text-[13px] font-medium flex items-center gap-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 size={12} className="animate-spin" />
              Generating
            </>
          ) : (
            <>
              Generate
              <CornerDownLeft size={12} strokeWidth={2.25} />
            </>
          )}
        </button>
      </form>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1.5">
        <span className="text-[12px] text-muted-design">Try:</span>
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => {
              setValue(example);
              submit(example);
            }}
            disabled={isLoading}
            className="text-[12px] text-muted-design hover:text-ink underline decoration-line underline-offset-4 hover:decoration-ink/40 transition-colors disabled:opacity-50"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
