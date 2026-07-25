export interface ChartArtifact {
  id: string;
  kind: string;
  title: string | null;
  spec: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
  artifacts: ChartArtifact[];
}

export interface ChatSession {
  id: string;
  dataset_id: string;
  title: string;
  created_at: string;
}

export type ChatStreamEvent =
  | { type: "token"; data: string }
  | { type: "tool_start"; data: { name?: string; input?: unknown } }
  | { type: "tool_end"; data: { name?: string } }
  | { type: "chart"; data: ChartArtifact }
  | { type: "done"; data: { message_id: string } }
  | { type: "error"; data: { detail: string } };
