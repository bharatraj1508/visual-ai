"use client";

import { AxiosError } from "axios";
import { toast } from "react-toastify";

/**
 * Consistent error surfacing for mutations: pulls FastAPI's `detail` field.
 */
export default function useShowApiErrorMessage() {
  return (error: unknown) => {
    const detail = (error as AxiosError<{ detail?: string }>)?.response?.data
      ?.detail;
    toast.error(
      typeof detail === "string" ? detail : "Something went wrong. Try again.",
    );
  };
}
