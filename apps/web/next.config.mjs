import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server (.next/standalone) so the Docker runtime image
  // ships only the traced deps, not the whole workspace node_modules.
  output: "standalone",
  // This app lives in a yarn workspace; trace files from the repo root so the
  // standalone bundle picks up hoisted deps.
  experimental: {
    outputFileTracingRoot: path.join(__dirname, "../../"),
  },
  webpack: (config) => {
    // Vega pulls in an optional native `canvas` dep we don't use (charts render
    // client-side via SVG). Stub it so the build doesn't warn/try to resolve it.
    config.resolve.alias = { ...config.resolve.alias, canvas: false };
    return config;
  },
};

export default nextConfig;
