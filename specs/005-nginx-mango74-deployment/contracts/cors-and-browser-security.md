# Contract: Cross-Origin Browser Security

## Environment allowlists

| Environment | Allowed origin set |
|---|---|
| Production | `https://www.mangosgo.com` only |
| Firebase preview disabled | Production origin only; Firebase receives no usable CORS response |
| Firebase preview explicitly enabled | Production origin plus `https://inw3d-ai-local.web.app` |
| Local automated tests | Explicit test origins supplied by isolated test configuration |

An origin is the exact scheme, host, and optional port. URL paths do not form
part of the `Origin` value, so the production entry is
`https://www.mangosgo.com`, not a value ending in `/mango74/`.

## Preflight contract

For an allowed origin, middleware may return:

```text
Access-Control-Allow-Origin: <exact request origin>
Vary: Origin
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Accept, Content-Type, X-Job-Token
Access-Control-Allow-Credentials: absent
```

The implementation may normalize header name case as required by HTTP. It must
not reflect an origin unless that exact normalized origin is configured.

The required matrix includes:

| Origin | Expected browser-readable result |
|---|---|
| `https://www.mangosgo.com` | Allowed in production |
| `http://www.mangosgo.com` | Denied |
| `https://www.mangosgo.com:444` | Denied as an unexpected non-default port |
| `https://mangosgo.com` | Denied |
| `https://www.mangosgo.com.evil.example` | Denied |
| `https://sub.www.mangosgo.com` | Denied |
| `null` | Denied |
| arbitrary website | Denied |
| Firebase exact origin | Allowed only while preview flag is explicitly enabled |

An explicit default HTTPS port `:443` normalizes to the same browser origin as
`https://www.mangosgo.com`; the unexpected-port tests therefore use a
non-default port.

Denial means no usable `Access-Control-Allow-Origin` response. The HTTP status
may still be safe and meaningful to non-browser clients; CORS is not a network
firewall or authentication system.

## Authorization independence

An allowed origin without the correct `X-Job-Token` receives the same uniform
job-not-found response as a missing, expired, incorrect, or cross-job token.
An unauthorized origin with a valid token still receives no usable browser
cross-origin response. Both dimensions must be tested independently.

Tokens must not appear in:

- query strings or fragments;
- `Location` headers;
- Nginx or Cloudflare logs;
- frontend release files;
- public evidence;
- error messages.

## Transport failure classification

The frontend client distinguishes:

| Condition | User-visible class |
|---|---|
| DNS, TLS, offline, Tunnel, timeout, aborted fetch, or CORS failure | AI service unavailable/retrying |
| API `404 job_not_found` after a readable response | Job unavailable or expired |
| API `409` | Accurate result/cancellation conflict |
| API `429`, `503`, `507` | Capacity, dependency, or storage guidance |
| malformed/non-JSON proxy error | Generic safe service-unavailable/request-failed result |

No transport exception text, browser internal wording, upstream page, stack
trace, hostname other than the approved public boundary, or local path is
shown to the user.
