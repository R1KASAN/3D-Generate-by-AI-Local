import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");

test("preview reports backend unavailable instead of a missing job", async ({ page }) => {
  await page.route("**/api/v1/jobs", async (route) => {
    if (route.request().method() === "POST") return route.abort("failed");
    return route.continue();
  });
  await page.goto("/");
  await page.setInputFiles("#reference-image", fixture);
  await page.getByRole("button", { name: "Generate 3D" }).click();
  await expect(page.getByText(/The AI service is temporarily unavailable/i)).toBeVisible();
  await expect(page.locator("body")).not.toContainText("This job is no longer available");
});
