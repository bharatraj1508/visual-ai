import React from "react";
import { AbsoluteFill, Series } from "remotion";
import {
  CtaScene,
  HeadlineScene,
  IntroScene,
  ReportScene,
  ScopeScene,
  UploadScene,
} from "./scenes";

// Scene durations in frames (30fps).
export const SCENES = [
  { c: IntroScene, d: 84 },
  { c: HeadlineScene, d: 126 },
  { c: UploadScene, d: 132 },
  { c: ScopeScene, d: 150 },
  { c: ReportScene, d: 168 },
  { c: CtaScene, d: 120 },
];

export const PROMO_DURATION = SCENES.reduce((a, s) => a + s.d, 0);

export const VisualAiPromo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Series>
        {SCENES.map(({ c: Comp, d }, i) => (
          <Series.Sequence key={i} durationInFrames={d}>
            <Comp />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
