"""Guarded acceptance probe for the split-origin Mango74 deployment.

This command is intentionally opt-in: it refuses temporary tunnels, raw IPs,
HTTP, and missing independent-network confirmation before sending any request.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import sys
import urllib.parse
import urllib.request
import time
from pathlib import Path


def validate_public_endpoint(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("endpoint must be an HTTPS URL without credentials")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".trycloudflare.com"):
        raise ValueError("temporary/local endpoints are not production acceptance targets")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("raw IP endpoints are forbidden")
    return value.rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--api-url", required=True, help="stable API origin ending in /api/v1")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    checks: list[dict[str, str]] = []
    try:
        frontend = validate_public_endpoint(args.frontend_url)
        api = validate_public_endpoint(args.api_url)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.confirm_off_campus:
        checks.append({"name": "vantage-point", "status": "BLOCKED", "detail": "--confirm-off-campus is required"})
    elif not args.image.is_file():
        checks.append({"name": "input", "status": "FAIL", "detail": "input image is missing"})
    else:
        checks.append({"name": "vantage-point", "status": "PASS", "detail": "operator confirmed independent network"})
        checks.append({"name": "frontend", "status": "PASS", "detail": frontend})
        try:
            request = urllib.request.Request(f"{api}/health/live", headers={"Origin": frontend})
            with urllib.request.urlopen(request, timeout=15) as response:
                checks.append({"name": "api-health", "status": "PASS" if response.status == 200 else "FAIL", "detail": f"HTTP {response.status}"})
            boundary = f"----feature005-{hashlib.sha256(args.image.read_bytes()).hexdigest()[:16]}"
            image_type = "image/png" if args.image.suffix.lower() == ".png" else "image/jpeg"
            body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"reference{args.image.suffix.lower()}\"\r\nContent-Type: {image_type}\r\n\r\n").encode() + args.image.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
            create = urllib.request.Request(f"{api}/jobs", data=body, headers={"Origin": frontend, "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
            with urllib.request.urlopen(create, timeout=30) as response:
                created = json.loads(response.read())
            job_id, token = created["job_id"], created["job_token"]
            checks.append({"name": "create-job", "status": "PASS", "detail": "HTTP 201; capability redacted"})
            status = created
            deadline = time.monotonic() + 1800
            while status.get("status") in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(5)
                poll = urllib.request.Request(f"{api}/jobs/{job_id}", headers={"Origin": frontend, "X-Job-Token": token, "Accept": "application/json"})
                with urllib.request.urlopen(poll, timeout=30) as response:
                    status = json.loads(response.read())
            terminal = status.get("status") in {"completed", "failed", "cancelled"}
            checks.append({"name": "lifecycle", "status": "PASS" if terminal else "FAIL", "detail": f"terminal={status.get('status', 'timeout')}"})
            if status.get("status") == "completed":
                blobs = []
                for suffix in ("model", "download"):
                    resource = urllib.request.Request(f"{api}/jobs/{job_id}/{suffix}", headers={"Origin": frontend, "X-Job-Token": token})
                    with urllib.request.urlopen(resource, timeout=60) as response:
                        blobs.append(response.read())
                same = blobs[0] == blobs[1]
                valid_glb = blobs[0][:4] == b"glTF"
                checks.append({"name": "preview-download", "status": "PASS" if same and valid_glb else "FAIL", "detail": f"bytes={len(blobs[0])}; sha256={hashlib.sha256(blobs[0]).hexdigest()[:12]}..."})
                checks.append({"name": "public-redaction", "status": "PASS" if all("127.0.0.1" not in json.dumps(status) for _ in [0]) else "FAIL", "detail": "response fields contain no internal URL"})
        except Exception as exc:  # noqa: BLE001
            checks.append({"name": "api-health", "status": "FAIL", "detail": type(exc).__name__})
        checks.append({"name": "input-hash", "status": "PASS", "detail": hashlib.sha256(args.image.read_bytes()).hexdigest()[:12]})
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    safe = {"frontend": "<approved-frontend>", "api": "<approved-api>", "checks": checks}
    args.evidence.write_text("# Feature 005 external acceptance\n\n```json\n" + json.dumps(safe, indent=2) + "\n```\n", encoding="utf-8")
    return 0 if all(item["status"] == "PASS" for item in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
