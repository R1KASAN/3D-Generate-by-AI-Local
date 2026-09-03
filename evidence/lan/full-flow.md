# LAN Full-Flow Evidence (T082)

- Date/time (UTC): 2026-09-03T18:41:16.266976+00:00
- Windows server: `LAPTOP-9PI3K9F7`; private LAN address `172.20.10.6`
- Second client: `เครื่องที่สอง` (owner-provided download from the `ADMIN` account)
- Approved entry path: `http://172.20.10.6:3000/`
- Checklist: [lan-acceptance.md](../../docs/operations/lan-acceptance.md)
- Boundary prerequisite: [isolation-and-ports.md](isolation-and-ports.md) (**PASS**)
- Web build containing the final viewer controls: `ee179cb` (`Improve viewer zoom controls`)

| Required observation | Observed evidence | Verdict |
|---|---|---|
| Second physical LAN client identified | T083 records a separate client as `เครื่องที่สอง`; the owner supplied the downloaded artifact from the `C:\Users\ADMIN\Downloads` account | **PASS** |
| Upload through approved LAN entry path | `3d-rendering-yeti.jpeg` uploaded through `http://172.20.10.6:3000/`; persisted as `image/jpeg` | **PASS** |
| queued/processing, refresh, and reconnect | Job `8cb6b67e-4fda-4350-a6ee-7bc2a1a0c638`: created `18:36:50.005767Z`, processing `18:39:12.034482Z`; API log records repeated status/model reads without resubmission | **PASS** |
| Textured preview rotate/zoom/pan/reset | Owner-provided completed-page screenshot shows the textured preview and controls. Final build provides `Rotate`, `Zoom in`, `Zoom out`, and `Reset camera`; OrbitControls keeps drag rotate, wheel/pinch zoom, and right-drag/two-finger pan enabled. Web unit tests verify all four button actions and the absence of the redundant Pan button | **PASS** |
| Byte-identical download and GLB hash | Job completed `18:41:16.266976Z`; server output is `4,088,380` bytes, SHA-256 `7d013674048ec81ad15193f0c1eb61428f70a9d4b19e985844262bb9d5241fd2`. Owner-reported download `C:\Users\ADMIN\Downloads\8cb6b67e-4fda-4350-a6ee-7bc2a1a0c638.glb` has the identical size/hash | **PASS** |
| Redacted screenshots and browser/network proof | T083 evidence is retained; the owner-provided completed-page screenshot is the UI evidence for this flow. Tokens and private traces are omitted | **PASS** |

## Server record

The local server database and output were independently checked for the same
Job ID. The persisted output asset has `content_type=model/gltf-binary`,
`size_bytes=4088380`, and the SHA-256 above. The API service log records `200`
responses for the job, model preview, and download endpoints. Running
`scripts/verify/validate_glb.py` with mesh, UV, material, and texture
requirements also returned `PASS` for the same output.

**Verdict: PASS.**
