"""Create two real LAN jobs and run the T083 boundary verifier without exposing tokens.

Run this only from the separate LAN client. The job tokens exist only in the
child process environment used to invoke ``test_lan_boundary.py`` and are
never printed or written to evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID


def _multipart_body(path: Path) -> tuple[bytes, str]:
    boundary = f"----local3d-{secrets.token_hex(16)}"
    content = path.read_bytes()
    filename = path.name.replace('"', "")
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    return header + content + footer, f"multipart/form-data; boundary={boundary}"


def _create_job(entry_url: str, image_path: Path) -> tuple[str, str]:
    body, content_type = _multipart_body(image_path)
    request = urllib.request.Request(
        entry_url.rstrip("/") + "/api/v1/jobs",
        data=body,
        headers={"Content-Type": content_type, "Content-Length": str(len(body))},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 201:
                raise RuntimeError(f"job creation returned HTTP {response.status}")
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"job creation returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"job creation failed with {type(exc).__name__}") from None

    job_id = payload.get("job_id")
    token = payload.get("job_token")
    if not isinstance(job_id, str) or not isinstance(token, str):
        raise RuntimeError("job creation response omitted required opaque values")
    try:
        UUID(job_id)
    except ValueError:
        raise RuntimeError("job creation response contained an invalid job identifier") from None
    return job_id, token


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-host", required=True, help="server's private LAN IPv4 address")
    parser.add_argument("--entry-url", required=True, help="approved LAN web entry URL")
    parser.add_argument("--client-label", required=True, help="human-readable second-device label")
    parser.add_argument("--image", type=Path, required=True, help="valid JPEG or PNG fixture")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("evidence/lan/isolation-and-ports.md"),
    )
    args = parser.parse_args()
    if not args.image.is_file():
        parser.error(f"image does not exist: {args.image}")

    try:
        job_a, token_a = _create_job(args.entry_url, args.image)
        job_b, token_b = _create_job(args.entry_url, args.image)
    except RuntimeError as exc:
        print(f"BLOCKED: could not prepare two real LAN jobs ({exc})")
        return 1

    child_env = os.environ.copy()
    child_env.update(
        {
            "LAN_JOB_A": job_a,
            "LAN_TOKEN_A": token_a,
            "LAN_JOB_B": job_b,
            "LAN_TOKEN_B": token_b,
        }
    )
    verifier = Path(__file__).with_name("test_lan_boundary.py")
    result = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--server-host",
            args.server_host,
            "--entry-url",
            args.entry_url,
            "--client-label",
            args.client_label,
            "--evidence",
            str(args.evidence),
        ],
        env=child_env,
        check=False,
    )
    child_env["LAN_JOB_A"] = ""
    child_env["LAN_TOKEN_A"] = ""
    child_env["LAN_JOB_B"] = ""
    child_env["LAN_TOKEN_B"] = ""
    if result.returncode == 0:
        print(f"PASS: T083 boundary evidence written to {args.evidence}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
