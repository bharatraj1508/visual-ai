import { useQueryClient } from "@tanstack/react-query";
import { useDispatch } from "react-redux";

import { actions } from "../slices/auth";
import { AuthState } from "../types/auth";
import useStoreSelector from "./useStoreSelector";

export function useLogin() {
  const dispatch = useDispatch();
  return (payload: AuthState) => dispatch(actions.login(payload));
}

export function useLogout() {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  return () => {
    queryClient.clear();
    dispatch(actions.logout());
  };
}

export function useAccessToken() {
  return useStoreSelector(({ auth }) => auth.accessToken);
}
