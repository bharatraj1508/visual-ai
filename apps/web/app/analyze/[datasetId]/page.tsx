"use client";

import { useState } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";

import AppHeader from "@/components/AppHeader";
import Breadcrumb from "@/components/Breadcrumb";
import EditableTitle from "@/components/EditableTitle";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { useDataset, useRenameDataset } from "@/services/api/requests/datasets";
import { useCreateReport, useReports } from "@/services/api/requests/reports";
import {
  useDismissSuggestion,
  useRegenerateSuggestions,
  useSuggestions,
} from "@/services/api/requests/suggestions";
import { SuggestionQueryKey } from "@/services/api/types/SuggestionQueryKey";
import { Report } from "@/types/report";
import { ReportSuggestion } from "@/types/suggestion";

const CHART_LABELS: Record<string, string> = {
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

const chartLabel = (type: string) =>
  CHART_LABELS[type] ?? type.replace(/_/g, " ");

export default function AnalyzePage() {
  const token = useRequireAuth();
  const { datasetId } = useParams<{ datasetId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const showError = useShowApiErrorMessage();

  const { data: dataset } = useDataset(datasetId);
  const renameDataset = useRenameDataset(datasetId);
  const {
    data: suggestions,
    isLoading,
    isError,
  } = useSuggestions(datasetId);
  const { data: reports } = useReports(datasetId);

  const createReport = useCreateReport();
  const dismiss = useDismissSuggestion(datasetId);
  const regenerate = useRegenerateSuggestions(datasetId);

  const [busyId, setBusyId] = useState<string | null>(null);

  if (!token) return null;

  const generate = (suggestion: ReportSuggestion) => {
    if (busyId) return;
    setBusyId(suggestion.id);
    createReport.mutate(
      { dataset_id: datasetId, suggestion_id: suggestion.id },
      {
        onSuccess: (report) => {
          queryClient.invalidateQueries({
            queryKey: [SuggestionQueryKey.Suggestions, datasetId],
          });
          router.push(`/reports/${report.id}`);
        },
        onError: (error) => {
          setBusyId(null);
          showError(error);
        },
      },
    );
  };

  const generatedReports = reports ?? [];

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Breadcrumb
          items={[
            { label: "Datasets", href: "/dashboard" },
            { label: dataset?.filename ?? "Analyze" },
          ]}
        />

        <div className="mb-8">
          {dataset ? (
            <EditableTitle
              as="h1"
              value={dataset.filename}
              onSave={(filename) => renameDataset.mutate(filename)}
              saving={renameDataset.isPending}
              ariaLabel="Rename dataset"
              className="text-2xl font-semibold tracking-tight text-gray-900"
            />
          ) : (
            <h1 className="text-2xl font-semibold tracking-tight">
              Your dataset
            </h1>
          )}
          <p className="mt-1 text-sm text-gray-500">
            {dataset?.row_count != null
              ? `${dataset.row_count.toLocaleString()} rows · ${dataset.col_count} columns`
              : "Analyzed by AI to suggest the reports worth generating."}
          </p>
        </div>

        {isLoading ? (
          <Analyzing filename={dataset?.filename} />
        ) : isError ? (
          <ErrorPanel />
        ) : (
          <>
            {generatedReports.length > 0 && (
              <section className="mb-10">
                <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Generated reports
                </h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {generatedReports.map((report) => (
                    <GeneratedReportCard
                      key={report.id}
                      report={report}
                      onOpen={() => router.push(`/reports/${report.id}`)}
                    />
                  ))}
                </div>
              </section>
            )}

            <section>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Suggested reports
                </h2>
                <button
                  onClick={() => regenerate.mutate(undefined, { onError: showError })}
                  disabled={regenerate.isPending}
                  className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-primary disabled:opacity-50"
                >
                  {regenerate.isPending && <Spinner />}
                  Regenerate ideas
                </button>
              </div>

              {!suggestions?.length ? (
                <EmptyPanel />
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {suggestions.map((suggestion, index) => (
                    <SuggestionCard
                      key={suggestion.id}
                      index={index}
                      suggestion={suggestion}
                      busy={busyId === suggestion.id}
                      disabled={!!busyId}
                      onGenerate={() => generate(suggestion)}
                      onDismiss={() =>
                        dismiss.mutate(suggestion.id, { onError: showError })
                      }
                    />
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function GeneratedReportCard({
  report,
  onOpen,
}: {
  report: Report;
  onOpen: () => void;
}) {
  const running = report.status === "running";
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className="group relative flex cursor-pointer flex-col rounded-2xl border border-gray-200 bg-white p-5 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <rect x="7" y="11" width="3" height="6" />
            <rect x="12" y="7" width="3" height="10" />
            <rect x="17" y="13" width="3" height="4" />
          </svg>
        </span>
        <StatusPill status={report.status} />
      </div>

      <h3 className="text-base font-semibold leading-snug text-gray-900">
        {report.title}
      </h3>
      <p className="mt-1.5 line-clamp-3 text-sm text-gray-500">{report.goal}</p>

      <div className="mt-5 flex items-center gap-2 text-sm font-medium text-primary">
        {running ? (
          <>
            <Spinner /> Generating…
          </>
        ) : (
          <>
            View report
            <span className="transition-transform group-hover:translate-x-0.5">→</span>
          </>
        )}
      </div>
    </div>
  );
}

function SuggestionCard({
  index,
  suggestion,
  busy,
  disabled,
  onGenerate,
  onDismiss,
}: {
  index: number;
  suggestion: ReportSuggestion;
  busy: boolean;
  disabled: boolean;
  onGenerate: () => void;
  onDismiss: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !disabled && onGenerate()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          onGenerate();
        }
      }}
      className={`group relative flex flex-col rounded-2xl border border-gray-200 bg-white p-5 text-left transition-all ${
        disabled
          ? "cursor-default opacity-60"
          : "cursor-pointer hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
      }`}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {index + 1}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          aria-label="Dismiss suggestion"
          className="-mr-1 -mt-1 rounded-md p-1 text-gray-300 transition-colors hover:bg-gray-100 hover:text-gray-600"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <h3 className="text-base font-semibold leading-snug text-gray-900">
        {suggestion.title}
      </h3>
      <p className="mt-1.5 text-sm text-gray-600">{suggestion.question}</p>
      <p className="mt-2 text-sm leading-relaxed text-gray-400">
        {suggestion.rationale}
      </p>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {suggestion.chart_types.map((type) => (
          <span
            key={type}
            className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500"
          >
            {chartLabel(type)}
          </span>
        ))}
      </div>

      <div className="mt-5 flex items-center gap-2 text-sm font-medium text-primary">
        {busy ? (
          <>
            <Spinner /> Starting…
          </>
        ) : (
          <>
            Generate report
            <span className="transition-transform group-hover:translate-x-0.5">→</span>
          </>
        )}
      </div>
    </div>
  );
}

function Analyzing({ filename }: { filename?: string }) {
  return (
    <div>
      <div className="mb-8 flex items-center gap-4 rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-primary" />
        </span>
        <div>
          <p className="font-medium text-gray-900">
            Analyzing {filename ? <span className="text-primary">{filename}</span> : "your data"} with AI
          </p>
          <p className="text-sm text-gray-500">
            Finding the reports worth generating from this dataset…
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-52 animate-pulse rounded-2xl border border-gray-200 bg-white p-5"
          >
            <div className="mb-4 h-7 w-7 rounded-full bg-gray-100" />
            <div className="mb-2 h-4 w-2/3 rounded bg-gray-100" />
            <div className="mb-2 h-3 w-full rounded bg-gray-100" />
            <div className="h-3 w-4/5 rounded bg-gray-100" />
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyPanel() {
  return (
    <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-10 text-center">
      <p className="text-gray-500">
        No suggestions left. Regenerate ideas to explore this dataset from new
        angles.
      </p>
    </div>
  );
}

function ErrorPanel() {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      We couldn&apos;t analyze this dataset. Make sure it finished processing,
      then try again.
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    running: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] ?? "bg-gray-100 text-gray-600"
      }`}
    >
      {status}
    </span>
  );
}
