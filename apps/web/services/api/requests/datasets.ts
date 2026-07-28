import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dataset, DatasetProfile } from "@/types/dataset";

import api, { baseApiURL } from "../axios";
import { DatasetQueryKey } from "../types/DatasetQueryKey";

const baseURL = `${baseApiURL}/datasets`;

export function useDatasets(archived = false) {
  return useQuery({
    queryKey: [DatasetQueryKey.Datasets, "list", archived],
    async queryFn() {
      const { data } = await api.get<Dataset[]>("", {
        baseURL,
        params: { archived },
      });
      return data;
    },
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: [DatasetQueryKey.Datasets, id],
    async queryFn() {
      const { data } = await api.get<Dataset>(`/${id}`, { baseURL });
      return data;
    },
    enabled: !!id,
  });
}

export function useDatasetProfile(id: string) {
  return useQuery({
    queryKey: [DatasetQueryKey.DatasetProfile, id],
    async queryFn() {
      const { data } = await api.get<DatasetProfile>(`/${id}/profile`, {
        baseURL,
      });
      return data;
    },
    enabled: !!id,
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(files: File[]) {
      // Multiple files are combined server-side into one dataset. A single file
      // still works — it's just a one-element list.
      const form = new FormData();
      for (const file of files) form.append("files", file);
      const { data } = await api.post<Dataset>("", form, { baseURL });
      return data;
    },
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
    },
  });
}

export function useRenameDataset(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn(filename: string) {
      const { data } = await api.patch<Dataset>(
        `/${id}`,
        { filename },
        { baseURL },
      );
      return data;
    },
    onSuccess(data) {
      queryClient.setQueryData([DatasetQueryKey.Datasets, id], data);
      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
    },
  });
}

/** Applies safe data-cleaning to the dataset in place; reports generated
 * afterwards use the cleaned data. Returns the re-profiled dataset. */
export function usePreprocessDataset(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn() {
      const { data } = await api.post<DatasetProfile>(
        `/${id}/preprocess`,
        undefined,
        { baseURL },
      );
      return data;
    },
    onSuccess(data) {
      queryClient.setQueryData([DatasetQueryKey.Datasets, id], data);
      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
      queryClient.invalidateQueries({
        queryKey: [DatasetQueryKey.DatasetProfile, id],
      });
    },
  });
}

/** Archive (soft-delete) or restore a dataset — never a hard delete, so it can
 * always be brought back. */
export function useArchiveDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    async mutationFn({ id, archived }: { id: string; archived: boolean }) {
      const action = archived ? "archive" : "unarchive";
      const { data } = await api.post<Dataset>(`/${id}/${action}`, undefined, {
        baseURL,
      });
      return data;
    },
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
    },
  });
}
