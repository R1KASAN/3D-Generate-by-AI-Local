"""Record sanitized deployment facts; reject credentials and private artifacts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FORBIDDEN = re.compile(r"(?i)(token|password|secret|private.?key|credential|BEGIN [A-Z ]+PRIVATE KEY|trycloudflare\.com|127\.0\.0\.1|161\.200\.90\.4|\\uploads?\\|\\generated\\)")

def validate(value: str) -> str:
    if FORBIDDEN.search(value):
        raise ValueError("sensitive or private deployment value refused")
    return value

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-hash", required=True)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--rollback-id", required=True)
    parser.add_argument("--result", action="append", default=[])
    args = parser.parse_args()
    payload = {
        "release_hash": validate(args.release_hash),
        "change_id": validate(args.change_id),
        "rollback_id": validate(args.rollback_id),
        "results": [validate(value) for value in args.result],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
