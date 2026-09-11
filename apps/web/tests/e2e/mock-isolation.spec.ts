import { expect, test } from "@playwright/test";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");
const apiOrigin = "http://127.0.0.1:18000";

type StoredJob = { job_id: string; job_token: string };

async function storedJob(page: import("@playwright/test").Page): Promise<StoredJob> {
  await expect
    .poll(() =>
      page.evaluate(() => {
        const key = Object.keys(window.sessionStorage).find((candidate) =>
          candidate.startsWith("local3d:last-job:"),
        );
        const raw = key ? window.sessionStorage.getItem(key) : null;
        return raw ? (JSON.parse(raw) as StoredJob).job_id : null;
      }),
    )
    .not.toBeNull();
  return page.evaluate(() => {
    const key = Object.keys(window.sessionStorage).find((candidate) =>
      candidate.startsWith("local3d:last-job:"),
    );
    return JSON.parse(window.sessionStorage.getItem(key!)!) as StoredJob;
  });
}

test("independent sessions keep queue, token, activation, and result isolation", async ({ browser }) => {
  const firstContext = await browser.newContext();
  const secondContext = await browser.newContext();
  const firstPage = await firstContext.newPage();
  const secondPage = await secondContext.newPage();
  let firstSubmissions = 0;

  firstPage.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/jobs")) firstSubmissions += 1;
  });

  // Keep the initial GET pending briefly so both sessions visibly render the
  // independently admitted queued state before the serial mock worker drains.
  for (const page of [firstPage, secondPage]) {
    await page.route(/\/api\/v1\/jobs\/[^/]+$/, async (route) => {
      if (route.request().method() === "GET") await new Promise((resolve) => setTimeout(resolve, 750));
      await route.continue();
    });
    await page.goto("/");
    await page.setInputFiles("#reference-image", fixture);
  }

  await Promise.all([
    firstPage.getByRole("button", { name: "Generate 3D" }).dblclick(),
    secondPage.getByRole("button", { name: "Generate 3D" }).click(),
  ]);

  await expect(firstPage.getByRole("status")).toContainText("queued");
  await expect(secondPage.getByRole("status")).toContainText("queued");
  await expect(secondPage.getByText(/Queue position:/)).toBeVisible();

  const first = await storedJob(firstPage);
  const second = await storedJob(secondPage);
  expect(first.job_id).not.toBe(second.job_id);
  expect(first.job_token).not.toBe(second.job_token);
  expect(firstSubmissions).toBe(1);

  const swapped = await firstContext.request.get(`${apiOrigin}/api/v1/jobs/${second.job_id}`, {
    headers: { "X-Job-Token": first.job_token },
  });
  expect(swapped.status()).toBe(404);
  expect((await swapped.json()).error.code).toBe("job_not_found");

  await expect(firstPage.getByRole("status")).toContainText("completed", { timeout: 20_000 });
  await expect(secondPage.getByRole("status")).toContainText("completed", { timeout: 20_000 });

  const [firstModel, firstDownload, secondModel, secondDownload] = await Promise.all([
    firstContext.request.get(`${apiOrigin}/api/v1/jobs/${first.job_id}/model`, {
      headers: { "X-Job-Token": first.job_token },
    }),
    firstContext.request.get(`${apiOrigin}/api/v1/jobs/${first.job_id}/download`, {
      headers: { "X-Job-Token": first.job_token },
    }),
    secondContext.request.get(`${apiOrigin}/api/v1/jobs/${second.job_id}/model`, {
      headers: { "X-Job-Token": second.job_token },
    }),
    secondContext.request.get(`${apiOrigin}/api/v1/jobs/${second.job_id}/download`, {
      headers: { "X-Job-Token": second.job_token },
    }),
  ]);
  for (const response of [firstModel, firstDownload, secondModel, secondDownload]) {
    expect(response.ok()).toBeTruthy();
  }
  const firstModelBytes = await firstModel.body();
  const firstDownloadBytes = await firstDownload.body();
  const secondModelBytes = await secondModel.body();
  const secondDownloadBytes = await secondDownload.body();
  expect(firstModelBytes).toEqual(firstDownloadBytes);
  expect(secondModelBytes).toEqual(secondDownloadBytes);
  expect(firstModelBytes).not.toEqual(secondModelBytes);

  await firstContext.close();
  await secondContext.close();
});
