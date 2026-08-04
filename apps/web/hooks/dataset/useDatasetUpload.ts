"use client";

import { useCallback, useRef, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";

import api, { baseApiURL } from "@/services/api/axios";
import { DatasetQueryKey } from "@/services/api/types/DatasetQueryKey";
import store from "@/store";
import {
  Dataset,
  ProcessingDone,
  ProcessingStep,
  ProcessingStreamEvent,
  UploadPhase,
} from "@/types/dataset";
import { consumeSSE } from "@/utils/sse";

export interface UploadState {
  phase: UploadPhase;
  /** Real byte-upload progress, 0–100. */
  progress: number;
  /** Live processing checklist, in the order steps first appeared. */
  steps: ProcessingStep[];
  /** Files the user picked (for the "Uploading N files" label). */
  fileCount: number;
  /** Set on the `error` event or a failed request. */
  error: string | null;
  /** Set on the `done` event once the dataset is ready to analyze. */
  result: ProcessingDone | null;
}

const INITIAL: UploadState = {
  phase: "idle",
  progress: 0,
  steps: [],
  fileCount: 0,
  error: null,
  result: null,
};

function safeParse(data: string) {
  try {
    return JSON.parse(data);
  } catch {
    return {};
  }
}

function toStreamEvent(event: string, data: string): ProcessingStreamEvent | null {
  switch (event) {
    case "step":
    case "done":
    case "error":
      return { type: event, data: safeParse(data) } as ProcessingStreamEvent;
    default:
      return null;
  }
}

/** Upsert a step by key, preserving first-seen order so the checklist is stable. */
function upsertStep(steps: ProcessingStep[], step: ProcessingStep): ProcessingStep[] {
  const i = steps.findIndex((s) => s.key === step.key);
  if (i === -1) return [...steps, step];
  const next = [...steps];
  next[i] = step;
  return next;
}

/**
 * Drives the whole upload → ready flow behind one loading screen:
 *  1. POST the files with real upload-progress (axios `onUploadProgress`).
 *  2. Open GET /datasets/{id}/process/stream and relay each `step` live.
 *  3. Resolve with the ready dataset id on `done`.
 *
 * fetch (not EventSource) is used for the stream so the Bearer token can be
 * attached, matching useReportStream.
 */
export function useDatasetUpload() {
  const [state, setState] = useState<UploadState>(INITIAL);
  const queryClient = useQueryClient();
  const controllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState(INITIAL);
  }, []);

  const start = useCallback(
    async (files: File[]): Promise<ProcessingDone | null> => {
      setState({ ...INITIAL, phase: "uploading", fileCount: files.length });

      // 1. Upload the raw bytes — this is the honest progress bar.
      let dataset: Dataset;
      try {
        const form = new FormData();
        for (const file of files) form.append("files", file);
        const { data } = await api.post<Dataset>("", form, {
          baseURL: `${baseApiURL}/datasets`,
          onUploadProgress: (e) => {
            // Hold at 99 until the server acknowledges — 100 means "received".
            setState((s) => ({
              ...s,
              progress: e.total
                ? Math.min(99, Math.round((e.loaded / e.total) * 100))
                : Math.min(99, s.progress + 1),
            }));
          },
        });
        dataset = data;
        setState((s) => ({ ...s, progress: 100 }));
      } catch (error) {
        const detail =
          (error as { response?: { data?: { detail?: unknown } } })?.response
            ?.data?.detail;
        setState((s) => ({
          ...s,
          phase: "error",
          error:
            typeof detail === "string"
              ? detail
              : "Upload failed. Please try again.",
        }));
        return null;
      }

      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });

      // 2. Stream processing (cluster → clean → profile → suggest).
      setState((s) => ({ ...s, phase: "processing" }));
      const token = store.getState().auth.accessToken;
      const controller = new AbortController();
      controllerRef.current = controller;
      // Generous ceiling — large multi-file datasets plus an LLM idea call.
      const timeout = setTimeout(() => controller.abort(), 300_000);
      let result: ProcessingDone | null = null;
      try {
        const response = await fetch(
          `${baseApiURL}/datasets/${dataset.id}/process/stream`,
          {
            method: "GET",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          },
        );
        if (!response.ok || !response.body) {
          let detail = `Processing failed (${response.status})`;
          try {
            const body = await response.json();
            if (body?.detail) detail = String(body.detail);
          } catch {
            /* non-JSON body */
          }
          throw new Error(detail);
        }
        await consumeSSE(response.body, ({ event, data }) => {
          const parsed = toStreamEvent(event, data);
          if (!parsed) return;
          if (parsed.type === "step") {
            setState((s) => ({ ...s, steps: upsertStep(s.steps, parsed.data) }));
          } else if (parsed.type === "done") {
            result = parsed.data;
            setState((s) => ({ ...s, phase: "done", result: parsed.data }));
          } else if (parsed.type === "error") {
            setState((s) => ({ ...s, phase: "error", error: parsed.data.detail }));
          }
        });
      } catch (error) {
        const message = controller.signal.aborted
          ? "Processing timed out. Please try again."
          : error instanceof Error
            ? error.message
            : "Processing failed. Please try again.";
        setState((s) =>
          // A `done` may have already arrived before the stream closed.
          s.phase === "done" ? s : { ...s, phase: "error", error: message },
        );
      } finally {
        clearTimeout(timeout);
        controllerRef.current = null;
        // The dataset row and its (now-generated) suggestions changed.
        queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
      }
      return result;
    },
    [queryClient],
  );

  return { state, start, reset };
}
