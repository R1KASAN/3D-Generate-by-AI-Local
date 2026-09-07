import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("refreshes during running and keeps the same job token", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByRole("status")).toContainText(/queued|running|completed/, { timeout: 10_000 });
  await page.reload();
  await expect(page.getByRole("status")).toContainText(/queued|running|completed/, { timeout: 10_000 });
  await expect(page.getByRole("status")).toContainText("completed", { timeout: 20_000 });
});

test("shows safe failure text and never engine details", async ({ page }) => {
  let statusReads = 0;
  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "00000000-0000-4000-8000-000000000001",
        job_token: "test-token",
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
      }),
    });
  });
  await page.route("**/api/v1/jobs/00000000-0000-4000-8000-000000000001", async (route) => {
    statusReads += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "00000000-0000-4000-8000-000000000001",
        status: "failed",
        progress_percent: null,
        progress_message: null,
        queue_position: null,
        queue_position_is_approximate: true,
        error: { code: "generation_failed", message: "Generation failed" },
        model_url: null,
        download_url: null,
        created_at: "2026-01-01T00:00:00Z",
        expires_at: "2026-01-02T00:00:00Z",
      }),
    });
  });

  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByRole("status")).toContainText("failed", { timeout: 5_000 });
  expect(statusReads).toBeGreaterThan(0);
  await expect(page.locator("body")).not.toContainText(/traceback|prompt_id|storage\//i);
});

test("restores the owner credential after refresh and cancels a waiting job", async ({ page }) => {
  const jobId = "00000000-0000-4000-8000-000000000002";
  const token = "refresh-owner-token";
  const queued = {
    job_id: jobId,
    job_token: token,
    status: "queued",
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
  let cancelled = false;

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
      body: JSON.stringify({
        ...queued,
        status: "cancelled",
        queue_position: null,
        progress_message: "Cancelled by user",
        error: { code: "cancelled_by_user", message: "Cancelled by user" },
      }),
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
  await expect(page.getByRole("button", { name: /cancel queued job/i })).toBeVisible();
  await page.getByRole("button", { name: /cancel queued job/i }).click();
  await expect(page.getByRole("status")).toContainText("cancelled");
  await expect(page.getByRole("button", { name: /cancel queued job/i })).toHaveCount(0);
});

test("maps application and non-JSON edge capacity failures to retry guidance", async ({ page }) => {
  const fixtureStatuses = [
    { status: 429, body: JSON.stringify({ error: { code: "submission_limited", message: "busy" } }), expected: /busy.*try again/i },
    { status: 503, body: "upstream unavailable", expected: /temporarily unavailable/i },
    { status: 507, body: JSON.stringify({ error: { code: "low_storage", message: "low" } }), expected: /low on storage/i },
  ];
  let current = fixtureStatuses[0];
  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: current.status,
      contentType: current.status === 503 ? "text/html" : "application/json",
      body: current.body,
    });
  });

  for (const failure of fixtureStatuses) {
    current = failure;
    await page.goto("/");
    await page.setInputFiles("#reference-image", fixture);
    await page.getByRole("button", { name: "Generate 3D" }).click();
    await expect(page.locator('p[role="alert"]')).toContainText(failure.expected, { timeout: 5_000 });
  }
});
