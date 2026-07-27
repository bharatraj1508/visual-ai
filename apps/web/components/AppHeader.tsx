"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import CreditBalance from "@/components/CreditBalance";
import { useLogout } from "@/store/hooks/auth";

export default function AppHeader() {
  const logout = useLogout();
  const router = useRouter();

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
      <Link href="/dashboard" className="text-lg font-semibold text-primary">
        Visual AI
      </Link>
      <div className="flex items-center gap-4">
        <CreditBalance />
        <button
          onClick={() => {
            logout();
            router.push("/auth/login");
          }}
          className="text-sm text-gray-500 hover:text-gray-900"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
