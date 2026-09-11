import { describe, expect, it, vi } from "vitest";

import { DEFAULT_MANGO74_BASE_PATH, DEFAULT_PRODUCTION_API_BASE_URL, getPublicRuntimeConfig } from "../../lib/config/public-runtime";

describe("Firebase preview runtime", () => {
  it("labels preview without replacing the official Mango74 base path", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("MANGO74_STATIC_EXPORT", "1");
    vi.stubEnv("NEXT_PUBLIC_DEPLOYMENT_ENV", "preview");
    vi.stubEnv("NEXT_PUBLIC_BASE_PATH", DEFAULT_MANGO74_BASE_PATH);
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", DEFAULT_PRODUCTION_API_BASE_URL);
    const runtime = getPublicRuntimeConfig();
    expect(runtime.production).toBe(false);
    expect(runtime.deploymentEnv).toBe("preview");
    expect(runtime.basePath).toBe("/mango74");
    vi.unstubAllEnvs();
  });

  it("uses the stable API and rejects a temporary endpoint in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", DEFAULT_PRODUCTION_API_BASE_URL);
    expect(getPublicRuntimeConfig().apiBaseUrl).toBe(DEFAULT_PRODUCTION_API_BASE_URL);
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://example.trycloudflare.com/api/v1");
    expect(() => getPublicRuntimeConfig()).toThrow(/Quick Tunnel/i);
    vi.unstubAllEnvs();
  });
});
