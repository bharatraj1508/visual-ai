import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { color, color2, display, monoFamily, sans } from "../theme";
import { LogoMark } from "../parts";
import { inputBox, primaryBtn, StatusPill, useCountUp, useEnter } from "./ui";

const PAGE_BG = color.gray50;

// wrapper mimicking an app page inside the browser body
const Page: React.FC<{ children: React.ReactNode; pad?: number; center?: boolean }> = ({
  children,
  pad = 56,
  center,
}) => (
  <div
    style={{
      background: PAGE_BG,
      padding: pad,
      height: 1150,
      overflow: "hidden",
      boxSizing: "border-box",
      display: center ? "flex" : "block",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    {children}
  </div>
);

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      background: color.white,
      border: `1px solid ${color.gray200}`,
      borderRadius: 22,
      boxShadow: "0 20px 50px -30px rgba(11,18,32,0.3)",
      padding: 44,
      ...style,
    }}
  >
    {children}
  </div>
);

// ---------------------------------------------------------------- 1. Register
export const RegisterCard: React.FC = () => (
  <Page center>
    <Card style={{ width: 640 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 30 }}>
        <LogoMark size={52} />
        <span style={{ fontFamily: display, fontSize: 34, fontWeight: 700, color: color.ink }}>
          Create account
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={inputBox("", "Alex Rivera")}>Alex Rivera</div>
        <div style={inputBox("", "alex@acme.com")}>alex@acme.com</div>
        <div style={inputBox("Password")}>Password (min 8 chars)</div>
        <div style={{ ...primaryBtn(), marginTop: 8 }}>Register</div>
        <div style={{ textAlign: "center", fontFamily: sans, fontSize: 22, color: color.primary, marginTop: 4 }}>
          Have an account? Log in
        </div>
      </div>
    </Card>
  </Page>
);

// ---------------------------------------------------------------- 2. Check inbox
export const InboxCard: React.FC = () => {
  const p = useEnter(0, 0);
  return (
    <Page center>
      <Card style={{ width: 620, textAlign: "center" }}>
        <div style={{ ...p, display: "flex", justifyContent: "center", marginBottom: 26 }}>
          <div
            style={{
              width: 108,
              height: 108,
              borderRadius: 28,
              background: `${color.primary}12`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke={color.primary} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="5" width="18" height="14" rx="2" />
              <path d="m3 7 9 6 9-6" />
            </svg>
          </div>
        </div>
        <div style={{ fontFamily: display, fontSize: 40, fontWeight: 700, color: color.ink }}>
          Check your inbox
        </div>
        <p style={{ fontFamily: sans, fontSize: 25, lineHeight: 1.5, color: color.gray500, margin: "18px 0 0" }}>
          We sent a verification link to <b style={{ color: color.ink }}>alex@acme.com</b>. Click it to activate
          your account and unlock your free credits.
        </p>
        <div style={{ ...primaryBtn({ marginTop: 30 }) }}>Resend email</div>
      </Card>
    </Page>
  );
};

// ---------------------------------------------------------------- 3. Verified
export const VerifiedCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const check = spring({ frame: frame - 6, fps, config: { damping: 12, mass: 0.6 } });
  return (
    <Page center>
      <Card style={{ width: 620, textAlign: "center" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 26 }}>
          <div
            style={{
              width: 116,
              height: 116,
              borderRadius: 999,
              background: color2.green100,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transform: `scale(${check})`,
            }}
          >
            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke={color2.green600} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </div>
        </div>
        <div style={{ fontFamily: display, fontSize: 42, fontWeight: 700, color: color2.green600 }}>
          Email verified
        </div>
        <p style={{ fontFamily: sans, fontSize: 26, lineHeight: 1.5, color: color.gray500, margin: "18px 0 0" }}>
          Your account is active and <b style={{ color: color.ink }}>your free credits are ready.</b>
        </p>
        <div style={{ ...primaryBtn({ marginTop: 30 }) }}>Continue to log in</div>
      </Card>
    </Page>
  );
};

// ---------------------------------------------------------------- 4. Credits granted
const CoinIcon = ({ size = 44 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color.primary} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9" />
    <path d="M14.5 9.5A2.5 2.5 0 0 0 12 8c-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.9 2.5 2-1 2-2.5 2a2.5 2.5 0 0 1-2.5-1.5M12 6.5v11" />
  </svg>
);

export const CreditsGranted: React.FC = () => {
  const n = useCountUp(50, 12, 46);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 14 } });
  return (
    <Page center>
      <Card style={{ width: 660, textAlign: "center", padding: 56, transform: `scale(${interpolate(pop, [0, 1], [0.92, 1])})` }}>
        <div style={{ fontFamily: monoFamily, fontSize: 22, letterSpacing: "0.2em", color: color.gray400, textTransform: "uppercase" }}>
          Your balance
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 22, margin: "26px 0 10px" }}>
          <CoinIcon size={58} />
          <span style={{ fontFamily: display, fontSize: 150, fontWeight: 700, color: color.ink, lineHeight: 1 }}>
            {n}
          </span>
          <span style={{ fontFamily: display, fontSize: 44, fontWeight: 600, color: color.gray500, alignSelf: "flex-end", marginBottom: 20 }}>
            credits
          </span>
        </div>
        <div
          style={{
            display: "inline-flex",
            gap: 12,
            alignItems: "center",
            background: color2.green50,
            color: color2.green700,
            fontFamily: sans,
            fontSize: 26,
            fontWeight: 600,
            padding: "14px 26px",
            borderRadius: 999,
            marginTop: 18,
          }}
        >
          🎁 Free on signup — enough for about 5 full reports
        </div>
      </Card>
    </Page>
  );
};

// ---------------------------------------------------------------- 5. Upload
export const UploadMock: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = spring({ frame: frame - 14, fps, config: { damping: 16 } });
  const analyzing = frame > 58;
  return (
    <Page>
      <div style={{ fontFamily: display, fontSize: 38, fontWeight: 700, color: color.ink, marginBottom: 8 }}>
        Welcome, Alex 👋
      </div>
      <div style={{ fontFamily: sans, fontSize: 24, color: color.gray500, marginBottom: 34 }}>
        Upload your first dataset to get started.
      </div>
      <div
        style={{
          height: 460,
          borderRadius: 26,
          border: `3px dashed ${color.primary}66`,
          background: color.white,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        {!analyzing ? (
          <div
            style={{
              transform: `translateY(${interpolate(drop, [0, 1], [-320, 0])}px)`,
              opacity: interpolate(drop, [0, 0.15], [0, 1]),
              width: 420,
              borderRadius: 18,
              background: color.white,
              border: `1px solid ${color.gray200}`,
              boxShadow: "0 40px 70px -25px rgba(11,18,32,0.3)",
              padding: 30,
              display: "flex",
              alignItems: "center",
              gap: 22,
            }}
          >
            <div style={{ width: 68, height: 68, borderRadius: 16, background: `${color.primary}14`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke={color.primary} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
            </div>
            <div>
              <div style={{ fontFamily: display, fontSize: 30, fontWeight: 600, color: color.ink }}>sales_2025.csv</div>
              <div style={{ fontFamily: monoFamily, fontSize: 20, color: color.gray400, marginTop: 6 }}>48,210 rows · 12 columns</div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: "center" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
              <div
                style={{
                  width: 74,
                  height: 74,
                  borderRadius: 999,
                  border: `6px solid ${color.gray200}`,
                  borderTopColor: color.primary,
                  transform: `rotate(${(frame % 60) * 6}deg)`,
                }}
              />
            </div>
            <div style={{ fontFamily: display, fontSize: 34, fontWeight: 600, color: color.ink }}>
              Analyzing sales_2025.csv with AI
            </div>
            <div style={{ fontFamily: sans, fontSize: 24, color: color.gray500, marginTop: 10 }}>
              Finding the reports worth generating…
            </div>
          </div>
        )}
      </div>
    </Page>
  );
};

// ---------------------------------------------------------------- 6. Suggestions
const SUGGESTIONS = [
  { t: "Where revenue is quietly leaking", q: "Which regions and SKUs are losing margin?", tags: ["Bar", "Line"] },
  { t: "The churn signal hiding in signups", q: "Do signup cohorts predict who leaves?", tags: ["Line", "Area"] },
  { t: "Seasonality you can plan around", q: "When does demand spike each quarter?", tags: ["Area"] },
  { t: "Segments worth doubling down on", q: "Which customer segments compound fastest?", tags: ["Bar", "Pie"] },
  { t: "What your best customers have in common", q: "Which traits define your highest-value accounts?", tags: ["Bar", "Scatter"] },
];

export const SuggestionsMock: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Page>
      <div style={{ fontFamily: monoFamily, fontSize: 22, letterSpacing: "0.2em", textTransform: "uppercase", color: color.gray400, marginBottom: 8 }}>
        Suggested reports
      </div>
      <div style={{ fontFamily: display, fontSize: 34, fontWeight: 700, color: color.ink, marginBottom: 30 }}>
        5 reports worth running
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22 }}>
        {SUGGESTIONS.map((s, i) => {
          const sp = spring({ frame: frame - (10 + i * 9), fps, config: { damping: 200 } });
          return (
            <div
              key={s.t}
              style={{
                opacity: sp,
                transform: `translateY(${interpolate(sp, [0, 1], [26, 0])}px)`,
                gridColumn: i === SUGGESTIONS.length - 1 && SUGGESTIONS.length % 2 === 1 ? "1 / -1" : undefined,
                background: color.white,
                border: `1px solid ${color.gray200}`,
                borderRadius: 20,
                padding: 30,
                boxShadow: "0 18px 40px -30px rgba(11,18,32,0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
                <span style={{ width: 40, height: 40, borderRadius: 999, background: `${color.primary}12`, color: color.primary, fontFamily: monoFamily, fontSize: 22, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {i + 1}
                </span>
                <span style={{ display: "flex", gap: 8 }}>
                  {s.tags.map((t) => (
                    <span key={t} style={{ background: color.gray100, color: color.gray500, fontFamily: monoFamily, fontSize: 17, padding: "5px 14px", borderRadius: 999 }}>
                      {t}
                    </span>
                  ))}
                </span>
              </div>
              <div style={{ fontFamily: display, fontSize: 27, fontWeight: 600, color: color.ink, lineHeight: 1.2 }}>{s.t}</div>
              <div style={{ fontFamily: sans, fontSize: 21, color: color.gray500, marginTop: 12, lineHeight: 1.4 }}>{s.q}</div>
              <div style={{ fontFamily: sans, fontSize: 22, fontWeight: 600, color: color.primary, marginTop: 20 }}>
                Generate report →
              </div>
            </div>
          );
        })}
      </div>
    </Page>
  );
};

// ---------------------------------------------------------------- 7. Report streaming
export const ReportMock: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const streaming = frame < 70;
  const bars = [0.44, 0.62, 0.55, 0.78, 0.66, 0.95, 0.83];
  const findings = [
    { w: 0.9, d: 40 },
    { w: 0.78, d: 58 },
  ];
  return (
    <Page>
      <div style={{ fontFamily: monoFamily, fontSize: 20, color: color.gray400, marginBottom: 10 }}>
        Dashboard › sales_2025.csv › Revenue
      </div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 20 }}>
        <div style={{ fontFamily: display, fontSize: 40, fontWeight: 700, color: color.ink, lineHeight: 1.1, maxWidth: 560 }}>
          Where revenue is quietly leaking
        </div>
        <StatusPill kind={streaming ? "run" : "done"}>{streaming ? "generating…" : "10 credits"}</StatusPill>
      </div>

      {streaming ? (
        <div
          style={{
            marginTop: 28,
            background: `${color.primary}0A`,
            border: `1px solid ${color.primary}33`,
            borderRadius: 18,
            padding: 30,
            display: "flex",
            alignItems: "center",
            gap: 18,
          }}
        >
          <div style={{ display: "flex", gap: 8 }}>
            {[0, 1, 2].map((i) => {
              const o = interpolate((frame + i * 8) % 32, [0, 16, 32], [0.25, 1, 0.25]);
              return <span key={i} style={{ width: 14, height: 14, borderRadius: 999, background: color.primary, opacity: o }} />;
            })}
          </div>
          <span style={{ fontFamily: sans, fontSize: 26, color: color.ink, fontWeight: 500 }}>
            Writing the report — findings, narrative & charts…
          </span>
        </div>
      ) : (
        <div style={{ marginTop: 28 }}>
          <div style={{ fontFamily: display, fontSize: 30, fontWeight: 600, color: color.ink, marginBottom: 18 }}>
            Key findings
          </div>
          {findings.map((f, i) => {
            const s = spring({ frame: frame - f.d, fps, config: { damping: 200 } });
            return (
              <div key={i} style={{ opacity: s, marginBottom: 18 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                  <span style={{ width: 12, height: 12, borderRadius: 999, background: color.primary }} />
                  <span style={{ fontFamily: sans, fontSize: 24, fontWeight: 600, color: color.ink }}>Finding {i + 1}</span>
                </div>
                {[1, 0.8].map((m, k) => (
                  <div key={k} style={{ height: 14, borderRadius: 999, background: color.gray100, width: `${f.w * m * 100}%`, marginBottom: 10, transform: `scaleX(${s})`, transformOrigin: "left" }} />
                ))}
              </div>
            );
          })}
          {/* chart */}
          <div style={{ background: color.gray50, borderRadius: 18, padding: 30, marginTop: 20 }}>
            <div style={{ fontFamily: sans, fontSize: 24, fontWeight: 600, color: color.ink, marginBottom: 4 }}>Revenue by region</div>
            <div style={{ fontFamily: monoFamily, fontSize: 17, color: color.gray400, marginBottom: 22 }}>interactive · Recharts</div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 16, height: 220 }}>
              {bars.map((h, i) => {
                const bs = spring({ frame: frame - (74 + i * 6), fps, config: { damping: 18 } });
                return (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: `${h * 100 * bs}%`,
                      borderRadius: "10px 10px 4px 4px",
                      background: i === 5 ? `linear-gradient(${color.primary}, #ff8a80)` : `${color.primary}44`,
                    }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}
    </Page>
  );
};

// ---------------------------------------------------------------- 8. Download
export const DownloadMock: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const toast = spring({ frame: frame - 40, fps, config: { damping: 16 } });
  const btnPulse = interpolate(frame % 50, [0, 25, 50], [1, 1.04, 1]);
  const DownloadBtn = ({ label, filled }: { label: string; filled?: boolean }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "18px 30px",
        borderRadius: 14,
        border: `1px solid ${filled ? color.primary : color.gray200}`,
        background: filled ? color.primary : color.white,
        color: filled ? color.white : color.ink,
        fontFamily: sans,
        fontSize: 26,
        fontWeight: 600,
        transform: filled ? `scale(${btnPulse})` : undefined,
      }}
    >
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </svg>
      {label}
    </div>
  );
  return (
    <Page>
      <div style={{ fontFamily: monoFamily, fontSize: 20, color: color.gray400, marginBottom: 10 }}>
        Dashboard › sales_2025.csv › Revenue
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 30 }}>
        <div style={{ fontFamily: display, fontSize: 38, fontWeight: 700, color: color.ink, maxWidth: 500 }}>
          Where revenue is quietly leaking
        </div>
        <StatusPill kind="done">completed</StatusPill>
      </div>
      {/* the report body preview */}
      <Card style={{ padding: 34 }}>
        <div style={{ fontFamily: display, fontSize: 26, fontWeight: 600, color: color.ink }}>Executive summary</div>
        {[1, 0.9, 0.95, 0.6].map((w, i) => (
          <div key={i} style={{ height: 12, borderRadius: 999, background: color.gray100, width: `${w * 100}%`, margin: "16px 0" }} />
        ))}
        <div style={{ display: "flex", gap: 12, marginTop: 6 }}>
          {[0.5, 0.8, 0.65, 1].map((h, i) => (
            <div key={i} style={{ flex: 1, height: 120 * h, alignSelf: "flex-end", borderRadius: 8, background: i === 3 ? color.primary : `${color.primary}44` }} />
          ))}
        </div>
      </Card>
      <div style={{ display: "flex", gap: 20, marginTop: 34 }}>
        <DownloadBtn label="Download PDF" filled />
        <DownloadBtn label="Download all as ZIP" />
      </div>
      {/* success toast */}
      <div
        style={{
          position: "absolute",
          right: 40,
          bottom: 40,
          opacity: toast,
          transform: `translateY(${interpolate(toast, [0, 1], [30, 0])}px)`,
          display: "flex",
          alignItems: "center",
          gap: 14,
          background: color.ink,
          color: color.white,
          fontFamily: sans,
          fontSize: 24,
          fontWeight: 500,
          padding: "18px 26px",
          borderRadius: 14,
          boxShadow: "0 30px 60px -20px rgba(11,18,32,0.5)",
        }}
      >
        <span style={{ width: 30, height: 30, borderRadius: 999, background: color2.green600, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </span>
        report-revenue.pdf saved
      </div>
    </Page>
  );
};
