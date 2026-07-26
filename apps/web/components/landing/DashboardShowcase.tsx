"use client";

import { motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";

const HIGHLIGHTS = [
  {
    title: "Every rupee, visible",
    body: "Total spend and per-report cost, tracked to the token. Reports run for fractions of a cent.",
    icon: <CoinIcon />,
  },
  {
    title: "Your chart mix",
    body: "See which chart types your reports lean on most, at a glance across everything you've built.",
    icon: <ChartIcon />,
  },
  {
    title: "Worth a watch",
    body: "The dashboard surfaces your richest report so the best analysis is never buried.",
    icon: <StarIcon />,
  },
];

export default function DashboardShowcase() {
  return (
    <section id="dashboard" className="relative overflow-hidden py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            your command center
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            Every report, every rupee — one dashboard
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg text-gray-500">
            Datasets, generated reports, spend, and the charts you use most —
            all in a single, calm view.
          </motion.p>
        </motion.div>

        {/* Browser-framed screenshot */}
        <motion.div
          {...reveal}
          variants={fadeUp}
          className="mt-12 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-primary/5"
        >
          <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
            <span className="h-3 w-3 rounded-full bg-red-300" />
            <span className="h-3 w-3 rounded-full bg-amber-300" />
            <span className="h-3 w-3 rounded-full bg-green-300" />
            <span className="ml-3 hidden rounded-md bg-white px-3 py-1 font-mono text-[11px] text-gray-400 sm:inline">
              visual-ai.app/dashboard
            </span>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/dashboard.png"
            alt="The Visual AI dashboard: spend, reports, datasets and chart mix"
            className="w-full"
            loading="lazy"
          />
        </motion.div>

        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-10 grid gap-6 md:grid-cols-3"
        >
          {HIGHLIGHTS.map((h) => (
            <motion.div key={h.title} variants={fadeUp} className="flex gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                {h.icon}
              </span>
              <div>
                <h3 className="font-display text-base font-semibold text-ink">
                  {h.title}
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-500">
                  {h.body}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

const iconProps = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
function CoinIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.9 2.5 2-1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5v11" />
    </svg>
  );
}
function ChartIcon() {
  return (
    <svg {...iconProps}>
      <path d="M3 3v18h18" />
      <rect x="7" y="11" width="3" height="6" />
      <rect x="12" y="7" width="3" height="10" />
      <rect x="17" y="13" width="3" height="4" />
    </svg>
  );
}
function StarIcon() {
  return (
    <svg {...iconProps}>
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}
