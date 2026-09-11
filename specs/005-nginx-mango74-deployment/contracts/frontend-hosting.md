# Contract: NT Server Static Frontend

## Public boundary

| Request | Required result |
|---|---|
| `https://www.mangosgo.com/mango74` | One permanent HTTPS-preserving redirect to `/mango74/`; query retained |
| `https://www.mangosgo.com/mango74/` | Exported application `index.html` |
| `/mango74/_next/*` and declared assets | Corresponding release asset with correct media type |
| Supported Mango74 deep link | Exported route or approved `/mango74/` fallback |
| `/mango740`, `/Mango74`, unrelated paths | Existing website behavior; never Mango74 fallback |

Fragments are browser-only and are not sent to the server. Encoded separators,
dot segments, traversal attempts, mixed-case paths, and repeated slashes must
not broaden the Mango74 boundary.

## Build contract

The production build uses:

```text
Next.js output        = export
basePath              = /mango74
trailingSlash         = true
public API base       = https://mango74-api.mangosgo.com/api/v1
production frontend   = https://www.mangosgo.com/mango74/
```

Both `basePath` and the `NEXT_PUBLIC_API_BASE_URL` value are build-time
settings. A change to either creates a new release and archive hash.

The application must not depend on Next.js rewrites, redirects, headers, API
routes, cookies, Server Actions, or another Node runtime after export. The NT
Server owns the one outer redirect and static deep-link behavior.

## `front-end.zip` contract

The archive contains one deployable `mango74/` tree plus release metadata. The
administrator may unpack that tree into the platform-specific document root,
but no member may escape it.

Allowed content:

- HTML;
- CSS;
- JavaScript and required source-independent runtime chunks;
- fonts;
- images and icons;
- static data required by the compiled UI;
- a non-secret release and integrity manifest.

Rejected content:

- Python, FastAPI, Uvicorn, or Node server runtime files;
- ComfyUI, workflows, custom nodes, or models;
- SQLite databases, job events, uploads, GLBs, or generated outputs;
- `.env` files, credentials, tokens, passwords, keys, certificates, Tunnel
  configuration, private addresses, or temporary URLs;
- executable installers or unreviewed binaries.

Every member has a normalized relative path, byte length, and SHA-256 in the
artifact manifest. Packaging rejects traversal, alternate data streams,
symlinks/reparse points, and disallowed extensions. The archive itself receives
a SHA-256 recorded in the deployment evidence.

## Browser API behavior

Every generation, status, cancellation, preview, and download request resolves
against the configured stable API base. Root-relative API paths returned by the
backend are resolved against `https://mango74-api.mangosgo.com`, never against
the frontend origin.

If the API is unavailable, the static page remains usable and displays a clear
AI-service-unavailable result. A transport, DNS, TLS, Tunnel, or CORS failure is
not displayed as “This job is no longer available.” That message is reserved
for an API-confirmed uniform missing/expired/unauthorized job response.

Browser job state is stored in a versioned session key scoped to the normalized
API origin. Changing among local, Firebase-preview, or production API bases
cannot restore another environment's job reference.

## Caching

- HTML and deployment metadata: revalidate or `no-cache` so rollback is
  observable promptly.
- Content-hashed framework assets: immutable long-lived caching is permitted.
- Job/API/GLB responses: never cached by the NT Server; they are not served by
  it in this split-origin model.

## Deployment and rollback handoff

Before deployment, the authorized NT Server administrator records:

1. server product/version and deployment interface;
2. current `/mango74` and `/mango74/` behavior;
3. representative unrelated-route status, destination, and content hashes;
4. current Mango74 release or absence;
5. the exact platform rollback action.

Deployment changes only the `/mango74` static boundary. Rollback restores the
prior static tree and routing state without touching the AI Notebook, named
Tunnel, FastAPI, ComfyUI, SQLite, job files, or GPU workloads.
