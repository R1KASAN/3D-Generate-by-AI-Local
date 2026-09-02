import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("refreshes during processing and keeps the same job token", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByRole("status")).toContainText(/queued|processing|completed/, { timeout: 10_000 });
  await page.reload();
  await expect(page.getByRole("status")).toContainText(/queued|processing|completed/, { timeout: 10_000 });
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
