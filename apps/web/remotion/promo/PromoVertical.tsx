import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Series,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Audio } from "@remotion/media";
import { color, display, sans } from "../theme";
import { Background } from "../Background";
import { LogoMark, Pill, Wordmark } from "../parts";
import { BrowserFrame, Caption, useEnter, usePop } from "../flow/ui";
import { ReportMock, SuggestionsMock } from "../flow/screens";

// centered browser mock with a caption underneath — no step rail (this is a teaser)
const MockScene: React.FC<{ url: string; caption: React.ReactNode; children: React.ReactNode }> = ({
  url,
  caption,
  children,
}) => {
  const enter = useEnter(4, 60);
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "70px 0", gap: 40 }}>
        <div style={enter}>
          <BrowserFrame url={url} width={940}>
            {children}
          </BrowserFrame>
        </div>
        <Caption delay={12}>{caption}</Caption>
      </AbsoluteFill>
    </Background>
  );
};

const PIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const mark = usePop(0);
  const pill = useEnter(20, 26);
  const out = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 54, opacity: out }}>
        <div style={mark}>
          <Wordmark size={132} />
        </div>
        <div style={pill}>
          <Pill style={{ fontSize: 28 }}>not another AI chat</Pill>
        </div>
      </AbsoluteFill>
    </Background>
  );
};

const PHeadline: React.FC = () => {
  const frame = useCurrentFrame();
  const l1 = useEnter(4, 28);
  const l2 = useEnter(18, 28);
  const sub = useEnter(40, 24);
  const dash = interpolate(frame, [30, 64], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 80px", textAlign: "center" }}>
        <h1 style={{ fontFamily: display, fontWeight: 600, fontSize: 96, lineHeight: 1.06, letterSpacing: "-0.03em", color: color.ink, margin: 0 }}>
          <span style={{ display: "block", ...l1 }}>Stop chatting with your data.</span>
          <span style={{ display: "inline-block", position: "relative", color: color.primary, marginTop: 18, ...l2 }}>
            Read its report.
            <svg viewBox="0 0 300 12" preserveAspectRatio="none" style={{ position: "absolute", left: 0, bottom: -16, width: "100%", height: 22, color: color.primary, opacity: 0.45 }}>
              <path d="M2 8 C 60 2, 120 2, 180 6 S 260 10, 298 4" fill="none" stroke="currentColor" strokeWidth={4} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={dash} />
            </svg>
          </span>
        </h1>
        <p style={{ ...sub, fontFamily: sans, fontSize: 34, lineHeight: 1.5, color: color.gray500, maxWidth: 820, marginTop: 60 }}>
          Upload a CSV. Get five reports worth running — findings, narrative, and interactive charts.
        </p>
      </AbsoluteFill>
    </Background>
  );
};

const PIdeas: React.FC = () => (
  <MockScene url="visual-ai.app/analyze" caption={<>Five reports worth running.</>}>
    <SuggestionsMock />
  </MockScene>
);

const PReport: React.FC = () => (
  <MockScene url="visual-ai.app/reports" caption={<>Written for you — in minutes.</>}>
    <ReportMock />
  </MockScene>
);

const PCta: React.FC = () => {
  const mark = usePop(0);
  const head = useEnter(14, 30);
  const btn = useEnter(30, 26);
  const sub = useEnter(46, 20);
  return (
    <Background>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 46, padding: "0 80px" }}>
        <div style={mark}>
          <LogoMark size={120} />
        </div>
        <h2 style={{ ...head, fontFamily: display, fontWeight: 700, fontSize: 96, letterSpacing: "-0.03em", lineHeight: 1.05, color: color.ink, margin: 0, textAlign: "center" }}>
          Stop chatting.
          <br />
          <span style={{ color: color.primary }}>Start reading.</span>
        </h2>
        <div style={{ ...btn, background: `linear-gradient(90deg, ${color.primary}, #ff8a80)`, color: color.white, fontFamily: sans, fontWeight: 600, fontSize: 42, padding: "30px 60px", borderRadius: 22, boxShadow: `0 30px 60px -18px ${color.primary}90`, marginTop: 8 }}>
          Get started — free →
        </div>
        <div style={{ ...sub, fontFamily: sans, fontSize: 30, color: color.gray400, textAlign: "center" }}>
          50 free credits · No credit card
        </div>
      </AbsoluteFill>
    </Background>
  );
};

export const PROMO_V_SCENES = [
  { c: PIntro, d: 72 },
  { c: PHeadline, d: 114 },
  { c: PIdeas, d: 132 },
  { c: PReport, d: 156 },
  { c: PCta, d: 120 },
];

export const PROMO_V_DURATION = PROMO_V_SCENES.reduce((a, s) => a + s.d, 0);

export type PromoVProps = { hasMusic?: boolean };

export const VisualAiPromoVertical: React.FC<PromoVProps> = ({ hasMusic = false }) => {
  const total = PROMO_V_DURATION;
  return (
    <AbsoluteFill>
      <Series>
        {PROMO_V_SCENES.map(({ c: Comp, d }, i) => (
          <Series.Sequence key={i} durationInFrames={d}>
            <Comp />
          </Series.Sequence>
        ))}
      </Series>
      {hasMusic && (
        <Audio
          src={staticFile("music.mp3")}
          loop
          loopVolumeCurveBehavior="extend"
          volume={(f) =>
            interpolate(f, [0, 30, total - 40, total], [0, 0.18, 0.18, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      )}
    </AbsoluteFill>
  );
};
