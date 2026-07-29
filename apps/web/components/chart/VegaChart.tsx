"use client";

import dynamic from "next/dynamic";

// Vega touches the DOM/canvas, so load it client-side only.
const VegaLite = dynamic(
  () => import("react-vega").then((mod) => mod.VegaLite),
  { ssr: false },
);

export default function VegaChart({
  spec,
}: {
  spec: Record<string, unknown>;
}) {
  return (
    <div className="w-full overflow-x-auto rounded-md border border-gray-200 bg-white p-2 sm:p-3">
      <VegaLite spec={spec as any} actions={false} />
    </div>
  );
}
