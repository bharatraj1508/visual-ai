"use client";

import { AxiosError } from "axios";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";

import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import {
  useResendVerification,
  useVerifyEmail,
} from "@/services/api/requests/auth";

function VerifyInner() {
  const params = useSearchParams();
  const token = params.get("token");
  // Drive UI from the mutation's OWN state (isPending/isSuccess/isError), not
  // from per-call mutate callbacks — the latter get orphaned by React's
  // StrictMode setup/cleanup/setup cycle and leave the page stuck spinning.
  const { mutate: verify, isSuccess, isError, error } = useVerifyEmail();
  const { mutate: resend, isPending: isResending } = useResendVerification();
  const showError = useShowApiErrorMessage();

  const [resendEmail, setResendEmail] = useState<string>("");
  // Ensure the token is redeemed exactly once even across StrictMode's
  // double-invoked effect (the ref persists across the remount).
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;
    verify(token);
  }, [token, verify]);

  const detail = (error as AxiosError<{ detail?: string }>)?.response?.data
    ?.detail;
  const errorMsg =
    typeof detail === "string" ? detail : "We couldn't verify this link.";

  const onResend = () => {
    if (!resendEmail) return;
    resend(resendEmail, {
      onSuccess: () => toast.success("Verification email sent."),
      onError: showError,
    });
  };

  const showFailure = !token || isError;

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 bg-white p-6 text-center shadow-sm">
        {isSuccess ? (
          <>
            <h1 className="text-xl font-semibold text-green-600">
              Email verified
            </h1>
            <p className="text-sm text-gray-600">
              Your account is active and your free credits are ready.
            </p>
            <Link
              href="/auth/login"
              className="inline-flex w-full items-center justify-center rounded-md bg-primary py-2 text-sm font-medium text-white"
            >
              Continue to log in
            </Link>
          </>
        ) : showFailure ? (
          <>
            <h1 className="text-xl font-semibold">Verification failed</h1>
            <p className="text-sm text-gray-600">
              {!token
                ? "This link is missing its verification token."
                : errorMsg}
            </p>
            <div className="space-y-2 pt-2 text-left">
              <label className="text-xs font-medium text-gray-500">
                Enter your email to get a fresh link
              </label>
              <input
                type="email"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <button
                type="button"
                onClick={onResend}
                disabled={isResending || !resendEmail}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary py-2 text-sm font-medium text-white disabled:opacity-60"
              >
                {isResending && <Spinner />} Resend verification email
              </button>
            </div>
            <p className="text-center text-sm text-gray-500">
              <Link href="/auth/login" className="text-primary">
                Back to log in
              </Link>
            </p>
          </>
        ) : (
          <>
            <div className="flex justify-center">
              <Spinner />
            </div>
            <h1 className="text-xl font-semibold">Verifying your email…</h1>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
