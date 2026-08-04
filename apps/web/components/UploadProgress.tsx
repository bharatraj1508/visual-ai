"use client";

import { UploadState } from "@/hooks/dataset/useDatasetUpload";

/**
 * Full-screen loading screen shown from the moment files are picked until the
 * dataset is ready. It renders one honest, live checklist: a real upload
 * progress bar first, then a row per processing phase (reading → combining →
 * cleaning → generating ideas) that updates in place as SSE steps arrive.
 *
 * The user is never left on a blank "uploading" state — there is always a
 * labelled row describing what's happening right now.
 */
export default function UploadProgress({
  state,
  onCancel,
  onRetry,
}: {
  state: UploadState;
  onCancel: () => void;
  onRetry: () => void;
}) {
  if (state.phase === "idle") return null;

  const uploading = state.phase === "uploading";
  const errored = state.phase === "error";
  const fileLabel = `${state.fileCount} file${state.fileCount === 1 ? "" : "s"}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
        <div className="mb-6 flex items-start gap-4">
          <span
            className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
              errored
                ? "bg-red-100 text-red-600"
                : "bg-primary/10 text-primary"
            }`}
          >
            {errored ? <AlertIcon /> : <SparkIcon />}
            {!errored && state.phase !== "done" && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-xl bg-primary opacity-20" />
            )}
          </span>
          <div className="min-w-0">
            <h2 className="text-lg font-semibold tracking-tight text-gray-900">
              {errored
                ? "Something went wrong"
                : state.phase === "done"
                  ? "Ready to analyze"
                  : "Preparing your dataset"}
            </h2>
            <p className="mt-0.5 text-sm text-gray-500">
              {errored
                ? "We couldn't finish preparing this dataset."
                : state.phase === "done"
                  ? "Taking you to your report suggestions…"
                  : `Uploading and analyzing ${fileLabel}. This only takes a moment.`}
            </p>
          </div>
        </div>

        {errored ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {state.error}
          </div>
        ) : (
          <ol className="space-y-1">
            {/* Upload is always the first row; its progress bar is the honest one. */}
            <StepRow
              label="Uploading your files"
              state={uploading ? "active" : "done"}
              detail={uploading ? undefined : `${fileLabel} received`}
            >
              {uploading && <ProgressBar value={state.progress} />}
            </StepRow>

            {state.steps.map((step) => (
              <StepRow
                key={step.key}
                label={step.label}
                state={step.state}
                detail={step.detail ?? undefined}
              />
            ))}

            {/* While the server is warming up the stream, before the first step. */}
            {!uploading && state.steps.length === 0 && (
              <StepRow label="Analyzing your data" state="active" />
            )}
          </ol>
        )}

        <div className="mt-6 flex justify-end gap-2">
          {errored ? (
            <>
              <button
                onClick={onCancel}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:border-gray-300"
              >
                Close
              </button>
              <button
                onClick={onRetry}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary/90"
              >
                Try again
              </button>
            </>
          ) : (
            state.phase !== "done" && (
              <button
                onClick={onCancel}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-500 transition-colors hover:border-gray-300 hover:text-gray-700"
              >
                Cancel
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function StepRow({
  label,
  state,
  detail,
  children,
}: {
  label: string;
  state: "active" | "done";
  detail?: string;
  children?: React.ReactNode;
}) {
  const done = state === "done";
  return (
    <li className="flex gap-3 rounded-lg px-2 py-2">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
        {done ? (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">
            <CheckIcon />
          </span>
        ) : (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span
            className={`text-sm font-medium ${done ? "text-gray-500" : "text-gray-900"}`}
          >
            {label}
          </span>
          {detail && (
            <span className="shrink-0 text-xs tabular-nums text-gray-400">
              {detail}
            </span>
          )}
        </div>
        {children}
      </div>
    </li>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="mt-2 flex items-center gap-3">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-200 ease-out"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-9 shrink-0 text-right text-xs tabular-nums text-gray-400">
        {value}%
      </span>
    </div>
  );
}

/* ---------------------------------- icons --------------------------------- */
const CheckIcon = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 6 9 17l-5-5" />
  </svg>
);
const SparkIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
    <circle cx="12" cy="12" r="3.5" />
  </svg>
);
const AlertIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </svg>
);
