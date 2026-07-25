"use client";

import { PropsWithChildren } from "react";

import {
  QueryClient,
  QueryClientProvider as TanstackQueryClientProvider,
} from "@tanstack/react-query";

import { useSetupAxios } from "@/hooks/api/useSetupAxios";
import api from "@/services/api/axios";

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Wire axios interceptors once, inside the React Query context (useLogout needs it).
function AxiosInterceptors() {
  useSetupAxios(api);
  return null;
}

export default function QueryClientProvider({ children }: PropsWithChildren) {
  return (
    <TanstackQueryClientProvider client={queryClient}>
      <AxiosInterceptors />
      {children}
    </TanstackQueryClientProvider>
  );
}
