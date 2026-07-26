"use client";

import { motion } from "framer-motion";

import { fadeUp, reveal, stagger } from "./motion";

export default function Thesis() {
  return (
    <section className="relative overflow-hidden bg-ink py-24 text-white sm:py-32">
      {/* faint drifting grid — the one dark anchor of the page */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 animate-grid-pan opacity-[0.14] [background-image:linear-gradient(rgba(255,255,255,0.35)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.35)_1px,transparent_1px)] [background-size:40px_40px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 h-64 w-[700px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]"
      />

      <motion.div
        {...reveal}
        variants={stagger}
        className="relative mx-auto max-w-4xl px-5 text-center sm:px-8"
      >
        <motion.p
          variants={fadeUp}
          className="mb-6 font-mono text-xs uppercase tracking-[0.3em] text-primary"
        >
          the difference
        </motion.p>
        <motion.h2
          variants={fadeUp}
          className="font-display text-3xl font-semibold leading-[1.15] tracking-tight sm:text-5xl"
        >
          A chatbot gives you a{" "}
          <span className="text-gray-500 line-through decoration-primary/60">
            conversation
          </span>
          .
          <br />
          Visual AI gives you a{" "}
          <span className="text-teal">conclusion</span>.
        </motion.h2>
        <motion.p
          variants={fadeUp}
          className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-gray-400"
        >
          No blinking cursor, no back-and-forth prompting to coax an answer out.
          Visual AI does the analyst&apos;s job end to end — it decides which
          questions are worth asking, then answers them in writing, with the
          charts to prove it.
        </motion.p>
      </motion.div>
    </section>
  );
}
