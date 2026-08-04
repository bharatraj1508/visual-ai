import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { color, color2, display, monoFamily, sans } from "../theme";

// -------------------------------------------------------------- animation helpers
export const useEnter = (delay = 0, distance = 40) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 200 } });
  return {
    opacity: interpolate(s, [0, 1], [0, 1]),
    transform: `translateY(${interpolate(s, [0, 1], [distance, 0])}px)`,
  };
};

export const usePop = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 13, mass: 0.7 } });
  return { opacity: s, transform: `scale(${interpolate(s, [0, 1], [0.7, 1])})` };
};

// count a number up from 0 -> value between [start,end] frames
export const useCountUp = (value: number, start: number, end: number) => {
  const frame = useCurrentFrame();
  return Math.round(
    interpolate(frame, [start, end], [0, value], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
};

// -------------------------------------------------------------- browser chrome
export const BrowserFrame: React.FC<{
  url: string;
  width?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ url, width = 900, children, style }) => (
  <div
    style={{
      width,
      borderRadius: 30,
      background: color.white,
      border: `1px solid ${color.gray200}`,
      boxShadow: "0 60px 120px -50px rgba(11,18,32,0.45)",
      overflow: "hidden",
      ...style,
    }}
  >
    <div
      style={{
        height: 74,
        background: color.gray50,
        borderBottom: `1px solid ${color.gray200}`,
        display: "flex",
        alignItems: "center",
        gap: 20,
        padding: "0 28px",
      }}
    >
      <div style={{ display: "flex", gap: 12 }}>
        {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
          <span key={c} style={{ width: 18, height: 18, borderRadius: 999, background: c }} />
        ))}
      </div>
      <div
        style={{
          flex: 1,
          height: 44,
          borderRadius: 999,
          background: color.white,
          border: `1px solid ${color.gray200}`,
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "0 20px",
          fontFamily: monoFamily,
          fontSize: 22,
          color: color.gray400,
        }}
      >
        <LockIcon />
        {url}
      </div>
    </div>
    <div style={{ position: "relative" }}>{children}</div>
  </div>
);

// -------------------------------------------------------------- cursor
export const Cursor: React.FC<{
  from: [number, number];
  to: [number, number];
  moveStart: number;
  moveEnd: number;
  clickAt?: number;
}> = ({ from, to, moveStart, moveEnd, clickAt }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({ frame: frame - moveStart, fps, durationInFrames: moveEnd - moveStart, config: { damping: 200 } });
  const x = interpolate(t, [0, 1], [from[0], to[0]]);
  const y = interpolate(t, [0, 1], [from[1], to[1]]);
  const click = clickAt
    ? interpolate(frame, [clickAt - 3, clickAt, clickAt + 6], [1, 0.82, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const ring = clickAt
    ? interpolate(frame, [clickAt, clickAt + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${click})`, zIndex: 50 }}>
      {clickAt && ring > 0 && ring < 1 && (
        <div
          style={{
            position: "absolute",
            left: -8,
            top: -8,
            width: 60,
            height: 60,
            borderRadius: 999,
            border: `3px solid ${color.primary}`,
            opacity: 1 - ring,
            transform: `translate(-50%,-50%) scale(${0.3 + ring * 1.6})`,
          }}
        />
      )}
      <svg width="46" height="46" viewBox="0 0 24 24" style={{ filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.25))" }}>
        <path d="M4 2l6 16 2.5-6.5L19 9z" fill="#0B1220" stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

// -------------------------------------------------------------- pieces
export const StatusPill: React.FC<{ kind: "done" | "run" | "fail"; children: React.ReactNode }> = ({
  kind,
  children,
}) => {
  const map = {
    done: { bg: color2.green100, fg: color2.green700 },
    run: { bg: color2.amber100, fg: color2.amber700 },
    fail: { bg: color2.red100, fg: color2.red700 },
  }[kind];
  return (
    <span
      style={{
        background: map.bg,
        color: map.fg,
        fontFamily: monoFamily,
        fontSize: 20,
        fontWeight: 500,
        padding: "6px 16px",
        borderRadius: 999,
      }}
    >
      {children}
    </span>
  );
};

export const StepHeader: React.FC<{ n: string; label: string; total?: number; index?: number }> = ({
  n,
  label,
  total = 7,
  index = 0,
}) => {
  const e = useEnter(2, 24);
  return (
    <div style={{ ...e, display: "flex", flexDirection: "column", alignItems: "center", gap: 30 }}>
      <div style={{ display: "flex", gap: 14 }}>
        {Array.from({ length: total }).map((_, i) => (
          <span
            key={i}
            style={{
              width: i === index ? 46 : 16,
              height: 16,
              borderRadius: 999,
              background: i === index ? color.primary : i < index ? `${color.primary}55` : color.gray200,
            }}
          />
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 18, fontFamily: monoFamily, fontSize: 30, letterSpacing: "0.24em", textTransform: "uppercase" }}>
        <span style={{ color: color.primary }}>{n}</span>
        <span style={{ color: color.gray400 }}>{label}</span>
      </div>
    </div>
  );
};

export const Caption: React.FC<{ delay?: number; children: React.ReactNode }> = ({ delay = 30, children }) => {
  const e = useEnter(delay, 24);
  return (
    <div
      style={{
        ...e,
        fontFamily: display,
        fontWeight: 600,
        fontSize: 52,
        lineHeight: 1.2,
        letterSpacing: "-0.02em",
        color: color.ink,
        textAlign: "center",
        maxWidth: 900,
      }}
    >
      {children}
    </div>
  );
};

// -------------------------------------------------------------- icons
export const LockIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color.gray400} strokeWidth={2}>
    <rect x="5" y="11" width="14" height="9" rx="2" />
    <path d="M8 11V8a4 4 0 0 1 8 0v3" />
  </svg>
);

export const primaryBtn = (extra?: React.CSSProperties): React.CSSProperties => ({
  background: color.primary,
  color: color.white,
  fontFamily: sans,
  fontWeight: 600,
  fontSize: 26,
  padding: "18px 0",
  borderRadius: 14,
  textAlign: "center",
  ...extra,
});

export const inputBox = (placeholder: string, value?: string): React.CSSProperties => ({
  border: `1px solid ${color.gray200}`,
  borderRadius: 12,
  padding: "18px 22px",
  fontFamily: sans,
  fontSize: 26,
  color: value ? color.ink : color.gray400,
});
