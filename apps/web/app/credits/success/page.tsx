"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import AppHeader from "@/components/AppHeader";
import Spinner from "@/components/common/Spinner";
import api, { baseApiURL } from "@/services/api/axios";
import { useRequireAuth } from "@/hooks/auth/useRequireAuth";
import { CreditQueryKey } from "@/services/api/types/CreditQueryKey";
import { Purchase } from "@/types/credits";

// After this many poll attempts (~2s each) we stop implying it's still coming
// and show a "taking longer" note instead of an endless spinner.
const MAX_POLLS = 12;

function SuccessInner() {
  const token = useRequireAuth();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  // Razorpay returns our purchase id as the payment-link reference.
  const purchaseId = params.get("razorpay_payment_link_reference_id");

  const [done, setDone] = useState(false);
  const [polls, setPolls] = useState(0);

  const { data: purchases } = useQuery({
    queryKey: [CreditQueryKey.Purchases, "success-poll"],
    async queryFn() {
      const { data } = await api.get<Purchase[]>("/purchases", {
        baseURL: `${baseApiURL}/credits`,
      });
      return data;
    },
    enabled: !!token && !done && polls < MAX_POLLS,
    refetchInterval: done || polls >= MAX_POLLS ? false : 2000,
  });

  // The purchase this success page is for (by id from the URL, else the newest).
  const purchase = useMemo(() => {
    if (!purchases?.length) return undefined;
    return (
      (purchaseId && purchases.find((p) => p.id === purchaseId)) ||
      purchases[0]
    );
  }, [purchases, purchaseId]);

  useEffect(() => {
    if (purchases) setPolls((n) => n + 1);
  }, [purchases]);

  useEffect(() => {
    if (purchase?.status === "completed") {
      setDone(true);
      // Refresh the header chip + any balance views now that credits landed.
      queryClient.invalidateQueries({ queryKey: [CreditQueryKey.Balance] });
    }
  }, [purchase, queryClient]);

  if (!token) return null;

  const stillWaiting = !done && polls < MAX_POLLS;
  const timedOut = !done && polls >= MAX_POLLS;

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <main className="mx-auto max-w-md px-4 py-12 text-center sm:px-6 sm:py-16">
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          {done ? (
            <>
              <h1 className="text-xl font-semibold text-green-600">
                Payment successful
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                {purchase
                  ? `${purchase.credits_granted} credits have been added to your account.`
                  : "Your credits have been added to your account."}
              </p>
            </>
          ) : stillWaiting ? (
            <>
              <div className="flex justify-center">
                <Spinner />
              </div>
              <h1 className="mt-3 text-xl font-semibold">
                Confirming your purchase…
              </h1>
              <p className="mt-2 text-sm text-gray-500">
                This takes a few seconds. You can keep working — credits appear
                automatically.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-xl font-semibold">Still processing</h1>
              <p className="mt-2 text-sm text-gray-500">
                Your payment went through and credits usually arrive within a
                few seconds. If your balance hasn&apos;t updated, refresh this
                page or check your purchase history.
              </p>
            </>
          )}
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/dashboard"
              className="flex-1 rounded-lg bg-primary py-2.5 text-sm font-medium text-white"
            >
              Go to dashboard
            </Link>
            <Link
              href="/credits"
              className="flex-1 rounded-lg border border-gray-300 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {timedOut ? "View history" : "Buy more"}
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

export default function CreditsSuccessPage() {
  return (
    <Suspense fallback={null}>
      <SuccessInner />
    </Suspense>
  );
}
