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
