"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { fadeUp, reveal, stagger } from "./motion";

export default function CtaBand() {
  return (
    <section className="px-5 py-16 sm:px-8 sm:py-24">
      <motion.div
        {...reveal}
        variants={stagger}
        className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl bg-gradient-to-br from-primary to-[#ff8a80] px-6 py-16 text-center text-white sm:px-16"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_1px_1px,#fff_1px,transparent_0)] [background-size:22px_22px]"
        />
        <motion.h2
          variants={fadeUp}
          className="relative font-display text-3xl font-semibold leading-tight tracking-tight sm:text-4xl"
        >
          Read your first report in under a minute
        </motion.h2>
        <motion.p
          variants={fadeUp}
          className="relative mx-auto mt-4 max-w-xl text-white/85"
        >
          Bring a CSV. Leave with a set of reports you&apos;d have paid an
          analyst to write.
        </motion.p>
        <motion.div
          variants={fadeUp}
          className="relative mt-9 flex flex-wrap items-center justify-center gap-3"
        >
          <Link
            href="/auth/register"
            className="rounded-xl bg-white px-6 py-3.5 text-sm font-semibold text-primary shadow-lg transition-transform hover:-translate-y-0.5"
          >
            Get started — free
          </Link>
          <Link
            href="/auth/login"
            className="rounded-xl border border-white/40 px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
          >
            Log in
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}
