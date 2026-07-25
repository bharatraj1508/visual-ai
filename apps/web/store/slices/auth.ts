import { createSlice } from "@reduxjs/toolkit";
import { persistReducer } from "redux-persist";
import storage from "redux-persist/lib/storage";

import { AuthCaseReducers, AuthState } from "../types/auth";

const initialState: AuthState = {};

export const { actions, ...slice } = createSlice<
  AuthState,
  AuthCaseReducers,
  "auth",
  Record<string, never>
>({
  name: "auth",
  initialState,
  reducers: {
    login: (_state, { payload }) => payload,
    logout: () => initialState,
  },
});

// Persist the access token to localStorage so sessions survive reloads.
export const reducer = persistReducer(
  {
    key: "visual-ai-auth",
    version: 1,
    storage,
  },
  slice.reducer,
);
