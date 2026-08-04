import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  Series,
  staticFile,
} from "remotion";
import { Audio } from "@remotion/media";
import {
  CreditsScene,
  DownloadScene,
  IdeasScene,
  InboxScene,
  IntroScene,
  OutroScene,
  ReportScene,
  SignupScene,
  UploadScene,
  VerifiedScene,
} from "./flowScenes";
import { NARRATION, VO_DIR } from "./narration";

// Each scene: its component + designed minimum length (frames) tuned to the animation.
export const SCENE_DEFS = [
  { c: IntroScene, min: 90 },
  { c: SignupScene, min: 110 },
  { c: InboxScene, min: 84 },
  { c: VerifiedScene, min: 90 },
  { c: CreditsScene, min: 100 },
  { c: UploadScene, min: 132 },
  { c: IdeasScene, min: 120 },
  { c: ReportScene, min: 172 },
  { c: DownloadScene, min: 120 },
  { c: OutroScene, min: 120 },
];

export const DEFAULT_DURATIONS = SCENE_DEFS.map((s) => s.min);
export const FLOW_DURATION = DEFAULT_DURATIONS.reduce((a, b) => a + b, 0);

export type FlowProps = {
  // Per-scene durations in frames. Falls back to the designed minimums.
  sceneDurations?: number[];
  // Whether public/vo/<id>.mp3 narration clips exist and should play.
  hasVoiceover?: boolean;
  // Whether public/music.mp3 exists and should play as a bed.
  hasMusic?: boolean;
  // [startFrame, endFrame] where narration is speaking — music ducks inside these.
  voiceSpans?: [number, number][];
};

// Music volume for frame f: swells to GAP in silence, ducks to DUCK under voice.
const GAP_VOL = 0.2;
const DUCK_VOL = 0.07;
const RAMP = 12; // frames to cross-fade between the two levels

const musicVolume = (f: number, total: number, spans: [number, number][]) => {
  let duck = 0; // 0 = full gap volume, 1 = fully ducked
  for (const [s, e] of spans) {
    const up = interpolate(f, [s - RAMP, s], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const down = interpolate(f, [e, e + RAMP], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    duck = Math.max(duck, Math.min(up, down));
  }
  const level = GAP_VOL + (DUCK_VOL - GAP_VOL) * duck;
  const env = interpolate(f, [0, 30, total - 45, total], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return level * env;
};

export const VisualAiFlow: React.FC<FlowProps> = ({
  sceneDurations,
  hasVoiceover = false,
  hasMusic = false,
  voiceSpans = [],
}) => {
  const durations = sceneDurations ?? DEFAULT_DURATIONS;
  const total = durations.reduce((a, b) => a + b, 0);

  return (
    <AbsoluteFill
      from={-40}
      style={{
        scale: 0.944,
      }}
    >
      <Series>
        {SCENE_DEFS.map(({ c: Comp }, i) => (
          <Series.Sequence key={i} durationInFrames={durations[i]}>
            <Comp />
            {hasVoiceover && (
              // small offset so the line lands just after the scene cuts in
              <Sequence from={6}>
                <Audio src={staticFile(`${VO_DIR}/${NARRATION[i].id}.mp3`)} />
              </Sequence>
            )}
          </Series.Sequence>
        ))}
      </Series>
      {hasMusic && (
        <Audio
          src={staticFile("music.mp3")}
          loop
          loopVolumeCurveBehavior="extend"
          // swells in the silence, ducks under the narration, fades in/out at the edges
          volume={(f) => musicVolume(f, total, voiceSpans)}
        />
      )}
    </AbsoluteFill>
  );
};
