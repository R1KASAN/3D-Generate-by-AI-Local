import type { NextConfig } from "next";

const isFirebaseStaticExport = process.env.FIREBASE_STATIC_EXPORT === "1";
const isMango74StaticExport = process.env.MANGO74_STATIC_EXPORT === "1";
const isStaticExport = isFirebaseStaticExport || isMango74StaticExport;
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? (isStaticExport ? "/mango74" : "");

const commonConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  basePath,
  trailingSlash: isStaticExport,
};

const nextConfig: NextConfig = isStaticExport
  ? {
      ...commonConfig,
      output: "export",
    }
  : {
      ...commonConfig,
  // Development-only fallback when Caddy is not running. Public test traffic
  // uses Caddy's /api/* split and never depends on this rewrite.
      async rewrites() {
        const apiOrigin = process.env.NEXT_DEV_API_ORIGIN ?? "http://127.0.0.1:8000";
        return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
      },
    };

export default nextConfig;
