// A cohesive analytical palette anchored on the app's coral primary. Series
// pick colors by index so every chart in a report stays visually consistent.
export const CHART_COLORS = [
  "#FB676E", // coral (primary)
  "#2DD4BF", // teal
  "#6366F1", // indigo
  "#F59E0B", // amber
  "#A855F7", // violet
  "#38BDF8", // sky
  "#FB7185", // rose
  "#84CC16", // lime
  "#F97316", // orange
  "#14B8A6", // emerald-teal
];

export const colorAt = (index: number) =>
  CHART_COLORS[index % CHART_COLORS.length];
