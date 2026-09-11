import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("queued job token survives refresh and cancellation", async ({ page }) => {
  const jobId = "00000000-0000-4000-8000-000000000010";
  const token = "refresh-cancel-token";
  let cancelled = false;
  const queued = {
    job_id: jobId,
    job_token: token,
    status: "queued",
    progress_percent: null,
    progress_message: null,
    queue_position: 1,
    queue_position_is_approximate: true,
    error: null,
    model_url: null,
    download_url: null,
    created_at: "2026-01-01T00:00:00Z",
    expires_at: "2099-01-02T00:00:00Z",
  };
  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(queued) });
  });
  await page.route(`**/api/v1/jobs/${jobId}/cancel`, async (route) => {
    expect(route.request().headers()["x-job-token"]).toBe(token);
    cancelled = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...queued, status: "cancelled", queue_position: null }),
    });
  });
  await page.route(`**/api/v1/jobs/${jobId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(cancelled ? { ...queued, status: "cancelled", queue_position: null } : queued),
    });
  });

  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByRole("button", { name: /cancel queued job/i })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /cancel queued job/i }).click();
  await expect(page.getByRole("status")).toContainText("cancelled");
});
