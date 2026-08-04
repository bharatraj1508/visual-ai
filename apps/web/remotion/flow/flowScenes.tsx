import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { color, color2, display, monoFamily, sans } from "../theme";
import { Background } from "../Background";
import { LogoMark, Pill, Wordmark } from "../parts";
import { BrowserFrame, Caption, StepHeader, useEnter, usePop } from "./ui";
import {
  CreditsGranted,
  DownloadMock,
  InboxCard,
  RegisterCard,
  ReportMock,
  SuggestionsMock,
  UploadMock,
  VerifiedCard,
} from "./screens";

const FRAME_W = 940;

// Vertical scaffold: step rail on top, browser mock centered, caption below.
const StepScene: React.FC<{
  n: string;
  label: string;
  index: number;
  url: string;
  caption: React.ReactNode;
  children: React.ReactNode;
}> = ({ n, label, index, url, caption, children }) => {
  const frameEnter = useEnter(6, 60);
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", padding: "96px 0" }}>
        <StepHeader n={n} label={label} index={index} />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", width: "100%" }}>
          <div style={frameEnter}>
            <BrowserFrame url={url} width={FRAME_W}>
              {children}
            </BrowserFrame>
          </div>
        </div>
        <Caption delay={16}>{caption}</Caption>
      </AbsoluteFill>
    </Background>
  );
};

// ------------------------------------------------------------------ INTRO
export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const mark = usePop(0);
  const pill = useEnter(20, 26);
  const line = useEnter(40, 30);
  const out = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 54, opacity: out }}>
        <div style={mark}>
          <Wordmark size={130} />
        </div>
        <div style={pill}>
          <Pill style={{ fontSize: 26 }}>not another AI chat</Pill>
        </div>
        <div
          style={{
            ...line,
            fontFamily: display,
            fontSize: 62,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: color.ink,
            textAlign: "center",
            marginTop: 20,
          }}
        >
          From signup to report
          <br />
          <span style={{ color: color.primary }}>in one flow →</span>
        </div>
      </AbsoluteFill>
    </Background>
  );
};

// ------------------------------------------------------------------ STEPS
export const SignupScene: React.FC = () => (
  <StepScene n="01" label="Sign up" index={0} url="visual-ai.app/auth/register" caption={<>Create your account<br />in seconds.</>}>
    <RegisterCard />
  </StepScene>
);

export const InboxScene: React.FC = () => (
  <StepScene n="02" label="Verify email" index={1} url="visual-ai.app/auth/register" caption={<>Confirm your email to<br />unlock your account.</>}>
    <InboxCard />
  </StepScene>
);

export const VerifiedScene: React.FC = () => (
  <StepScene n="02" label="Verify email" index={1} url="visual-ai.app/auth/verify" caption={<>Verified — your free<br />credits are ready.</>}>
    <VerifiedCard />
  </StepScene>
);

export const CreditsScene: React.FC = () => (
  <StepScene n="03" label="Free credits" index={2} url="visual-ai.app/credits" caption={<><b style={{ color: color.primary }}>50 credits</b>, free on signup.</>}>
    <CreditsGranted />
  </StepScene>
);

export const UploadScene: React.FC = () => (
  <StepScene n="04" label="Upload data" index={3} url="visual-ai.app/dashboard" caption={<>Drop a CSV —<br />no SQL, no Python.</>}>
    <UploadMock />
  </StepScene>
);

export const IdeasScene: React.FC = () => (
  <StepScene n="05" label="Generated ideas" index={4} url="visual-ai.app/analyze" caption={<>The AI scopes the five<br />reports worth running.</>}>
    <SuggestionsMock />
  </StepScene>
);

export const ReportScene: React.FC = () => (
  <StepScene n="06" label="Run a report" index={5} url="visual-ai.app/reports" caption={<>Findings, narrative &<br />charts — for 10 credits.</>}>
    <ReportMock />
  </StepScene>
);

export const DownloadScene: React.FC = () => (
  <StepScene n="07" label="Download" index={6} url="visual-ai.app/reports" caption={<>Export as PDF or ZIP.<br />Yours to keep.</>}>
    <DownloadMock />
  </StepScene>
);

// ------------------------------------------------------------------ OUTRO
export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mark = usePop(0);
  const head = useEnter(14, 30);
  const btn = useEnter(30, 26);
  const sub = useEnter(46, 20);
  const steps = ["Sign up", "Upload", "Report", "Download"];
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 46, padding: "0 80px" }}>
        <div style={mark}>
          <LogoMark size={120} />
        </div>
        <h2
          style={{
            ...head,
            fontFamily: display,
            fontWeight: 700,
            fontSize: 88,
            letterSpacing: "-0.03em",
            lineHeight: 1.05,
            color: color.ink,
            margin: 0,
            textAlign: "center",
          }}
        >
          Stop chatting.
          <br />
          <span style={{ color: color.primary }}>Start reading.</span>
        </h2>
        {/* recap chips */}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center", maxWidth: 760 }}>
          {steps.map((s, i) => {
            const sp = spring({ frame: frame - (20 + i * 6), fps, config: { damping: 200 } });
            return (
              <span
                key={s}
                style={{
                  opacity: sp,
                  transform: `translateY(${interpolate(sp, [0, 1], [16, 0])}px)`,
                  fontFamily: monoFamily,
                  fontSize: 24,
                  color: color.gray500,
                  background: color.white,
                  border: `1px solid ${color.gray200}`,
                  borderRadius: 999,
                  padding: "12px 24px",
                }}
              >
                {i > 0 ? "→ " : ""}
                {s}
              </span>
            );
          })}
        </div>
        <div
          style={{
            ...btn,
            background: `linear-gradient(90deg, ${color.primary}, #ff8a80)`,
            color: color.white,
            fontFamily: sans,
            fontWeight: 600,
            fontSize: 40,
            padding: "28px 56px",
            borderRadius: 20,
            boxShadow: `0 30px 60px -18px ${color.primary}90`,
            marginTop: 8,
          }}
        >
          Get started — free →
        </div>
        <div style={{ ...sub, fontFamily: monoFamily, fontSize: 26, color: color.gray400, textAlign: "center" }}>
          50 free credits · No credit card
        </div>
      </AbsoluteFill>
    </Background>
  );
};
