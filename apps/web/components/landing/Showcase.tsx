"use client";

import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fadeUp, reveal, stagger } from "./motion";

const SUGGESTIONS = [
  {
    n: 1,
    title: "Valuation vs. Realized Impact: Where does the market misprice performance?",
    question:
      "How does market_value_eur correlate with tournament_rating, player_of_match_awards, and total_goals_tournament when segmented by position and age?",
    charts: ["Scatter", "Bar", "Grouped bar"],
  },
  {
    n: 2,
    title: "The Defensive-Offensive Trade-off: Mapping player positional profiles",
    question:
      "Across positions, what is the relationship between offensive_contribution, defensive_contribution, and possession_impact?",
    charts: ["Scatter", "Radar", "Grouped bar"],
  },
];

const CHART_DATA = [
  { position: "Defender", pass_accuracy_pct: 81, clutch_score: 55 },
  { position: "Forward", pass_accuracy_pct: 78, clutch_score: 55 },
  { position: "Midfielder", pass_accuracy_pct: 85, clutch_score: 56 },
];

export default function Showcase() {
  return (
    <section id="showcase" className="relative bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            what it hands you
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            Questions a senior analyst would ask — answered
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg text-gray-500">
            Real suggestions, from a real dataset. Each one names the columns it
            interrogates and the charts that settle it.
          </motion.p>
        </motion.div>

        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          {/* suggestion cards */}
          <motion.div {...reveal} variants={stagger} className="flex flex-col gap-6">
            {SUGGESTIONS.map((s) => (
              <motion.article
                key={s.n}
                variants={fadeUp}
                className="group rounded-2xl border border-gray-200 bg-white p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5"
              >
                <div className="mb-3 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 font-mono text-xs font-semibold text-primary">
                    {s.n}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-gray-400">
                    suggested report
                  </span>
                </div>
                <h3 className="font-display text-lg font-semibold leading-snug text-ink">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">
                  {s.question}
                </p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {s.charts.map((c) => (
                    <span
                      key={c}
                      className="rounded-full bg-gray-100 px-2.5 py-0.5 font-mono text-[11px] text-gray-500"
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div className="mt-5 flex items-center gap-1.5 text-sm font-medium text-primary">
                  Generate report
                  <span className="transition-transform group-hover:translate-x-0.5">
                    →
                  </span>
                </div>
              </motion.article>
            ))}
          </motion.div>

          {/* live, interactive report chart */}
          <motion.div
            {...reveal}
            variants={fadeUp}
            className="flex flex-col rounded-2xl border border-gray-200 bg-white p-6"
          >
            <span className="font-mono text-[10px] uppercase tracking-wider text-teal">
              generated report · excerpt
            </span>
            <h3 className="mt-2 font-display text-lg font-semibold leading-snug text-ink">
              Do elite physical workloads sacrifice technical efficiency?
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-500">
              Midfielders dominate passing accuracy (85%) while every cohort
              holds a comparable clutch score — sustained workload doesn&apos;t
              erode precision.
            </p>

            <div className="mt-5 rounded-xl border border-gray-100 p-3">
              <p className="mb-2 text-xs font-medium text-gray-600">
                Technical &amp; Clutch Output by Positional Cohort
              </p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={CHART_DATA} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#EEF0F3" vertical={false} />
                    <XAxis
                      dataKey="position"
                      stroke="#9CA3AF"
                      tickLine={false}
                      tick={{ fontSize: 12, fill: "#6B7280" }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      stroke="#9CA3AF"
                      tickLine={false}
                      tick={{ fontSize: 11, fill: "#9CA3AF" }}
                    />
                    <Tooltip
                      cursor={{ fill: "rgba(0,0,0,0.03)" }}
                      contentStyle={{
                        borderRadius: 10,
                        border: "1px solid #E5E7EB",
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                    <Bar dataKey="pass_accuracy_pct" fill="#FB676E" radius={[4, 4, 0, 0]} maxBarSize={44} />
                    <Bar dataKey="clutch_score" fill="#2DD4BF" radius={[4, 4, 0, 0]} maxBarSize={44} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <p className="mt-3 font-mono text-[11px] text-gray-400">
              ↑ hover the bars — every chart in a report is interactive.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
