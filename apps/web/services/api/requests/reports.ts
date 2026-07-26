import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Report, ReportDetail } from "@/types/report";

import api, { baseApiURL } from "../axios";
import { ReportQueryKey } from "../types/ReportQueryKey";

const baseURL = `${baseApiURL}/reports`;

/** All of the user's reports, optionally scoped to one dataset. */
export function useReports(datasetId?: string) {
  return useQuery({
    queryKey: [ReportQueryKey.Reports, datasetId ?? "all"],
    async queryFn() {
      const { data } = await api.get<Report[]>("", {
        baseURL,
        params: datasetId ? { dataset_id: datasetId } : undefined,
      });
      return data;
    },
    // Report status changes out-of-band while it generates, so always refetch
    // on mount and poll while any report is still running.
    staleTime: 0,
    refetchOnMount: "always",
    refetchInterval: (query) =>
      (query.state.data as Report[] | undefined)?.some(
        (report) => report.status === "running",
      )
        ? 4000
        : false,
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: [ReportQueryKey.Report, id],
    async queryFn() {
      const { data } = await api.get<ReportDetail>(`/${id}`, { baseURL });
      return data;
    },
    enabled: !!id,
  });
}

/** All versions of a report's problem statement (same dataset + goal), oldest
 * first: the original at the top, regenerations appended below. */
export function useReportVersions(id: string) {
  return useQuery({
    queryKey: [ReportQueryKey.Versions, id],
    async queryFn() {
      const { data } = await api.get<ReportDetail[]>(`/${id}/versions`, {
        baseURL,
      });
      return data;
    },
    enabled: !!id,
    staleTime: 0,
    refetchOnMount: "always",
    // Poll while any version is still generating so a new one flips to completed.
    refetchInterval: (query) =>
      (query.state.data as ReportDetail[] | undefined)?.some(
        (r) => r.status === "running",
      )
        ? 4000
        : false,
  });
}

/** Creates a brand-new report version for the same problem statement. The caller
 * streams it with `fresh` so the result cache is bypassed. */
export function useRegenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(sourceId: string) {
      const { data } = await api.post<Report>(
        `/${sourceId}/regenerate`,
        undefined,
        { baseURL },
      );
      return data;
    },
    onSuccess(_report, sourceId) {
      queryClient.invalidateQueries({
        queryKey: [ReportQueryKey.Versions, sourceId],
      });
      queryClient.invalidateQueries({ queryKey: [ReportQueryKey.Reports] });
    },
  });
}

export interface CreateReportPayload {
  dataset_id: string;
  suggestion_id?: string;
  goal?: string;
  title?: string;
}

export function useRenameReport(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(title: string) {
      const { data } = await api.patch<Report>(`/${id}`, { title }, { baseURL });
      return data;
    },
    onSuccess(data) {
      queryClient.setQueryData<ReportDetail | undefined>(
        [ReportQueryKey.Report, id],
        (old) => (old ? { ...old, title: data.title } : old),
      );
      queryClient.invalidateQueries({ queryKey: [ReportQueryKey.Reports] });
    },
  });
}

/** Creates the report row (status `running`); generation streams separately. */
export function useCreateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(payload: CreateReportPayload) {
      const { data } = await api.post<Report>("", payload, { baseURL });
      return data;
    },
    onSuccess(_report, variables) {
      queryClient.invalidateQueries({
        queryKey: [ReportQueryKey.Reports, variables.dataset_id],
      });
    },
  });
}
