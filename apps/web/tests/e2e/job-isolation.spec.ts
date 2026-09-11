import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");
const apiOrigin = "http://127.0.0.1:18000";

test("two sessions cannot read or mutate each other's job token", async ({ browser }) => {
  const first = await browser.newContext();
  const second = await browser.newContext();
  const firstPage = await first.newPage();
  const secondPage = await second.newPage();
  await Promise.all([firstPage.goto("/"), secondPage.goto("/")]);
  await firstPage.setInputFiles("#reference-image", fixture);
  await secondPage.setInputFiles("#reference-image", fixture);
  await Promise.all([
    firstPage.getByRole("button", { name: "Generate 3D" }).click(),
    secondPage.getByRole("button", { name: "Generate 3D" }).click(),
  ]);
  const readStored = async (page: typeof firstPage) => {
    await expect
      .poll(() => page.evaluate(() => Object.keys(sessionStorage).some((key) => key.startsWith("local3d:last-job:"))))
      .toBe(true);
    return page.evaluate(() => {
      const key = Object.keys(sessionStorage).find((candidate) => candidate.startsWith("local3d:last-job:"));
      return JSON.parse(sessionStorage.getItem(key!)!) as { job_id: string; job_token: string };
    });
  };
  const a = await readStored(firstPage);
  const b = await readStored(secondPage);
  expect(a.job_id).not.toBe(b.job_id);
  const denied = await first.request.get(`${apiOrigin}/api/v1/jobs/${b.job_id}`, {
    headers: { "X-Job-Token": a.job_token },
  });
  expect(denied.status()).toBe(404);
  await expect(firstPage.getByRole("status")).toContainText("completed", { timeout: 30_000 });
  await expect(secondPage.getByRole("status")).toContainText("completed", { timeout: 30_000 });
  await first.close();
  await second.close();
});
