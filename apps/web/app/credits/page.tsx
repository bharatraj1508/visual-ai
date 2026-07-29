"use client";

import { useState } from "react";

import AppHeader from "@/components/AppHeader";
import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import {
  useBalance,
  useCheckout,
  usePacks,
  usePurchases,
} from "@/services/api/requests/credits";
import { CreditPack, Purchase } from "@/types/credits";

function CoinIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      <ellipse cx="12" cy="6.2" rx="7" ry="3.1" fill="currentColor" opacity="0.9" />
      <path
        d="M5 6.2v3.4c0 1.7 3.13 3.1 7 3.1s7-1.4 7-3.1V6.2"
        stroke="currentColor"
        strokeWidth="1.6"
        opacity="0.55"
      />
      <path
        d="M5 9.6v3.4c0 1.7 3.13 3.1 7 3.1s7-1.4 7-3.1V9.6"
        stroke="currentColor"
        strokeWidth="1.6"
        opacity="0.4"
      />
      <path
        d="M5 13v3.4c0 1.7 3.13 3.1 7 3.1s7-1.4 7-3.1V13"
        stroke="currentColor"
        strokeWidth="1.6"
        opacity="0.25"
      />
    </svg>
  );
}

export default function CreditsPage() {
  const token = useRequireAuth();
  const { data: balance } = useBalance();
  const { data: packs, isLoading } = usePacks();
  const { data: purchases } = usePurchases();
  const checkout = useCheckout();
  const showError = useShowApiErrorMessage();
  // Track WHICH pack is checking out, so only that card shows a spinner.
  const [loadingPackId, setLoadingPackId] = useState<string | null>(null);

  if (!token) return null;

  const buy = (packId: string) => {
    if (loadingPackId) return;
    setLoadingPackId(packId);
    checkout.mutate(packId, {
      onSuccess: ({ checkout_url }) => {
        window.location.href = checkout_url;
      },
      onError: (err) => {
        setLoadingPackId(null);
        showError(err);
      },
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Balance hero */}
        <div className="mb-10 flex flex-col items-start justify-between gap-4 rounded-3xl border border-gray-100 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:p-7">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Your balance
            </p>
            <div className="mt-1 flex items-center gap-2.5">
              <CoinIcon className="h-8 w-8 text-primary" />
              <span className="text-4xl font-bold tracking-tight text-gray-900">
                {balance?.available ?? 0}
              </span>
              <span className="pb-1 text-sm text-gray-400">credits</span>
            </div>
          </div>
          <p className="max-w-xs text-sm text-gray-500">
            Credits generate reports. Reports cost ~10 credits each — top up
            below.
            {balance && balance.held > 0
              ? ` (${balance.held} reserved for reports in progress.)`
              : ""}
          </p>
        </div>

        <h1 className="mb-1 text-xl font-semibold tracking-tight text-gray-900">
          Buy credits
        </h1>
        <p className="mb-6 text-sm text-gray-500">
          One-time packs. Bigger packs give more bonus credits.
        </p>

        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-500">
            <Spinner /> Loading packs…
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {packs?.map((pack) => (
              <PackCard
                key={pack.id}
                pack={pack}
                loading={loadingPackId === pack.id}
                disabled={loadingPackId !== null}
                onBuy={() => buy(pack.id)}
              />
            ))}
          </div>
        )}

        <PurchaseHistory purchases={purchases ?? []} />
      </main>
    </div>
  );
}

function PackCard({
  pack,
  loading,
  disabled,
  onBuy,
}: {
  pack: CreditPack;
  loading: boolean;
  disabled: boolean;
  onBuy: () => void;
}) {
  const featured = pack.badge === "Best value";
  return (
    <div
      className={`relative flex flex-col rounded-2xl border bg-white p-6 transition-all ${
        featured
          ? "border-primary/60 shadow-lg shadow-primary/10 ring-1 ring-primary/20"
          : "border-gray-200 hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md"
      }`}
    >
      {pack.badge && (
        <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-primary px-3 py-0.5 text-[11px] font-semibold text-white shadow-sm">
          {pack.badge}
        </span>
      )}

      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">{pack.name}</span>
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${
            featured ? "bg-primary/10 text-primary" : "bg-amber-50 text-amber-500"
          }`}
        >
          <CoinIcon className="h-6 w-6" />
        </span>
      </div>

      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold tracking-tight text-gray-900">
          {pack.total_credits.toLocaleString()}
        </span>
        <span className="text-sm text-gray-400">credits</span>
      </div>
      <p className="mt-1 h-4 text-xs font-medium text-green-600">
        {pack.bonus_credits > 0
          ? `${pack.base_credits.toLocaleString()} + ${pack.bonus_credits} bonus`
          : ""}
      </p>

      <button
        onClick={onBuy}
        disabled={disabled}
        className={`mt-6 flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
          featured
            ? "bg-primary text-white hover:bg-primary/90"
            : "border border-gray-300 text-gray-800 hover:bg-gray-50"
        }`}
      >
        {loading ? (
          <>
            <Spinner /> Redirecting…
          </>
        ) : (
          "Buy"
        )}
      </button>
    </div>
  );
}

function formatMoney(minor: number, currency: string) {
  const major = minor / 100;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency.toUpperCase(),
      maximumFractionDigits: 0,
    }).format(major);
  } catch {
    return `${major} ${currency.toUpperCase()}`;
  }
}

function PurchaseHistory({ purchases }: { purchases: Purchase[] }) {
  if (!purchases.length) return null;
  return (
    <section className="mt-14">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Purchase history
      </h2>
      <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white">
        <table className="w-full min-w-[420px] text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-400">
            <tr>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">Credits</th>
              <th className="px-4 py-2.5 font-medium">Amount</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {purchases.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-2.5 text-gray-600">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2.5 font-medium text-gray-900">
                  +{p.credits_granted}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {formatMoney(p.price_minor, p.currency)}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      p.status === "completed"
                        ? "bg-green-100 text-green-700"
                        : p.status === "pending"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {p.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
