"use client";

import { useCallback, useState } from "react";

import { baseApiURL } from "@/services/api/axios";
import store from "@/store";
import { ReportStreamEvent } from "@/types/report";
import { consumeSSE } from "@/utils/sse";

function safeParse(data: string) {
  try {
    return JSON.parse(data);
  } catch {
    return {};
  }
}

function toStreamEvent(event: string, data: string): ReportStreamEvent | null {
  switch (event) {
    case "token":
      return { type: "token", data };
    case "report_start":
    case "section_start":
    case "tool_start":
    case "tool_end":
    case "chart":
    case "section_end":
    case "report_done":
    case "error":
      return { type: event, data: safeParse(data) } as ReportStreamEvent;
    default:
      return null;
  }
}

/**
 * Streams report generation over SSE (GET /reports/{id}/stream). Uses fetch +
 * ReadableStream so we can attach the Bearer token, which EventSource can't.
 * Report runs are longer than chat turns, so the safety timeout is generous.
 */
export function useReportStream() {
  const [streaming, setStreaming] = useState(false);

  const start = useCallback(
    async (
      reportId: string,
      onEvent: (event: ReportStreamEvent) => void,
      options?: { fresh?: boolean; variant?: number },
    ) => {
      setStreaming(true);
      const token = store.getState().auth.accessToken;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 300_000);
      try {
        const params = new URLSearchParams();
        if (options?.fresh) params.set("fresh", "true");
        if (options?.variant) params.set("variant", String(options.variant));
        const query = params.toString();
        const response = await fetch(
          `${baseApiURL}/reports/${reportId}/stream${query ? `?${query}` : ""}`,
          {
            method: "GET",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          },
        );
        if (!response.ok) {
          let detail = `Request failed (${response.status})`;
          try {
            const body = await response.json();
            if (body?.detail) detail = String(body.detail);
          } catch {
            /* non-JSON body */
          }
          throw new Error(detail);
        }
        if (!response.body) {
          throw new Error("The server did not return a stream.");
        }
        await consumeSSE(response.body, ({ event, data }) => {
          const parsed = toStreamEvent(event, data);
          if (parsed) onEvent(parsed);
        });
      } catch (error) {
        if (controller.signal.aborted) {
          throw new Error("The report timed out. Please try again.");
        }
        throw error;
      } finally {
        clearTimeout(timeout);
        setStreaming(false);
      }
    },
    [],
  );

  return { start, streaming };
}
