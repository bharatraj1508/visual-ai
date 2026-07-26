"use client";

import { PropsWithChildren } from "react";

import { MotionConfig } from "framer-motion";

/** Applies the honored reduced-motion preference across the whole landing. */
export default function LandingShell({ children }: PropsWithChildren) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
