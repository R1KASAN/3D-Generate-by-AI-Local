"""Full external generation flow against the public endpoint (T094).

Uploads a real image to the public hostname, polls status with the
returned X-Job-Token until the job completes, downloads the result, and
verifies its integrity. Must be run from outside the university network.

If --expected-sha256 is supplied (computed separately by the operator from
the file on the GPU laptop's storage directory), the downloaded GLB's hash
is compared against it - this is the strongest available proof that what
the external user received is bit-for-bit the file the laptop actually
generated, not a truncated or corrupted transfer through the edge/tunnel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402


def _multipart_body(path: Path) -> tuple[bytes, str]:
    boundary = f"----local3d-{secrets.token_hex(16)}"
    content = path.read_bytes()
    filename = path.name.replace('"', "")
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    image_content_type = content_types[path.suffix.lower()]
    header = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {image_content_type}\r\n\r\n").encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    return header + content + footer, f"multipart/form-data; boundary={boundary}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--max-wait-seconds", type=int, default=1800)
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/full-flow.md"))
    args = parser.parse_args()
    base = f"https://{args.hostname}"

    if not args.confirm_off_campus:
        checks = [Check("vantage-point", "--confirm-off-campus was not supplied", "run from outside the university network", "BLOCKED")]
        write_evidence(args.evidence, "External Acceptance Flow Evidence", "T094", [f"- Hostname: {args.hostname}"], checks, "BLOCKED")
        print(f"BLOCKED: acceptance evidence written to {args.evidence}")
        return 1
    if not args.image.is_file():
        parser.error(f"image does not exist: {args.image}")

    checks = [Check("vantage-point", "operator attested off-campus", "run from outside the university network", "PASS")]

    # --- Create job ---
    try:
        body, content_type = _multipart_body(args.image)
        request = urllib.request.Request(f"{base}/api/v1/jobs", data=body, headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        job_id = payload["job_id"]
        token = payload["job_token"]
        checks.append(Check("create-job", "HTTP 201, job created", "job accepted", "PASS"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("create-job", f"failed with {type(exc).__name__}", "job accepted", "FAIL"))
        write_evidence(args.evidence, "External Acceptance Flow Evidence", "T094", [f"- Hostname: {args.hostname}"], checks, "FAIL")
        print(f"FAIL: acceptance evidence written to {args.evidence}")
        return 1

    # --- Poll status ---
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
    checks.append(Check("job-completes", f"final status={status.get('status') if status else 'timeout'}", "status reaches completed", "PASS" if completed else "FAIL"))
    if not completed:
        write_evidence(args.evidence, "External Acceptance Flow Evidence", "T094", [f"- Hostname: {args.hostname}"], checks, "FAIL")
        print(f"FAIL: acceptance evidence written to {args.evidence}")
        return 1

    # --- Preview ---
    try:
        request = urllib.request.Request(f"{base}/api/v1/jobs/{job_id}/model", headers={"X-Job-Token": token})
        with urllib.request.urlopen(request, timeout=60) as response:
            preview_ok = response.status == 200
        checks.append(Check("preview", f"HTTP {response.status if preview_ok else 'error'}", "2xx GLB preview", "PASS" if preview_ok else "FAIL"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("preview", f"failed with {type(exc).__name__}", "2xx GLB preview", "FAIL"))

    # --- Download + integrity ---
    try:
        request = urllib.request.Request(f"{base}/api/v1/jobs/{job_id}/download", headers={"X-Job-Token": token})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        digest = hashlib.sha256(data).hexdigest()
        checks.append(Check("download", f"{len(data)} bytes, sha256={digest[:12]}...", "downloads successfully with non-trivial size", "PASS" if len(data) > 1024 else "FAIL"))
        if args.expected_sha256:
            match = digest == args.expected_sha256.strip().lower()
            checks.append(Check("integrity-hash-match", f"sha256={digest[:12]}...", f"matches expected sha256={args.expected_sha256[:12]}...", "PASS" if match else "FAIL"))
        else:
            checks.append(Check("integrity-hash-match", "--expected-sha256 not supplied", "downloaded GLB hash matches the laptop's source file", "BLOCKED"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("download", f"failed with {type(exc).__name__}", "downloads successfully", "FAIL"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "External Acceptance Flow Evidence",
        "T094",
        [f"- Hostname: {args.hostname}"],
        checks,
        verdict,
        footnote="Compute --expected-sha256 on the laptop's storage directory separately (never transmit the token used to fetch it alongside the hash).",
    )
    print(f"{verdict}: acceptance evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
