"use client";

import Link from "next/link";

/**
 * Shown only when the user tries to generate/regenerate but doesn't have enough
 * credits. There is no pre-generation confirmation dialog — generation just
 * runs; this appears solely on a 402.
 */
export default function InsufficientCreditsModal({
  open,
  needed,
  available,
  onClose,
}: {
  open: boolean;
  needed: number | null;
  available: number | null;
  onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-500">
          <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden>
            <ellipse cx="12" cy="7" rx="7" ry="3" fill="currentColor" opacity="0.9" />
            <path d="M5 7v6c0 1.66 3.13 3 7 3s7-1.34 7-3V7" stroke="currentColor" strokeWidth="1.6" opacity="0.5" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-gray-900">
          You&apos;re out of credits
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          {needed != null && available != null
            ? `This report needs ${needed} credits and you have ${available}. Top up to keep generating.`
            : "Top up your credits to keep generating reports."}
        </p>
        <div className="mt-5 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <Link
            href="/credits"
            className="flex-1 rounded-lg bg-primary py-2.5 text-sm font-medium text-white hover:bg-primary/90"
          >
            Buy credits
          </Link>
        </div>
      </div>
    </div>
  );
}
