import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { JobStatusView } from "../../components/job-status";
import type { Job } from "../../lib/api/jobs";

const job: Job = {
  job_id: "job-1",
  status: "running",
  progress_percent: 50,
  progress_message: "Working",
  queue_position: null,
  queue_position_is_approximate: true,
  error: null,
  model_url: null,
  download_url: null,
  created_at: "2026-01-01T00:00:00Z",
  expires_at: "2099-01-01T00:00:00Z",
};

describe("safe failure presentation", () => {
  afterEach(() => cleanup());
  it("preserves the last confirmed state while reporting API unavailability", () => {
    render(<JobStatusView job={job} error="The AI service is temporarily unavailable. Please retry." />);

    expect(screen.getByRole("status")).toHaveTextContent("Status: running");
    expect(screen.getByRole("alert")).toHaveTextContent(/temporarily unavailable/i);
    expect(screen.queryByText(/127\.0\.0\.1|traceback|storage\//i)).not.toBeInTheDocument();
  });

  it("renders an API-confirmed terminal error separately from transport failure", () => {
    render(
      <JobStatusView
        job={{ ...job, status: "failed", error: { code: "generation_failed", message: "Generation failed" } }}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Status: failed");
    expect(screen.getByRole("alert")).toHaveTextContent("Generation failed");
  });
});
