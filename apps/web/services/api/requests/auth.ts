import { useMutation, useQuery } from "@tanstack/react-query";

import { useLogin } from "@/store/hooks/auth";
import { AuthFormValues, LoginResponse, User } from "@/types/auth";

import api, { baseApiURL } from "../axios";
import { AuthQueryKey } from "../types/AuthQueryKey";

const baseURL = `${baseApiURL}/auth`;

export function useRegister() {
  return useMutation({
    mutationFn(payload: AuthFormValues) {
      return api.post<User>("/register", payload, { baseURL });
    },
  });
}

export function useRequestLogin() {
  const login = useLogin();
  return useMutation({
    async mutationFn(payload: AuthFormValues) {
      // Backend /auth/login is an OAuth2 password form (username = email).
      const body = new URLSearchParams({
        username: payload.email,
        password: payload.password,
      });
      const { data } = await api.post<LoginResponse>("/login", body, {
        baseURL,
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return data;
    },
    onSuccess(data) {
      login({ accessToken: data.access_token });
    },
  });
}

export function useCurrentUser(enabled = true) {
  return useQuery({
    queryKey: [AuthQueryKey.CurrentUser],
    async queryFn() {
      const { data } = await api.get<User>("/me", { baseURL });
      return data;
    },
    enabled,
  });
}
