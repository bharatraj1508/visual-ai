"use client";

import { motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";
import Chart3D from "./three/Chart3D";

const STEPS = [
  {
    n: "01",
    title: "Drop your CSV",
    body: "Profiled in seconds. Only the schema — column names, types, ranges — ever reaches the model, never your rows.",
    art: <UploadArt />,
  },
  {
    n: "02",
    title: "The AI scopes the work",
    body: "Five thesis-driven reports, each combining several columns into a real question worth answering — not a pile of generic charts.",
    art: <SuggestArt />,
  },
  {
    n: "03",
    title: "Generate the report",
    body: "Findings, a written narrative, and interactive charts — streamed onto the page as the analyst writes it.",
    art: <ReportArt />,
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="max-w-2xl">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            how it works
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            Three steps from spreadsheet to insight
          </motion.h2>
        </motion.div>

        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-14 grid gap-6 md:grid-cols-3"
        >
          {STEPS.map((step) => (
            <motion.div
              key={step.n}
              variants={fadeUp}
              className="group relative flex flex-col rounded-2xl border border-gray-200 bg-white p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5"
            >
              <div className="mb-5 flex h-36 items-center justify-center overflow-hidden rounded-xl bg-gray-50">
                {step.art}
              </div>
              <span className="font-mono text-xs text-primary">{step.n}</span>
              <h3 className="mt-2 font-display text-xl font-semibold text-ink">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-500">
                {step.body}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function UploadArt() {
  return (
    <motion.div
      initial={{ y: 6 }}
      whileInView={{ y: -6 }}
      viewport={{ once: false }}
      transition={{ repeat: Infinity, repeatType: "reverse", duration: 1.8, ease: "easeInOut" }}
      className="flex h-20 w-28 flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-primary/40 bg-white"
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FB676E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3v12M7 8l5-5 5 5" />
        <path d="M5 21h14" />
      </svg>
      <span className="font-mono text-[10px] text-gray-400">data.csv</span>
    </motion.div>
  );
}

function SuggestArt() {
  return (
    <div className="flex w-40 flex-col gap-2">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.4, x: -8 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.15, duration: 0.5 }}
          className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-2.5 py-2"
        >
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary/10 font-mono text-[9px] text-primary">
            {i + 1}
          </span>
          <span className="h-1.5 flex-1 rounded-full bg-gray-200" />
        </motion.div>
      ))}
    </div>
  );
}

function ReportArt() {
  // The report's chart, rendered as a live 3D model like the rest of the page.
  return <Chart3D kind="area" className="h-full w-full" />;
}
