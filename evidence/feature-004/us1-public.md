# Feature 004 public-route browser evidence (T034)

- Date/time (UTC): 2026-09-07T02:21:00Z
- Hostname: `<redacted-quick-tunnel>`
- Vantage: Codex in-app browser reached the public HTTPS route; off-campus/campus egress was not independently attested.
- The temporary non-production test notice was visible.
- A real reference image was submitted through the public route.
- Browser status transitioned to `running`, then `completed` with `Progress: 100%`.
- The 3D model viewer and `Download GLB` control were visible after completion.
- Local health-chain verification with the current temporary URL returned root HTTP 200 and `/api/v1/health/live` HTTP 200.
- No ComfyUI identifier was exposed in the rendered page.
- Credentials, capability tokens, full hostname, and private IP addresses are omitted.

## Verdict

**BLOCKED for the strict T034 gate**: the public-route real generation was
observed, but an independently attested off-campus vantage and a captured
download/hash result are still required before marking T034 complete.
