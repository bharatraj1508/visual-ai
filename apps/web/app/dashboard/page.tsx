"use client";

import { ChangeEvent, useMemo, useRef } from "react";

import { useRouter } from "next/navigation";
import { toast } from "react-toastify";

import AppHeader from "@/components/AppHeader";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import {
  useDatasets,
  useDeleteDataset,
  useUploadDataset,
} from "@/services/api/requests/datasets";
import { useReports } from "@/services/api/requests/reports";
import { Dataset } from "@/types/dataset";
import { Report } from "@/types/report";
import { chartLabel } from "@/utils/charts";
import { MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from "@/utils/config";
import { formatCostDual, formatInr } from "@/utils/currency";

export default function DashboardPage() {
  const token = useRequireAuth();
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const showError = useShowApiErrorMessage();

  const { data: datasets, isLoading } = useDatasets();
  const { data: reports } = useReports();
  const upload = useUploadDataset();
  const remove = useDeleteDataset();

  const stats = useMemo(() => {
    const ds = datasets ?? [];
    const rs = reports ?? [];
    const completed = rs.filter((r) => r.status === "completed");
    const totalSpent = rs.reduce((s, r) => s + (r.cost_usd ?? 0), 0);
    const rowsAnalyzed = ds.reduce((s, d) => s + (d.row_count ?? 0), 0);
    const reportsByDataset = new Map<string, number>();
    for (const r of rs)
      reportsByDataset.set(
        r.dataset_id,
        (reportsByDataset.get(r.dataset_id) ?? 0) + 1,
      );
    // "Worth a watch": the richest completed report (most output, then priciest).
    const featured = [...completed].sort(
      (a, b) =>
        (b.output_tokens ?? 0) - (a.output_tokens ?? 0) ||
        (b.cost_usd ?? 0) - (a.cost_usd ?? 0),
    )[0];
    const recent = [...rs].sort(
      (a, b) => +new Date(b.created_at) - +new Date(a.created_at),
    );
    const nameById = new Map(ds.map((d) => [d.id, d.filename] as const));
    // Which chart types you use most, across every report.
    const mixCounts = new Map<string, number>();
    for (const r of rs)
      for (const t of r.chart_types ?? [])
        mixCounts.set(t, (mixCounts.get(t) ?? 0) + 1);
    const chartMix = Array.from(mixCounts.entries())
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);
    const totalCharts = rs.reduce((s, r) => s + (r.chart_count ?? 0), 0);
    const avgCost = completed.length ? totalSpent / completed.length : 0;
    return {
      totalSpent,
      rowsAnalyzed,
      reportCount: completed.length,
      datasetCount: ds.length,
      reportsByDataset,
      featured,
      recent,
      nameById,
      chartMix,
      totalCharts,
      avgCost,
    };
  }, [datasets, reports]);

  if (!token) return null;

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error(`File exceeds the ${MAX_UPLOAD_MB} MB limit`);
      return;
    }
    upload.mutate(file, {
      onSuccess: (dataset) => router.push(`/analyze/${dataset.id}`),
      onError: showError,
    });
  };

  const uploadButton = (
    <button
      onClick={() => fileInput.current?.click()}
      disabled={upload.isPending}
      className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-60"
    >
      {upload.isPending ? <Spinner /> : <PlusIcon />} Upload CSV
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50/60">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-gray-900">
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Your data, the reports you&apos;ve generated, and what they cost.
            </p>
          </div>
          {uploadButton}
          <input
            ref={fileInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={onFile}
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Spinner className="text-primary" />
          </div>
        ) : !datasets?.length ? (
          <EmptyState onUpload={() => fileInput.current?.click()} />
        ) : (
          <div className="space-y-8">
            {/* Stats */}
            <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard
                label="Total spent"
                value={formatInr(stats.totalSpent)}
                sub={`on ${stats.reportCount} report${stats.reportCount === 1 ? "" : "s"}`}
                icon={<CoinIcon />}
              />
              <StatCard
                label="Reports generated"
                value={String(stats.reportCount)}
                sub="across all datasets"
                icon={<ChartIcon />}
              />
              <StatCard
                label="Datasets"
                value={String(stats.datasetCount)}
                sub="uploaded & profiled"
                icon={<GridIcon />}
              />
              <StatCard
                label="Rows analyzed"
                value={compact(stats.rowsAnalyzed)}
                sub="across every dataset"
                icon={<LayersIcon />}
              />
            </section>

            {/* Featured report + chart mix */}
            {(stats.featured || stats.chartMix.length > 0) && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {stats.featured && (
                  <div className="lg:col-span-2">
                    <FeaturedReport
                      report={stats.featured}
                      datasetName={stats.nameById.get(
                        stats.featured.dataset_id,
                      )}
                      onOpen={() =>
                        router.push(`/reports/${stats.featured!.id}`)
                      }
                    />
                  </div>
                )}
                {stats.chartMix.length > 0 && (
                  <ChartMixWidget
                    mix={stats.chartMix}
                    totalCharts={stats.totalCharts}
                  />
                )}
              </div>
            )}

            {/* Reports table */}
            {stats.recent.length > 0 && (
              <section>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                    All reports
                  </h2>
                  <span className="text-xs text-gray-400">
                    avg {formatInr(stats.avgCost)} · {stats.totalCharts} charts
                    total
                  </span>
                </div>
                <ReportsTable
                  reports={stats.recent}
                  nameById={stats.nameById}
                  onOpen={(id) => router.push(`/reports/${id}`)}
                />
              </section>
            )}

            {/* Datasets */}
            <section>
              <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
                Your datasets
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {datasets.map((dataset) => (
                  <DatasetCard
                    key={dataset.id}
                    dataset={dataset}
                    reportCount={stats.reportsByDataset.get(dataset.id) ?? 0}
                    onAnalyze={() => router.push(`/analyze/${dataset.id}`)}
                    onDelete={() =>
                      remove.mutate(dataset.id, { onError: showError })
                    }
                  />
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

/* --------------------------------- widgets -------------------------------- */

function StatCard({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <p className="text-2xl font-semibold tracking-tight text-gray-900">
        {value}
      </p>
      <p className="mt-0.5 text-sm font-medium text-gray-600">{label}</p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  );
}

function FeaturedReport({
  report,
  datasetName,
  onOpen,
}: {
  report: Report;
  datasetName?: string;
  onOpen: () => void;
}) {
  const tokens = (report.input_tokens ?? 0) + (report.output_tokens ?? 0);
  return (
    <button
      onClick={onOpen}
      className="group relative w-full overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/5 via-white to-white p-6 text-left transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
          <StarIcon /> Worth a watch
        </span>
        {datasetName && (
          <span className="text-xs text-gray-400">from {datasetName}</span>
        )}
      </div>
      <h3 className="mt-3 max-w-2xl text-xl font-semibold leading-snug text-gray-900">
        {report.title}
      </h3>
      <p className="mt-1.5 max-w-2xl line-clamp-2 text-sm text-gray-500">
        {report.goal}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
        <span className="font-medium text-gray-700">
          {formatCostDual(report.cost_usd ?? 0)}
        </span>
        <span className="font-mono text-xs text-gray-400">
          {compact(tokens)} tokens
        </span>
        <span className="ml-auto flex items-center gap-1 font-medium text-primary">
          Open report
          <span className="transition-transform group-hover:translate-x-0.5">
            →
          </span>
        </span>
      </div>
    </button>
  );
}

function DatasetCard({
  dataset,
  reportCount,
  onAnalyze,
  onDelete,
}: {
  dataset: Dataset;
  reportCount: number;
  onAnalyze: () => void;
  onDelete: () => void;
}) {
  const ready = dataset.status === "ready";
  return (
    <div className="group flex flex-col rounded-2xl border border-gray-200 bg-white p-5 transition-all hover:border-primary/30 hover:shadow-md hover:shadow-primary/5">
      <div className="mb-3 flex items-start justify-between gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <FileIcon />
        </span>
        <div className="flex items-center gap-2">
          {dataset.preprocessed && (
            <span className="rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-medium text-green-700">
              cleaned
            </span>
          )}
          <StatusPill status={dataset.status} />
        </div>
      </div>
      <p className="truncate font-medium text-gray-900" title={dataset.filename}>
        {dataset.filename}
      </p>
      <p className="mt-0.5 text-sm text-gray-500">
        {dataset.row_count != null
          ? `${dataset.row_count.toLocaleString()} rows · ${dataset.col_count} cols`
          : "profiling…"}
        {reportCount > 0 &&
          ` · ${reportCount} report${reportCount === 1 ? "" : "s"}`}
      </p>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={onAnalyze}
          disabled={!ready}
          className="flex-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Analyze
        </button>
        <button
          onClick={onDelete}
          aria-label="Delete dataset"
          className="rounded-lg p-1.5 text-gray-300 transition-colors hover:bg-red-50 hover:text-red-500"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

function ChartMixWidget({
  mix,
  totalCharts,
}: {
  mix: { type: string; count: number }[];
  totalCharts: number;
}) {
  const max = mix[0]?.count ?? 1;
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-gray-900">Chart mix</h3>
      <p className="mb-4 text-xs text-gray-400">
        {totalCharts} charts across your reports
      </p>
      <ul className="space-y-2.5">
        {mix.slice(0, 7).map(({ type, count }) => (
          <li key={type} className="flex items-center gap-3">
            <span className="w-24 shrink-0 truncate text-xs font-medium text-gray-600">
              {chartLabel(type)}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-primary/70"
                style={{ width: `${Math.max(8, (count / max) * 100)}%` }}
              />
            </div>
            <span className="w-5 shrink-0 text-right text-xs tabular-nums text-gray-400">
              {count}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ChartBadges({ types }: { types: string[] }) {
  if (!types.length) return <span className="text-xs text-gray-300">—</span>;
  const shown = types.slice(0, 3);
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((t) => (
        <span
          key={t}
          className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-500"
        >
          {chartLabel(t)}
        </span>
      ))}
      {types.length > shown.length && (
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-400">
          +{types.length - shown.length}
        </span>
      )}
    </div>
  );
}

function ReportsTable({
  reports,
  nameById,
  onOpen,
}: {
  reports: Report[];
  nameById: Map<string, string>;
  onOpen: (id: string) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs uppercase tracking-wider text-gray-400">
            <th className="px-4 py-3 font-medium">Report</th>
            <th className="px-4 py-3 font-medium">Dataset</th>
            <th className="px-4 py-3 font-medium">Charts</th>
            <th className="px-4 py-3 text-center font-medium">Sections</th>
            <th className="px-4 py-3 text-right font-medium">Cost</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 text-right font-medium">When</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {reports.map((r) => (
            <tr
              key={r.id}
              onClick={() => onOpen(r.id)}
              className="cursor-pointer transition-colors hover:bg-gray-50/70"
            >
              <td className="max-w-[240px] px-4 py-3">
                <p className="truncate font-medium text-gray-800">{r.title}</p>
              </td>
              <td className="max-w-[160px] px-4 py-3">
                <p className="truncate text-gray-500">
                  {nameById.get(r.dataset_id) ?? "—"}
                </p>
              </td>
              <td className="px-4 py-3">
                <ChartBadges types={r.chart_types ?? []} />
              </td>
              <td className="px-4 py-3 text-center tabular-nums text-gray-500">
                {r.section_count || "—"}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                {r.cost_usd != null ? formatInr(r.cost_usd) : "—"}
              </td>
              <td className="px-4 py-3">
                <StatusPill status={r.status} />
              </td>
              <td className="px-4 py-3 text-right text-xs text-gray-400">
                {relativeTime(r.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-16 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <UploadIcon />
      </div>
      <h2 className="text-lg font-semibold text-gray-900">
        Upload your first CSV
      </h2>
      <p className="mx-auto mt-1 max-w-sm text-sm text-gray-500">
        Visual AI profiles it, suggests the reports worth building, and writes
        each one with charts — no SQL or Python needed.
      </p>
      <button
        onClick={onUpload}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90"
      >
        <PlusIcon /> Upload CSV
      </button>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ready: "bg-green-100 text-green-700",
    profiling: "bg-amber-100 text-amber-700",
    uploading: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
        styles[status] ?? "bg-gray-100 text-gray-600"
      }`}
    >
      {status}
    </span>
  );
}

/* Compact a number: 54600 -> "54.6k", 1200000 -> "1.2M". */
function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  return String(n);
}

/* "3h ago", "2d ago", or a short date for older items. */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

/* ---------------------------------- icons --------------------------------- */
const sv = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const PlusIcon = () => (
  <svg {...sv}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);
const CoinIcon = () => (
  <svg {...sv}>
    <circle cx="12" cy="12" r="9" />
    <path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.9 2.5 2-1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5v11" />
  </svg>
);
const ChartIcon = () => (
  <svg {...sv}>
    <path d="M3 3v18h18" />
    <rect x="7" y="11" width="3" height="6" />
    <rect x="12" y="7" width="3" height="10" />
    <rect x="17" y="13" width="3" height="4" />
  </svg>
);
const GridIcon = () => (
  <svg {...sv}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
);
const LayersIcon = () => (
  <svg {...sv}>
    <path d="M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
  </svg>
);
const StarIcon = () => (
  <svg {...sv} width={13} height={13}>
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  </svg>
);
const FileIcon = () => (
  <svg {...sv}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6M8 13h8M8 17h5" />
  </svg>
);
const TrashIcon = () => (
  <svg {...sv}>
    <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
  </svg>
);
const UploadIcon = () => (
  <svg {...sv} width={24} height={24}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
  </svg>
);
