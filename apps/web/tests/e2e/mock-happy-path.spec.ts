import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("uploads an image, reaches completion, previews, and downloads the GLB", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("note", { name: "Test service notice" })).toContainText(
    "Temporary non-production test service",
  );
  const apiOrigins = new Set<string>();
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/")) apiOrigins.add(new URL(request.url()).origin);
  });
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();

  // The serial mock can advance from queued before the first browser poll. The
  // lifecycle contract is covered separately; this browser test verifies that
  // the user sees a safe lifecycle state and can reach the terminal result.
  await expect(page.getByRole("status")).toHaveText(/Status: (queued|running|completed)/);
  await expect(page.getByRole("status")).toContainText("completed", { timeout: 20_000 });
  await expect(page.getByRole("button", { name: "Download GLB" })).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible({ timeout: 10_000 });
  expect(apiOrigins).toEqual(new Set(["http://127.0.0.1:18000"]));
  expect(
    await page.evaluate(() => {
      const storageKey = Object.keys(window.sessionStorage).find((key) =>
        key.startsWith("local3d:last-job:"),
      );
      const stored = storageKey ? window.sessionStorage.getItem(storageKey) : null;
      if (!stored) return false;
      const parsed = JSON.parse(stored) as { job_id?: string; job_token?: string };
      return Boolean(parsed.job_id && parsed.job_token);
    }),
  ).toBe(true);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download GLB" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.glb$/);
});
