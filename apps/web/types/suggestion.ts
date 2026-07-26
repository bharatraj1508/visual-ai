export type SuggestionStatus = "suggested" | "generated" | "dismissed";

export interface ReportSuggestion {
  id: string;
  dataset_id: string;
  title: string;
  question: string;
  rationale: string;
  chart_types: string[];
  status: SuggestionStatus;
  report_id: string | null;
  created_at: string;
}
