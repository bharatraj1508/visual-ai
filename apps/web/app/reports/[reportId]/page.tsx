"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
import { useRenameReport, useReport } from "@/services/api/requests/reports";
import { ReportQueryKey } from "@/services/api/types/ReportQueryKey";
import { ChartSpec } from "@/types/chart";
import { ReportSection } from "@/types/report";

const TOOL_LABELS: Record<string, string> = {
  query_data: "Querying the data",
  describe_data: "Summarizing the data",
  value_counts: "Counting values",
  correlate: "Finding correlations",
  create_chart: "Building a chart",
  run_python: "Running analysis",
};

type LiveSection = { title: string; narrative: string; charts: ChartSpec[] };

export default function ReportPage() {
  const token = useRequireAuth();
  const { reportId } = useParams<{ reportId: string }>();
  const queryClient = useQueryClient();

  const { data: report } = useReport(reportId);
  const { data: dataset } = useDataset(report?.dataset_id ?? "");
  const renameReport = useRenameReport(reportId);
  const { start, streaming } = useReportStream();

  const [live, setLive] = useState<LiveSection[]>([]);
  const [activity, setActivity] = useState("Planning the report");
  const [streamError, setStreamError] = useState<string | null>(null);
  const started = useRef(false);

  const runStream = useCallback(() => {
    started.current = true;
    setStreamError(null);
    setLive([]);
    setActivity("Planning the report");

    start(reportId, (event) => {
      switch (event.type) {
        case "section_start":
          setActivity(`Writing "${event.data.title}"`);
          setLive((prev) => [
            ...prev,
            { title: event.data.title, narrative: "", charts: [] },
          ]);
          break;
        case "token":
          setLive((prev) => appendToLast(prev, (s) => ({
            ...s,
            narrative: s.narrative + event.data,
          })));
          break;
        case "tool_start":
          setActivity(TOOL_LABELS[event.data.name ?? ""] ?? "Working");
          break;
        case "chart":
          setLive((prev) => appendToLast(prev, (s) => ({
            ...s,
            charts: [...s.charts, event.data.spec],
          })));
          break;
        case "report_done":
          queryClient.invalidateQueries({
            queryKey: [ReportQueryKey.Report, reportId],
          });
          // Refresh the analyze panel's list so its status stops showing "running".
          queryClient.invalidateQueries({ queryKey: [ReportQueryKey.Reports] });
          break;
        case "error":
          setStreamError(event.data.detail || "The report failed to generate.");
          break;
      }
    }).catch((error) => {
      setStreamError(
        error instanceof Error ? error.message : "The report failed to generate.",
      );
    });
  }, [reportId, start, queryClient]);

  useEffect(() => {
    if (!report || started.current) return;
    if (report.status !== "running") return;
    runStream();
  }, [report, runStream]);

  if (!token) return null;

  const showRetry =
    !streaming && (!!streamError || report?.status === "failed");

  const completed = report?.status === "completed" && report.content;
  const sections: (ReportSection | LiveSection)[] = completed
    ? (report!.content as ReportSection[])
    : live;

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

        {(streamError || report?.status === "failed") && (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <span>
              ⚠ {streamError || report?.error || "This report failed to generate."}
            </span>
            {showRetry && (
              <button
                onClick={runStream}
                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700"
              >
                Try again
              </button>
            )}
          </div>
        )}

        {!completed && streaming && (
          <div className="sticky top-4 z-10 mb-8 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 shadow-sm backdrop-blur">
            <ThinkingIndicator label={activity} />
          </div>
        )}

        <div className="space-y-12">
          {sections.map((section, i) => (
            <section key={i} className="scroll-mt-8">
              <h2 className="mb-4 text-xl font-semibold tracking-tight text-gray-900">
                {section.title}
              </h2>
              {/* While streaming, render the narrative as plain text — partial
                  Markdown (a lone "#" or "**") would flash as giant headings.
                  The finished report renders as Markdown for the clean look. */}
              {section.narrative &&
                (completed ? (
                  <MarkdownMessage content={section.narrative} />
                ) : (
                  <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-gray-600">
                    {section.narrative}
                  </p>
                ))}
              {section.charts.length > 0 && (
                <div className="mt-5 space-y-5">
                  {section.charts.map((spec, ci) => (
                    <ChartRenderer key={ci} spec={spec} />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      </main>
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
