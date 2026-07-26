import { ChartSpec } from "./chart";

export type ReportStatus = "running" | "completed" | "failed";

export interface Report {
  id: string;
  dataset_id: string;
  title: string;
  goal: string;
  status: ReportStatus;
  error: string | null;
  created_at: string;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  // Lightweight content stats for list/dashboard views.
  section_count: number;
  chart_count: number;
  chart_types: string[];
}

export interface ReportSection {
  title: string;
  narrative: string;
  charts: ChartSpec[];
}

export interface ReportDetail extends Report {
  content: ReportSection[] | null;
}

export type ReportStreamEvent =
  | { type: "report_start"; data: { sections: string[] } }
  | { type: "section_start"; data: { index: number; title: string } }
  | { type: "token"; data: string }
  | { type: "tool_start"; data: { name?: string } }
  | { type: "tool_end"; data: { name?: string } }
  | {
      type: "chart";
      data: { id: string; title: string | null; spec: ChartSpec };
    }
  | { type: "section_end"; data: { index: number } }
  | {
      type: "report_done";
      data: {
        report_id: string;
        cost_usd?: number;
        input_tokens?: number;
        output_tokens?: number;
      };
    }
  | { type: "error"; data: { detail: string } };
