# Mango74 rollback runbook

## Frontend only

Stop the NT deployment, restore the recorded `/mango74` backup, verify unrelated routes, then re-publish the approved archive. Do not restart or move the AI backend.

## Nginx/proxy

Stop `Local3D-Nginx`, validate the retained Caddy definition, and restore `Local3D-Caddy` only when the API contract and rollback approval match. Never allow both services to bind port 8080.

## Tunnel/API

Disable the named Tunnel route through the authorized Cloudflare administrator, preserve the stable hostname record, and restore the connector only after local Nginx/API readiness passes. A Tunnel rollback must not change the official frontend URL.

## Stop criteria and verification

Stop on unknown release/change IDs, unsafe active work, non-loopback listeners, missing durable job metadata, or any secret in evidence. After rollback, verify frontend availability, explicit API-unavailable behavior when expected, loopback health, listener boundaries, and route preservation.
