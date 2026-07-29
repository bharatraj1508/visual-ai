"use client";

import { useEffect, useRef, useState } from "react";

import {
  animate,
  motion,
  useInView,
  useReducedMotion,
} from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";

// A new signature moment for the multi-file / ZIP feature: a pile of source
// files visibly collapses into a handful of clean, query-ready tables — using a
// real upload (a 950-file FPL season export → 7 tables, 107,955 rows).

// Source files as they'd sit in the ZIP; the ×N badge stands for many same-shape
// per-gameweek exports that get stacked together.
const SOURCE_FILES = [
  { name: "players.csv", mult: 136 },
  { name: "playerstats.csv", mult: 271 },
  { name: "GW/matches.csv", mult: 270 },
  { name: "GW/playermatchstats.csv", mult: 135 },
  { name: "team_history.csv", mult: 136 },
  { name: "teams.csv", mult: null },
  { name: "gameweek_summaries.csv", mult: null },
];

// The tables they resolve into — exactly what the app produced for this dataset.
const TABLES = [
  { name: "playerstats", rows: 59108 },
  { name: "team_history", rows: 31920 },
  { name: "playermatchstats", rows: 15228 },
  { name: "players", rows: 869 },
  { name: "matches", rows: 526 },
  { name: "teams", rows: 266 },
  { name: "gameweek_summaries", rows: 38 },
];

const FEATURES = [
  {
    title: "Bring up to 1,000 files",
    body: "Drop a ZIP of a whole folder tree. Every CSV inside — at any depth — joins the dataset, so you never flatten your exports by hand.",
    icon: <ZipIcon />,
  },
  {
    title: "Schema-matched automatically",
    body: "Files that share columns stack into one table. Genuinely different files stay separate — and the analyst can still join them on shared keys.",
    icon: <MergeIcon />,
  },
  {
    title: "Cleaned, never damaged",
    body: "Blank space trimmed, exact duplicate rows removed, obvious inconsistencies fixed. Nothing is invented or dropped, and your original upload is kept.",
    icon: <ShieldIcon />,
  },
];

export default function DataPipeline() {
  return (
    <section
      id="data"
      className="relative overflow-hidden bg-gradient-to-b from-white to-gray-50 py-24 sm:py-32"
    >
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            built for real-world data
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            Bring the whole folder. We make it one dataset.
          </motion.h2>
          <motion.p variants={fadeUp} className="mt-4 text-lg leading-relaxed text-gray-500">
            Real data rarely arrives as one tidy file. Upload a stack of CSVs — or
            a single ZIP of nested folders holding up to a thousand of them — and
            Visual&nbsp;AI combines and cleans them into query-ready tables before
            it writes a word.
          </motion.p>
        </motion.div>

        <MergeDiagram />

        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-10 grid gap-6 md:grid-cols-3"
        >
          {FEATURES.map((f) => (
            <motion.div
              key={f.title}
              variants={fadeUp}
              className="flex gap-3 rounded-2xl border border-gray-200 bg-white p-5"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                {f.icon}
              </span>
              <div>
                <h3 className="font-display text-base font-semibold text-ink">
                  {f.title}
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-500">
                  {f.body}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function MergeDiagram() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const reduce = !!useReducedMotion();
  const play = inView || reduce;

  return (
    <div
      ref={ref}
      className="mt-14 overflow-hidden rounded-3xl border border-gray-200 bg-white p-6 shadow-xl shadow-primary/5 sm:p-8"
    >
      <div className="grid items-center gap-6 lg:grid-cols-[1fr_auto_1.1fr]">
        {/* sources */}
        <div>
          <p className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-gray-400">
            <FolderIcon />
            2025-2026.zip · 950 files
          </p>
          <div className="flex flex-wrap gap-2">
            {SOURCE_FILES.map((f, i) => (
              <motion.span
                key={f.name}
                initial={reduce ? false : { opacity: 0, y: 8, filter: "blur(4px)" }}
                animate={play ? { opacity: 1, y: 0, filter: "blur(0px)" } : {}}
                transition={{ delay: i * 0.06, duration: 0.45, ease: [0.22, 0.61, 0.36, 1] }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 font-mono text-[11px] text-gray-500"
              >
                <FileGlyph />
                {f.name}
                {f.mult && (
                  <span className="rounded bg-primary/10 px-1 text-[10px] font-semibold text-primary">
                    ×{f.mult}
                  </span>
                )}
              </motion.span>
            ))}
          </div>
        </div>

        {/* flow */}
        <motion.div
          initial={reduce ? false : { opacity: 0, scale: 0.85 }}
          animate={play ? { opacity: 1, scale: 1 } : {}}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="mx-auto flex flex-col items-center gap-1 text-primary"
        >
          <span className="font-mono text-[10px] uppercase tracking-wider text-gray-400">
            combine + clean
          </span>
          <FlowArrow />
        </motion.div>

        {/* resulting tables */}
        <div>
          <p className="mb-3 flex items-center justify-between font-mono text-[11px] uppercase tracking-wider text-gray-400">
            <span className="flex items-center gap-2">
              <TableIcon />7 query-ready tables
            </span>
          </p>
          <div className="space-y-1.5">
            {TABLES.map((t, i) => (
              <motion.div
                key={t.name}
                initial={reduce ? false : { opacity: 0, x: 16 }}
                animate={play ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: 0.6 + i * 0.08, duration: 0.5, ease: [0.22, 0.61, 0.36, 1] }}
                className="flex items-center justify-between gap-2 rounded-lg border border-gray-100 bg-gradient-to-r from-primary/[0.04] to-transparent px-3 py-2"
              >
                <span className="flex min-w-0 items-center gap-2 font-mono text-xs text-ink">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span className="truncate">{t.name}</span>
                </span>
                <span className="shrink-0 font-mono text-[11px] text-gray-400">
                  <CountUp to={t.rows} play={play} reduce={!!reduce} /> rows
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* worked-example footer */}
      <motion.div
        initial={reduce ? false : { opacity: 0 }}
        animate={play ? { opacity: 1 } : {}}
        transition={{ delay: 1.2, duration: 0.6 }}
        className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-gray-100 pt-5 text-sm text-gray-500"
      >
        <span className="font-semibold text-ink">One real upload:</span>
        a 950-file FPL season export became
        <b className="font-semibold text-primary">7 tables</b>·
        <b className="font-semibold text-ink">
          <CountUp to={107955} play={play} reduce={!!reduce} /> rows
        </b>
        — in a single drag-and-drop.
      </motion.div>
    </div>
  );
}

function CountUp({
  to,
  play,
  reduce,
}: {
  to: number;
  play: boolean;
  reduce: boolean;
}) {
  const [val, setVal] = useState(reduce ? to : 0);
  useEffect(() => {
    if (!play || reduce) {
      setVal(to);
      return;
    }
    const controls = animate(0, to, {
      duration: 1.1,
      delay: 0.6,
      ease: [0.22, 0.61, 0.36, 1],
      onUpdate: (v) => setVal(Math.round(v)),
    });
    return () => controls.stop();
  }, [play, reduce, to]);
  return <>{val.toLocaleString()}</>;
}

/* icons */
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};
function ZipIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
      <path d="M21 8v13H3V3h10M14 3v5h7M14 3l7 5M9 12h2M9 16h2" />
    </svg>
  );
}
function MergeIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
      <path d="M6 3v6a6 6 0 0 0 6 6h6M18 12l3 3-3 3" />
    </svg>
  );
}
function ShieldIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
      <path d="M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6l7-3zM9 12l2 2 4-4" />
    </svg>
  );
}
function FolderIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" {...stroke}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}
function TableIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" {...stroke}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 4v16" />
    </svg>
  );
}
function FileGlyph() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" {...stroke} className="text-gray-400">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}
function FlowArrow() {
  return (
    <svg width="46" height="24" viewBox="0 0 46 24" fill="none" className="rotate-90 lg:rotate-0">
      <path d="M2 12h38m0 0-6-6m6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
