# External-Network Full-Flow Acceptance Checklist (T093)

Run from a genuinely external vantage point (mobile data, home network, or
an off-campus VPS) — never from inside the university network. Automated
where noted by `scripts/verify/test_external_acceptance.py`.

## Prerequisites

- [ ] Public cutover complete (`docs/operations/public-cutover.md` Stage 3–4).
- [ ] `test_https_boundary.py` and `test_wireguard_reachability.py --mode positive` already PASS.
- [ ] A real fixture image (jpg/png) available on the external device.
- [ ] The operator can compute a sha256 of the corresponding GLB file on the
      GPU laptop's storage directory separately, to pass as
      `--expected-sha256`.

## Procedure

1. **Submit** — run:
   ```powershell
   python scripts/verify/test_external_acceptance.py --hostname <host> --image <fixture.jpg> --confirm-off-campus --expected-sha256 <sha256-from-laptop>
   ```
2. **Watch real queue/process state** — while the script polls, separately
   open `https://<host>/` in a browser and confirm the UI shows progress
   (queue position, then processing) rather than a static placeholder.
3. **Preview** — confirm the browser's 3D viewer actually renders the
   textured model with working rotate/zoom/pan/reset controls. The script
   only checks the preview endpoint returns 2xx; the interactive quality
   check is manual.
4. **Download** — confirm the script's `integrity-hash-match` check is
   PASS, not BLOCKED (BLOCKED means `--expected-sha256` was not supplied
   and the check proves nothing).

## Expected result

`evidence/public-deployment/full-flow.md` shows `Overall verdict: **PASS**`
with `create-job`, `job-completes`, `preview`, `download`, and
`integrity-hash-match` all PASS.

## If it fails

| Symptom | Likely cause |
|---|---|
| `create-job` fails | Caddy or the tunnel is down — check `test_wireguard_reachability.py --mode positive` on the laptop first. |
| `job-completes` times out | GPU/ComfyUI issue on the laptop, not a networking issue — check `Local3D-API`/`Local3D-ComfyUI` logs directly. |
| `download` succeeds but `integrity-hash-match` fails | Possible corruption in transit through the edge/tunnel, or a stale/wrong `--expected-sha256`. Re-verify the source file's hash on the laptop before assuming a transport bug. |
