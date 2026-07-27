// Neutral chart spec emitted by the backend (app/agent/tools/chart_spec.py).
// The renderer maps `render` to a Recharts container and `series` to the marks
// drawn inside it.
export type ChartRender = "cartesian" | "pie" | "scatter" | "radar";
export type SeriesMark = "bar" | "line" | "area" | "pie" | "radar";

export interface ChartSeries {
  key: string;
  name: string;
  chartType: SeriesMark;
  yAxis: "left" | "right";
  stackId: string | null;
}

export interface ChartSpec {
  type: string;
  render: ChartRender;
  title: string | null;
  data: Record<string, unknown>[];
  xKey: string;
  xType: "category" | "number" | "time";
  series: ChartSeries[];
  seriesField: string | null;
  yKey: string | null;
  xLabel: string | null;
  yLabel: string | null;
  // Scatter only: the per-point identity column (e.g. player name) surfaced in
  // the tooltip so a dot is identifiable, not just an (x, y) pair.
  labelKey?: string | null;
}
