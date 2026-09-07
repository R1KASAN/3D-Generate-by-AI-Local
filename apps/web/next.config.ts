import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Development-only fallback when Caddy is not running. Public test traffic
  // uses Caddy's /api/* split and never depends on this rewrite.
  async rewrites() {
    const apiOrigin = process.env.NEXT_DEV_API_ORIGIN ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
