import React from "react";
import { AbsoluteFill } from "remotion";
import { color } from "./theme";

// Light canvas with the site's dotted grid + soft brand glow.
export const Background: React.FC<{ children?: React.ReactNode }> = ({
  children,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: color.white }}>
      <AbsoluteFill
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(11,18,32,0.06) 1px, transparent 0)",
          backgroundSize: "38px 38px",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(880px 520px at 50% -8%, rgba(251,103,110,0.10), rgba(45,212,191,0.08) 40%, transparent 70%)",
        }}
      />
      {children}
    </AbsoluteFill>
  );
};
