import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_MANGO74_BASE_PATH,
  DEFAULT_PRODUCTION_API_BASE_URL,
  joinApiUrl,
  normalizeBasePath,
  resolveApiResource,
  validateApiBaseUrl,
} from "../../lib/config/public-runtime";

describe("Mango74 public runtime configuration", () => {
  afterEach(() => vi.unstubAllEnvs());
  it("normalizes the frontend base path", () => {
    expect(normalizeBasePath("mango74/")).toBe(DEFAULT_MANGO74_BASE_PATH);
    expect(normalizeBasePath("/")).toBe("");
  });

  it("accepts the approved production API and rejects unsafe production endpoints", () => {
    expect(validateApiBaseUrl(DEFAULT_PRODUCTION_API_BASE_URL, true)).toBe(
      DEFAULT_PRODUCTION_API_BASE_URL,
    );
    for (const value of [
      "http://www.mangosgo.com/api/v1",
      "http://127.0.0.1:8000/api/v1",
      "https://161.200.90.4/api/v1",
      "https://temporary.trycloudflare.com/api/v1",
    ]) {
      expect(() => validateApiBaseUrl(value, true)).toThrow();
    }
  });

  it("joins API paths without moving them to the frontend origin", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", DEFAULT_PRODUCTION_API_BASE_URL);
    expect(joinApiUrl(DEFAULT_PRODUCTION_API_BASE_URL, "/jobs/1")).toBe(
      "https://www.mangosgo.com/api/v1/jobs/1",
    );
    expect(resolveApiResource("/api/v1/jobs/1/model")).toBe(
      "https://www.mangosgo.com/api/v1/jobs/1/model",
    );
  });
});
