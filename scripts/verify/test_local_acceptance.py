"""Run one sanitized real generation through the loopback Caddy boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import struct
import tempfile
import time
import urllib.request
import zlib
from pathlib import Path
from urllib.parse import urlparse


def padded_png(source: Path, target_bytes: int) -> Path:
    data = source.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[-8:-4] != b"IEND":
        raise ValueError("source must be a complete PNG")
    payload_length = target_bytes - len(data) - 12
    if payload_length < 0:
        raise ValueError("target size is smaller than the source PNG")
    chunk_type = b"vpAg"  # private ancillary chunk ignored by image decoders
    payload = b"\0" * payload_length
    chunk = struct.pack(">I", payload_length) + chunk_type + payload
    chunk += struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    handle = tempfile.NamedTemporaryFile(prefix="local3d-near-limit-", suffix=".png", delete=False)
    with handle:
        handle.write(data[:-12] + chunk + data[-12:])
    result = Path(handle.name)
    if result.stat().st_size != target_bytes:
        result.unlink(missing_ok=True)
        raise RuntimeError("near-limit PNG size is incorrect")
    return result


def multipart(image: Path) -> tuple[bytes, str]:
    boundary = f"----local3d-{secrets.token_hex(16)}"
    header = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        'filename="near-limit.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode()
    return header + image.read_bytes() + f"\r\n--{boundary}--\r\n".encode(), boundary


def request_json(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"X-Job-Token": token, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def fetch_bytes(url: str, token: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"X-Job-Token": token})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.status, response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--target-bytes", type=int, default=10 * 1024 * 1024 - 1024)
    parser.add_argument("--max-wait-seconds", type=int, default=1800)
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.path.rstrip("/")) != (
        "http",
        "127.0.0.1",
        8080,
        "",
    ):
        parser.error("--base-url must be exactly the loopback Caddy origin http://127.0.0.1:8080")
    if not args.image.is_file():
        parser.error("--image must exist")

    padded = padded_png(args.image, args.target_bytes)
    states: list[str] = []
    try:
        body, boundary = multipart(padded)
        created_at = time.monotonic()
        create = urllib.request.Request(
            f"{args.base_url}/api/v1/jobs",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(create, timeout=60) as response:
            create_status = response.status
            accepted_seconds = time.monotonic() - created_at
            payload = json.loads(response.read())
        job_id = payload["job_id"]
        token = payload["job_token"]
        deadline = time.monotonic() + args.max_wait_seconds
        status = payload
        while time.monotonic() < deadline:
            public_state = status["status"]
            if not states or states[-1] != public_state:
                states.append(public_state)
            if public_state in {"completed", "failed", "cancelled"}:
                break
            time.sleep(2)
            status = request_json(f"{args.base_url}/api/v1/jobs/{job_id}", token)
        if status["status"] != "completed":
            raise RuntimeError(f"job ended as {status['status']}")
        preview_status, preview = fetch_bytes(f"{args.base_url}/api/v1/jobs/{job_id}/model", token)
        download_status, download = fetch_bytes(f"{args.base_url}/api/v1/jobs/{job_id}/download", token)
        digest = hashlib.sha256(preview).hexdigest()
        result = {
            "job_id": job_id,
            "input_bytes": padded.stat().st_size,
            "create_http": create_status,
            "accepted_seconds": round(accepted_seconds, 3),
            "states": states,
            "preview_http": preview_status,
            "download_http": download_status,
            "result_bytes": len(preview),
            "sha256": digest,
            "preview_download_equal": preview == download,
            "glb_magic": preview[:4].decode("ascii", errors="replace"),
        }
        print(json.dumps(result, indent=2))
        return 0 if preview == download and preview[:4] == b"glTF" else 1
    finally:
        padded.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
