"use client";

import { motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";

export default function ProblemStatement() {
  return (
    <section id="problem-statement" className="relative bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* copy */}
          <motion.div {...reveal} variants={stagger}>
            <motion.p
              variants={fadeUp}
              className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
            >
              one question, many takes
            </motion.p>
            <motion.h2
              variants={fadeUp}
              className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
            >
              What&apos;s a problem statement?
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="mt-4 text-lg leading-relaxed text-gray-500"
            >
              A <span className="font-medium text-ink">problem statement</span>{" "}
              is a single analytical question you put to your data — like{" "}
              <em className="text-gray-600">
                &ldquo;Which country markets produce the highest solo-vs-lead
                streamers?&rdquo;
              </em>
            </motion.p>
            <motion.p
              variants={fadeUp}
              className="mt-3 text-lg leading-relaxed text-gray-500"
            >
              Generate it once, then{" "}
              <span className="font-medium text-ink">regenerate</span> for a
              fresh take. Every version stacks under that one question — newest
              open, the rest a click away — so you can compare angles instead of
              losing them.
            </motion.p>

            <motion.div variants={fadeUp} className="mt-6 space-y-3">
              {[
                {
                  icon: <RefreshIcon />,
                  text: "Regenerate to explore a different angle on the same question.",
                },
                {
                  icon: <DownloadIcon />,
                  text: "Download any single version as a polished PDF — charts included.",
                },
                {
                  icon: <ZipIcon />,
                  text: "Download all versions of a problem statement as one ZIP.",
                },
              ].map((row) => (
                <div key={row.text} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    {row.icon}
                  </span>
                  <p className="text-sm leading-relaxed text-gray-600">
                    {row.text}
                  </p>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* screenshot */}
          <motion.div
            {...reveal}
            variants={fadeUp}
            className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-primary/5"
          >
            <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
              <span className="h-3 w-3 rounded-full bg-red-300" />
              <span className="h-3 w-3 rounded-full bg-amber-300" />
              <span className="h-3 w-3 rounded-full bg-green-300" />
              <span className="ml-2 font-mono text-[11px] text-gray-400">
                Original · Regeneration 1
              </span>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/report-versions.png"
              alt="A report with an Original and a Regeneration version, each downloadable"
              className="w-full"
              loading="lazy"
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

const iconProps = {
  width: 15,
  height: 15,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
function RefreshIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
    </svg>
  );
}
function DownloadIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  );
}
function ZipIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 8v13H3V3h10M14 3v5h7M14 3l7 5M9 13h2M9 17h2" />
    </svg>
  );
}
