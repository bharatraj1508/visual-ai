"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { fadeUp, reveal, stagger } from "./motion";

const POINTS = [
  {
    title: "Start with 50 free credits",
    body: "Enough for about 5 full reports the moment you verify your email — no card required.",
    icon: <GiftIcon />,
  },
  {
    title: "Pay only when you generate",
    body: "A full multi-section report costs about 10 credits. No subscription, no monthly bill — credits never expire on you mid-project.",
    icon: <BoltIcon />,
  },
  {
    title: "Regenerate for a fraction",
    body: "Iterating on the same question costs one-third of the original — refine your analysis without paying full price again.",
    icon: <RefreshIcon />,
  },
  {
    title: "UPI, cards & netbanking",
    body: "Top up in seconds through secure checkout. Bigger credit packs come with bigger bonus credits.",
    icon: <CoinIcon />,
  },
];

// Marketing view of the packs — CREDITS and report counts only, never currency.
const PACKS = [
  { name: "Starter", credits: 100, reports: 10, badge: null },
  { name: "Analyst", credits: 350, reports: 35, badge: "Most popular" },
  { name: "Pro", credits: 900, reports: 90, badge: "Best value" },
  { name: "Studio", credits: 2600, reports: 260, badge: null },
];

export default function Pricing() {
  return (
    <section id="pricing" className="relative overflow-hidden py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            simple, pay as you go
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            Credits, not subscriptions
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg text-gray-500">
            You only pay when you generate a report. Buy a pack of credits once,
            spend them whenever you need answers.
          </motion.p>
        </motion.div>

        {/* Points */}
        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-12 grid gap-6 sm:grid-cols-2"
        >
          {POINTS.map((p) => (
            <motion.div
              key={p.title}
              variants={fadeUp}
              className="flex gap-4 rounded-2xl border border-gray-200 bg-white p-5"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                {p.icon}
              </span>
              <div>
                <h3 className="font-display text-base font-semibold text-ink">
                  {p.title}
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-500">
                  {p.body}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Packs — credits only */}
        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4"
        >
          {PACKS.map((pack) => {
            const featured = pack.badge === "Best value";
            return (
              <motion.div
                key={pack.name}
                variants={fadeUp}
                className={`relative rounded-2xl border p-5 text-center ${
                  featured
                    ? "border-primary/60 bg-primary/[0.03] ring-1 ring-primary/20"
                    : "border-gray-200 bg-white"
                }`}
              >
                {pack.badge && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-primary px-2.5 py-0.5 text-[11px] font-semibold text-white">
                    {pack.badge}
                  </span>
                )}
                <p className="text-sm font-semibold text-gray-900">
                  {pack.name}
                </p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900">
                  {pack.credits.toLocaleString()}
                </p>
                <p className="text-xs text-gray-400">credits</p>
                <p className="mt-2 text-xs font-medium text-primary">
                  ~{pack.reports} reports
                </p>
              </motion.div>
            );
          })}
        </motion.div>

        <motion.div {...reveal} variants={fadeUp} className="mt-10 text-center">
          <Link
            href="/auth/register"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition-transform hover:-translate-y-0.5"
          >
            Start with 50 free credits
            <span>→</span>
          </Link>
          <p className="mt-3 text-xs text-gray-400">
            No subscription · no card to start · pay only for what you generate
          </p>
        </motion.div>
      </div>
    </section>
  );
}

const iconProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
function GiftIcon() {
  return (
    <svg {...iconProps}>
      <rect x="3" y="8" width="18" height="4" rx="1" />
      <path d="M12 8v13M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7" />
      <path d="M12 8S10 3 7.5 3 5 6 5 6s2 2 4 2M12 8s2-5 4.5-5S19 6 19 6s-2 2-4 2" />
    </svg>
  );
}
function BoltIcon() {
  return (
    <svg {...iconProps}>
      <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />
    </svg>
  );
}
function RefreshIcon() {
  return (
    <svg {...iconProps}>
      <path d="M23 4v6h-6M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}
function CoinIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.9 2.5 2-1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5v11" />
    </svg>
  );
}
