"use client";

import { ChangeEvent, useRef } from "react";

import { useRouter } from "next/navigation";

import AppHeader from "@/components/AppHeader";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { useCreateSession } from "@/services/api/requests/chat";
import {
  useDatasets,
  useDeleteDataset,
  useUploadDataset,
} from "@/services/api/requests/datasets";

export default function DashboardPage() {
  const token = useRequireAuth();
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const showError = useShowApiErrorMessage();

  const { data: datasets, isLoading } = useDatasets();
  const upload = useUploadDataset();
  const remove = useDeleteDataset();
  const createSession = useCreateSession();

  if (!token) return null;

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) upload.mutate(file, { onError: showError });
    event.target.value = "";
  };

  const openChat = (datasetId: string) =>
    createSession.mutate(
      { dataset_id: datasetId },
      {
        onSuccess: (session) => router.push(`/chat/${session.id}`),
        onError: showError,
      },
    );

  return (
    <div>
      <AppHeader />
      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Your datasets</h1>
          <button
            onClick={() => fileInput.current?.click()}
            disabled={upload.isPending}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {upload.isPending && <Spinner />} Upload CSV
          </button>
          <input
            ref={fileInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={onFile}
          />
        </div>

        {isLoading ? (
          <Spinner className="text-primary" />
        ) : !datasets?.length ? (
          <p className="text-gray-500">
            No datasets yet. Upload a CSV to get started.
          </p>
        ) : (
          <ul className="space-y-3">
            {datasets.map((dataset) => (
              <li
                key={dataset.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
              >
                <div>
                  <p className="font-medium">{dataset.filename}</p>
                  <p className="text-sm text-gray-500">
                    {dataset.status}
                    {dataset.row_count != null &&
                      ` · ${dataset.row_count} rows × ${dataset.col_count} cols`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => openChat(dataset.id)}
                    disabled={
                      dataset.status !== "ready" || createSession.isPending
                    }
                    className="rounded-md bg-secondary px-3 py-1.5 text-sm text-white disabled:opacity-40"
                  >
                    Chat
                  </button>
                  <button
                    onClick={() =>
                      remove.mutate(dataset.id, { onError: showError })
                    }
                    className="text-sm text-gray-400 hover:text-red-500"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
