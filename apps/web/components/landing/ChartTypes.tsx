"use client";

import { ReactNode } from "react";

import { motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";
import Chart3D from "./three/Chart3D";
import type { ChartKind } from "./three/Scene";

const C = "#FB676E";
const T = "#2DD4BF";

function G({ children }: { children: ReactNode }) {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

// The headline gallery: four chart families as live 3D models.
const GALLERY: { kind: ChartKind; label: string }[] = [
  { kind: "bars", label: "grouped bar" },
  { kind: "scatter", label: "scatter" },
  { kind: "donut", label: "donut" },
  { kind: "area", label: "area / line" },
];

// The full toolkit, as compact glyphs — every type the analyst can reach for.
const CHARTS: { label: string; icon: ReactNode }[] = [
  { label: "bar", icon: <G><rect x="4" y="10" width="3.5" height="9" fill={C} /><rect x="10" y="6" width="3.5" height="13" fill={C} /><rect x="16" y="13" width="3.5" height="6" fill={C} /></G> },
  { label: "grouped_bar", icon: <G><rect x="4" y="9" width="3" height="10" fill={C} /><rect x="7.5" y="12" width="3" height="7" fill={T} /><rect x="14" y="6" width="3" height="13" fill={C} /><rect x="17.5" y="10" width="3" height="9" fill={T} /></G> },
  { label: "stacked_bar", icon: <G><rect x="6" y="12" width="5" height="7" fill={C} /><rect x="6" y="7" width="5" height="5" fill={T} /><rect x="14" y="10" width="5" height="9" fill={C} /><rect x="14" y="6" width="5" height="4" fill={T} /></G> },
  { label: "line", icon: <G><polyline points="4,16 9,10 13,13 20,5" stroke={C} strokeWidth="2" /></G> },
  { label: "multi_line", icon: <G><polyline points="4,15 9,9 14,12 20,6" stroke={C} strokeWidth="2" /><polyline points="4,18 9,15 14,16 20,12" stroke={T} strokeWidth="2" /></G> },
  { label: "area", icon: <G><path d="M4 16 L9 10 L13 13 L20 6 V19 H4 Z" fill={C} fillOpacity="0.2" stroke={C} strokeWidth="1.6" /></G> },
  { label: "scatter", icon: <G><circle cx="6" cy="15" r="1.6" fill={C} /><circle cx="10" cy="9" r="1.6" fill={C} /><circle cx="13" cy="14" r="1.6" fill={T} /><circle cx="17" cy="7" r="1.6" fill={C} /><circle cx="18" cy="15" r="1.6" fill={T} /></G> },
  { label: "pie", icon: <G><circle cx="12" cy="12" r="8" fill={T} fillOpacity="0.25" /><path d="M12 12 L12 4 A8 8 0 0 1 19 15 Z" fill={C} /></G> },
  { label: "donut", icon: <G><circle cx="12" cy="12" r="7.5" stroke={T} strokeOpacity="0.35" strokeWidth="3.2" /><path d="M12 4.5 A7.5 7.5 0 0 1 18.5 15.5" stroke={C} strokeWidth="3.2" /></G> },
  { label: "histogram", icon: <G><rect x="4" y="13" width="3.2" height="6" fill={C} /><rect x="7.4" y="9" width="3.2" height="10" fill={C} /><rect x="10.8" y="6" width="3.2" height="13" fill={C} /><rect x="14.2" y="11" width="3.2" height="8" fill={C} /><rect x="17.6" y="15" width="3.2" height="4" fill={C} /></G> },
  { label: "dual_axis", icon: <G><rect x="5" y="12" width="3.5" height="7" fill={C} /><rect x="15" y="9" width="3.5" height="10" fill={C} /><polyline points="4,10 10,7 15,11 20,5" stroke={T} strokeWidth="2" /></G> },
  { label: "radar", icon: <G><polygon points="12,3 20,9 17,19 7,19 4,9" stroke={T} strokeOpacity="0.4" strokeWidth="1.4" /><polygon points="12,7 16,10 15,16 9,16 8,10" fill={C} fillOpacity="0.35" stroke={C} strokeWidth="1.4" /></G> },
];

export default function ChartTypes() {
  return (
    <section id="charts" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            the toolkit
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            One chart for every question
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg text-gray-500">
            The analyst picks the visualization that actually settles the point —
            not whichever one is easiest to draw. Scroll to turn them.
          </motion.p>
        </motion.div>

        {/* live 3D gallery */}
        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-14 grid grid-cols-2 gap-4 lg:grid-cols-4"
        >
          {GALLERY.map((g) => (
            <motion.div
              key={g.kind}
              variants={fadeUp}
              whileHover={{ y: -5 }}
              className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-b from-white to-gray-50/60 transition-colors hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5"
            >
              <Chart3D kind={g.kind} className="h-44 w-full sm:h-52" label={g.label} />
            </motion.div>
          ))}
        </motion.div>

        {/* the full set, as labels */}
        <motion.p
          {...reveal}
          variants={fadeUp}
          className="mt-12 font-mono text-xs uppercase tracking-[0.2em] text-gray-400"
        >
          …and the full set
        </motion.p>
        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
        >
          {CHARTS.map((c) => (
            <motion.div
              key={c.label}
              variants={fadeUp}
              whileHover={{ y: -4 }}
              className="group flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 transition-colors hover:border-primary/30 hover:shadow-md hover:shadow-primary/5"
            >
              <span className="transition-transform duration-300 group-hover:scale-110">
                {c.icon}
              </span>
              <span className="font-mono text-sm text-gray-500 transition-colors group-hover:text-ink">
                {c.label}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
