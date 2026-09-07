import { describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { cancelJob, createJob, downloadJob, getJob, JobsApiError, modelUrl, userFacingJobError } from "../../lib/api/jobs";
import { GenerationForm } from "../../components/generation-form";
import { GenerationResult } from "../../components/generation-result";
import HomePage from "../../app/page";

describe("generation API client", () => {
  it("sends multipart upload and keeps the returned token in memory", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "job-1", status: "queued", job_token: "token-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );

    const result = await createJob(new File(["image"], "input.png", { type: "image/png" }), fetcher);

    expect(result.job_token).toBe("token-1");
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/jobs",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
  });

  it("uses X-Job-Token and never puts the token in a URL", async () => {
    const fetcher = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ job_id: "job-1", status: "completed" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      })),
    );

    await getJob("job-1", "token-1", fetcher);
    await cancelJob("job-1", "token-1", fetcher);
    await downloadJob("job-1", "token-1", fetcher);

    for (const [url, options] of fetcher.mock.calls) {
      expect(url).not.toContain("token-1");
      expect(options.headers["X-Job-Token"]).toBe("token-1");
    }
    expect(modelUrl("job-1")).toBe("/api/v1/jobs/job-1/model");
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/jobs/job-1/cancel",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("renders a supported image picker and generation action", () => {
    render(<GenerationForm onCreated={vi.fn()} />);

    expect(screen.getByLabelText(/reference image/i)).toHaveAttribute("accept", ".jpg,.jpeg,.png");
    expect(screen.getByRole("button", { name: /generate 3d/i })).toBeInTheDocument();
  });

  it("maps edge and application failures to actionable guidance", () => {
    expect(userFacingJobError(new JobsApiError(429, "submission_limited", "busy"), "fallback")).toMatch(
      /busy.*try again/i,
    );
    expect(userFacingJobError(new JobsApiError(503, "service_unavailable", "down"), "fallback")).toMatch(
      /temporarily unavailable/i,
    );
    expect(userFacingJobError(new Error("network"), "fallback")).toBe("network");
  });

  it("maps low storage and non-JSON edge failures without exposing proxy text", async () => {
    expect(userFacingJobError(new JobsApiError(507, "low_storage", "disk details"), "fallback")).toMatch(
      /low on storage/i,
    );
    const fetcher = vi.fn().mockResolvedValue(new Response("upstream unavailable", { status: 503 }));
    await expect(downloadJob("job-1", "token-1", fetcher)).rejects.toMatchObject({
      status: 503,
      code: "request_failed",
      message: "Request failed",
    });
    expect(userFacingJobError(new JobsApiError(503, "request_failed", "Request failed"), "fallback")).toMatch(
      /temporarily unavailable/i,
    );
  });

  it("disables duplicate generation clicks until the accepted response arrives", async () => {
    cleanup();
    let resolveResponse!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    });
    const fetchMock = vi.fn().mockReturnValue(pending);
    vi.stubGlobal("fetch", fetchMock);
    const onCreated = vi.fn();
    const view = render(<GenerationForm onCreated={onCreated} />);
    const input = view.container.querySelector("input[type=file]") as HTMLInputElement;
    const file = new File(["image"], "input.png", { type: "image/png" });
    Object.defineProperty(input, "files", { configurable: true, value: [file] });
    fireEvent.change(input);
    const button = view.container.querySelector('button[type="submit"]') as HTMLButtonElement;
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    fireEvent.click(button);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(button).toBeDisabled();
    resolveResponse(
      new Response(JSON.stringify({ job_id: "job-1", status: "queued", job_token: "token-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    vi.unstubAllGlobals();
  });

  it("rejects unsupported and oversized files before any request", async () => {
    cleanup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<GenerationForm onCreated={vi.fn()} />);
    const input = view.container.querySelector("input[type=file]") as HTMLInputElement;
    const button = view.container.querySelector('button[type="submit"]') as HTMLButtonElement;

    const unsupported = new File(["text"], "notes.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", { configurable: true, value: [unsupported] });
    fireEvent.change(input);
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    expect(await view.findByRole("alert")).toHaveTextContent(/jpeg or png/i);
    expect(fetchMock).not.toHaveBeenCalled();

    cleanup();
    const second = render(<GenerationForm onCreated={vi.fn()} />);
    const secondInput = second.container.querySelector("input[type=file]") as HTMLInputElement;
    const secondButton = second.container.querySelector('button[type="submit"]') as HTMLButtonElement;
    const oversized = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.png", {
      type: "image/png",
    });
    Object.defineProperty(secondInput, "files", { configurable: true, value: [oversized] });
    fireEvent.change(secondInput);
    await waitFor(() => expect(secondButton).not.toBeDisabled());
    fireEvent.click(secondButton);
    expect(await second.findByRole("alert")).toHaveTextContent(/10 mib/i);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("always labels the public endpoint as a temporary non-production test", () => {
    render(<HomePage />);
    expect(screen.getByRole("note", { name: /test service notice/i })).toHaveTextContent(
      /temporary non-production test service/i,
    );
  });

  it("does not offer a download when a completed job has no result artifact", () => {
    cleanup();
    render(
      <GenerationResult
        job={{
          job_id: "job-missing-result",
          status: "completed",
          progress_percent: 100,
          progress_message: "Generation completed but the result is unavailable",
          queue_position: null,
          queue_position_is_approximate: true,
          error: null,
          model_url: null,
          download_url: null,
          created_at: "2026-01-01T00:00:00Z",
          expires_at: "2026-01-02T00:00:00Z",
        }}
        jobToken="token-1"
      />,
    );

    expect(screen.queryByRole("button", { name: /download glb/i })).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/result is unavailable/i);
  });

  it("lets the owner cancel a queued job and then removes the cancel action", async () => {
    cleanup();
    const queued = {
      job_id: "job-cancel",
      status: "queued" as const,
      progress_percent: null,
      progress_message: null,
      queue_position: 2,
      queue_position_is_approximate: true,
      error: null,
      model_url: null,
      download_url: null,
      created_at: "2026-01-01T00:00:00Z",
      expires_at: "2026-01-02T00:00:00Z",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cancel") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            ...queued,
            status: "cancelled",
            queue_position: null,
            progress_message: "Cancelled by user",
            error: { code: "cancelled_by_user", message: "Cancelled by user" },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(JSON.stringify(queued), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<GenerationResult job={queued} jobToken="owner-token" />);
    fireEvent.click(await screen.findByRole("button", { name: /cancel queued job/i }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Status: cancelled"));
    expect(screen.queryByRole("button", { name: /cancel queued job/i })).not.toBeInTheDocument();
    const cancelCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/cancel"));
    expect(cancelCall?.[1]?.headers).toMatchObject({ "X-Job-Token": "owner-token" });
    vi.unstubAllGlobals();
  });

});
