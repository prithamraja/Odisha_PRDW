/**
 * Client for DiscoverChat — the findings-retrieval service (DiscoverChat/main.py).
 *
 * A SEPARATE backend from Ask, on its own port, deliberately: Ask answers
 * questions about the records, DiscoverChat reports patterns the analysis has
 * already found. They are never the same base URL, so they get their own env
 * var rather than sharing `VITE_API_BASE_URL` — a single var would send Discover
 * questions to Ask's `/query` the moment one of the two moved.
 */

const DISCOVER_CONFIG = {
  baseUrl:
    import.meta.env.VITE_DISCOVER_API_BASE_URL || "http://localhost:8100",
  headers: {
    "Content-Type": "application/json",
  } as Record<string, string>,
};

export function configureDiscoverApi(config: Partial<typeof DISCOVER_CONFIG>) {
  Object.assign(DISCOVER_CONFIG, config);
}

/** The turn decision the backend made. `lookup` is the route-to-Ask decline. */
export type DiscoverMove = "retrieve" | "navigate" | "lookup" | "why" | string;

/** One finding, exactly as the corpus holds it. Never model-written. */
export interface DiscoverFinding {
  id: string;
  sentence: string;
  coverage: string;
  view: string;
}

/**
 * One cited finding, as the service's citation map holds it.
 *
 * `sentence` is the STORED form the citation check matched against and the one
 * `/record/{id}` serves; `display_sentence` is the readable form. The hover
 * shows the readable one — `findings-verbatim` in the service's gate proves
 * every digit is the same in both, so this is a reading aid, not a second
 * version of the number.
 */
export interface DiscoverCitation {
  id: string;
  sentence: string;
  display_sentence: string;
  scope: string;
  standing: string;
  view: string;
  is_decomposition: boolean;
  stamp: string;
  /** `/record/{id}` — a path by default, an absolute URL if the service is
   *  configured with `DISCOVERCHAT_RECORD_URL_BASE`. Use `recordHref`. */
  url: string;
}

export interface DiscoverChatResponse {
  answer: string;
  move: DiscoverMove;
  session_id: string;
  turn_id: string;
  findings: DiscoverFinding[];
  routing: Record<string, unknown>;
  retrieval: Record<string, unknown>;
  prose: Record<string, unknown>;
  stamp: string;

  // ---- hover-to-source (WP-D7 §3–§4). All three are OPTIONAL on purpose:
  // a service running pre-D7 code omits them, and a turn whose narrative fell
  // back to bare sentences sends them empty. The tab renders exactly as it did
  // before in both cases, so an older backend degrades to plain text rather
  // than to a blank report.
  /** The prose with `[id]` tags after each bound figure or claim. */
  answer_tagged?: string;
  /** Per cited id: everything a hover card and a record link need. */
  citations?: Record<string, DiscoverCitation>;
  /** The service's reference render. We take the SPAN BOUNDARIES from it and
   *  nothing else — see `src/lib/discover-answer.ts`. */
  answer_html?: string;

  // ---- the report layout (WP-D12). OPTIONAL: an older service omits it and
  // every path that shows no findings sends `{}`. Anything but `version: 1`
  // renders the report exactly as before.
  layout?: DiscoverLayout | Record<string, never>;
}

// ---------------------------------------------------------------------------
// The report layout (WP-D12, DiscoverChat/layout.py)
//
// Built by code from the stored records the answer already uses. EVERY string
// here is formatted by the service — figures, shares, direction words — so the
// tab formats no number and decides no ranking. `fraction` is the one number,
// and it is for bar geometry only. Every item carries its own record `url`,
// because on the bare-sentence fallback the `citations` map is empty.
// ---------------------------------------------------------------------------

export interface LayoutTotalCard {
  id: string;
  url: string;
  kind: "total";
  /** The record's total, formatted, direction in words where signed. */
  value: string;
  /** The measure, in officer words. */
  label: string;
  scope: string;
}

export interface LayoutPatternCard {
  id: string;
  url: string;
  kind: "pattern";
  /** The pattern's own sentence, verbatim. */
  text: string;
  scope: string;
}

export type LayoutCard = LayoutTotalCard | LayoutPatternCard;

export interface LayoutWarning {
  id: string;
  url: string;
  /** Rows with no value on file, formatted. */
  rows: string;
  /** What is missing — the breakdown's name ("sanctioning authority"). */
  missing: string;
  measure: string;
  share: string;
  amount: string;
  scope: string;
}

export interface LayoutBar {
  member: string;
  /** abs(share), in [0, 1] — geometry only, never printed. */
  fraction: number;
  share: string;
  value: string;
  role: "member" | "not_recorded";
}

export interface LayoutCompareRow {
  id: string;
  url: string;
  label: string;
  total: string;
  direction: string | null;
  /** One per member, in the panel's `members` order. */
  parts: LayoutBar[];
}

export interface LayoutComparePanel {
  kind: "compare";
  ids: string[];
  by: string;
  scope: string;
  members: string[];
  rows: LayoutCompareRow[];
}

export interface LayoutBarsPanel {
  kind: "ranked" | "time";
  id: string;
  ids: string[];
  url: string;
  label: string;
  by: string;
  scope: string;
  total: string;
  direction: string | null;
  /** Bars drawn (the null bar aside) and members there are. */
  shown: number;
  of: number;
  bars: LayoutBar[];
}

export type LayoutPanel = LayoutComparePanel | LayoutBarsPanel;

export interface DiscoverLayout {
  version: number;
  cards?: LayoutCard[];
  warnings?: LayoutWarning[];
  /** A panel of a kind this tab does not know is skipped, never fatal. */
  panels?: Array<LayoutPanel | { kind: string; ids?: string[] }>;
}

/**
 * The absolute link to a finding's readable record view.
 *
 * `record_url()` server-side returns a bare path unless the deployment sets
 * `DISCOVERCHAT_RECORD_URL_BASE`, so a path is resolved against the same base
 * `askDiscover` posts to — not against the frontend's own origin, which is a
 * different host in every deployed configuration.
 */
export function recordHref(url: string): string {
  if (!url) return "";
  const absolute = /^https?:\/\//i.test(url)
    ? url
    : `${DISCOVER_CONFIG.baseUrl.replace(/\/$/, "")}/${url.replace(/^\//, "")}`;
  return absolute.includes("?")
    ? `${absolute}&format=html`
    : `${absolute}?format=html`;
}

export async function askDiscover(
  message: string,
  options?: { session_id?: string; signal?: AbortSignal }
): Promise<DiscoverChatResponse> {
  const res = await fetch(`${DISCOVER_CONFIG.baseUrl}/chat`, {
    method: "POST",
    headers: DISCOVER_CONFIG.headers,
    body: JSON.stringify({
      message,
      ...(options?.session_id ? { session_id: options.session_id } : {}),
    }),
    signal: options?.signal,
  });

  if (!res.ok) {
    throw new Error(`Server error: ${res.status}`);
  }

  return res.json();
}
