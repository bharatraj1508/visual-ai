"use client";

import { useState } from "react";

import { motion, useMotionValueEvent, useScroll } from "framer-motion";
import Link from "next/link";

const LINKS = [
  { label: "How it works", href: "#how" },
  { label: "Reports", href: "#showcase" },
  { label: "Problem statements", href: "#problem-statement" },
  { label: "Dashboard", href: "#dashboard" },
  { label: "Charts", href: "#charts" },
  { label: "Pricing", href: "#pricing" },
];

export default function LandingNav() {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 12));

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 0.61, 0.36, 1] }}
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled
          ? "border-b border-gray-200/70 bg-white/80 backdrop-blur-md"
          : "border-b border-transparent"
      }`}
    >
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5 sm:px-8">
        <Link href="/" className="group flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-50" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-ink">
            Visual&nbsp;AI
          </span>
        </Link>

        <div className="hidden items-center gap-6 lg:flex">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-gray-500 transition-colors hover:text-ink"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/auth/login"
            className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:text-ink"
          >
            Log in
          </Link>
          <Link
            href="/auth/register"
            className="group relative overflow-hidden rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition-transform hover:-translate-y-0.5"
          >
            <span className="relative z-10">Get started</span>
            <span className="absolute inset-0 -translate-x-full bg-primary transition-transform duration-300 group-hover:translate-x-0" />
          </Link>
        </div>
      </nav>
    </motion.header>
  );
}
