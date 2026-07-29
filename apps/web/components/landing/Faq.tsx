"use client";

import { useState } from "react";

import { AnimatePresence, motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";

// Every answer below reflects how the product actually behaves — file handling,
// the schema-only privacy model, the cleaning pass, custom questions, and
// credit pricing — not aspirational copy.
const FAQS = [
  {
    q: "What can I upload?",
    a: "A single CSV, several CSVs at once, or a ZIP containing up to 1,000 CSVs across nested folders. Visual AI expands the ZIP, finds every CSV wherever it sits in the folder tree, and builds one dataset from them — no need to flatten or rename anything first.",
  },
  {
    q: "How does it combine multiple files?",
    a: "Files that share the same columns are stacked into one table — for example a season split into one file per gameweek. Files with a different shape each become their own table, which the analyst can still query and join on shared columns. In practice a 950-file export usually collapses into a handful of tables.",
  },
  {
    q: "Is my data sent to the AI?",
    a: "Not your rows. Only a compact profile of each column — its name, type, range, and a few example values — is shared with the model. That profile is what the analyst reasons over; the full dataset stays in your workspace and is queried locally to produce every number and chart.",
  },
  {
    q: "What does the clean-up do to my data?",
    a: "A safe, non-destructive pass: it trims blank space, removes exact duplicate rows, and normalizes obvious inconsistencies. It never invents values or drops real data, and your original upload is always kept as a backup — you can see exactly what was changed before generating anything.",
  },
  {
    q: "Can I ask my own question instead of the suggestions?",
    a: "Yes. Type a question in plain English on the analyze page. Visual AI checks it against your dataset's columns, and if the data can answer it, turns it into a problem statement you generate like any other report. If it can't, it tells you why rather than inventing an answer.",
  },
  {
    q: "What does it cost?",
    a: "You start with 50 free credits — about five full reports — the moment you verify your email, no card required. A full multi-section report is roughly 10 credits, and regenerating the same question costs a third of that. Top up with credit packs via UPI, cards, or netbanking whenever you need more; credits don't expire mid-project.",
  },
];

export default function Faq() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="relative bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-3xl px-5 sm:px-8">
        <motion.div {...reveal} variants={stagger} className="text-center">
          <motion.p
            variants={fadeUp}
            className="mb-3 font-mono text-xs uppercase tracking-[0.25em] text-primary"
          >
            questions, answered
          </motion.p>
          <motion.h2
            variants={fadeUp}
            className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            The things people ask first
          </motion.h2>
        </motion.div>

        <motion.div
          {...reveal}
          variants={stagger}
          className="mt-12 divide-y divide-gray-200 overflow-hidden rounded-2xl border border-gray-200 bg-white"
        >
          {FAQS.map((item, i) => {
            const isOpen = open === i;
            return (
              <motion.div key={item.q} variants={fadeUp}>
                <h3>
                  <button
                    onClick={() => setOpen(isOpen ? null : i)}
                    aria-expanded={isOpen}
                    aria-controls={`faq-panel-${i}`}
                    className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition-colors hover:bg-gray-50/70 sm:px-6"
                  >
                    <span className="font-display text-base font-semibold text-ink sm:text-lg">
                      {item.q}
                    </span>
                    <motion.span
                      animate={{ rotate: isOpen ? 45 : 0 }}
                      transition={{ duration: 0.25, ease: [0.22, 0.61, 0.36, 1] }}
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors ${
                        isOpen
                          ? "border-primary/40 bg-primary/10 text-primary"
                          : "border-gray-200 text-gray-400"
                      }`}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M12 5v14M5 12h14" />
                      </svg>
                    </motion.span>
                  </button>
                </h3>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={`faq-panel-${i}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.22, 0.61, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-5 text-[15px] leading-relaxed text-gray-500 sm:px-6">
                        {item.a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>

        <motion.p
          {...reveal}
          variants={fadeUp}
          className="mt-8 text-center text-sm text-gray-400"
        >
          Still curious?{" "}
          <a href="#data" className="font-medium text-primary hover:underline">
            See how the data pipeline works
          </a>
          .
        </motion.p>
      </div>
    </section>
  );
}
