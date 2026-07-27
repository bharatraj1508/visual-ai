import { useMutation, useQuery } from "@tanstack/react-query";

import {
  CreditBalance,
  CreditPack,
  EstimateResponse,
  LedgerEntry,
  Purchase,
} from "@/types/credits";

import api, { baseApiURL } from "../axios";
import { CreditQueryKey } from "../types/CreditQueryKey";

const baseURL = `${baseApiURL}/credits`;

export function useBalance(enabled = true) {
  return useQuery({
    queryKey: [CreditQueryKey.Balance],
    async queryFn() {
      const { data } = await api.get<CreditBalance>("/balance", { baseURL });
      return data;
    },
    enabled,
    staleTime: 10_000,
  });
}

export function usePacks() {
  return useQuery({
    queryKey: [CreditQueryKey.Packs],
    async queryFn() {
      const { data } = await api.get<CreditPack[]>("/packs", { baseURL });
      return data;
    },
    staleTime: 5 * 60_000,
  });
}

export function usePurchases() {
  return useQuery({
    queryKey: [CreditQueryKey.Purchases],
    async queryFn() {
      const { data } = await api.get<Purchase[]>("/purchases", { baseURL });
      return data;
    },
  });
}

export function useLedger() {
  return useQuery({
    queryKey: [CreditQueryKey.Ledger],
    async queryFn() {
      const { data } = await api.get<LedgerEntry[]>("/ledger", { baseURL });
      return data;
    },
  });
}

/** Quote the credit cost of a report before generating it. */
export function useEstimateReport() {
  return useMutation({
    async mutationFn(datasetId: string) {
      const { data } = await api.post<EstimateResponse>(
        "/estimate",
        { dataset_id: datasetId },
        { baseURL: `${baseApiURL}/reports` },
      );
      return data;
    },
  });
}

/** Start a Razorpay checkout for a pack; returns the hosted payment URL. */
export function useCheckout() {
  return useMutation({
    async mutationFn(packId: string) {
      const { data } = await api.post<{ checkout_url: string }>(
        "/checkout",
        { pack_id: packId },
        { baseURL },
      );
      return data;
    },
  });
}
