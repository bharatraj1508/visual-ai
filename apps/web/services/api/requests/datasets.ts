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
