"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useParams } from "next/navigation";
import { toast } from "react-toastify";

import AppHeader from "@/components/AppHeader";
import Breadcrumb from "@/components/Breadcrumb";
import ChartRenderer from "@/components/chart/ChartRenderer";
import MarkdownMessage from "@/components/chat/MarkdownMessage";
import ThinkingIndicator from "@/components/chat/ThinkingIndicator";
import Spinner from "@/components/common/Spinner";
import EditableTitle from "@/components/EditableTitle";
import InsufficientCreditsModal from "@/components/InsufficientCreditsModal";
import { useReportStream } from "@/hooks/report/useReportStream";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { useDataset } from "@/services/api/requests/datasets";
import {
  useArchiveReport,
  useRegenerateReport,
  useRenameReport,
  useReport,
  useReportVersions,
} from "@/services/api/requests/reports";
import { CreditQueryKey } from "@/services/api/types/CreditQueryKey";
import { ReportQueryKey } from "@/services/api/types/ReportQueryKey";
import { ChartSpec } from "@/types/chart";
import { ReportDetail, ReportSection } from "@/types/report";
import { downloadReportPdf, downloadReportsZip } from "@/utils/reportPdf";

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
  const archiveReport = useArchiveReport();
  const { start, streaming } = useReportStream();

  // PDF download state (null = idle, "all" = zipping, else a version id).
  const [downloading, setDownloading] = useState<string | null>(null);

  // Live-streaming state for the ONE version currently generating.
  const [activeId, setActiveId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveSection[]>([]);
  const [activity, setActivity] = useState("Planning the report");
  const [streamError, setStreamError] = useState<string | null>(null);
  const startedIds = useRef<Set<string>>(new Set());

  // Which panels are expanded. Default: newest open, the rest collapsed.
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());
  const defaultedOpen = useRef(false);

  // Set when a regenerate attempt is rejected for insufficient credits (402).
  const [shortfall, setShortfall] = useState<
    { needed: number | null; available: number | null } | null
  >(null);

  const ordered: ReportDetail[] = useMemo(
    () => versions ?? (report ? [report] : []),
    [versions, report],
  );
  const collapsible = ordered.length > 1;

  // Regeneration costs 1/3 of the original report (min 1) — mirrors the backend
  // REPORT_REGEN_DIVISOR. Based on the original version's charged cost.
  const originalCost = ordered[0]?.credit_cost ?? report?.credit_cost ?? null;
  const regenCost =
    originalCost != null ? Math.max(1, Math.round(originalCost / 3)) : null;

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
              // Credits were charged on completion — refresh the balance chip
              // so it updates immediately instead of going stale.
              queryClient.invalidateQueries({
                queryKey: [CreditQueryKey.Balance],
              });
              break;
            case "error":
              setStreamError(
                event.data.detail || "The report failed to generate.",
              );
              // Failed generation auto-refunds the hold — refresh the balance.
              queryClient.invalidateQueries({
                queryKey: [CreditQueryKey.Balance],
              });
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

  const onDownload = useCallback(async (version: ReportDetail) => {
    setDownloading(version.id);
    try {
      await downloadReportPdf(version);
    } catch {
      toast.error("Could not generate the PDF.");
    } finally {
      setDownloading(null);
    }
  }, []);

  const onDownloadAll = useCallback(async () => {
    setDownloading("all");
    try {
      await downloadReportsZip(ordered, report?.title ?? "report");
    } catch {
      toast.error("Could not generate the ZIP.");
    } finally {
      setDownloading(null);
    }
  }, [ordered, report?.title]);

  const onArchive = useCallback(
    (version: ReportDetail, index: number) => {
      archiveReport.mutate(
        { id: version.id, archived: true },
        {
          onSuccess: () => {
            toast.success(
              `${index === 0 ? "Original" : `Regeneration ${index}`} archived`,
            );
            queryClient.invalidateQueries({
              queryKey: [ReportQueryKey.Versions, reportId],
            });
          },
          onError: () => toast.error("Could not archive the report."),
        },
      );
    },
    [archiveReport, queryClient, reportId],
  );

  if (!token) return null;

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <Breadcrumb
          items={[
            { label: "Dashboard", href: "/dashboard" },
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
              className="text-2xl font-semibold tracking-tight text-gray-900 sm:text-3xl"
            />
          ) : (
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Report</h1>
          )}
          {report?.goal && (
            <p className="mt-2 text-sm leading-relaxed text-gray-500">
              {report.goal}
            </p>
          )}
          {collapsible && (
            <div className="mt-4">
              <button
                onClick={onDownloadAll}
                disabled={downloading !== null}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-50"
              >
                {downloading === "all" ? <Spinner /> : <ZipIcon />}
                Download all ({ordered.length}) as ZIP
              </button>
            </div>
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
                regenCost={regenCost}
                anyStreaming={streaming}
                onDownload={() => onDownload(version)}
                onArchive={() => onArchive(version, i)}
                downloading={downloading === version.id}
                canArchive={collapsible}
              />
            );
          })}
        </div>
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
  regenCost,
  anyStreaming,
  onDownload,
  onArchive,
  downloading,
  canArchive,
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
  regenCost: number | null;
  anyStreaming: boolean;
  onDownload: () => void;
  onArchive: () => void;
  downloading: boolean;
  canArchive: boolean;
}) {
  const label = index === 0 ? "Original" : `Regeneration ${index}`;
  const failed = version.status === "failed" || !!streamError;
  const showRetry = !streamingThis && failed;
  const done = version.status === "completed";

  const header = (
    <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
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
      <div className="flex shrink-0 flex-wrap items-center gap-3">
        {version.status === "completed" && version.credit_cost != null && (
          <CreditBadge credits={version.credit_cost} />
        )}
        {done && (
          <button
            type="button"
            onClick={onDownload}
            disabled={downloading}
            title="Download this report as PDF"
            aria-label="Download this report as PDF"
            className="rounded-md border border-gray-200 p-1.5 text-gray-500 transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-50"
          >
            {downloading ? <Spinner /> : <DownloadIcon />}
          </button>
        )}
        {canArchive && done && (
          <button
            type="button"
            onClick={onArchive}
            title="Archive this version"
            aria-label="Archive this version"
            className="rounded-md border border-gray-200 p-1.5 text-gray-400 transition-colors hover:border-amber-300 hover:text-amber-600"
          >
            <ArchiveIcon />
          </button>
        )}
        <div className="flex items-center gap-2">
          {regenCost != null && (
            <span className="text-[11px] text-gray-400">
              Regeneration costs {regenCost} credit
              {regenCost === 1 ? "" : "s"}
            </span>
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
    </div>
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
      {header}
      {open && (
        <div className="border-t border-gray-100 px-3 pb-6 pt-5 sm:px-4">
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
                <h2 className="mb-4 text-lg font-semibold tracking-tight text-gray-900 sm:text-xl">
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

function CreditBadge({ credits }: { credits: number }) {
  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5"
      title="Credits used for this report"
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5 text-primary" aria-hidden>
        <ellipse cx="12" cy="7" rx="7" ry="3" fill="currentColor" opacity="0.9" />
        <path d="M5 7v6c0 1.66 3.13 3 7 3s7-1.34 7-3V7" stroke="currentColor" strokeWidth="1.6" opacity="0.5" />
      </svg>
      <span className="text-sm font-semibold text-ink">{credits} credits</span>
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

const iconSvg = {
  width: 15,
  height: 15,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
const DownloadIcon = () => (
  <svg {...iconSvg}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
  </svg>
);
const ZipIcon = () => (
  <svg {...iconSvg} width={16} height={16}>
    <path d="M21 8v13H3V3h10M14 3v5h7M14 3l7 5M9 13h2M9 17h2" />
  </svg>
);
const ArchiveIcon = () => (
  <svg {...iconSvg}>
    <rect x="3" y="4" width="18" height="4" rx="1" />
    <path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4" />
  </svg>
);
