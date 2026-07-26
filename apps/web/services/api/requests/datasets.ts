import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Dataset, DatasetProfile } from "@/types/dataset";

import api, { baseApiURL } from "../axios";
import { DatasetQueryKey } from "../types/DatasetQueryKey";

const baseURL = `${baseApiURL}/datasets`;

export function useDatasets() {
  return useQuery({
    queryKey: [DatasetQueryKey.Datasets],
    async queryFn() {
      const { data } = await api.get<Dataset[]>("", { baseURL });
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
    async mutationFn(file: File) {
      const form = new FormData();
      form.append("file", file);
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

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn(id: string) {
      return api.delete(`/${id}`, { baseURL });
    },
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: [DatasetQueryKey.Datasets] });
    },
  });
}
