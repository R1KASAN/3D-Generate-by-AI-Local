import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const fixture = path.resolve(__dirname, "../../../../fixtures/inputs/valid-reference.png");
const buffer = fs.readFileSync(fixture);

test("two jobs use distinct IDs/tokens and swapped access is rejected", async ({ request }) => {
  const first = await request.post("/api/v1/jobs", {
    multipart: { file: { name: "one.png", mimeType: "image/png", buffer } },
  });
  const second = await request.post("/api/v1/jobs", {
    multipart: { file: { name: "two.png", mimeType: "image/png", buffer } },
  });
  expect(first.ok()).toBeTruthy();
  expect(second.ok()).toBeTruthy();
  const firstBody = await first.json();
  const secondBody = await second.json();
  expect(firstBody.job_id).not.toBe(secondBody.job_id);
  expect(firstBody.job_token).not.toBe(secondBody.job_token);

  // Drain both jobs so the shared single-GPU mock dispatcher is clean for the
  // next browser test while retaining the isolation assertions below.
  for (const body of [firstBody, secondBody]) {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const status = await request.get(`/api/v1/jobs/${body.job_id}`, {
        headers: { "X-Job-Token": body.job_token },
      });
      expect(status.ok()).toBeTruthy();
    }
  }

  const swapped = await request.get(`/api/v1/jobs/${secondBody.job_id}`, {
    headers: { "X-Job-Token": firstBody.job_token },
  });
  expect(swapped.status()).toBe(404);
  expect((await swapped.json()).error.code).toBe("job_not_found");
});
