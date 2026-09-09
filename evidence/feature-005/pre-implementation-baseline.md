# Feature 005 Pre-Implementation Baseline

Captured: 2026-09-09 (local workstation; sanitized)

## Repository and runtime

- Repository: Git working tree detected.
- Node: `v24.19.0`; npm: `11.17.0`.
- Python: `3.12.10`; uv: `0.12.9`.
- Existing framework packages remain Next 16/React 19 and FastAPI/Python 3.12.
- Existing user changes were present in `.gitignore`, constitution, web config,
  `HANDOFF-ISSUES.md`, `firebase.json`, and `output/`; they were preserved.

## Windows services observed

| Service | State | Note |
|---|---|---|
| Local3D-API | Running | existing service |
| Local3D-Web | Running | existing service |
| Local3D-ComfyUI | Running | existing service |
| Local3D-Caddy | Running | Feature 004 proxy; Nginx cutover is not yet performed |
| Local3D-Nginx | Not installed/observed | Feature 005 work pending |
| cloudflared | Not installed/observed as a service | named Tunnel activation is an administrator gate |

## Listener boundary observed

The project application listeners were loopback-only at capture time:

- `127.0.0.1:3000` (Web)
- `127.0.0.1:8000` (FastAPI)
- `127.0.0.1:8080` (Caddy)
- `127.0.0.1:8188` (ComfyUI)

No portproxy mappings were returned by `netsh interface portproxy show all`.
This is a point-in-time observation and must be rechecked after Nginx/Tunnel
changes. No direct public-IP probe was performed.

## Scope boundary

Feature 004 was not modified. Feature 005 production work is not complete:
the stable API hostname, named Tunnel, NT Server deployment, and external
acceptance still require their authorized gates.
