import { expect, test } from "@playwright/test";

test("only the exact Firebase preview origin is opt-in for CORS", async ({ request }) => {
  const production = await request.fetch("http://127.0.0.1:18000/api/v1/health/live", {
    method: "OPTIONS",
    headers: {
      Origin: "https://www.mangosgo.com",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "X-Job-Token",
    },
  });
  expect(production.status()).toBe(200);
  expect(production.headers()["access-control-allow-origin"]).toBe("https://www.mangosgo.com");

  const firebase = await request.fetch("http://127.0.0.1:18000/api/v1/health/live", {
    method: "OPTIONS",
    headers: {
      Origin: "https://inw3d-ai-local.web.app",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "X-Job-Token",
    },
  });
  expect(firebase.status()).toBe(400);
  expect(firebase.headers()["access-control-allow-origin"]).toBeUndefined();
});
