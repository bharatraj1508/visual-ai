"use client";

import { useState } from "react";

import { motion, useReducedMotion } from "framer-motion";

import Chart3D from "./three/Chart3D";

// The page's signature moment: a CSV is scanned, resolves into an analytical
// question, and the answering chart builds itself — now as a real 3D model that
// grows from the floor and turns as you scroll. Mirrors the app's suggestion
// card + report chart.

const COLUMNS = [
  ["distance_covered_km", "11.2"],
  ["pass_accuracy_pct", "85"],
  ["clutch_score", "62.6"],
  ["sprint_distance_km", "3.1"],
  ["key_passes", "1.76"],
];

const BARS = [
  { label: "Defender", values: [81, 55] },
  { label: "Forward", values: [78, 55] },
  { label: "Midfielder", values: [85, 56] },
];

export default function DataMorph() {
  const reduce = useReducedMotion();
  const [runId, setRunId] = useState(0);
  const replay = () => setRunId((n) => n + 1);

  const t = (delay: number, duration = 0.5) =>
    reduce ? { duration: 0 } : { duration, delay, ease: [0.22, 0.61, 0.36, 1] };

  return (
    <div className="relative w-full">
      <div
        aria-hidden
        className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-tr from-primary/10 via-teal/10 to-transparent blur-2xl"
      />

      <motion.div
        key={runId}
        initial={reduce ? false : { opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={t(0, 0.6)}
        className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-[0_24px_70px_-30px_rgba(11,18,32,0.35)]"
      >
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-gray-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-gray-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-gray-200" />
          <span className="ml-2 truncate font-mono text-xs text-gray-400">
            fifa_world_cup_2026_player_performance.csv
          </span>
          <span className="ml-auto flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-primary">
            <span className="relative flex h-1.5 w-1.5">
              {!reduce && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
              )}
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            analyzing
          </span>
        </div>

        {/* scan line sweeping the card once */}
        {!reduce && (
          <motion.div
            key={`scan-${runId}`}
            aria-hidden
            initial={{ top: "18%", opacity: 0 }}
            animate={{ top: "100%", opacity: [0, 0.9, 0.9, 0] }}
            transition={{ duration: 1.3, delay: 0.4, ease: "easeInOut" }}
            className="pointer-events-none absolute inset-x-0 z-20 h-16 bg-gradient-to-b from-transparent via-primary/15 to-transparent"
          >
            <div className="absolute bottom-0 h-px w-full bg-primary/70" />
          </motion.div>
        )}

        <div className="space-y-4 p-5">
          {/* data ribbon */}
          <motion.div
            className="flex flex-wrap gap-1.5"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: reduce ? 0 : 0.05 } } }}
          >
            {COLUMNS.map(([col, val]) => (
              <motion.span
                key={col}
                variants={{
                  hidden: { opacity: 0, y: 6 },
                  show: { opacity: 1, y: 0, transition: t(0, 0.35) },
                }}
                className="flex items-baseline gap-1 rounded-md bg-gray-50 px-2 py-1 font-mono text-[10px] text-gray-400"
              >
                {col}
                <b className="font-semibold text-gray-600">{val}</b>
              </motion.span>
            ))}
          </motion.div>

          {/* the resolved analytical question */}
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={t(1.25)}
          >
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-teal">
              suggested report
            </div>
            <p className="font-display text-[15px] font-semibold leading-snug text-ink">
              Do elite physical workloads sacrifice technical efficiency — or
              spark clutch success?
            </p>
          </motion.div>

          {/* the answering chart, in 3D */}
          <div>
            <Chart3D key={`chart-${runId}`} kind="bars" bars={BARS} className="h-56 w-full" />
            <motion.div
              initial={reduce ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={t(1.6)}
              className="mt-1 flex items-center justify-center gap-4 font-mono text-[10px]"
            >
              <span className="flex items-center gap-1.5 text-gray-500">
                <span className="h-2 w-2 rounded-sm bg-primary" />
                pass_accuracy_pct
              </span>
              <span className="flex items-center gap-1.5 text-gray-500">
                <span className="h-2 w-2 rounded-sm bg-teal" />
                clutch_score
              </span>
            </motion.div>
          </div>
        </div>

        <button
          onClick={replay}
          className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-full border border-gray-200 bg-white/90 px-3 py-1.5 font-mono text-[10px] text-gray-500 backdrop-blur transition-colors hover:border-primary/40 hover:text-primary"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          replay
        </button>
      </motion.div>
    </div>
  );
}
