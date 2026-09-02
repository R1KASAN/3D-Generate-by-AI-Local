import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = path.resolve(__dirname, "../..");
const e2eStorage = fs.mkdtempSync(path.join(os.tmpdir(), "local3d-e2e-"));

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["json", { outputFile: "test-results/mock-e2e.json" }]],
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: "uv run --project apps/api python -m uvicorn local3d.main:app --host 127.0.0.1 --port 8000",
      cwd: root,
      env: {
        GENERATION_ADAPTER: "mock",
        STORAGE_ROOT: e2eStorage,
        DATABASE_PATH: path.join(e2eStorage, "jobs.sqlite3"),
      },
      port: 8000,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3100",
      cwd: __dirname,
      env: { NODE_ENV: "test" },
      port: 3100,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
