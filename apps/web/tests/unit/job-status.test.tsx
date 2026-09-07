import { act, cleanup, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Job, JobStatus } from "../../lib/api/jobs";
import { JobStatusView } from "../../components/job-status";
import { useJobStatus } from "../../lib/jobs/use-job-status";

const baseJob: Job = {
  job_id: "job-1",
  status: "queued",
  progress_percent: null,
  progress_message: null,
  queue_position: null,
  queue_position_is_approximate: true,
  error: null,
  model_url: null,
  download_url: null,
  created_at: "2026-01-01T00:00:00Z",
  expires_at: "2026-01-02T00:00:00Z",
};

function Harness({ fetchStatus }: { fetchStatus: (id: string, token: string) => Promise<Job> }) {
  const { job, error } = useJobStatus("job-1", "secret-token", { initialJob: baseJob, fetchStatus });
  return <output>{error ?? `${job?.status}:${job?.progress_percent ?? "unknown"}`}</output>;
}

function job(status: JobStatus, progress_percent: number | null = null): Job {
  return { ...baseJob, status, progress_percent };
}

describe("useJobStatus", () => {
  it("refreshes after two seconds, then stops on a terminal state", async () => {
    vi.useFakeTimers();
    const fetchStatus = vi
      .fn<(id: string, token: string) => Promise<Job>>()
      .mockResolvedValueOnce(job("running", 25))
      .mockResolvedValueOnce(job("completed", 100));

    render(<Harness fetchStatus={fetchStatus} />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchStatus).toHaveBeenCalledTimes(1);
    expect(fetchStatus).toHaveBeenCalledWith("job-1", "secret-token", expect.any(AbortSignal));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_999);
    });
    expect(fetchStatus).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(fetchStatus).toHaveBeenCalledTimes(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(fetchStatus).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("renders safe failure text and does not expose internal details", async () => {
    const fetchStatus = vi.fn().mockResolvedValue({
      ...job("failed"),
      error: { code: "generation_failed", message: "Generation failed" },
    });

    render(<Harness fetchStatus={fetchStatus} />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText("failed:unknown")).toBeInTheDocument();
    expect(screen.queryByText(/traceback|prompt_id|storage/i)).not.toBeInTheDocument();
  });

  it("renders approximate queue/progress and terminal recovery text", () => {
    render(
      <JobStatusView
        job={{ ...baseJob, status: "running", progress_percent: null, progress_message: null }}
      />,
    );
    expect(screen.getByText(/running/i)).toBeInTheDocument();
    expect(screen.getByText(/progress unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/queue position unavailable/i)).toBeInTheDocument();
  });

  it("retries after a transient 503 and clears the error when polling recovers", async () => {
    cleanup();
    vi.useFakeTimers();
    const fetchStatus = vi
      .fn<(id: string, token: string, signal?: AbortSignal) => Promise<Job>>()
      .mockRejectedValueOnce(new Error("edge returned HTML"))
      .mockResolvedValueOnce(job("completed", 100));
    render(<Harness fetchStatus={fetchStatus} />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText(/edge returned HTML/i)).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(screen.getAllByText("completed:100").length).toBeGreaterThan(0);
    vi.useRealTimers();
  });

  it("does not report a cancellation as a completed result", async () => {
    cleanup();
    vi.useFakeTimers();
    const fetchStatus = vi.fn<(id: string, token: string, signal?: AbortSignal) => Promise<Job>>(
      () => Promise.reject(new DOMException("aborted", "AbortError")),
    );
    render(<Harness fetchStatus={fetchStatus} />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText(/status unavailable|aborted/i)).toBeInTheDocument();
    expect(screen.queryByText(/completed/)).not.toBeInTheDocument();
    vi.useRealTimers();
  });
});
