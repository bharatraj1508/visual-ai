"use client";

import { ChangeEvent, useRef } from "react";

import { useRouter } from "next/navigation";
import { toast } from "react-toastify";

import AppHeader from "@/components/AppHeader";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import {
  useDatasets,
  useDeleteDataset,
  useUploadDataset,
} from "@/services/api/requests/datasets";
import { MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from "@/utils/config";

export default function DashboardPage() {
  const token = useRequireAuth();
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const showError = useShowApiErrorMessage();

  const { data: datasets, isLoading } = useDatasets();
  const upload = useUploadDataset();
  const remove = useDeleteDataset();

  if (!token) return null;

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    // Refuse oversized files up front — no point uploading what the API rejects.
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error(`File exceeds the ${MAX_UPLOAD_MB} MB limit`);
      return;
    }
    // A fresh upload goes straight to analysis — no intermediate step.
    upload.mutate(file, {
      onSuccess: (dataset) => router.push(`/analyze/${dataset.id}`),
      onError: showError,
    });
  };

  const openAnalyze = (datasetId: string) =>
    router.push(`/analyze/${datasetId}`);

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
                    onClick={() => openAnalyze(dataset.id)}
                    disabled={dataset.status !== "ready"}
                    className="rounded-md bg-primary px-3 py-1.5 text-sm text-white disabled:opacity-40"
                  >
                    Analyze
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
