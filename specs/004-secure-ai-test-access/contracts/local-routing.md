# Contract: Single-Node Local Routing and Exposure Boundary

## Purpose

This contract fixes the only approved request path for feature 004. It is an
implementation and verification boundary, not an example topology.

```text
Public User
  -> HTTPS Cloudflare edge
  -> outbound-established Cloudflare Tunnel
  -> cloudflared on the Notebook
  -> http://127.0.0.1:8080 (Caddy only)
  -> 127.0.0.1:3000 (web) or 127.0.0.1:8000 (API)
  -> 127.0.0.1:8188 (ComfyUI, from FastAPI only)
```

`161.200.90.4` is the Notebook's assigned network identity. It is not a URL,
origin, bind address, public DNS target, or application ingress endpoint.

## Listener ownership

| Port | Process | Required bind | Permitted caller | Public route |
|---:|---|---|---|---|
| 3000 | Next.js | `127.0.0.1` | Caddy; direct local developer checks | Through Caddy `/` only |
| 8000 | FastAPI/Uvicorn | `127.0.0.1` | Caddy; direct local operator checks | Through Caddy `/api` only |
| 8080 | Caddy | `127.0.0.1` | cloudflared; direct local operator checks | Sole Tunnel origin |
| 8188 | ComfyUI | `127.0.0.1` | FastAPI adapter; local operator checks | None |

No application process may bind these ports to `0.0.0.0`, `::`,
`161.200.90.4`, a LAN address, or a public interface. No inbound firewall,
router, NAT, Windows portproxy, or DNS rule may expose them.

## Caddy route contract

The implementation must be equivalent to this routing shape; security headers,
logging, and error handling are additional required controls:

```caddyfile
{
    admin off
}

:8080 {
    bind 127.0.0.1

    @api path /api /api/*
    handle @api {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

Normative rules:

1. The site address is `:8080` and interface restriction is a separate
   `bind 127.0.0.1`. Using `http://127.0.0.1:8080` as the site address is not
   equivalent because it also constrains the `Host` header and can reject the
   public hostname forwarded by Cloudflare.
2. Exact `/api` and every `/api/*` path go to FastAPI. They do not fall through
   to Next.js.
3. Caddy preserves method, path prefix, query, body, and `X-Job-Token` for the
   upstream request. `handle_path`, `uri strip_prefix`, and other `/api`
   rewrites are forbidden.
4. All non-API paths, including Next.js static assets and application routes,
   go to `127.0.0.1:3000`.
5. The Next.js `/api/*` rewrite may remain for direct developer access to port
   3000, but it is not part of the public or Caddy route and must not create a
   second network boundary.
6. Caddy never routes a browser path to ComfyUI. Requests such as `/prompt`,
   `/queue`, `/history/*`, `/upload/image`, `/system_stats`, or `/ws` are handled
   by the frontend unless they are beneath `/api`; no public route maps them to
   8188.
7. Caddy does not make an AI-engine health request before every normal proxy
   request. FastAPI controls admission, and the frontend remains loadable while
   the AI dependency is unavailable.

## Quick Tunnel origin contract

The development/test connector invocation is:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

- The connector runs on the same Notebook and makes outbound connections.
- The generated `*.trycloudflare.com` address is temporary, potentially public,
  not authentication, and not a production endpoint.
- The feature does not create a default cloudflared config, credentials file,
  tunnel token, named tunnel, custom hostname, or DNS record.
- Both TCP and UDP egress to port 7844 are permitted so automatic QUIC/HTTP2
  transport selection can work. No inbound permission is requested.
- A Quick Tunnel session starts only after local readiness. Stopping it does not
  stop or migrate the local application.
- The connector log level is `info` or safer during user traffic. Debug request
  logging is prohibited.

## Body and response handling

- Caddy applies a 12 MB whole-request guard to provide multipart framing
  headroom. FastAPI remains authoritative for the 10 MiB image-file limit.
- Caddy does not enable `request_buffers`, `response_buffers`, or an equivalent
  disk spool. Upload and GLB bodies stream through the proxy.
- FastAPI returns `201` only after durable admission; AI generation continues
  asynchronously and never holds the upload request open until completion.
- Model and download responses are `model/gltf-binary`, `private, no-store`,
  and contain only an atomically published GLB.
- Browser progress uses ordinary GET polling. Required behavior does not use
  SSE. A public WebSocket is not part of this contract.

## Headers, caching, and logging

Caddy overwrites any client-provided correlation value with a generated
`X-Request-ID` and passes the resulting ID upstream. Public responses include
safe security headers and suppress the `Server` header. Job/API responses and
artifacts are never placed in a shared cache.

Neither Caddy's access log nor its runtime/error log may contain:

- `X-Job-Token`, `Authorization`, `Cookie`, or `Set-Cookie` values;
- query values, request/response bodies, original user filenames, or image/GLB
  content;
- private filesystem paths, raw ComfyUI payloads/identifiers, or GPU details;
- the complete temporary Quick Tunnel URL.

Allowed diagnostic fields are request ID, safe Job ID when its path format is
validated, route class (`web` or `api`), status, duration, byte counts, and safe
upstream availability. Logs use bounded file rotation.

## Failure contract

| Failure | Public behavior | Internal effect |
|---|---|---|
| Next.js unavailable | Safe `503` maintenance page that still says temporary non-production; no internal address/path | API and AI state remain intact |
| FastAPI unavailable | Safe `503` API error for `/api/*`; no HTML stack trace or upstream address | Frontend can still load and show unavailable guidance |
| ComfyUI/GPU unavailable | Frontend loads; health reports unavailable; new admission returns safe `503`; accepted jobs reconcile safely | No Caddy topology change |
| Quick Tunnel interrupted | Browser gets a transport/edge failure; local Caddy/app continue | Operator restarts a new session and communicates its new URL |
| Quick Tunnel edge limit | May be non-JSON `429`; frontend shows a safe generic capacity/retry message | Accepted jobs are unchanged |
| Oversized body | Caddy or FastAPI returns `413` without forwarding/processing an unbounded body | No job is admitted |

## Verification assertions

1. Listener inventory proves 3000, 8000, 8080, and 8188 are loopback-only.
2. Local `Host: <random>.trycloudflare.com` against Caddy succeeds, proving the
   site address does not accidentally constrain Host.
3. `/` and a Next.js static route reach port 3000.
4. `/api`, `/api/v1/health/live`, and `/api/v1/jobs` reach port 8000 with the
   complete path unchanged.
5. Public requests cannot obtain a ComfyUI route or engine identifier.
6. Authorized external probes to `161.200.90.4` on 3000, 8000, 8080, and 8188
   receive no project application response. Timeouts alone are recorded as
   inconclusive and paired with local listener/firewall evidence.
7. Token/content sentinels do not appear in any project-controlled log.
8. Stopping cloudflared leaves local Caddy, API, job state, and generation
   available.
