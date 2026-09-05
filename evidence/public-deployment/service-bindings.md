# Service Binding Audit — Feature 003

**Feature**: `003-outbound-tunnel-entry` | **Task**: T013 | **Checked**: 2026-09-06

Confirms `deploy/windows/services/api.xml` and `deploy/windows/services/comfyui.xml` bind loopback only and declare no dependency on the WireGuard tunnel service, so the LAN-independence fix in T009/T010 does not need to touch them.

## api.xml (`Local3D-API`)

| Property | Value |
|---|---|
| Listen address | `127.0.0.1:8000` (`-HostAddress 127.0.0.1`, `API_HOST=127.0.0.1`) |
| ComfyUI target | `http://127.0.0.1:8188` — loopback |
| WireGuard dependency | None. Only `<depend>Local3D-ComfyUI</depend>` |
| Reference to `10.10.0.2` or `WireGuardTunnel$upstream` | None |

## comfyui.xml (`Local3D-ComfyUI`)

| Property | Value |
|---|---|
| Listen address | `127.0.0.1:8188` (`--listen 127.0.0.1`) |
| WireGuard dependency | None declared |
| Reference to `10.10.0.2` or `WireGuardTunnel$upstream` | None |

## Conclusion

Both services were already correctly isolated before this feature's changes. The deadlock fixed in T009/T010 was specific to `web.xml`, which bound the tunnel address directly and depended on the WireGuard service — neither `api.xml` nor `comfyui.xml` had that defect. `tests/security/test_compute_link_startup.py::test_api_and_comfy_services_have_no_wireguard_dependency` asserts this programmatically going forward.

**Verdict: PASS.** No changes required to either file.
