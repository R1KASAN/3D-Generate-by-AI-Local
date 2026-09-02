import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { createJob, downloadJob, getJob, modelUrl } from "../../lib/api/jobs";
import { GenerationForm } from "../../components/generation-form";

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
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ job_id: "job-1", status: "completed" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    await getJob("job-1", "token-1", fetcher);
    await downloadJob("job-1", "token-1", fetcher);

    for (const [url, options] of fetcher.mock.calls) {
      expect(url).not.toContain("token-1");
      expect(options.headers["X-Job-Token"]).toBe("token-1");
    }
    expect(modelUrl("job-1")).toBe("/api/v1/jobs/job-1/model");
  });

  it("renders a supported image picker and generation action", () => {
    render(<GenerationForm onCreated={vi.fn()} />);

    expect(screen.getByLabelText(/reference image/i)).toHaveAttribute("accept", ".jpg,.jpeg,.png");
    expect(screen.getByRole("button", { name: /generate 3d/i })).toBeInTheDocument();
  });
});
