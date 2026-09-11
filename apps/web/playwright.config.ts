import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = path.resolve(__dirname, "../..");
const e2eStorage = fs.mkdtempSync(path.join(os.tmpdir(), "local3d-e2e-"));
// Keep browser tests isolated from the operator's live API on :8000. This is
// test-only infrastructure; the approved runtime contract remains :8000.
const e2eThroughNginx = process.env.E2E_NGINX === "1";
const e2eApiPort = e2eThroughNginx ? 18001 : 18000;
const e2ePublicApiPort = 18000;
const nginxBinary = process.env.NGINX_BINARY ?? path.join(root, "deploy", "windows", "services", "nginx.exe");
const nginxTestRoot = path.join(e2eStorage, "nginx");
const nginxTestConfig = path.join(nginxTestRoot, "nginx.conf");

if (e2eThroughNginx) {
  if (!fs.existsSync(nginxBinary)) {
    throw new Error(`E2E_NGINX=1 requires an Nginx binary: ${nginxBinary}`);
  }
  for (const directory of [
    "logs",
    "temp/client_body_temp",
    "temp/proxy_temp",
    "temp/fastcgi_temp",
    "temp/uwsgi_temp",
    "temp/scgi_temp",
  ]) {
    fs.mkdirSync(path.join(nginxTestRoot, directory), { recursive: true });
  }
  fs.writeFileSync(path.join(nginxTestRoot, "mime.types"), "types {}\n", "utf8");
  fs.writeFileSync(
    nginxTestConfig,
    `worker_processes 1;
error_log logs/error.log warn;
pid logs/nginx.pid;
events { worker_connections 64; }
http {
  server_names_hash_bucket_size 64;
  include mime.types;
  access_log logs/access.log;
  client_max_body_size 12m;
  server {
    listen 127.0.0.1:${e2ePublicApiPort};
    server_name 127.0.0.1 localhost mango74-api.mangosgo.com www.mangosgo.com;
    location /api/ {
      proxy_pass http://127.0.0.1:${e2eApiPort};
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-Proto http;
      proxy_set_header Connection "";
    }
    location / { return 404; }
  }
}
`,
    "utf8",
  );
}

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
      command: `uv run --project apps/api python -m uvicorn local3d.main:app --host 127.0.0.1 --port ${e2eApiPort}`,
      cwd: root,
      env: {
        GENERATION_ADAPTER: "mock",
        API_PORT: String(e2eApiPort),
        CORS_ALLOWED_ORIGINS: "http://127.0.0.1:3100,https://www.mangosgo.com",
        STORAGE_ROOT: e2eStorage,
        DATABASE_PATH: path.join(e2eStorage, "jobs.sqlite3"),
        WORKER_INTERVAL_SECONDS: e2eThroughNginx ? "5" : "2",
        MAX_IDENTICAL_PER_MINUTE: "100",
        MAX_SUBMISSIONS_PER_MINUTE: "100",
      },
      port: e2eApiPort,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    ...(e2eThroughNginx
      ? [
          {
            command: `"${nginxBinary}" -p "${nginxTestRoot}" -c "${nginxTestConfig}" -g "daemon off;"`,
            cwd: root,
            port: e2ePublicApiPort,
            reuseExistingServer: false,
            timeout: 120_000,
          },
        ]
      : []),
    {
      command: "npm run dev -- --port 3100",
      cwd: __dirname,
      env: {
        NODE_ENV: "test",
        NEXT_DEV_API_ORIGIN: `http://127.0.0.1:${e2ePublicApiPort}`,
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${e2ePublicApiPort}/api/v1`,
      },
      port: 3100,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
