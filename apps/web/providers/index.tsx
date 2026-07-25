"use client";

import { PropsWithChildren } from "react";

import { ToastContainer } from "react-toastify";

import QueryClientProvider from "./QueryClientProvider";
import StoreProvider from "./StoreProvider";

/**
 * Provider tree (outer -> inner): Redux + PersistGate, then React Query
 * (which also mounts the axios interceptors), then the app.
 */
export default function AppProviders({ children }: PropsWithChildren) {
  return (
    <StoreProvider>
      <QueryClientProvider>
        {children}
        <ToastContainer position="top-right" autoClose={4000} theme="light" />
      </QueryClientProvider>
    </StoreProvider>
  );
}
