import React from "react";
import { CalculateMetadataFunction, Composition, staticFile } from "remotion";
import { PROMO_DURATION, VisualAiPromo } from "./VisualAiPromo";
import {
  DEFAULT_DURATIONS,
  FLOW_DURATION,
  FlowProps,
  SCENE_DEFS,
  VisualAiFlow,
} from "./flow/VisualAiFlow";
import {
  PROMO_V_DURATION,
  PromoVProps,
  VisualAiPromoVertical,
} from "./promo/PromoVertical";
import { NARRATION, VO_DIR } from "./flow/narration";
import { VERTICAL, VIDEO } from "./theme";

const TAIL_FRAMES = 20; // breathing room after each narration line

// probe a static asset without throwing
const exists = async (path: string): Promise<boolean> => {
  try {
    const res = await fetch(staticFile(path), { method: "HEAD" });
    return res.ok;
  } catch {
    return false;
  }
};

const VO_OFFSET = 6; // matches the <Sequence from={6}> the narration plays under

const calculateFlowMetadata: CalculateMetadataFunction<FlowProps> = async () => {
  const fps = VERTICAL.fps;
  let sceneDurations = DEFAULT_DURATIONS;
  let hasVoiceover = false;
  let voiceSpans: [number, number][] = [];

  try {
    const res = await fetch(staticFile(`${VO_DIR}/manifest.json`));
    if (res.ok) {
      const manifest: { id: string; seconds: number }[] = await res.json();
      const byId = new Map(manifest.map((m) => [m.id, m.seconds]));
      // every scene needs a clip for voiceover mode to engage
      if (NARRATION.every((n) => byId.has(n.id))) {
        hasVoiceover = true;
        const voFrames = SCENE_DEFS.map((_, i) => Math.ceil((byId.get(NARRATION[i].id) ?? 0) * fps));
        sceneDurations = SCENE_DEFS.map((s, i) => Math.max(s.min, voFrames[i] + TAIL_FRAMES));
        let start = 0;
        voiceSpans = sceneDurations.map((d, i) => {
          const span: [number, number] = [start + VO_OFFSET, start + VO_OFFSET + voFrames[i]];
          start += d;
          return span;
        });
      }
    }
  } catch {
    // no manifest yet — silent, non-voiceover render
  }

  const hasMusic = await exists("music.mp3");
  const durationInFrames = sceneDurations.reduce((a, b) => a + b, 0);

  return { durationInFrames, props: { sceneDurations, hasVoiceover, hasMusic, voiceSpans } };
};

const calculatePromoVMetadata: CalculateMetadataFunction<PromoVProps> = async () => {
  const hasMusic = await exists("music.mp3");
  return { props: { hasMusic } };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Primary deliverable: 9:16 vertical product-flow walkthrough for Reels. */}
      <Composition
        id="VisualAiFlow"
        component={VisualAiFlow}
        durationInFrames={FLOW_DURATION}
        fps={VERTICAL.fps}
        width={VERTICAL.width}
        height={VERTICAL.height}
        calculateMetadata={calculateFlowMetadata}
        defaultProps={{ sceneDurations: undefined, hasVoiceover: false, hasMusic: false, voiceSpans: [] }}
      />
      {/* Short brand teaser — 9:16 vertical for mobile / Reels. */}
      <Composition
        id="VisualAiPromoVertical"
        component={VisualAiPromoVertical}
        durationInFrames={PROMO_V_DURATION}
        fps={VERTICAL.fps}
        width={VERTICAL.width}
        height={VERTICAL.height}
        calculateMetadata={calculatePromoVMetadata}
        defaultProps={{ hasMusic: false }}
      />
      {/* Original 16:9 landscape promo. */}
      <Composition
        id="VisualAiPromo"
        component={VisualAiPromo}
        durationInFrames={PROMO_DURATION}
        fps={VIDEO.fps}
        width={VIDEO.width}
        height={VIDEO.height}
      />
    </>
  );
};
