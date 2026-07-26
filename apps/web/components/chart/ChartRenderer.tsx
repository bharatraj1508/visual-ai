"use client";

import { useState } from "react";

import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { ChartSeries, ChartSpec } from "@/types/chart";

import { colorAt } from "./palette";

const HEIGHT = 320;
const GRID = "#EEF0F3";
const AXIS = "#9CA3AF";

const axisProps = {
  stroke: AXIS,
  tick: { fontSize: 12, fill: "#6B7280" },
  tickLine: false,
} as const;

const tooltipStyle = {
  contentStyle: {
    borderRadius: 10,
    border: "1px solid #E5E7EB",
    boxShadow: "0 8px 24px -12px rgba(0,0,0,0.25)",
    fontSize: 12,
  },
  cursor: { fill: "rgba(0,0,0,0.03)" },
} as const;

/** Renders a neutral ChartSpec as an interactive Recharts chart. */
export default function ChartRenderer({ spec }: { spec: ChartSpec }) {
  // Clicking a legend entry toggles that series off — a quick way to isolate.
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const toggle = (key: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  if (!spec?.data?.length) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-gray-200 text-sm text-gray-400">
        No data to plot.
      </div>
    );
  }

  return (
    <figure className="rounded-xl border border-gray-200 bg-white p-4">
      {spec.title && (
        <figcaption className="mb-3 text-sm font-medium text-gray-700">
          {spec.title}
        </figcaption>
      )}
      <ResponsiveContainer width="100%" height={HEIGHT}>
        {renderBody(spec, hidden, toggle)}
      </ResponsiveContainer>
    </figure>
  );
}

function legend(toggle: (key: string) => void) {
  return (
    <Legend
      onClick={(entry: any) => toggle(String(entry.dataKey ?? entry.value))}
      wrapperStyle={{ fontSize: 12, cursor: "pointer", paddingTop: 8 }}
    />
  );
}

function renderBody(
  spec: ChartSpec,
  hidden: Set<string>,
  toggle: (key: string) => void,
) {
  switch (spec.render) {
    case "pie":
      return renderPie(spec);
    case "scatter":
      return renderScatter(spec, hidden, toggle);
    case "radar":
      return renderRadar(spec, hidden, toggle);
    default:
      return renderCartesian(spec, hidden, toggle);
  }
}

function renderCartesian(
  spec: ChartSpec,
  hidden: Set<string>,
  toggle: (key: string) => void,
) {
  const hasRight = spec.series.some((s) => s.yAxis === "right");
  return (
    <ComposedChart data={spec.data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis
        dataKey={spec.xKey}
        type={spec.xType === "number" ? "number" : "category"}
        {...axisProps}
        minTickGap={16}
      />
      <YAxis yAxisId="left" {...axisProps} width={48} />
      {hasRight && (
        <YAxis yAxisId="right" orientation="right" {...axisProps} width={48} />
      )}
      <Tooltip {...tooltipStyle} />
      {legend(toggle)}
      {spec.series.map((s, i) => seriesMark(s, i, hidden))}
    </ComposedChart>
  );
}

function seriesMark(s: ChartSeries, index: number, hidden: Set<string>) {
  const color = colorAt(index);
  const axisId = s.yAxis === "right" ? "right" : "left";
  const hide = hidden.has(s.key);
  const common = { key: s.key, dataKey: s.key, name: s.name, yAxisId: axisId, hide };

  if (s.chartType === "line") {
    return (
      <Line
        {...common}
        type="monotone"
        stroke={color}
        strokeWidth={2}
        dot={false}
        activeDot={{ r: 4 }}
      />
    );
  }
  if (s.chartType === "area") {
    return (
      <Area
        {...common}
        type="monotone"
        stroke={color}
        fill={color}
        fillOpacity={0.18}
        strokeWidth={2}
        stackId={s.stackId ?? undefined}
      />
    );
  }
  return (
    <Bar
      {...common}
      fill={color}
      radius={[4, 4, 0, 0]}
      stackId={s.stackId ?? undefined}
      maxBarSize={64}
    />
  );
}

function renderPie(spec: ChartSpec) {
  const valueKey = spec.series[0]?.key ?? spec.yKey ?? "value";
  const isDonut = spec.type === "donut";
  return (
    <PieChart>
      <Tooltip {...tooltipStyle} cursor={false} />
      <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
      <Pie
        data={spec.data}
        dataKey={valueKey}
        nameKey={spec.xKey}
        cx="50%"
        cy="50%"
        outerRadius={110}
        innerRadius={isDonut ? 64 : 0}
        paddingAngle={isDonut ? 2 : 0}
        stroke="#fff"
        strokeWidth={2}
      >
        {spec.data.map((_, i) => (
          <Cell key={i} fill={colorAt(i)} />
        ))}
      </Pie>
    </PieChart>
  );
}

function renderScatter(
  spec: ChartSpec,
  hidden: Set<string>,
  toggle: (key: string) => void,
) {
  const yKey = spec.yKey ?? "y";
  // Split into one <Scatter> per distinct series value when a split field is set.
  const groups = spec.seriesField
    ? Array.from(
        new Set(spec.data.map((row) => String(row[spec.seriesField as string]))),
      )
    : [null];
  return (
    <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
      <CartesianGrid stroke={GRID} />
      <XAxis
        type="number"
        dataKey={spec.xKey}
        name={spec.xLabel ?? spec.xKey}
        {...axisProps}
      />
      <YAxis type="number" dataKey={yKey} name={spec.yLabel ?? yKey} {...axisProps} width={48} />
      <ZAxis range={[50, 50]} />
      <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: "3 3" }} />
      {spec.seriesField && legend(toggle)}
      {groups.map((group, i) => {
        const key = group ?? "points";
        return (
          <Scatter
            key={key}
            name={group ?? spec.yLabel ?? yKey}
            data={
              group === null
                ? spec.data
                : spec.data.filter(
                    (row) => String(row[spec.seriesField as string]) === group,
                  )
            }
            fill={colorAt(i)}
            hide={hidden.has(key)}
          />
        );
      })}
    </ScatterChart>
  );
}

function renderRadar(
  spec: ChartSpec,
  hidden: Set<string>,
  toggle: (key: string) => void,
) {
  return (
    <RadarChart data={spec.data} outerRadius="72%">
      <PolarGrid stroke={GRID} />
      <PolarAngleAxis dataKey={spec.xKey} tick={{ fontSize: 12, fill: "#6B7280" }} />
      <PolarRadiusAxis tick={{ fontSize: 11, fill: AXIS }} />
      <Tooltip {...tooltipStyle} cursor={false} />
      {legend(toggle)}
      {spec.series.map((s, i) => (
        <Radar
          key={s.key}
          dataKey={s.key}
          name={s.name}
          stroke={colorAt(i)}
          fill={colorAt(i)}
          fillOpacity={0.22}
          hide={hidden.has(s.key)}
        />
      ))}
    </RadarChart>
  );
}
