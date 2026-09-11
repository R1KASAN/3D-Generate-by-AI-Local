import { afterEach, describe, expect, it } from "vitest";

import {
  clearStoredJob,
  jobStorageKey,
  readStoredJob,
  writeStoredJob,
} from "../../lib/jobs/job-storage";
import type { JobCreated } from "../../lib/api/jobs";

const job: JobCreated = {
  job_id: "job-1",
  job_token: "token-1",
  status: "queued",
  progress_percent: null,
  progress_message: null,
  queue_position: 1,
  queue_position_is_approximate: true,
  error: null,
  model_url: null,
  download_url: null,
  created_at: "2026-01-01T00:00:00Z",
  expires_at: "2099-01-01T00:00:00Z",
};

describe("API-origin-scoped remembered jobs", () => {
  afterEach(() => sessionStorage.clear());

  it("stores and restores the owner job without exposing the token in the key", () => {
    writeStoredJob(job, sessionStorage, "https://mango74-api.mangosgo.com/api/v1");
    expect(readStoredJob(sessionStorage, "https://mango74-api.mangosgo.com/api/v1")).toEqual(job);
    expect(jobStorageKey("https://mango74-api.mangosgo.com/api/v1")).not.toContain(job.job_token);
  });

  it("does not restore a job from another API origin", () => {
    writeStoredJob(job, sessionStorage, "https://mango74-api.mangosgo.com/api/v1");
    expect(readStoredJob(sessionStorage, "https://other.example/api/v1")).toBeNull();
  });

  it("removes expired or malformed records safely", () => {
    sessionStorage.setItem(
      jobStorageKey("https://mango74-api.mangosgo.com/api/v1"),
      JSON.stringify({ ...job, expires_at: "2020-01-01T00:00:00Z" }),
    );
    expect(readStoredJob(sessionStorage, "https://mango74-api.mangosgo.com/api/v1")).toBeNull();
    sessionStorage.setItem(
      jobStorageKey("https://mango74-api.mangosgo.com/api/v1"),
      "not-json",
    );
    expect(readStoredJob(sessionStorage, "https://mango74-api.mangosgo.com/api/v1")).toBeNull();
    clearStoredJob(sessionStorage, "https://mango74-api.mangosgo.com/api/v1");
  });
});
