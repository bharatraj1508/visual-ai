"use client";

import { FormEvent, useState } from "react";

import { useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "react-toastify";

import AppHeader from "@/components/AppHeader";
import ChartRenderer from "@/components/chart/ChartRenderer";
import MarkdownMessage from "@/components/chat/MarkdownMessage";
import ThinkingIndicator from "@/components/chat/ThinkingIndicator";
import Spinner from "@/components/common/Spinner";
import { useChatStream } from "@/hooks/chat/useChatStream";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { useMessages } from "@/services/api/requests/chat";
import { ChatQueryKey } from "@/services/api/types/ChatQueryKey";
import { ChartSpec } from "@/types/chart";
import { ChartArtifact } from "@/types/chat";

// Friendly labels for the "what's the agent doing" indicator.
const TOOL_LABELS: Record<string, string> = {
  query_data: "Querying the data",
  describe_data: "Summarizing the data",
  value_counts: "Counting values",
  correlate: "Finding correlations",
  create_chart: "Creating a chart",
  run_python: "Running analysis",
};

function toolLabel(name?: string) {
  return (name && TOOL_LABELS[name]) || "Working";
}

function Bubble({
  role,
  children,
}: {
  role: "user" | "assistant";
  children: React.ReactNode;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`min-w-0 max-w-[85%] space-y-3 break-words rounded-lg px-4 py-3 text-sm sm:max-w-2xl ${
          isUser ? "bg-primary text-white" : "bg-white border border-gray-200"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const token = useRequireAuth();
  const { sessionId } = useParams<{ sessionId: string }>();
  const queryClient = useQueryClient();

  const { data: messages } = useMessages(sessionId);
  const { send, streaming } = useChatStream();

  const [draft, setDraft] = useState("");
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [liveText, setLiveText] = useState("");
  const [liveCharts, setLiveCharts] = useState<ChartArtifact["spec"][]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activity, setActivity] = useState<string>("Thinking");

  if (!token) return null;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || streaming) return;

    setDraft("");
    setPendingUser(content);
    setLiveText("");
    setLiveCharts([]);
    setStreamError(null);
    setActivity("Thinking");

    try {
      await send(sessionId, content, (streamEvent) => {
        switch (streamEvent.type) {
          case "token":
            setLiveText((prev) => prev + streamEvent.data);
            break;
          case "tool_start":
            setActivity(toolLabel(streamEvent.data?.name));
            break;
          case "tool_end":
            setActivity("Thinking");
            break;
          case "chart":
            setLiveCharts((prev) => [...prev, streamEvent.data.spec]);
            break;
          case "error": {
            const detail =
              streamEvent.data?.detail || "The assistant hit an error.";
            setStreamError(detail);
            toast.error(detail);
            break;
          }
          case "done":
            queryClient.invalidateQueries({
              queryKey: [ChatQueryKey.Messages, sessionId],
            });
            setPendingUser(null);
            setLiveText("");
            setLiveCharts([]);
            break;
        }
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "The request failed. Please try again.";
      setStreamError(message);
      toast.error(message);
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <AppHeader />
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden px-4 sm:px-6">
        <div className="flex-1 space-y-4 overflow-y-auto py-6">
          {messages?.map((message) => (
            <Bubble
              key={message.id}
              role={message.role === "user" ? "user" : "assistant"}
            >
              {message.content &&
                (message.role === "user" ? (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                ) : (
                  <MarkdownMessage content={message.content} />
                ))}
              {message.artifacts.map((artifact) => (
                <ChartRenderer
                  key={artifact.id}
                  spec={artifact.spec as unknown as ChartSpec}
                />
              ))}
            </Bubble>
          ))}

          {pendingUser && <Bubble role="user">{pendingUser}</Bubble>}

          {(streaming || liveText || liveCharts.length > 0) &&
            !streamError && (
              <Bubble role="assistant">
                {streaming && <ThinkingIndicator label={activity} />}
                {liveText && <MarkdownMessage content={liveText} />}
                {liveCharts.map((spec, index) => (
                  <ChartRenderer
                    key={index}
                    spec={spec as unknown as ChartSpec}
                  />
                ))}
              </Bubble>
            )}

          {streamError && (
            <Bubble role="assistant">
              <p className="whitespace-pre-wrap text-red-600">
                ⚠ {streamError}
              </p>
            </Bubble>
          )}
        </div>

        <form onSubmit={onSubmit} className="flex gap-2 border-t py-4">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask about your data…"
            className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={streaming}
            className="flex shrink-0 items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {streaming && <Spinner />} Send
          </button>
        </form>
      </div>
    </div>
  );
}
