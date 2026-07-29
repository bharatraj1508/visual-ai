"use client";

// The WebGL scene for the landing's 3D charts. Kept in its own module so it can
// be dynamically imported with `ssr: false` (see Chart3D) — three.js needs the
// browser. Every chart type the product can draw has a clean, animated 3D
// stand-in here: bars grow from the floor, points drift, the donut sweeps in.
// A scroll-linked MotionValue (passed from Chart3D) gently turns the model as
// the page moves, so the motion reads as one system with the rest of the page.

import { useMemo, useRef, useState } from "react";

import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows } from "@react-three/drei";
import type { MotionValue } from "framer-motion";
import * as THREE from "three";

const CORAL = "#FB676E";
const TEAL = "#2DD4BF";

export type ChartKind = "bars" | "scatter" | "donut" | "area";

const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

type SceneProps = {
  kind: ChartKind;
  scroll?: MotionValue<number>;
  reduced?: boolean;
  /** grouped-bar data (groups × series), 0–100 */
  bars?: { label: string; values: number[] }[];
};

const DEFAULT_BARS = [
  { label: "Defender", values: [81, 55] },
  { label: "Forward", values: [78, 55] },
  { label: "Midfielder", values: [85, 56] },
];

export default function Scene({ kind, scroll, reduced, bars }: SceneProps) {
  // Frame each model so it sits comfortably regardless of type.
  const camera = kind === "donut" ? { position: [0, 1.2, 5.2] as const, fov: 42 }
    : kind === "scatter" ? { position: [0, 1.4, 6] as const, fov: 44 }
    : { position: [0, 1.7, 6.2] as const, fov: 42 };

  return (
    <Canvas
      dpr={[1, 1.75]}
      camera={camera}
      gl={{ antialias: true, alpha: true }}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.75} />
      <directionalLight position={[4, 7, 5]} intensity={1.15} />
      <directionalLight position={[-5, 3, -4]} intensity={0.35} color={TEAL} />

      <Rig scroll={scroll} reduced={reduced}>
        {kind === "bars" && <Bars data={bars ?? DEFAULT_BARS} reduced={reduced} />}
        {kind === "scatter" && <Scatter reduced={reduced} />}
        {kind === "donut" && <Donut reduced={reduced} />}
        {kind === "area" && <Area reduced={reduced} />}
      </Rig>

      <ContactShadows
        position={[0, -1.15, 0]}
        opacity={0.22}
        blur={2.6}
        scale={12}
        far={4}
        color="#0B1220"
      />
    </Canvas>
  );
}

/** Auto-rotates gently and adds a scroll-driven yaw so the model turns with the
 * page. Honors reduced motion by holding still at a flattering angle. */
function Rig({
  children,
  scroll,
  reduced,
}: {
  children: React.ReactNode;
  scroll?: MotionValue<number>;
  reduced?: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  useFrame((state, dt) => {
    if (!group.current) return;
    if (reduced) {
      group.current.rotation.y = -0.5;
      group.current.rotation.x = 0.12;
      return;
    }
    const p = scroll ? scroll.get() : 0.5;
    // Continuous drift + a scroll offset centered on the section midpoint.
    group.current.rotation.y += dt * 0.18;
    group.current.rotation.y += (p - 0.5) * dt * 1.2;
    // A touch of breathing tilt.
    group.current.rotation.x = 0.12 + Math.sin(state.clock.elapsedTime * 0.4) * 0.04;
  });
  return <group ref={group}>{children}</group>;
}

/** One extruded column that grows from the floor and lifts on hover. */
function Bar({
  x,
  z,
  height,
  width,
  depth,
  color,
  delay,
  reduced,
}: {
  x: number;
  z: number;
  height: number;
  width: number;
  depth: number;
  color: string;
  delay: number;
  reduced?: boolean;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const t = useRef(0);
  const [hover, setHover] = useState(false);
  useFrame((_, dt) => {
    if (!mesh.current) return;
    t.current += dt;
    const grown = reduced ? 1 : easeOut((t.current - delay) / 0.7);
    const lift = hover ? 1.06 : 1;
    const h = Math.max(0.0001, height * grown * lift);
    mesh.current.scale.y = h;
    mesh.current.position.y = h / 2 - 1.15;
  });
  return (
    <mesh
      ref={mesh}
      position={[x, -1.15, z]}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHover(true);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        setHover(false);
        document.body.style.cursor = "";
      }}
    >
      <boxGeometry args={[width, 1, depth]} />
      <meshStandardMaterial
        color={color}
        roughness={0.34}
        metalness={0.12}
        emissive={color}
        emissiveIntensity={hover ? 0.25 : 0}
      />
    </mesh>
  );
}

function Bars({
  data,
  reduced,
}: {
  data: { label: string; values: number[] }[];
  reduced?: boolean;
}) {
  const colors = [CORAL, TEAL];
  const groupW = 1.5;
  const barW = 0.42;
  const gap = 0.12;
  const startX = -((data.length - 1) * groupW) / 2;
  return (
    <group>
      {data.map((g, gi) =>
        g.values.map((v, si) => {
          const seriesSpan = g.values.length * barW + (g.values.length - 1) * gap;
          const bx = startX + gi * groupW - seriesSpan / 2 + si * (barW + gap) + barW / 2;
          return (
            <Bar
              key={`${gi}-${si}`}
              x={bx}
              z={0}
              width={barW}
              depth={0.42}
              height={(v / 100) * 2.6}
              color={colors[si % colors.length]}
              delay={gi * 0.12 + si * 0.07}
              reduced={reduced}
            />
          );
        }),
      )}
    </group>
  );
}

function Scatter({ reduced }: { reduced?: boolean }) {
  // Deterministic cloud so it renders identically each mount.
  const points = useMemo(() => {
    const pts: { p: [number, number, number]; c: string; s: number }[] = [];
    let seed = 7;
    const rnd = () => {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };
    for (let i = 0; i < 26; i++) {
      pts.push({
        p: [(rnd() - 0.5) * 4.4, (rnd() - 0.3) * 2.8, (rnd() - 0.5) * 3.2],
        c: rnd() > 0.5 ? CORAL : TEAL,
        s: 0.13 + rnd() * 0.12,
      });
    }
    return pts;
  }, []);
  return (
    <group>
      {points.map((pt, i) => (
        <Point key={i} {...pt} reduced={reduced} />
      ))}
    </group>
  );
}

function Point({
  p,
  c,
  s,
  reduced,
}: {
  p: [number, number, number];
  c: string;
  s: number;
  reduced?: boolean;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  useFrame((state) => {
    if (!mesh.current || reduced) return;
    mesh.current.position.y = p[1] + Math.sin(state.clock.elapsedTime * 0.9 + phase) * 0.12;
  });
  return (
    <mesh ref={mesh} position={p}>
      <sphereGeometry args={[s, 24, 24]} />
      <meshStandardMaterial color={c} roughness={0.3} metalness={0.15} />
    </mesh>
  );
}

function Donut({ reduced }: { reduced?: boolean }) {
  const spin = useRef<THREE.Group>(null);
  const grow = useRef(0);
  const arc = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    grow.current += dt;
    if (arc.current) {
      const g = reduced ? 1 : easeOut(grow.current / 0.9);
      // Sweep the coral arc in by scaling the geometry's theta via rotation trick:
      // simplest visible growth is a scale-in.
      arc.current.scale.setScalar(reduced ? 1 : 0.6 + g * 0.4);
    }
    if (spin.current && !reduced) spin.current.rotation.z -= dt * 0.25;
  });
  return (
    <group ref={spin} rotation={[Math.PI / 2.4, 0, 0]}>
      {/* base ring */}
      <mesh>
        <torusGeometry args={[1.4, 0.5, 32, 80]} />
        <meshStandardMaterial color={TEAL} roughness={0.35} metalness={0.12} />
      </mesh>
      {/* highlighted slice */}
      <mesh ref={arc}>
        <torusGeometry args={[1.4, 0.52, 32, 80, Math.PI * 1.1]} />
        <meshStandardMaterial color={CORAL} roughness={0.32} metalness={0.14} />
      </mesh>
    </group>
  );
}

function Area({ reduced }: { reduced?: boolean }) {
  // A 3D area/line read: a row of thin columns tracing a smooth curve.
  const heights = useMemo(
    () => [0.5, 0.85, 0.7, 1.15, 1.4, 1.15, 1.55, 1.9, 1.6, 2.1].map((h) => h),
    [],
  );
  const w = 0.36;
  const gap = 0.12;
  const startX = -((heights.length - 1) * (w + gap)) / 2;
  return (
    <group>
      {heights.map((h, i) => (
        <Bar
          key={i}
          x={startX + i * (w + gap)}
          z={0}
          width={w}
          depth={0.36}
          height={h}
          color={i % 3 === 0 ? TEAL : CORAL}
          delay={i * 0.05}
          reduced={reduced}
        />
      ))}
    </group>
  );
}
