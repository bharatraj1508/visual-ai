"use client";

import { useEffect } from "react";

import {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";
import { toast } from "react-toastify";

import store from "@/store";
import { useLogout } from "@/store/hooks/auth";

/**
 * Attaches request/response interceptors to the shared axios instance:
 * - request: inject `Authorization: Bearer <token>` from the Redux store
 * - response: on 401 while still logged in, toast + log the user out
 *   (trailing 401s during a deliberate logout stay silent)
 */
export function useSetupAxios(instance: AxiosInstance) {
  const logout = useLogout();

  useEffect(() => {
    const requestId = instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const {
          auth: { accessToken },
        } = store.getState();
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
      },
      (error: AxiosError) => Promise.reject(error),
    );

    const responseId = instance.interceptors.response.use(
      (response) => response,
      (error: AxiosError<{ detail?: string }>) => {
        // Only treat a 401 as an expired session when we still believe we're
        // logged in. During a deliberate logout the token is already cleared,
        // so trailing 401s from in-flight / refetching queries stay silent.
        const stillLoggedIn = !!store.getState().auth.accessToken;
        if (error.response?.status === 401 && stillLoggedIn) {
          toast.error("Session expired. Please log in again.");
          logout();
        }
        return Promise.reject(error);
      },
    );

    return () => {
      instance.interceptors.request.eject(requestId);
      instance.interceptors.response.eject(responseId);
    };
  }, [instance, logout]);
}
