import { configureStore } from "@reduxjs/toolkit";
import { persistStore } from "redux-persist";

import { rootReducer } from "./slices";

const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      // redux-persist actions carry non-serializable values.
      serializableCheck: false,
    }),
});

export const persistor = persistStore(store);

export type AppDispatch = typeof store.dispatch;

export default store;
