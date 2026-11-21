/**
 * The report layout's two decisions the tab makes for itself (WP-D12).
 *
 * The service computes every card, warning and chart and formats every string
 * in them (`DiscoverChat/layout.py`). What is left to the tab is:
 *
 *   1. whether there is a layout to draw at all — anything but `version: 1`,
 *      or a layout with nothing in it, renders the report exactly as before;
 *   2. where each chart goes — under the first paragraph that cites any of
 *      its records, or after the last block if no paragraph does (which, on
 *      the bare-sentence fallback, is every chart).
 *
 * Both are pure functions over the parsed answer, so they are tested without
 * React. No number is formatted here and nothing is ranked.
 */

import type { CitedBlock } from "@/lib/discover-answer";
import type {
  LayoutCard,
  LayoutPanel,
  LayoutWarning,
} from "@/services/discover-api";

/** The panel kinds this tab can draw. Anything else is skipped. */
const KNOWN_PANEL_KINDS = new Set(["compare", "ranked", "time"]);

export interface UsableLayout {
  cards: LayoutCard[];
  warnings: LayoutWarning[];
  panels: LayoutPanel[];
}

function isPanel(panel: unknown): panel is LayoutPanel {
  if (!panel || typeof panel !== "object") return false;
  const p = panel as { kind?: unknown; ids?: unknown };
  return (
    typeof p.kind === "string" &&
    KNOWN_PANEL_KINDS.has(p.kind) &&
    Array.isArray(p.ids)
  );
}

function isCard(card: unknown): card is LayoutCard {
  const kind = (card as { kind?: unknown } | null)?.kind;
  return kind === "total" || kind === "pattern";
}

/**
 * The layout to draw, or null to render the report exactly as before.
 *
 * Null for an absent layout, `{}`, a version other than 1, or a layout whose
 * every list is empty. A panel or card of a kind this tab does not know is
 * dropped on its own; the rest still draws — never a blank report.
 */
export function usableLayout(layout: unknown): UsableLayout | null {
  if (!layout || typeof layout !== "object") return null;
  const l = layout as {
    version?: unknown;
    cards?: unknown;
    warnings?: unknown;
    panels?: unknown;
  };
  if (l.version !== 1) return null;
  const cards = Array.isArray(l.cards) ? l.cards.filter(isCard) : [];
  const warnings = Array.isArray(l.warnings)
    ? (l.warnings as LayoutWarning[])
    : [];
  const panels = Array.isArray(l.panels) ? l.panels.filter(isPanel) : [];
  if (!cards.length && !warnings.length && !panels.length) return null;
  return { cards, warnings, panels };
}

export interface PanelPlacement {
  /** Panels to draw under block i, in the service's order. */
  byBlock: LayoutPanel[][];
  /** Panels no block cites, drawn after the last block. */
  trailing: LayoutPanel[];
}

/** The record ids a block's bound figures and claims cite. */
export function citedIds(block: CitedBlock): Set<string> {
  const ids = new Set<string>();
  for (const segment of block.segments) {
    if (segment.citation) ids.add(segment.citation.id);
  }
  return ids;
}

/**
 * Each panel under the FIRST block that cites any of its records.
 *
 * The citations are the ones `parseCitedAnswer` already bound per block, so a
 * writer that puts everything in one paragraph gets every chart under that
 * paragraph, and a turn that fell back to bare sentences (no citations at
 * all) gets every chart after the last block.
 */
export function placePanels(
  blocks: CitedBlock[],
  panels: LayoutPanel[]
): PanelPlacement {
  const cited = blocks.map(citedIds);
  const byBlock: LayoutPanel[][] = blocks.map(() => []);
  const trailing: LayoutPanel[] = [];
  for (const panel of panels) {
    const index = cited.findIndex((ids) => panel.ids.some((id) => ids.has(id)));
    if (index === -1) trailing.push(panel);
    else byBlock[index].push(panel);
  }
  return { byBlock, trailing };
}
