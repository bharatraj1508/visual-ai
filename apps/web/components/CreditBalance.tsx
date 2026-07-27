"use client";

import Link from "next/link";

import { useBalance } from "@/services/api/requests/credits";

/** Compact credits chip for the app header. Links to the purchase page. */
export default function CreditBalance() {
  const { data, isLoading } = useBalance();
  const available = data?.available ?? 0;
  const low = !isLoading && available <= 20;

  return (
    <Link
      href="/credits"
      title="Your credits — click to buy more"
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium transition-colors ${
        low
          ? "border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100"
          : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
      }`}
    >
      <span aria-hidden className="text-primary">
        ◈
      </span>
      {isLoading ? "…" : available.toLocaleString()}
      <span className="text-gray-400">credits</span>
    </Link>
  );
}
