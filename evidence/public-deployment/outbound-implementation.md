# Outbound implementation evidence (T003)

- Date: 2026-09-06
- Scope: repository-local implementation and isolated loopback validation
- Live-origin access: **BLOCKED** — no authorized physical or remote connection is available; the approved public address is not used for management discovery.
- Credentials, capability tokens, uploaded content, and full public addresses are omitted.

| Area | Evidence | Verdict |
|---|---|---|
| API admission bounds | 5 simultaneous API submissions accepted with unique jobs; sixth request returned safe HTTP 429 with `Retry-After: 60`; accepted jobs remained readable | **PASS** |
| Durable limits | Two service instances sharing SQLite accepted only the configured pending/submission limits; restart preserved accepted work and refusal | **PASS** |
| Capability/log masking | Evidence helper masks IPv4/IPv6 and synthetic credential fields; masking tests cover new phase artifacts | **PASS** |
| Provider evidence | Unsuccessful, mixed, pending, and incomplete Cloudflare connection responses fail closed; zrok requires exact local process and origin vantage | **PASS** |
| DNS evidence | Provider-range retrieval failure returns `BLOCKED`; origin address disclosure fails | **PASS** |
| Direct-boundary evidence | Local/network errors are inconclusive, not lockdown success; external probe requires explicit off-campus attestation | **PASS** |
| Health chain | Origin edge/connector probes are independent; laptop health uses independent GPU probe and separate engine probe; watchdog limits retries and waits for dependent grace | **PASS** |
| Caddy static contract | No public listener, TLS/mTLS, buffering directives, or certificate paths; loopback listener, streaming guard, request ID, header redaction, and cache control present | **PASS** |
| Caddy runtime | Verified with Caddy 2.11.4 against its published SHA-512 checksum. Isolated upstream trial confirmed request ID forwarding, no-store responses, unavailable response within five seconds, and no synthetic token in Caddy logs | **PASS** |
| Caddy configuration | `caddy validate --config deploy/caddy/Caddyfile --adapter caddyfile` returned `Valid configuration` | **PASS** |
| Software test suite | `pytest tests/security apps/api/tests --import-mode=importlib` with the verified Caddy binary: 168 passed, 4 skipped (hardware/live tests) | **PASS** |
| Type/lint | mypy passed; ruff passed after removing two pre-existing unused/f-string findings | **PASS** |
| Live origin setup | cloudflared installation, named tunnel, service auto-start, Quick Tunnel journey, reboot/recovery, DNS, egress, credential rotation, direct external boundary, real GPU and provider-account checks | **BLOCKED / MANUAL** |

The production route remains blocked until the manual evidence is captured. The compute-link transport clarification selects Option A: a narrowly scoped, authenticated WireGuard UDP listener is permitted on the approved origin, while application and management listeners remain prohibited. No firewall exception or public management probe was performed.

**Remediation, 2026-09-06 (Option A consistency pass).** `scripts/verify/test_origin_lockdown.py` was reopened and revised: the permitted WireGuard UDP transport port is now accepted explicitly and refused as a probe target, application and management TCP ports remain prohibited, and every probe outcome that is not an unambiguous refusal or reset is recorded INCONCLUSIVE with a non-zero exit rather than counted as a pass. The remote vantage point cannot prove the transport listener's scope at all, so the script now says so and defers that to origin-local evidence. `tests/security/test_origin_lockdown_contract.py` pins the classification locally; `pytest tests/security -q` returned 74 passed, 1 skipped. Nothing about the live boundary changed — only what this repository is willing to claim from a remote probe.
