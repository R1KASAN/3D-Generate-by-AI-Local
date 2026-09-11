"""Read-only route baseline capture for authorized Mangosgo verification."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path


def validate_target(base_url: str, paths: list[str]) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("baseline target must be HTTPS")
    if parsed.hostname not in {"www.mangosgo.com"}:
        raise ValueError("target host is not allowlisted")
    if any(not path.startswith("/mango74") and path != "/" for path in paths):
        raise ValueError("paths must be Mango74 or administrator-supplied root baseline")
    return base_url.rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", action="append", dest="paths", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = validate_target(args.base_url, args.paths)
    routes: list[dict[str, object]] = []
    for path in args.paths:
        request = urllib.request.Request(base + path, method="GET")
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
            routes.append({"path": path, "status": response.status, "headers": {k.lower(): v for k, v in response.headers.items() if k.lower() in {"location", "content-type", "cache-control", "referrer-policy", "x-content-type-options"}}, "sha256": hashlib.sha256(body).hexdigest(), "body_bytes": len(body)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"base_url": "<redacted>", "routes": routes}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
