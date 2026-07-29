"use client";

import { useState } from "react";

import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useScroll,
} from "framer-motion";
import Link from "next/link";

// Trimmed to the four destinations that matter, so the bar reads at a glance.
const LINKS = [
  { label: "How it works", href: "#how" },
  { label: "Your data", href: "#data" },
  { label: "Reports", href: "#showcase" },
  { label: "Pricing", href: "#pricing" },
];

const EASE = [0.22, 0.61, 0.36, 1] as const;

export default function LandingNav() {
  const { scrollY, scrollYProgress } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 12));

  return (
    <>
      {/* reading-progress hairline */}
      <motion.div
        aria-hidden
        style={{ scaleX: scrollYProgress }}
        className="fixed inset-x-0 top-0 z-[60] h-0.5 origin-left bg-gradient-to-r from-primary to-teal"
      />

      <motion.header
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: EASE }}
        className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-5"
      >
        <nav
          className={`mx-auto flex max-w-5xl items-center justify-between rounded-2xl px-4 py-2.5 transition-all duration-300 sm:px-5 ${
            scrolled
              ? "border border-gray-200/70 bg-white/80 shadow-lg shadow-ink/[0.04] backdrop-blur-md"
              : "border border-transparent"
          }`}
        >
          {/* logo */}
          <Link href="/" className="group flex items-center gap-2">
            <motion.span
              whileHover={{ scale: 1.15, rotate: 8 }}
              transition={{ type: "spring", stiffness: 400, damping: 12 }}
              className="relative flex h-2.5 w-2.5"
            >
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-50" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
            </motion.span>
            <span className="font-display text-lg font-semibold tracking-tight text-ink">
              Visual&nbsp;AI
            </span>
          </Link>

          {/* links with a sliding highlight */}
          <div
            className="hidden items-center lg:flex"
            onMouseLeave={() => setHovered(null)}
          >
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onMouseEnter={() => setHovered(l.href)}
                className="relative px-3.5 py-1.5 text-sm text-gray-500 transition-colors hover:text-ink"
              >
                {hovered === l.href && (
                  <motion.span
                    layoutId="nav-highlight"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    className="absolute inset-0 -z-10 rounded-lg bg-gray-100"
                  />
                )}
                {l.label}
              </a>
            ))}
          </div>

          {/* auth actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/auth/login"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:text-ink sm:block"
            >
              Log in
            </Link>
            <Link
              href="/auth/register"
              className="group relative hidden overflow-hidden rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition-transform hover:-translate-y-0.5 sm:block"
            >
              <span className="relative z-10">Get started</span>
              <span className="absolute inset-0 -translate-x-full bg-primary transition-transform duration-300 group-hover:translate-x-0" />
            </Link>

            {/* mobile toggle */}
            <button
              onClick={() => setMenuOpen((o) => !o)}
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 bg-white/70 text-ink lg:hidden"
            >
              <div className="flex w-4 flex-col gap-1">
                <motion.span
                  animate={menuOpen ? { rotate: 45, y: 5 } : { rotate: 0, y: 0 }}
                  className="h-0.5 w-full rounded bg-ink"
                />
                <motion.span
                  animate={menuOpen ? { opacity: 0 } : { opacity: 1 }}
                  className="h-0.5 w-full rounded bg-ink"
                />
                <motion.span
                  animate={menuOpen ? { rotate: -45, y: -5 } : { rotate: 0, y: 0 }}
                  className="h-0.5 w-full rounded bg-ink"
                />
              </div>
            </button>
          </div>
        </nav>

        {/* mobile sheet */}
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22, ease: EASE }}
              className="mx-auto mt-2 max-w-5xl overflow-hidden rounded-2xl border border-gray-200 bg-white/95 p-2 shadow-xl backdrop-blur-md lg:hidden"
            >
              {LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setMenuOpen(false)}
                  className="block rounded-lg px-4 py-3 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-ink"
                >
                  {l.label}
                </a>
              ))}
              <div className="mt-1 flex gap-2 border-t border-gray-100 p-2 pt-3">
                <Link
                  href="/auth/login"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-center text-sm font-medium text-ink"
                >
                  Log in
                </Link>
                <Link
                  href="/auth/register"
                  onClick={() => setMenuOpen(false)}
                  className="flex-1 rounded-lg bg-primary px-4 py-2.5 text-center text-sm font-semibold text-white"
                >
                  Get started
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>
    </>
  );
}
