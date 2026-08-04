import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { color, display, monoFamily } from "./theme";

// ---- shared primitives ---------------------------------------------------

export const useFadeUp = (delay = 0, distance = 28) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return {
    opacity: interpolate(s, [0, 1], [0, 1]),
    transform: `translateY(${interpolate(s, [0, 1], [distance, 0])}px)`,
  };
};

export const StepEyebrow: React.FC<{ n: string; label: string; delay?: number }> = ({
  n,
  label,
  delay = 0,
}) => {
  const st = useFadeUp(delay);
  return (
    <div
      style={{
        ...st,
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        fontFamily: monoFamily,
        fontSize: 22,
        letterSpacing: "0.28em",
        textTransform: "uppercase",
        color: color.primary,
      }}
    >
      <span>{n}</span>
      <span style={{ color: color.gray400 }}>{label}</span>
    </div>
  );
};

// Brand logo mark: rounded gradient tile with a small bar-chart glyph.
export const LogoMark: React.FC<{ size?: number }> = ({ size = 64 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.28,
      background: `linear-gradient(135deg, ${color.primary}, ${color.primarySoft})`,
      boxShadow: `0 18px 40px -12px ${color.primary}80`,
      display: "flex",
      alignItems: "flex-end",
      justifyContent: "center",
      gap: size * 0.09,
      padding: size * 0.24,
      boxSizing: "border-box",
    }}
  >
    {[0.45, 0.8, 0.6].map((h, i) => (
      <div
        key={i}
        style={{
          width: size * 0.12,
          height: size * h * 0.6,
          borderRadius: 4,
          background: "rgba(255,255,255,0.95)",
        }}
      />
    ))}
  </div>
);

export const Wordmark: React.FC<{ size?: number }> = ({ size = 64 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.28 }}>
    <LogoMark size={size} />
    <span
      style={{
        fontFamily: display,
        fontWeight: 700,
        fontSize: size * 0.82,
        letterSpacing: "-0.02em",
        color: color.ink,
      }}
    >
      Visual<span style={{ color: color.primary }}> AI</span>
    </span>
  </div>
);

export const Pill: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 12,
      borderRadius: 999,
      border: `1px solid ${color.gray200}`,
      background: "rgba(255,255,255,0.7)",
      padding: "12px 22px",
      fontFamily: monoFamily,
      fontSize: 20,
      letterSpacing: "0.22em",
      textTransform: "uppercase",
      color: color.gray500,
      ...style,
    }}
  >
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: 999,
        background: color.primary,
      }}
    />
    {children}
  </div>
);
