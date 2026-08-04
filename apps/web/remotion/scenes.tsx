import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { color, display, monoFamily, sans } from "./theme";
import { Background } from "./Background";
import { LogoMark, Pill, StepEyebrow, useFadeUp, Wordmark } from "./parts";

const center: React.CSSProperties = {
  justifyContent: "center",
  alignItems: "center",
  textAlign: "center",
};

// ---------------------------------------------------------------- Scene 1
export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 14, mass: 0.7 } });
  const pill = useFadeUp(22);
  const out = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" },
  );
  return (
    <Background>
      <AbsoluteFill style={{ ...center, gap: 40, opacity: out }}>
        <div style={{ transform: `scale(${interpolate(pop, [0, 1], [0.8, 1])})`, opacity: pop }}>
          <Wordmark size={110} />
        </div>
        <div style={pill}>
          <Pill>not another AI chat</Pill>
        </div>
      </AbsoluteFill>
    </Background>
  );
};

// ---------------------------------------------------------------- Scene 2
export const HeadlineScene: React.FC = () => {
  const frame = useCurrentFrame();
  const line1 = useFadeUp(6);
  const line2 = useFadeUp(20);
  const sub = useFadeUp(40);
  // hand-drawn underline draw-in
  const dash = interpolate(frame, [34, 70], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <Background>
      <AbsoluteFill style={{ ...center, padding: "0 160px" }}>
        <h1
          style={{
            fontFamily: display,
            fontWeight: 600,
            fontSize: 104,
            lineHeight: 1.05,
            letterSpacing: "-0.03em",
            color: color.ink,
            margin: 0,
          }}
        >
          <span style={{ display: "block", ...line1 }}>
            Stop chatting with your data.
          </span>
          <span
            style={{
              display: "inline-block",
              position: "relative",
              color: color.primary,
              ...line2,
            }}
          >
            Read its report.
            <svg
              viewBox="0 0 300 12"
              preserveAspectRatio="none"
              style={{
                position: "absolute",
                left: 0,
                bottom: -18,
                width: "100%",
                height: 24,
                color: color.primary,
                opacity: 0.45,
              }}
            >
              <path
                d="M2 8 C 60 2, 120 2, 180 6 S 260 10, 298 4"
                fill="none"
                stroke="currentColor"
                strokeWidth={4}
                strokeLinecap="round"
                pathLength={1}
                strokeDasharray={1}
                strokeDashoffset={dash}
              />
            </svg>
          </span>
        </h1>
        <p
          style={{
            ...sub,
            fontFamily: sans,
            fontSize: 34,
            lineHeight: 1.5,
            color: color.gray500,
            maxWidth: 1100,
            marginTop: 56,
          }}
        >
          Upload a CSV. Visual AI scopes the five reports worth running — then
          writes each one with findings, a narrative, and interactive charts.
        </p>
      </AbsoluteFill>
    </Background>
  );
};

// ---------------------------------------------------------------- Scene 3
export const UploadScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = spring({ frame: frame - 18, fps, config: { damping: 16 } });
  const dropY = interpolate(drop, [0, 1], [-260, 0]);
  const eyebrow = useFadeUp(4);
  const cols = [
    "order_id · int",
    "region · text",
    "revenue · float",
    "signup_date · date",
    "churned · bool",
  ];
  return (
    <Background>
      <AbsoluteFill style={{ ...center, gap: 56 }}>
        <div style={eyebrow}>
          <StepEyebrow n="01" label="Drop your CSV" />
        </div>
        {/* dropzone */}
        <div
          style={{
            width: 560,
            height: 300,
            borderRadius: 28,
            border: `3px dashed ${color.primary}66`,
            background: "rgba(255,255,255,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
        >
          {/* the file card */}
          <div
            style={{
              transform: `translateY(${dropY}px)`,
              opacity: interpolate(drop, [0, 0.15], [0, 1]),
              width: 300,
              borderRadius: 18,
              background: color.white,
              border: `1px solid ${color.gray200}`,
              boxShadow: "0 30px 60px -20px rgba(11,18,32,0.25)",
              padding: 26,
              display: "flex",
              alignItems: "center",
              gap: 18,
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: `${color.primary}14`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width={30} height={30} viewBox="0 0 24 24" fill="none" stroke={color.primary} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
            </div>
            <div>
              <div style={{ fontFamily: display, fontSize: 26, fontWeight: 600, color: color.ink }}>
                sales_2025.csv
              </div>
              <div style={{ fontFamily: monoFamily, fontSize: 18, color: color.gray400, marginTop: 4 }}>
                48,210 rows · 12 columns
              </div>
            </div>
          </div>
        </div>
        {/* schema chips reveal — only the schema ever reaches the model */}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center", maxWidth: 1000 }}>
          {cols.map((c, i) => {
            const s = spring({ frame: frame - (46 + i * 6), fps, config: { damping: 200 } });
            return (
              <span
                key={c}
                style={{
                  opacity: s,
                  transform: `translateY(${interpolate(s, [0, 1], [14, 0])}px)`,
                  fontFamily: monoFamily,
                  fontSize: 20,
                  color: color.gray500,
                  background: color.white,
                  border: `1px solid ${color.gray200}`,
                  borderRadius: 999,
                  padding: "10px 20px",
                }}
              >
                {c}
              </span>
            );
          })}
        </div>
        <p style={{ ...useFadeUp(78), fontFamily: sans, fontSize: 26, color: color.gray400 }}>
          Profiled in seconds — only the schema ever reaches the model, never your rows.
        </p>
      </AbsoluteFill>
    </Background>
  );
};

// ---------------------------------------------------------------- Scene 4
const REPORTS = [
  { t: "Where revenue is quietly leaking", tag: "Revenue" },
  { t: "Which regions are outperforming — and why", tag: "Geography" },
  { t: "The churn signal hiding in signups", tag: "Retention" },
  { t: "Seasonality you can plan around", tag: "Time series" },
  { t: "The segments worth doubling down on", tag: "Segmentation" },
];

export const ScopeScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const head = useFadeUp(4);
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 46 }}>
        <div style={{ ...head, textAlign: "center" }}>
          <StepEyebrow n="02" label="The AI scopes the work" />
          <h2
            style={{
              fontFamily: display,
              fontWeight: 600,
              fontSize: 72,
              letterSpacing: "-0.02em",
              color: color.ink,
              margin: "22px 0 0",
              maxWidth: 1300,
            }}
          >
            The five reports worth running
          </h2>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18, width: 1180 }}>
          {REPORTS.map((r, i) => {
            const s = spring({ frame: frame - (24 + i * 10), fps, config: { damping: 200 } });
            return (
              <div
                key={r.t}
                style={{
                  opacity: s,
                  transform: `translateX(${interpolate(s, [0, 1], [-40, 0])}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 26,
                  background: color.white,
                  border: `1px solid ${color.gray200}`,
                  borderRadius: 20,
                  padding: "26px 32px",
                  boxShadow: "0 20px 40px -30px rgba(11,18,32,0.3)",
                }}
              >
                <span
                  style={{
                    fontFamily: monoFamily,
                    fontSize: 24,
                    color: color.primary,
                    width: 44,
                    height: 44,
                    borderRadius: 12,
                    background: `${color.primary}12`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ fontFamily: display, fontSize: 34, fontWeight: 600, color: color.ink, flex: 1 }}>
                  {r.t}
                </span>
                <span
                  style={{
                    fontFamily: monoFamily,
                    fontSize: 18,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: color.gray400,
                    border: `1px solid ${color.gray200}`,
                    borderRadius: 999,
                    padding: "8px 18px",
                  }}
                >
                  {r.tag}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Background>
  );
};

// ---------------------------------------------------------------- Scene 5
export const ReportScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const panel = spring({ frame, fps, config: { damping: 18 } });
  const eyebrow = useFadeUp(2);
  const bars = [0.42, 0.63, 0.55, 0.78, 0.68, 0.92, 0.85];
  const findings = [
    { w: "88%", d: 30 },
    { w: "72%", d: 44 },
    { w: "80%", d: 58 },
  ];
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "absolute", top: 90, ...eyebrow }}>
          <StepEyebrow n="03" label="Generate the report" />
        </div>
        <div
          style={{
            width: 1360,
            transform: `translateY(${interpolate(panel, [0, 1], [40, 0])}px) scale(${interpolate(panel, [0, 1], [0.96, 1])})`,
            opacity: panel,
            background: color.white,
            border: `1px solid ${color.gray200}`,
            borderRadius: 28,
            boxShadow: "0 50px 90px -40px rgba(11,18,32,0.35)",
            padding: 56,
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 56,
          }}
        >
          {/* left: narrative streaming in */}
          <div>
            <div style={{ fontFamily: monoFamily, fontSize: 18, letterSpacing: "0.18em", textTransform: "uppercase", color: color.primary }}>
              Report · Revenue
            </div>
            <h3 style={{ fontFamily: display, fontSize: 46, fontWeight: 700, color: color.ink, margin: "16px 0 30px", lineHeight: 1.1 }}>
              Where revenue is quietly leaking
            </h3>
            {findings.map((f, i) => {
              const s = spring({ frame: frame - f.d, fps, config: { damping: 200 } });
              return (
                <div key={i} style={{ marginBottom: 22, opacity: interpolate(s, [0, 0.2], [0, 1]) }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                    <span style={{ width: 12, height: 12, borderRadius: 999, background: color.primary }} />
                    <span style={{ fontFamily: sans, fontSize: 24, fontWeight: 600, color: color.ink }}>
                      Finding {i + 1}
                    </span>
                  </div>
                  {[1, 0.82].map((mult, k) => (
                    <div
                      key={k}
                      style={{
                        height: 14,
                        borderRadius: 999,
                        background: color.gray100,
                        width: `calc(${f.w} * ${mult})`,
                        marginBottom: 10,
                        transform: `scaleX(${interpolate(s, [0, 1], [0, 1])})`,
                        transformOrigin: "left",
                      }}
                    />
                  ))}
                </div>
              );
            })}
          </div>
          {/* right: live chart drawing */}
          <div
            style={{
              background: color.gray50,
              borderRadius: 20,
              padding: 36,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{ fontFamily: sans, fontSize: 24, fontWeight: 600, color: color.ink, marginBottom: 8 }}>
              Revenue by region
            </div>
            <div style={{ fontFamily: monoFamily, fontSize: 16, color: color.gray400, marginBottom: 24 }}>
              interactive · Recharts
            </div>
            <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: 20, paddingBottom: 8 }}>
              {bars.map((h, i) => {
                const s = spring({ frame: frame - (26 + i * 7), fps, config: { damping: 18 } });
                return (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: `${h * 100 * s}%`,
                      borderRadius: "10px 10px 4px 4px",
                      background:
                        i === 5
                          ? `linear-gradient(${color.primary}, ${color.primarySoft})`
                          : `${color.primary}44`,
                    }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </Background>
  );
};

// ---------------------------------------------------------------- Scene 6
export const CtaScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mark = spring({ frame, fps, config: { damping: 14 } });
  const head = useFadeUp(14);
  const btn = useFadeUp(30);
  const sub = useFadeUp(44);
  return (
    <Background>
      <AbsoluteFill style={{ ...center, gap: 44 }}>
        <div style={{ opacity: mark, transform: `scale(${interpolate(mark, [0, 1], [0.85, 1])})` }}>
          <LogoMark size={96} />
        </div>
        <h2
          style={{
            ...head,
            fontFamily: display,
            fontWeight: 700,
            fontSize: 92,
            letterSpacing: "-0.03em",
            color: color.ink,
            margin: 0,
            textAlign: "center",
          }}
        >
          Stop chatting. <span style={{ color: color.primary }}>Start reading.</span>
        </h2>
        <div
          style={{
            ...btn,
            display: "inline-flex",
            alignItems: "center",
            gap: 16,
            background: `linear-gradient(90deg, ${color.primary}, ${color.primarySoft})`,
            color: color.white,
            fontFamily: sans,
            fontWeight: 600,
            fontSize: 34,
            padding: "24px 46px",
            borderRadius: 20,
            boxShadow: `0 26px 50px -18px ${color.primary}90`,
          }}
        >
          Get started — free →
        </div>
        <div style={{ ...sub, fontFamily: monoFamily, fontSize: 24, color: color.gray400 }}>
          50 free credits to start · No credit card · visual-ai
        </div>
      </AbsoluteFill>
    </Background>
  );
};
