# Convergence audit — Cloudflare public entry

**Feature:** `002-cloudflare-public-entry`  
**Checked:** 2026-09-05  
**Method:** Compare the current worktree with `spec.md`, `plan.md`,
`research.md`, `data-model.md`, `quickstart.md`, all feature contracts,
`tasks.md`, and Constitution v1.2.0.

## Final repository verification

- `uv run --project apps/api pytest -q`: **130 passed, 4 skipped**
- Web lint and TypeScript no-emit check: **PASS**
- Python compilation, PowerShell parsing, service XML parsing, and `git diff --check`: **PASS**
- Public-evidence address scan and Caddy/HTTP-marker audit: **PASS**

## Requirement coverage

| Area | Repository evidence | Current result |
|---|---|---|
| Cloudflare naming/proxy design | `deploy/cloudflare/dns-records.md`, `docs/operations/cloudflare-setup.md` | Implemented as a safe template; live DNS/provider state blocked. |
| Origin TLS and admission | `deploy/caddy/Caddyfile`, `tests/security/test_caddy_contract.py` | Static contract PASS; Origin CA installation and live mTLS proof blocked. |
| Public port policy | Firewall configure/refresh/verifier scripts and `contracts/port-policy.md` | Static policy PASS; live origin rule and management proof blocked. |
| Credential boundary | Caddy log filter and public-auth verifier | Project-controlled log protection implemented; provider logging controls blocked. |
| DNS/origin disclosure | `test_dns_disclosure.py`, address-scope static audit | Verifiers implemented; external DNS proof blocked. |
| WireGuard mobility | Tunnel templates, startup wrapper, watchdog, reachability verifier | Static topology/recovery checks PASS; live handshake/positive traversal blocked. |
| Laptop availability | `laptop-power.md`, startup/recovery checks | AC sleep/hibernate/lid policy PASS; firewall and multi-network acceptance blocked. |
| Degraded service | Maintenance page, Caddy `handle_errors`, maintenance evidence | Static contract PASS; live disconnected-laptop acceptance blocked. |
| Continuity and handover | `naming-continuity.md`, owner-gate evidence | Safe template complete; real owner/account/certificate facts and reviewer blocked. |
| Evidence safety | `evidence-review.md` | 11 public-deployment evidence files scanned: no unmasked IPv4 or credential matches. |
| Superseded feature reconciliation | Feature 001 task-list withdrawal note | Complete. |

## No remaining safe repository gap

All remaining unchecked task IDs are recorded as blocked in
`specs/002-cloudflare-public-entry/tasks.md`. No remaining task can be honestly
completed with repository-only evidence, and no live operation was performed
that could expose the service, change DNS, or risk management lockout.

**Convergence result: MAXIMUM SAFE PROGRESS.** The feature is not ready for
public cutover until the blocked owner, network, origin, provider, and external
acceptance gates are closed.
