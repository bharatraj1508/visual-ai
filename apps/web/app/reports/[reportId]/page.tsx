"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import AppHeader from "@/components/AppHeader";
import Breadcrumb from "@/components/Breadcrumb";
import ChartRenderer from "@/components/chart/ChartRenderer";
import MarkdownMessage from "@/components/chat/MarkdownMessage";
import ThinkingIndicator from "@/components/chat/ThinkingIndicator";
import EditableTitle from "@/components/EditableTitle";
import { useReportStream } from "@/hooks/report/useReportStream";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { useDataset } from "@/services/api/requests/datasets";
import {
  useRegenerateReport,
  useRenameReport,
  useReport,
  useReportVersions,
} from "@/services/api/requests/reports";
import { ReportQueryKey } from "@/services/api/types/ReportQueryKey";
import { ChartSpec } from "@/types/chart";
import { ReportDetail, ReportSection } from "@/types/report";
import { formatInr, formatUsd } from "@/utils/currency";

type LiveSection = { title: string; narrative: string; charts: ChartSpec[] };

export default function ReportPage() {
  const token = useRequireAuth();
  const { reportId } = useParams<{ reportId: string }>();
  const queryClient = useQueryClient();

  const { data: report } = useReport(reportId);
  const { data: versions } = useReportVersions(reportId);
  const { data: dataset } = useDataset(report?.dataset_id ?? "");
  const renameReport = useRenameReport(reportId);
  const regenerate = useRegenerateReport();
  const { start, streaming } = useReportStream();

  // Live-streaming state for the ONE version currently generating.
  const [activeId, setActiveId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveSection[]>([]);
  const [activity, setActivity] = useState("Planning the report");
  const [streamError, setStreamError] = useState<string | null>(null);
  const startedIds = useRef<Set<string>>(new Set());

  // Which panels are expanded. Default: newest open, the rest collapsed.
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());
  const defaultedOpen = useRef(false);

  const ordered: ReportDetail[] = useMemo(
    () => versions ?? (report ? [report] : []),
    [versions, report],
  );
  const collapsible = ordered.length > 1;

  const runStream = useCallback(
    (id: string, options?: { fresh?: boolean; variant?: number }) => {
      setActiveId(id);
      setStreamError(null);
      setLive([]);
      setActivity("Planning the report");

      start(
        id,
        (event) => {
          switch (event.type) {
            case "section_start":
              setActivity(`Writing "${event.data.title}"`);
              setLive((prev) => [
                ...prev,
                { title: event.data.title, narrative: "", charts: [] },
              ]);
              break;
            case "token":
              setLive((prev) =>
                appendToLast(prev, (s) => ({
                  ...s,
                  narrative: s.narrative + event.data,
                })),
              );
              break;
            case "chart":
              setLive((prev) =>
                appendToLast(prev, (s) => ({
                  ...s,
                  charts: [...s.charts, event.data.spec],
                })),
              );
              break;
            case "report_done":
              queryClient.invalidateQueries({
                queryKey: [ReportQueryKey.Report, id],
              });
              queryClient.invalidateQueries({
                queryKey: [ReportQueryKey.Versions, reportId],
              });
              queryClient.invalidateQueries({
                queryKey: [ReportQueryKey.Reports],
              });
              break;
            case "error":
              setStreamError(
                event.data.detail || "The report failed to generate.",
              );
              break;
          }
        },
        options,
      ).catch((error) => {
        setStreamError(
          error instanceof Error
            ? error.message
            : "The report failed to generate.",
        );
      });
    },
    [start, queryClient, reportId],
  );

  // Auto-stream any version that is still running (e.g. the original on first
  // load, or a reload mid-generation). Regenerations are started explicitly.
  useEffect(() => {
    const running = ordered.find(
      (v) => v.status === "running" && !startedIds.current.has(v.id),
    );
    if (running) {
      startedIds.current.add(running.id);
      runStream(running.id);
    }
  }, [ordered, runStream]);

  // Default the newest version open once, when versions first load. A ref guard
  // means manually collapsing every panel doesn't spring the newest back open.
  useEffect(() => {
    if (!defaultedOpen.current && ordered.length) {
      defaultedOpen.current = true;
      setOpenIds(new Set([ordered[ordered.length - 1].id]));
    }
  }, [ordered]);

  const onRegenerate = useCallback(async () => {
    try {
      const created = await regenerate.mutateAsync(reportId);
      startedIds.current.add(created.id);
      setOpenIds(new Set([created.id])); // only the new one open; collapse the rest
      runStream(created.id, { fresh: true, variant: ordered.length });
    } catch (error) {
      setStreamError(
        error instanceof Error ? error.message : "Could not start a new report.",
      );
    }
  }, [regenerate, reportId, runStream, ordered.length]);

  const toggle = useCallback((id: string) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  if (!token) return null;

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-3xl px-6 py-8">
        <Breadcrumb
          items={[
            { label: "Datasets", href: "/dashboard" },
            {
              label: dataset?.filename ?? "Analyze",
              href: report ? `/analyze/${report.dataset_id}` : undefined,
            },
            { label: report?.title ?? "Report" },
          ]}
        />

        <header className="mb-8 border-b border-gray-200 pb-6">
          {report ? (
            <EditableTitle
              as="h1"
              value={report.title}
              onSave={(title) => renameReport.mutate(title)}
              saving={renameReport.isPending}
              ariaLabel="Rename report"
              className="text-3xl font-semibold tracking-tight text-gray-900"
            />
          ) : (
            <h1 className="text-3xl font-semibold tracking-tight">Report</h1>
          )}
          {report?.goal && (
            <p className="mt-2 text-sm leading-relaxed text-gray-500">
              {report.goal}
            </p>
          )}
        </header>

        <div className="space-y-6">
          {ordered.map((version, i) => {
            const isActive = activeId === version.id;
            const streamingThis = streaming && isActive;
            const persisted = version.content ?? [];
            const sections: (ReportSection | LiveSection)[] = streamingThis
              ? live
              : persisted.length
                ? persisted
                : isActive
                  ? live
                  : [];
            const open = !collapsible || openIds.has(version.id);
            return (
              <VersionPanel
                key={version.id}
                version={version}
                index={i}
                collapsible={collapsible}
                open={open}
                onToggle={() => toggle(version.id)}
                sections={sections}
                streamingThis={streamingThis}
                activity={activity}
                streamError={isActive ? streamError : null}
                onRetry={() => runStream(version.id)}
                onRegenerate={onRegenerate}
                regenerating={regenerate.isPending}
                anyStreaming={streaming}
              />
            );
          })}
        </div>
      </main>
    </div>
  );
}

function VersionPanel({
  version,
  index,
  collapsible,
  open,
  onToggle,
  sections,
  streamingThis,
  activity,
  streamError,
  onRetry,
  onRegenerate,
  regenerating,
  anyStreaming,
}: {
  version: ReportDetail;
  index: number;
  collapsible: boolean;
  open: boolean;
  onToggle: () => void;
  sections: (ReportSection | LiveSection)[];
  streamingThis: boolean;
  activity: string;
  streamError: string | null;
  onRetry: () => void;
  onRegenerate: () => void;
  regenerating: boolean;
  anyStreaming: boolean;
}) {
  const label = index === 0 ? "Original" : `Regeneration ${index}`;
  const failed = version.status === "failed" || !!streamError;
  const showRetry = !streamingThis && failed;

  const header = (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <button
        type="button"
        onClick={collapsible ? onToggle : undefined}
        className={`flex min-w-0 items-center gap-2 text-left ${
          collapsible ? "cursor-pointer" : "cursor-default"
        }`}
        aria-expanded={open}
      >
        {collapsible && (
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 text-gray-400 transition-transform ${
              open ? "rotate-90" : ""
            }`}
          >
            <path d="M9 18l6-6-6-6" />
          </svg>
        )}
        <span className="truncate text-sm font-semibold text-gray-900">
          {label}
        </span>
        <span className="shrink-0 text-xs text-gray-400">
          {formatWhen(version.created_at)}
        </span>
        {streamingThis && (
          <span className="shrink-0 text-xs font-medium text-primary">
            · generating…
          </span>
        )}
      </button>
      <div className="flex shrink-0 items-center gap-3">
        {version.status === "completed" && version.cost_usd != null && (
          <CostBadge
            cost={version.cost_usd}
            inputTokens={version.input_tokens}
            outputTokens={version.output_tokens}
          />
        )}
        <button
          type="button"
          onClick={onRegenerate}
          disabled={regenerating || anyStreaming}
          title="Generate a new version of this report"
          className="rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {regenerating ? "Starting…" : "Regenerate"}
        </button>
      </div>
    </div>
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
      {header}
      {open && (
        <div className="border-t border-gray-100 px-4 pb-6 pt-5">
          {failed && (
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <span>
                ⚠ {streamError || version.error || "This report failed to generate."}
              </span>
              {showRetry && (
                <button
                  onClick={onRetry}
                  className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700"
                >
                  Try again
                </button>
              )}
            </div>
          )}

          {streamingThis && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3">
              <ThinkingIndicator label={activity} />
            </div>
          )}

          <div className="space-y-12">
            {sections.map((section, i) => (
              <div key={i} className="scroll-mt-8">
                <h2 className="mb-4 text-xl font-semibold tracking-tight text-gray-900">
                  {section.title}
                </h2>
                {section.narrative && (
                  <MarkdownMessage content={section.narrative} />
                )}
                {section.charts.length > 0 && (
                  <div className="mt-5 space-y-5">
                    {section.charts.map((spec, ci) => (
                      <ChartRenderer key={ci} spec={spec} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function formatWhen(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatTokens(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;
}

function CostBadge({
  cost,
  inputTokens,
  outputTokens,
}: {
  cost: number;
  inputTokens: number | null;
  outputTokens: number | null;
}) {
  const total = (inputTokens ?? 0) + (outputTokens ?? 0);
  const detail =
    inputTokens != null && outputTokens != null
      ? `${formatTokens(inputTokens)} in · ${formatTokens(outputTokens)} out`
      : `${formatTokens(total)} tokens`;
  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5"
      title={`${inputTokens ?? 0} input + ${outputTokens ?? 0} output tokens`}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FB676E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.9 2.5 2-1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5v11" />
      </svg>
      <span className="text-sm font-semibold text-ink">{formatInr(cost)}</span>
      <span className="text-xs text-gray-400">({formatUsd(cost)})</span>
      <span className="hidden font-mono text-[11px] text-gray-400 sm:inline">
        · {detail}
      </span>
    </div>
  );
}

function appendToLast(
  sections: LiveSection[],
  update: (section: LiveSection) => LiveSection,
): LiveSection[] {
  if (sections.length === 0) return sections;
  const next = [...sections];
  next[next.length - 1] = update(next[next.length - 1]);
  return next;
}
