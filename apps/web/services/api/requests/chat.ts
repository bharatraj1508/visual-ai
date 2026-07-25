import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ChatSession, Message } from "@/types/chat";

import api, { baseApiURL } from "../axios";
import { ChatQueryKey } from "../types/ChatQueryKey";

const baseURL = `${baseApiURL}/chat`;

export function useSessions() {
  return useQuery({
    queryKey: [ChatQueryKey.Sessions],
    async queryFn() {
      const { data } = await api.get<ChatSession[]>("/sessions", { baseURL });
      return data;
    },
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(payload: { dataset_id: string; title?: string }) {
      const { data } = await api.post<ChatSession>("/sessions", payload, {
        baseURL,
      });
      return data;
    },
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: [ChatQueryKey.Sessions] });
    },
  });
}

export function useMessages(sessionId: string) {
  return useQuery({
    queryKey: [ChatQueryKey.Messages, sessionId],
    async queryFn() {
      const { data } = await api.get<Message[]>(
        `/sessions/${sessionId}/messages`,
        { baseURL },
      );
      return data;
    },
    enabled: !!sessionId,
  });
}
