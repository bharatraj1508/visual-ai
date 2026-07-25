export type DatasetStatus = "uploading" | "profiling" | "ready" | "failed";

export interface Dataset {
  id: string;
  filename: string;
  status: DatasetStatus;
  row_count: number | null;
  col_count: number | null;
  error: string | null;
  created_at: string;
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
