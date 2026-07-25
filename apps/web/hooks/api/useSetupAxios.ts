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
 * - response: on 401, toast + log the user out
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
        if (error.response?.status === 401) {
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
