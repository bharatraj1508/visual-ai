"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import Spinner from "@/components/common/Spinner";
import useShowApiErrorMessage from "@/hooks/api/useShowApiErrorMessage";
import { useRequestLogin } from "@/services/api/requests/auth";
import { AuthFormValues } from "@/types/auth";

export default function LoginPage() {
  const { register, handleSubmit } = useForm<AuthFormValues>();
  const router = useRouter();
  const showError = useShowApiErrorMessage();
  const { mutate, isPending } = useRequestLogin();

  const onSubmit = (values: AuthFormValues) =>
    mutate(values, {
      onSuccess: () => router.push("/dashboard"),
      onError: showError,
    });

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      >
        <h1 className="text-xl font-semibold">Log in</h1>
        <input
          {...register("email", { required: true })}
          type="email"
          placeholder="Email"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          {...register("password", { required: true })}
          type="password"
          placeholder="Password"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isPending && <Spinner />} Log in
        </button>
        <p className="text-center text-sm text-gray-500">
          No account?{" "}
          <Link href="/auth/register" className="text-primary">
            Register
          </Link>
        </p>
      </form>
    </div>
  );
}
