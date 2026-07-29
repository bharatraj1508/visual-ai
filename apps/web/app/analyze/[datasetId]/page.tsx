"use client";

import { useMemo, useState } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useParams, useRouter } from "next/navigation";

import AppHeader from "@/components/AppHeader";
import Breadcrumb from "@/components/Breadcrumb";
import EditableTitle from "@/components/EditableTitle";
import InsufficientCreditsModal from "@/components/InsufficientCreditsModal";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import {
  useDataset,
  usePreprocessDataset,
  useRenameDataset,
} from "@/services/api/requests/datasets";
import { useCreateReport, useReports } from "@/services/api/requests/reports";
import {
  useCreateCustomSuggestion,
  useDismissSuggestion,
  useRegenerateSuggestions,
  useSuggestions,
} from "@/services/api/requests/suggestions";
import { SuggestionQueryKey } from "@/services/api/types/SuggestionQueryKey";
import { PreprocessChange } from "@/types/dataset";
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
  const preprocess = usePreprocessDataset(datasetId);
  // Lifted out of the composer so the grid can show a skeleton card while the
  // problem statement is being crafted.
  const createCustom = useCreateCustomSuggestion(datasetId);

  const [busyId, setBusyId] = useState<string | null>(null);
  // Set when a generate attempt is rejected for insufficient credits (402).
  const [shortfall, setShortfall] = useState<
    { needed: number | null; available: number | null } | null
  >(null);

  // Group report versions by problem statement (same goal) so regenerations
  // stack into one card instead of showing as duplicates. Representative = the
  // newest version; opening it lands on the report page with all versions.
  const reportGroups = useMemo(() => {
    const map = new Map<string, { rep: Report; count: number }>();
    for (const r of reports ?? []) {
      const g = map.get(r.goal);
      if (!g) {
        map.set(r.goal, { rep: r, count: 1 });
      } else {
        g.count += 1;
        if (new Date(r.created_at) > new Date(g.rep.created_at)) g.rep = r;
      }
    }
    return Array.from(map.values()).sort(
      (a, b) => +new Date(b.rep.created_at) - +new Date(a.rep.created_at),
    );
  }, [reports]);

  if (!token) return null;

  const runPreprocess = () => {
    if (preprocess.isPending) return;
    preprocess.mutate(undefined, {
      onSuccess: () => {
        // The schema changed, so the old suggestions are stale — refresh them
        // on the cleaned data.
        queryClient.invalidateQueries({
          queryKey: [SuggestionQueryKey.Suggestions, datasetId],
        });
        regenerate.mutate(undefined, { onError: showError });
      },
      onError: showError,
    });
  };

  const changes = dataset?.preprocessing_summary ?? [];
  const needsPreprocess = !!dataset && !dataset.preprocessed && changes.length > 0;

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
          // Out of credits — show the buy-more modal (the only credit dialog;
          // there is no pre-generation cost confirmation).
          const err = error as AxiosError<{
            detail?: { needed?: number; available?: number };
          }>;
          if (err?.response?.status === 402) {
            const d = err.response?.data?.detail;
            setShortfall({
              needed: d?.needed ?? null,
              available: d?.available ?? null,
            });
            return;
          }
          showError(error);
        },
      },
    );
  };

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Breadcrumb
          items={[
            { label: "Dashboard", href: "/dashboard" },
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
            {(needsPreprocess ||
              (dataset?.preprocessed && changes.length > 0)) && (
              <PreprocessCard
                done={!!dataset?.preprocessed}
                changes={changes}
                busy={preprocess.isPending || regenerate.isPending}
                onRun={runPreprocess}
              />
            )}

            {reportGroups.length > 0 && (
              <section className="mb-10">
                <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
                  Generated reports
                </h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {reportGroups.map(({ rep, count }) => (
                    <GeneratedReportCard
                      key={rep.id}
                      report={rep}
                      versionCount={count}
                      onOpen={() => router.push(`/reports/${rep.id}`)}
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
              <PromptComposer
                pending={createCustom.isPending}
                onSubmit={createCustom.mutateAsync}
              {!suggestions?.length && !createCustom.isPending ? (
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
                  {createCustom.isPending && (
                    <SuggestionSkeletonCard question={createCustom.variables} />
                </div>
              )}
            </section>
          </>
        )}
      </main>

      <InsufficientCreditsModal
        open={shortfall !== null}
        needed={shortfall?.needed ?? null}
        available={shortfall?.available ?? null}
        onClose={() => setShortfall(null)}
      />
    </div>
  );
}

function PreprocessCard({
  done,
  changes,
  busy,
  onRun,
}: {
  done: boolean;
  changes: PreprocessChange[];
  busy: boolean;
  onRun: () => void;
}) {
  const accent = done
    ? "border-green-200 bg-green-50/60"
    : "border-amber-200 bg-amber-50/60";
  return (
    <section className={`mb-8 rounded-2xl border p-5 ${accent}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
              done ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
            }`}
          >
            {done ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            ) : (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18M7 12h10M10 18h4" />
              </svg>
            )}
          </span>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {done
                ? "Dataset cleaned"
                : "Pre-processing recommended"}
            </h3>
            <p className="mt-0.5 text-sm text-gray-600">
              {done
                ? "Reports are generated from the cleaned data. Applied:"
                : "We spotted data-quality issues worth fixing before generating reports:"}
            </p>
          </div>
        </div>
        {!done && (
          <button
            onClick={onRun}
            disabled={busy}
            className="shrink-0 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? "Pre-processing…" : "Pre-process now"}
          </button>
        )}
      </div>

      <ul className="mt-4 space-y-1.5 pl-11">
        {changes.map((c, i) => (
          <li key={i} className="flex gap-2 text-sm text-gray-600">
            <span className={done ? "text-green-600" : "text-amber-600"}>•</span>
            <span>
              <span className="font-medium text-gray-800">{c.title}.</span>{" "}
              {c.detail}
            </span>
          </li>
        ))}
      </ul>

      {!done && (
        <p className="mt-3 pl-11 text-xs text-gray-400">
          Non-destructive — your original file is kept, and only safe fixes are
          applied (no data is invented or dropped beyond exact duplicates).
        </p>
      )}
    </section>
  );
}

function GeneratedReportCard({
  report,
  versionCount = 1,
  onOpen,
}: {
  report: Report;
  versionCount?: number;
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
        <div className="flex items-center gap-2">
          {report.credit_cost != null && report.status === "completed" && (
            <span className="text-[11px] text-gray-400" title="Credits used">
              {report.credit_cost} credits
            </span>
          )}
          <StatusPill status={report.status} />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <h3 className="text-base font-semibold leading-snug text-gray-900">
          {report.title}
        </h3>
        {versionCount > 1 && (
          <span
            title={`${versionCount} versions`}
            className="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary"
          >
            +{versionCount - 1}
          </span>
        )}
      </div>
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

function PromptComposer({
        we&apos;ll turn it into a problem statement grounded in your data.
          {pending ? "Analyzing…" : "Add problem statement"}
 * into a problem statement — it occupies the slot the real card will fill.
function SuggestionSkeletonCard({ question }: { question?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
          Crafting problem statement…
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
        angles, or ask your own question above.
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
