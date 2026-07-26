// Human labels for the chart types the backend emits.
export const CHART_LABELS: Record<string, string> = {
  bar: "Bar",
  grouped_bar: "Grouped bar",
  stacked_bar: "Stacked bar",
  line: "Line",
  multi_line: "Multi-line",
  area: "Area",
  stacked_area: "Stacked area",
  scatter: "Scatter",
  pie: "Pie",
  donut: "Donut",
  histogram: "Histogram",
  dual_axis: "Dual axis",
  radar: "Radar",
};

export const chartLabel = (type: string): string =>
  CHART_LABELS[type] ?? type.replace(/_/g, " ");
