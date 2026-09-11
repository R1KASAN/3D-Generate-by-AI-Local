import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("cross-origin mock API supports the complete public job flow without GPU work", async ({ page }) => {
  const apiOrigins = new Set<string>();
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/")) apiOrigins.add(new URL(request.url()).origin);
  });

  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByRole("status")).toContainText(/queued|running|completed/);
  await expect(page.getByRole("status")).toContainText("completed", { timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Download GLB" })).toBeVisible();
  expect(apiOrigins).toEqual(new Set(["http://127.0.0.1:18000"]));
  await expect(page.locator("canvas")).toBeVisible({ timeout: 10_000 });
});
