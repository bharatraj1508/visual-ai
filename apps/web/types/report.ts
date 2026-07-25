export type ReportStatus = "running" | "completed" | "failed";

export interface Report {
  id: string;
  dataset_id: string;
  title: string;
  goal: string;
  status: ReportStatus;
  error: string | null;
  created_at: string;
}

export interface ReportSection {
  title: string;
  narrative: string;
  charts: Record<string, unknown>[];
}

export interface ReportDetail extends Report {
  content: ReportSection[] | null;
}
