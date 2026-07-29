import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ReportSuggestion } from "@/types/suggestion";

import api, { baseApiURL } from "../axios";
import { SuggestionQueryKey } from "../types/SuggestionQueryKey";

const baseURL = `${baseApiURL}`;

/**
 * Fetches a dataset's report suggestions. The first call triggers the AI
 * analysis on the backend, so expect this query to take a few seconds before
 * resolving — that latency is what the "analyzing" panel covers.
 */
export function useSuggestions(datasetId: string) {
  return useQuery({
    queryKey: [SuggestionQueryKey.Suggestions, datasetId],
    async queryFn() {
      const { data } = await api.get<ReportSuggestion[]>(
        `/datasets/${datasetId}/suggestions`,
        { baseURL },
      );
      return data;
    },
    enabled: !!datasetId,
    // The suggestion set is stable; don't re-analyze on every refocus.
    staleTime: Infinity,
    retry: false,
  });
}

export function useRegenerateSuggestions(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn() {
      const { data } = await api.post<ReportSuggestion[]>(
        `/datasets/${datasetId}/suggestions/regenerate`,
        undefined,
        { baseURL },
      );
      return data;
    },
    onSuccess(data) {
      queryClient.setQueryData(
        [SuggestionQueryKey.Suggestions, datasetId],
        data,
      );
    },
  });
}

/**
 * Turns the user's own question into a suggestion card. The backend validates
 * it against the dataset's columns first — a 422 means it was rejected and the
 * response `detail` carries a user-facing reason to show inline.
 */
export function useCreateCustomSuggestion(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(prompt: string) {
      const { data } = await api.post<ReportSuggestion>(
        `/datasets/${datasetId}/suggestions/custom`,
        { prompt },
        { baseURL },
      );
      return data;
    },
    onSuccess(suggestion) {
      queryClient.setQueryData<ReportSuggestion[]>(
        [SuggestionQueryKey.Suggestions, datasetId],
        (prev) => (prev ? [...prev, suggestion] : [suggestion]),
      );
    },
  });
}

export function useDismissSuggestion(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn(suggestionId: string) {
      return api.delete(`/suggestions/${suggestionId}`, { baseURL });
    },
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: [SuggestionQueryKey.Suggestions, datasetId],
      });
    },
  });
}
