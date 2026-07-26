export type DatasetStatus = "uploading" | "profiling" | "ready" | "failed";

export interface PreprocessChange {
  code: string;
  title: string;
  detail: string;
}

export interface Dataset {
  id: string;
  filename: string;
  status: DatasetStatus;
  row_count: number | null;
  col_count: number | null;
  error: string | null;
  created_at: string;
  preprocessed: boolean;
  // At upload: what cleaning WOULD do (drives the recommendation card).
  // After preprocessing: what was applied. null when the data is already clean.
  preprocessing_summary: PreprocessChange[] | null;
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

export interface DatasetProfile extends Dataset {
  columns: DatasetColumn[];
}
