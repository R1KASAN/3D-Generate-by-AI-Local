# Feature 003 external security acceptance

**Status:** MANUAL/BLOCKED pending authorized lab-origin access and an external test connection. Do not probe the approved public IP to discover remote management. This is an execution checklist; it is not the spec-quality checklist.

- [ ] Local origin inventory confirms no public HTTP or management listener, Origin CA, or client-auth configuration; the only permitted inbound socket is the C1a WireGuard UDP transport listener, restricted to the approved address/port/service and isolated from application, storage, metrics, and administration.
- [ ] Authorized external tests receive no direct application response from origin pass-through, API, AI engine, database/storage, metrics, or administration. Confirm test vantage and connectivity; local network errors are not proof of lockdown.
- [ ] The running origin transport boundary matches the C1a declaration: exactly one WireGuard UDP port on the approved origin address, WireGuard service only, peer public-key admission, `/32` scope on both sides, and no TCP application listener, SSH/RDP/VNC or other management listener, catch-all inbound rule, or router port forward (SC-018). Confirm the static verifier also **rejects** a deliberately widened fixture; a verifier that only confirms expected rules would pass a configuration that has those rules plus a violation.
- [ ] The approved origin **directly receives** the WireGuard UDP transport on its approved network path without router port forwarding (FR-041). A negative result voids Option A: keep production blocked and redesign the transport. Do not enable router forwarding, a public application port, a public GPU-laptop listener, or a paid relay as a workaround.
- [ ] Laptop remains unreachable from the Internet while the trusted-LAN port forward remains functional.
- [ ] Missing, wrong, expired, and cross-job tokens return uniform 404 for status, preview, and download.
- [ ] Unsupported, corrupt, disguised, and oversized uploads fail before GPU execution; below 10% free disk new jobs are rejected safely.
- [ ] Queue, retry, and identical-submission limits return safe 429 without modifying accepted work; five accepted jobs execute with GPU concurrency one.
- [ ] Status, creation, artifacts, and failure responses have no-store; confirm provider cache controls on the actual account.
- [ ] A synthetic capability token has zero matches across all project-controlled connector, origin pass-through, application, and diagnostic logs. Only request IDs and validated job IDs are retained for correlation.
- [ ] Provider-facing DNS contains no approved-origin address; inability to verify provider ranges is BLOCKED.
- [ ] Active Cloudflare connector addresses all match the approved origin; on zrok independently capture origin-local connector and egress evidence. Correlate the tagged external journey at the origin.
- [ ] Observe filesystem events for both maximum-size transfers throughout the trial, including files created then removed. No project-authored spool or complete-body temporary file; OS paging excluded.
- [ ] Reboot each machine three times and in both orders. LAN starts with binding absent/origin down; public path resumes without app restart when the binding returns.
- [ ] Three Internet interruption/restores recover the route within five minutes after connectivity returns.
- [ ] The laptop reconnects after moving between at least two distinct external networks (for example university or home Wi-Fi and a mobile hotspot) with the public DNS record, public hostname, provider tunnel route, approved-origin configuration, feature 001 application configuration, and WireGuard tunnel addressing all unchanged (FR-040, SC-017). Editing any of those to make a move succeed is a failure, not a fix.
- [ ] Separate engine, binding, and job-service failure trials return the project unavailable experience within five seconds; origin/connector down returns the provider error.
- [ ] Public-route disable preserves jobs/results and LAN operation; credential revocation stops traffic and replacement restores the same hostname.
- [ ] Never-authorized and withdrawn-hostname rehearsals follow the cause gate, owner recovery window, and provider-specific TLS exposure acceptance.

Do not retain obsolete inbound HTTPS range allowlists as the deployment procedure. Provider IP ranges used by DNS verification identify routing only. Any failed or blocked result leaves its acceptance task unchecked; diagnose the failing layer and use `tunnel-setup.md` rollback without weakening the boundary.
