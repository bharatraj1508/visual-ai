/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    // Vega pulls in an optional native `canvas` dep we don't use (charts render
    // client-side via SVG). Stub it so the build doesn't warn/try to resolve it.
    config.resolve.alias = { ...config.resolve.alias, canvas: false };
    return config;
  },
};

export default nextConfig;
