export type ColumnType =
  | "dimension"
  | "temporal"
  | "identifier"
  | "additive_count"
  | "additive_value"
  | "ratio"
  | "snapshot_stock"
  | "unclassified";

export interface ColumnMetadata {
  name: string;
  column_type: ColumnType;
}

export interface Chip {
  label: string;
  send_text: string;
}

export interface Clarification {
  reason:
    | "ambiguous_templates"
    | "missing_parameter"
    | "unknown_entity"
    | "broad_question"
    | "no_match";
  prompt: string;
  options: Chip[];
}

export interface ContextFrameSnapshot {
  template_id: string;
  template_question?: string | null;
  bound_params: Record<string, string>;
  active_filters: { dimension: string; operator: string; value: string }[];
  time_range: { start: string | null; end: string | null; grain: string };
  grouping_dimension: string | null;
  result_set: { id: string; row_count: number; columns: ColumnMetadata[] };
}

export interface ContextFrame extends ContextFrameSnapshot {
  history_stack: ContextFrameSnapshot[];
}


// Which question the answer answers, and how the message got there. The
// backend stamps it on every path that binds a message to the question already
// on screen; "new_question" means it was routed standalone and nothing is drawn.
//
// THIS CANNOT BE INFERRED HERE. A frame edit ("and ganjam?") re-queries the
// same template and comes back as an ordinary successful answer, identical in
// every other field to a fresh question that happened to match it.
export type InterpretationKind =
  | "new_question"
  | "frame_edit"
  | "operation"
  | "fragment_reroute"
  | "scope_inherited"
  | "clarification_reply";

export interface Interpretation {
  kind: InterpretationKind;
  anchor_question?: string | null;
  anchor_template_id?: string | null;
  // A short phrase ("district → Khordha"). Deliberately NOT rendered: the
  // anchor and the answered question are already stacked one above the other,
  // so it restates a difference the reader can see.
  detail?: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  tier?: "tier1" | "tier2" | "fallback" | "operation" | "clarify";
  result?: Record<string, unknown>[] | null;
  error?: string | null;
  date_range?: { start_date: string; end_date: string };
  date_filter_applied?: boolean;
  originalQuery?: string;
  context_frame?: ContextFrame | null;
  operation?: string | null;
  operation_mode?: "client" | "requery" | "rejected" | null;
  clarification?: Clarification | null;
  suggestions?: Chip[] | null;
  interpretation?: Interpretation | null;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}
