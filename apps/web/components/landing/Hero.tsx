"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import DataMorph from "./DataMorph";
import { fadeUp, stagger } from "./motion";

export default function Hero() {
  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden pt-28 pb-20 sm:pt-32">
      {/* atmosphere: dotted grid + soft brand glows */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_1px_1px,rgba(11,18,32,0.05)_1px,transparent_0)] [background-size:26px_26px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 left-1/2 -z-10 h-[520px] w-[880px] -translate-x-1/2 rounded-full bg-gradient-to-tr from-primary/10 via-teal/10 to-transparent blur-3xl"
      />

      <div className="mx-auto grid max-w-6xl items-center gap-14 px-5 sm:px-8 lg:grid-cols-[1.05fr_1fr]">
        <motion.div variants={stagger} initial="hidden" animate="show">
          <motion.div
            variants={fadeUp}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white/70 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.2em] text-gray-500 backdrop-blur"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            not another AI chat
          </motion.div>

          <motion.h1
            variants={fadeUp}
            className="font-display text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-6xl"
          >
            Stop chatting with
            <br className="hidden sm:block" /> your data.{" "}
            <span className="relative whitespace-nowrap text-primary">
              Read its report.
              <svg
                aria-hidden
                viewBox="0 0 300 12"
                className="absolute -bottom-1.5 left-0 h-2.5 w-full text-primary/40"
                preserveAspectRatio="none"
              >
                <path
                  d="M2 8 C 60 2, 120 2, 180 6 S 260 10, 298 4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
              </svg>
            </span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="mt-7 max-w-xl text-lg leading-relaxed text-gray-500"
          >
            Upload a CSV and Visual AI scopes the five reports worth running —
            then writes each one with findings, a clear narrative, and
            interactive charts. No prompts. No chat window.
          </motion.p>

          <motion.div
            variants={fadeUp}
            className="mt-9 flex flex-wrap items-center gap-3"
          >
            <Link
              href="/auth/register"
              className="group relative overflow-hidden rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition-transform hover:-translate-y-0.5"
            >
              <span className="relative z-10 flex items-center gap-2">
                Get started — free
                <span className="transition-transform group-hover:translate-x-0.5">
                  →
                </span>
              </span>
              <span className="absolute inset-0 bg-gradient-to-r from-primary to-[#ff8a80] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </Link>
            <a
              href="#showcase"
              className="rounded-xl border border-gray-300 px-6 py-3.5 text-sm font-semibold text-ink transition-colors hover:border-ink hover:bg-white"
            >
              See a live report
            </a>
          </motion.div>

          <motion.p
            variants={fadeUp}
            className="mt-6 font-mono text-xs text-gray-400"
          >
            CSV in → analyst-grade report out. No prompt engineering.
          </motion.p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 0.61, 0.36, 1] }}
        >
          <DataMorph />
        </motion.div>
      </div>
    </section>
  );
}
