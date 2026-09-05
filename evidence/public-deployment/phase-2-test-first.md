# Phase 2 Test-First Evidence

**Feature:** `002-cloudflare-public-entry`
**Recorded:** 2026-09-05

This evidence records the required pre-implementation checkpoint. Network
addresses and hostnames are represented by placeholders; no credentials,
tokens, or passwords are recorded.

## T009 — Caddy contract extension

Command:

```text
uv run --project apps/api pytest tests/security/test_caddy_contract.py -q -k "no_basic_auth or no_automatic_certificate_management or origin_listener_is_443_only or requires_provider_client_certificate"
```

Result: **expected failing baseline** — the preserved
`test_no_basic_auth` passed; the new checks failed because the current
Caddyfile still contains the old automatic certificate email, the `:443, :80`
catch-all, and no provider client-certificate verification. This is the
required test-first failure before the Phase 3 Caddy implementation tasks.

## T010 — direct-origin lockdown

The new verifier was run with the approved origin address and
`--confirm-off-campus` before origin configuration. It exited non-zero because
the probe timed out, which is inconclusive and therefore correctly not a pass.
The post-configuration acceptance run must produce a handshake-level refusal
or transport refusal, not a timeout and not an application response.

## T011 — DNS disclosure

The new verifier was run with `<PUBLIC_HOSTNAME>` and
`--confirm-off-campus` before the proxied record existed. It exited non-zero
because the placeholder hostname did not resolve. This correctly prevents a
missing record from being mistaken for a disclosure-free public entry.
