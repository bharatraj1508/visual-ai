"use client";

import { useEffect } from "react";

import { useRouter } from "next/navigation";

import { useAccessToken } from "@/store/hooks/auth";

/**
 * Redirects to the login page if there is no access token. Redux-persist has
 * already rehydrated by the time client components render (PersistGate).
 */
export function useRequireAuth() {
  const token = useAccessToken();
  const router = useRouter();

  useEffect(() => {
    if (!token) {
      router.replace("/auth/login");
    }
  }, [token, router]);

  return token;
}
