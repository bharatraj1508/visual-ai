export type DatasetStatus = "uploading" | "profiling" | "ready" | "failed";

export interface PreprocessChange {
  code: string;
  title: string;
  detail: string;
}

export interface DatasetTableSummary {
  name: string;
  filename: string;
  row_count: number | null;
  col_count: number | null;
}

export interface Dataset {
  id: string;
  filename: string;
  status: DatasetStatus;
  row_count: number | null;
  col_count: number | null;
  error: string | null;
  created_at: string;
  archived: boolean;
  preprocessed: boolean;
  // At upload: what cleaning WOULD do (drives the recommendation card).
  // After preprocessing: what was applied. null when the data is already clean.
  preprocessing_summary: PreprocessChange[] | null;
  // Per-table summary when the dataset spans multiple CSVs; null for single-table.
  tables: DatasetTableSummary[] | null;
}

export interface DatasetColumn {
  name: string;
  dtype: string;
  position: number;
  null_count: number;
  distinct_count: number;
  min_value: string | null;
  max_value: string | null;
  sample_values: unknown[];
}

export interface DatasetTableProfile extends DatasetTableSummary {
  columns: DatasetColumn[];
}

export interface DatasetProfile extends Dataset {
  columns: DatasetColumn[];
  // Full per-table profiles for multi-table datasets; null for single-table.
  tables: DatasetTableProfile[] | null;
}
