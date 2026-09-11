# Research: NT-Hosted Mango74 Frontend and Stable AI API

**Feature**: `005-nginx-mango74-deployment`

**Date**: 2026-09-09
**Constitution**: 5.0.0

This research resolves the technical choices needed to plan the split-origin
production deployment. Feature 004 remains the validated job, storage,
ComfyUI, and RTX 5070 baseline; only the public frontend, API boundary,
reverse proxy, and production Tunnel lifecycle change.

## 1. Preserve the existing application stack

**Decision**: Keep Next.js 16.3.4/React 19.2.8 for the frontend, FastAPI
0.116.1/Python 3.12 for the API, SQLite and per-job files for durable state,
the approved Hunyuan3D ComfyUI workflow, and the current RTX 5070 Notebook.
Replace Caddy with Nginx only at the production backend proxy boundary.

**Rationale**: The repository already has validated queueing, cancellation,
job-token isolation, restart reconciliation, GLB publication, and real GPU
evidence. Migrating frameworks or state systems would increase risk without
supporting the deployment requirement.

**Alternatives considered**:

- Move FastAPI or ComfyUI to the NT Server: rejected because the NT Server is
  authorized only for compiled static frontend files.
- Add a second AI backend or cloud GPU: rejected by Constitution 5.0.0.
- Keep Caddy in production: rejected because Nginx is the approved production
  proxy; Caddy remains disabled rollback history only.

## 2. Build a static Next.js frontend for `/mango74/`

**Decision**: Use Next.js static export with `output: "export"`, build-time
`basePath: "/mango74"`, and `trailingSlash: true`. Produce a deterministic
`front-end.zip` containing only the exported HTML, CSS, JavaScript, fonts,
images, and a non-secret integrity manifest.

**Rationale**: Next.js supports deployment of its `out` directory to any
static web server. `basePath` is embedded at build time and automatically
prefixes framework navigation; `trailingSlash: true` produces directory-style
HTML suitable for `/mango74/`. The NT Server must provide the one permanent
`/mango74` to `/mango74/` redirect and the documented deep-link fallback
because Next.js redirects and rewrites are not runtime features in static
export mode.

**Alternatives considered**:

- Run `next start` on the NT Server: rejected because the approved NT package
  is static-only and must not add a Node application runtime.
- Use only `assetPrefix`: rejected because it does not establish the complete
  application routing boundary that `basePath` provides.
- Hand-edit exported HTML paths: rejected as fragile and non-reproducible.

**Sources**:

- Next.js local documentation:
  `apps/web/node_modules/next/dist/docs/01-app/02-guides/static-exports.md`
- Next.js local documentation:
  `apps/web/node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/basePath.md`
- Next.js local documentation:
  `apps/web/node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/trailingSlash.md`

## 3. Compile the stable API base into the frontend

**Decision**: Build the production frontend with
`NEXT_PUBLIC_API_BASE_URL=https://mango74-api.mangosgo.com/api/v1` and resolve
all job operations against that absolute base. The build must fail if a
production export receives a missing, non-HTTPS, temporary, loopback, private,
or raw-IP API base.

**Rationale**: `NEXT_PUBLIC_*` values are inlined into browser bundles during
`next build`, which is appropriate for a public, non-secret API endpoint. A
static frontend has no server runtime from which to load later environment
changes, so changing the API URL requires rebuilding and redeploying the
frontend. The `/api/v1` base preserves the existing FastAPI routes under the
approved public `/api/*` boundary.

**Alternatives considered**:

- Root-relative `/api/v1`: rejected because it would call
  `www.mangosgo.com`, not the separate API origin.
- Runtime configuration endpoint on the NT Server: rejected because it adds
  server-side behavior and complexity to the static-only host.
- Quick Tunnel URL: rejected because it is temporary and non-production.

**Source**: Next.js local documentation:
`apps/web/node_modules/next/dist/docs/01-app/02-guides/environment-variables.md`.

## 4. Keep API resource references relative to the API origin

**Decision**: Preserve the existing API response paths such as
`/api/v1/jobs/{job_id}/model`, but require the frontend API client to resolve
them against the validated configured API origin rather than against
`window.location`. Every direct API operation must use the same URL builder.

**Rationale**: This preserves the existing FastAPI contract and makes local,
test, Firebase-preview, and production deployments use the same response
shape. It also avoids coupling durable job records to one public hostname.

**Alternatives considered**:

- Return absolute production URLs from FastAPI: rejected because it couples
  backend responses to one environment and complicates local testing.
- Ignore response resource locations and always reconstruct paths ad hoc:
  rejected because multiple URL construction paths can drift or leak the
  frontend origin.

## 5. Use an exact, environment-scoped CORS policy

**Decision**: Add validated backend configuration for an exact origin list.
Production permits only `https://www.mangosgo.com`. The optional Firebase
preview permits `https://inw3d-ai-local.web.app` only in an explicitly enabled
test configuration. Allow credentials remains false. Preflight permits only
the API's required methods and request headers: `GET`, `POST`, `OPTIONS`,
`Accept`, `Content-Type`, and `X-Job-Token`. Required readable response headers
are explicitly exposed when browser behavior needs them.

**Rationale**: FastAPI's CORS middleware is restrictive by default and accepts
an explicit origin list. Exact configuration meets the browser requirement
without presenting CORS as authentication. Job-token and ownership checks
remain authoritative for protected operations.

**Alternatives considered**:

- `Access-Control-Allow-Origin: *`: rejected by the specification and because
  it would permit arbitrary websites to read public API responses.
- Nginx-only CORS: rejected because application tests and environment-specific
  allowlists belong with the API; duplicate proxy and API CORS headers are
  error-prone.
- Cookies and credentialed CORS: rejected because the current capability token
  uses `X-Job-Token` and no cookie requirement exists.

**Source**: [FastAPI CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/).

## 6. Use a named, remotely managed Cloudflare Tunnel

**Decision**: The authorized Cloudflare administrator creates a named,
remotely managed Tunnel and publishes
`mango74-api.mangosgo.com` to `http://127.0.0.1:8080`. The administrator
provides the connector token through a secure out-of-repository process. The
Notebook runs `cloudflared` as a Windows service. The token, service command
output containing it, and dashboard evidence containing secrets are never
committed.

**Rationale**: The Project Lead does not require direct inbound access or a
public Notebook IP. Dashboard ownership remains with the authorized Zone
administrator, while the connector maintains outbound connections and the
public hostname stays stable across restarts.

**Alternatives considered**:

- Locally managed Tunnel with `cert.pem` and credential JSON: rejected for
  this project because it gives the Notebook broader account artifacts and
  shifts route ownership away from the administrator.
- Quick Tunnel: rejected because its hostname changes and it has no production
  identity.
- Direct `161.200.90.4:443`: rejected because the observed address is not bound
  to this Notebook and direct ingress is unnecessary.

**Sources**:

- [Cloudflare Tunnel routing](https://developers.cloudflare.com/tunnel/routing/)
- [Cloudflare Tunnel run parameters](https://developers.cloudflare.com/tunnel/advanced/run-parameters/)
- [Cloudflare Tunnel on Windows](https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/windows/)

## 7. Use Nginx on loopback and preserve `/api/*`

**Decision**: Install a pinned official Nginx Windows build outside version
control, verify its operator-approved SHA-256, and supervise it with the
existing WinSW approach as `Local3D-Nginx`. Nginx listens only on
`127.0.0.1:8080`, accepts the exact API hostname, rejects unmatched hosts and
paths, and proxies `/api/*` to `http://127.0.0.1:8000` without a URI component
in `proxy_pass`, preserving the request URI. It applies a 12 MiB edge body
limit while FastAPI keeps the authoritative 10 MiB decoded upload limit.

**Rationale**: Nginx on Windows is a console application rather than a native
service, so a reviewed wrapper is required for reproducible startup and
recovery. Its Windows build effectively uses one active worker, which is
acceptable for this low-volume service because one RTX job is the dominant
capacity constraint. Loopback binding prevents direct network exposure.

**Alternatives considered**:

- Bind Nginx to `0.0.0.0` or a public address: rejected by the Constitution.
- Strip `/api` at Nginx: rejected because FastAPI already serves `/api/v1/*`.
- Proxy ComfyUI from Nginx: rejected because FastAPI is the only approved
  ComfyUI caller.

**Sources**:

- [Nginx for Windows](https://nginx.org/en/docs/windows.html)
- [Nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Nginx core HTTP module](https://nginx.org/en/docs/http/ngx_http_core_module.html)

## 8. Scope browser job restoration to the API boundary

**Decision**: Store the current job reference under a versioned session-storage
key derived from the normalized configured API origin. Persist only the job
reference, the one-job capability token, and safe display state. A different
API base must not restore that record.

**Rationale**: The same compiled interface may be reviewed locally, on
Firebase, or on the NT Server. Origin-scoped browser state prevents a stale
job created through one backend boundary from being interpreted as a missing
job on another. Network failures receive a distinct transport-unavailable
error and never map to `job_not_found` unless an API response actually returns
the uniform 404 contract.

**Alternatives considered**:

- Keep the global `local3d:last-job` key: rejected because it crosses API
  environments.
- Store the token in a URL: rejected because it leaks through history, logs,
  referrers, and screenshots.
- Add user accounts: rejected as out of scope; per-job capabilities remain the
  approved access model.

## 9. Treat the NT Server implementation as an administrator adapter

**Decision**: Define one platform-neutral frontend hosting contract and release
artifact. Before production deployment, the authorized NT Server administrator
must record the server software, document root or deployment interface,
current `/mango74` behavior, representative unrelated-route baseline, deploy
command, and rollback command. Server-specific instructions are filled from
that inventory without changing application architecture.

**Rationale**: The application team knows the public URL and required static
behavior but not the NT Server software. Inventing Apache, Nginx, IIS, or a
control-panel command would be unsafe. The unknown does not block application
design because the deliverable is a static archive with a precise behavior
contract; it blocks only the production deployment gate until the
administrator supplies the adapter details.

**Alternatives considered**:

- Assume IIS, Apache, or Nginx: rejected because no evidence identifies it.
- Give the NT Server backend duties: rejected by the static-only boundary.
- Delay all planning: rejected because repository, archive, CORS, Nginx, and
  Tunnel contracts are independent of the host's upload mechanism.

## 10. Deploy and roll back frontend and backend independently

**Decision**: Use immutable frontend release archives with SHA-256 manifests
and an atomic NT Server release switch where the host supports it. Record the
current frontend and unrelated-route baseline before deployment. Backend
cutover separately replaces Caddy on loopback `:8080` with Nginx, then enables
the named Tunnel. Rollback reverses only the affected boundary and never edits
the SQLite job database.

**Rationale**: Independent rollback prevents a static-page failure from moving
AI state and prevents a Tunnel/backend failure from changing the official
frontend URL. It also lets acceptance distinguish which boundary failed.

**Alternatives considered**:

- Overwrite static files without a release record: rejected because rollback
  would be slow and unverifiable.
- Deploy frontend and backend as one irreversible step: rejected because it
  couples unrelated failure domains.

## Resolved Unknowns

All architecture and application design choices are resolved. The exact NT
Server product and operator commands are a mandatory production deployment
input, not a remaining software-design clarification. No unresolved planning
markers remain in the design artifacts.
