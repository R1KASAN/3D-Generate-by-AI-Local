"""Verify the LAN-only workflow survives an unavailable private binding
and an unreachable approved origin (feature-003 T017, SC-006d/SC-016).

This is the acceptance test for the deadlock fix in
scripts/windows/start_web_service.ps1 and deploy/windows/services/web.xml:
feature 002 bound the web service to the WireGuard tunnel address and made
it depend on the WireGuard service, so a private-binding failure took the
whole LAN-only workflow down with it. Feature 003 requires the opposite -
the application starts and serves the LAN regardless of the private
binding's state (FR-023a, FR-023d, FR-037).

Run ON THE GPU LAPTOP with WireGuard deliberately stopped and the approved
origin unreachable (--confirm-binding-down attests this was actually done;
this script cannot safely stop WireGuard itself). It performs the full
upload -> status -> preview -> download journey against the LAN address,
and separately confirms the private-binding address is genuinely absent -
a positive LAN result while the tunnel happens to still be up would not
prove independence at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402

PRIVATE_BINDING_ADDRESS = "10.10.0.2"


def _multipart_body(path: Path) -> tuple[bytes, str]:
    boundary = f"----local3d-{secrets.token_hex(16)}"
    content = path.read_bytes()
    filename = path.name.replace('"', "")
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    image_content_type = content_types[path.suffix.lower()]
    header = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {image_content_type}\r\n\r\n").encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    return header + content + footer, f"multipart/form-data; boundary={boundary}"


def _binding_address_absent() -> Check:
    """The tunnel address must genuinely not be assigned right now - proof
    the test is actually exercising the no-binding case, not accidentally
    succeeding because the tunnel was still up."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        # A UDP "connect" on a loopback-style probe does not require the
        # address to be reachable; we only need to know whether the local
        # stack considers it a bindable local address right now.
        try:
            sock.bind((PRIVATE_BINDING_ADDRESS, 0))
            # If bind succeeds, the address IS assigned locally - the
            # binding is up, which invalidates this test run.
            return Check(
                "binding-genuinely-down",
                f"{PRIVATE_BINDING_ADDRESS} is still assigned to a local interface",
                "private binding address absent for this test to be meaningful",
                "FAIL",
            )
        except OSError:
            return Check(
                "binding-genuinely-down",
                f"{PRIVATE_BINDING_ADDRESS} is not assigned locally",
                "private binding address absent",
                "PASS",
            )
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lan-base-url", required=True, help="e.g. http://192.168.1.50:3000")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--confirm-binding-down", action="store_true", help="operator attests WireGuard is stopped and the approved origin is unreachable")
    parser.add_argument("--max-wait-seconds", type=int, default=600)
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/lan-independence.md"))
    args = parser.parse_args()
    base = args.lan_base_url.rstrip("/")

    if not args.confirm_binding_down:
        checks = [Check("attestation", "--confirm-binding-down was not supplied", "operator attests WireGuard stopped and origin unreachable", "BLOCKED")]
        write_evidence(args.evidence, "LAN Independence Evidence", "T017", [f"- LAN base URL: {base}"], checks, "BLOCKED")
        print(f"BLOCKED: LAN-independence evidence written to {args.evidence}")
        return 1
    if not args.image.is_file():
        parser.error(f"image does not exist: {args.image}")

    checks = [Check("attestation", "operator attested WireGuard stopped and origin unreachable", "attested", "PASS")]
    checks.append(_binding_address_absent())

    try:
        body, content_type = _multipart_body(args.image)
        request = urllib.request.Request(f"{base}/api/v1/jobs", data=body, headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        job_id = payload["job_id"]
        token = payload["job_token"]
        checks.append(Check("create-job-on-lan", "HTTP 201, job created", "job accepted over the LAN address alone", "PASS"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("create-job-on-lan", f"failed with {type(exc).__name__}", "job accepted over the LAN address alone", "FAIL"))
        verdict = overall_verdict(checks)
        write_evidence(args.evidence, "LAN Independence Evidence", "T017", [f"- LAN base URL: {base}"], checks, verdict)
        print(f"{verdict}: LAN-independence evidence written to {args.evidence}")
        return 1

    deadline = time.monotonic() + args.max_wait_seconds
    status = None
    while time.monotonic() < deadline:
        request = urllib.request.Request(f"{base}/api/v1/jobs/{job_id}", headers={"X-Job-Token": token})
        with urllib.request.urlopen(request, timeout=15) as response:
            status = json.loads(response.read())
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(5)
    completed = bool(status) and status.get("status") == "completed"
    checks.append(Check("job-completes-on-lan", f"final status={status.get('status') if status else 'timeout'}", "status reaches completed without the private binding", "PASS" if completed else "FAIL"))

    if completed:
        try:
            request = urllib.request.Request(f"{base}/api/v1/jobs/{job_id}/model", headers={"X-Job-Token": token})
            with urllib.request.urlopen(request, timeout=60) as response:
                preview_ok = response.status == 200
            checks.append(Check("preview-on-lan", f"HTTP {response.status if preview_ok else 'error'}", "2xx GLB preview over the LAN", "PASS" if preview_ok else "FAIL"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("preview-on-lan", f"failed with {type(exc).__name__}", "2xx GLB preview over the LAN", "FAIL"))

        try:
            request = urllib.request.Request(f"{base}/api/v1/jobs/{job_id}/download", headers={"X-Job-Token": token})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            checks.append(Check("download-on-lan", f"{len(data)} bytes, sha256={hashlib.sha256(data).hexdigest()[:12]}...", "downloads successfully over the LAN", "PASS" if len(data) > 1024 else "FAIL"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("download-on-lan", f"failed with {type(exc).__name__}", "downloads successfully over the LAN", "FAIL"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "LAN Independence Evidence",
        "T017",
        [f"- LAN base URL: {base}"],
        checks,
        verdict,
        footnote="Proves SC-006d/SC-016: the LAN-only workflow does not depend on the private binding or the approved origin being reachable.",
    )
    print(f"{verdict}: LAN-independence evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
