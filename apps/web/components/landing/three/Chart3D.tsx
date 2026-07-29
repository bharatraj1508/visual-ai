"use client";

// Public wrapper for a single 3D chart. It owns the things that must live on the
// React side of the fence: a scroll progress value (Framer Motion) that drives
// the model's rotation, reduced-motion, and deferring the WebGL context until
// the chart nears the viewport so several can share a page cheaply. The heavy
// three.js Scene is imported with ssr:false — it only ever runs in the browser.

import { useRef } from "react";

import { useInView, useReducedMotion, useScroll } from "framer-motion";
import dynamic from "next/dynamic";

import type { ChartKind } from "./Scene";

const Scene = dynamic(() => import("./Scene"), {
  ssr: false,
  loading: () => <Skeleton />,
});

export default function Chart3D({
  kind,
  bars,
  className = "",
  label,
}: {
  kind: ChartKind;
  bars?: { label: string; values: number[] }[];
  className?: string;
  label?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion() ?? false;
  const inView = useInView(ref, { once: true, margin: "240px" });
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  return (
    <div ref={ref} className={`relative ${className}`} aria-hidden>
      {inView ? (
        <Scene kind={kind} bars={bars} scroll={scrollYProgress} reduced={reduced} />
      ) : (
        <Skeleton />
      )}
      {label && (
        <span className="pointer-events-none absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-white/70 px-2.5 py-0.5 font-mono text-[10px] text-gray-500 backdrop-blur">
          {label}
        </span>
      )}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="h-2 w-2 animate-ping rounded-full bg-primary/60" />
    </div>
  );
}
