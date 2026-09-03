import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("uploads an image, reaches completion, previews, and downloads the GLB", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();

  // The serial mock can advance from queued before the first browser poll. The
  // lifecycle contract is covered separately; this browser test verifies that
  // the user sees a safe lifecycle state and can reach the terminal result.
  await expect(page.getByRole("status")).toHaveText(/Status: (queued|processing|completed)/);
  await expect(page.getByRole("status")).toContainText("completed", { timeout: 20_000 });
  await expect(page.getByRole("button", { name: "Download GLB" })).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible({ timeout: 10_000 });

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download GLB" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.glb$/);
});
