// Brand tokens mirrored from tailwind.config.ts so the video matches the site.
import { loadFont as loadSora } from "@remotion/google-fonts/Sora";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const sora = loadSora("normal", { weights: ["500", "600", "700"] });
export const inter = loadInter("normal", { weights: ["400", "500", "600"] });
export const mono = loadMono("normal", { weights: ["400", "500"] });

export const display = sora.fontFamily;
export const sans = inter.fontFamily;
export const monoFamily = mono.fontFamily;

export const color = {
  primary: "#FB676E",
  primarySoft: "#ff8a80",
  ink: "#0B1220",
  gray500: "#6B7280",
  gray400: "#9CA3AF",
  gray300: "#D1D5DB",
  gray200: "#E5E7EB",
  gray100: "#F3F4F6",
  gray50: "#F9FAFB",
  teal: "#2DD4BF",
  white: "#FFFFFF",
  indigo: "#6366F1",
  amber: "#F59E0B",
  violet: "#A855F7",
  sky: "#38BDF8",
};

export const VIDEO = {
  fps: 30,
  width: 1920,
  height: 1080,
} as const;

// 9:16 vertical master for Reels / Stories / Shorts.
export const VERTICAL = {
  fps: 30,
  width: 1080,
  height: 1920,
} as const;

export const color2 = {
  green50: "#ECFDF5",
  green100: "#D1FAE5",
  green600: "#059669",
  green700: "#047857",
  amber50: "#FFFBEB",
  amber100: "#FEF3C7",
  amber500: "#F59E0B",
  amber700: "#B45309",
  red100: "#FEE2E2",
  red700: "#B91C1C",
};
