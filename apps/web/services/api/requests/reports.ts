import { useQuery } from "@tanstack/react-query";

import { Report, ReportDetail } from "@/types/report";

import api, { baseApiURL } from "../axios";
import { ReportQueryKey } from "../types/ReportQueryKey";

const baseURL = `${baseApiURL}/reports`;

export function useReports() {
  return useQuery({
    queryKey: [ReportQueryKey.Reports],
    async queryFn() {
      const { data } = await api.get<Report[]>("", { baseURL });
      return data;
    },
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
