"use client";

import { useCallback, useState } from "react";

import { baseApiURL } from "@/services/api/axios";
import store from "@/store";
import { ChatStreamEvent } from "@/types/chat";
import { consumeSSE } from "@/utils/sse";

const base = baseApiURL;

function toStreamEvent(event: string, data: string): ChatStreamEvent | null {
  switch (event) {
    case "token":
      return { type: "token", data };
    case "tool_start":
      return { type: "tool_start", data: safeParse(data) };
    case "tool_end":
      return { type: "tool_end", data: safeParse(data) };
    case "chart":
      return { type: "chart", data: safeParse(data) };
    case "done":
      return { type: "done", data: safeParse(data) };
    case "error":
      return { type: "error", data: safeParse(data) };
    default:
      return null;
  }
}

function safeParse(data: string) {
  try {
    return JSON.parse(data);
  } catch {
    return {};
  }
}

/**
 * Streams an agent turn over SSE (fetch + ReadableStream, since axios can't
 * stream in the browser). The Bearer token is read from Redux at send time.
 */
export function useChatStream() {
  const [streaming, setStreaming] = useState(false);

  const send = useCallback(
    async (
      sessionId: string,
      content: string,
      onEvent: (event: ChatStreamEvent) => void,
    ) => {
      setStreaming(true);
      const token = store.getState().auth.accessToken;
      // Safety net: never hang forever if the backend goes silent.
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120_000);
      try {
        const response = await fetch(
          `${base}/chat/sessions/${sessionId}/messages`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ content }),
            signal: controller.signal,
          },
        );
        if (!response.ok) {
          // The endpoint may reject before streaming (e.g. 503 missing key,
          // 401, 409). Surface the backend's `detail`.
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
          throw new Error("The request timed out. Please try again.");
        }
        throw error;
      } finally {
        clearTimeout(timeout);
        setStreaming(false);
      }
    },
    [],
  );

  return { send, streaming };
}
