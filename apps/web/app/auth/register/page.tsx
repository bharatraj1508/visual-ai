"use client";

import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";

import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRegister, useResendVerification } from "@/services/api/requests/auth";
import {
  AuthFormValues,
  REFERRAL_SOURCES,
  USE_PURPOSES,
} from "@/types/auth";

const inputClass =
  "w-full rounded-md border border-gray-300 px-3 py-2 text-sm";

// Pull any utm_* / gclid / ref params off the landing URL so we can attribute
// the signup later. Runs client-side; returns {} on the server or when empty.
function captureSignupMetadata(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const meta: Record<string, string> = {};
  params.forEach((value, key) => {
    if (/^(utm_|gclid$|fbclid$|ref$)/.test(key)) meta[key] = value;
  });
  return meta;
}

export default function RegisterPage() {
  const { register, handleSubmit, watch } = useForm<AuthFormValues>();
  const showError = useShowApiErrorMessage();
  const { mutate, isPending } = useRegister();
  const { mutate: resend, isPending: isResending } = useResendVerification();
  // Once set, we've registered and are waiting on the user to verify by email.
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);

  const referralSource = watch("referral_source");

  const onSubmit = (values: AuthFormValues) => {
    const metadata = captureSignupMetadata();
    // Drop empty optional selects so we send null, not "".
    const payload: AuthFormValues = {
      email: values.email,
      password: values.password,
      full_name: values.full_name,
      referral_source: values.referral_source || undefined,
      referral_source_other:
        values.referral_source === "other"
          ? values.referral_source_other
          : undefined,
      use_purpose: values.use_purpose || undefined,
      marketing_opt_in: values.marketing_opt_in ?? false,
      signup_metadata: Object.keys(metadata).length ? metadata : undefined,
    };
    mutate(payload, {
      onSuccess: () => setPendingEmail(values.email),
      onError: showError,
    });
  };

  const onResend = () => {
    if (!pendingEmail) return;
    resend(pendingEmail, {
      onSuccess: () => toast.success("Verification email sent."),
      onError: showError,
    });
  };

  if (pendingEmail) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-xl font-semibold">Check your inbox</h1>
          <p className="text-sm text-gray-600">
            We sent a verification link to{" "}
            <span className="font-medium text-gray-900">{pendingEmail}</span>.
            Click it to activate your account and unlock your free credits.
          </p>
          <button
            type="button"
            onClick={onResend}
            disabled={isResending}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-gray-300 py-2 text-sm font-medium disabled:opacity-60"
          >
            {isResending && <Spinner />} Resend email
          </button>
          <p className="text-center text-sm text-gray-500">
            Already verified?{" "}
            <Link href="/auth/login" className="text-primary">
              Log in
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      >
        <h1 className="text-xl font-semibold">Create account</h1>

        <input
          {...register("full_name", { required: true })}
          type="text"
          placeholder="Full name"
          className={inputClass}
        />
        <input
          {...register("email", { required: true })}
          type="email"
          placeholder="Email"
          className={inputClass}
        />
        <input
          {...register("password", { required: true, minLength: 8 })}
          type="password"
          placeholder="Password (min 8 chars)"
          className={inputClass}
        />

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">
            How did you hear about us?
          </label>
          <select
            {...register("referral_source")}
            defaultValue=""
            className={inputClass}
          >
            <option value="">Select an option (optional)</option>
            {REFERRAL_SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {referralSource === "other" && (
          <input
            {...register("referral_source_other", { maxLength: 200 })}
            type="text"
            placeholder="Where did you hear about us?"
            className={inputClass}
          />
        )}

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">
            What will you use Visual AI for?
          </label>
          <select
            {...register("use_purpose")}
            defaultValue=""
            className={inputClass}
          >
            <option value="">Select an option (optional)</option>
            {USE_PURPOSES.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-start gap-2 text-sm text-gray-600">
          <input
            {...register("marketing_opt_in")}
            type="checkbox"
            className="mt-0.5"
          />
          <span>Send me occasional product updates and tips.</span>
        </label>

        <button
          type="submit"
          disabled={isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isPending && <Spinner />} Register
        </button>
        <p className="text-center text-sm text-gray-500">
          Have an account?{" "}
          <Link href="/auth/login" className="text-primary">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
