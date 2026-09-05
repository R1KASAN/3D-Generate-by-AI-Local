# Lab Origin Management-Access Record

**Feature**: `003-outbound-tunnel-entry` | **Recorded**: 2026-09-06 | **Status**: `PENDING — no channel decided yet`

This file records the **one** management-channel decision `docs/operations/lab-origin-bootstrap.md` Step 1 requires before any remote shell to the approved origin exists. It is not filled in yet — the professor's approval to access the lab server is administrative authorization, not a technical connection method, and no channel has been chosen.

## Decision record (fill in once decided)

| Field | Value |
|---|---|
| Channel chosen | `PENDING` — one of: Console only / VPN-or-bastion-scoped SSH / Internet-facing SSH |
| Decided by | `PENDING` |
| Date decided | `PENDING` |
| Rationale | `PENDING` |
| If Internet-facing SSH (Option C): written owner risk-acceptance | `PENDING — required before use, not after` |

## Connection details (fill in only if Option B or C is chosen — never commit a private key or password)

| Field | Value |
|---|---|
| Account name (non-root, least-privilege) | `PENDING` |
| Public-key fingerprint | `PENDING` |
| Allowed source range | `PENDING` — the VPN/bastion CIDR for Option B; must never be recorded as `Any`/`0.0.0.0/0` without the Option C risk-acceptance above |
| Password authentication | `PENDING` — must be confirmed `disabled` before this row is filled in |

## Prerequisite check (from bootstrap Step 0 — must be done first, before this decision)

| Item | Status |
|---|---|
| Origin OS and version confirmed | `PENDING TARGET INSPECTION` (T065) |
| Origin's outbound egress address confirmed | `PENDING TARGET INSPECTION` (T065) |
| Direct WireGuard UDP reachability without router forwarding | `PENDING TARGET INSPECTION` (T066b) — **a failure here means Option A is not feasible and this file should not be filled in until the transport is redesigned (FR-041)** |

Do not skip ahead and fill in the decision record above before every row in this table is resolved.
