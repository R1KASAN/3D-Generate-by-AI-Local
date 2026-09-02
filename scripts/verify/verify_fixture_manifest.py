#!/usr/bin/env python3
"""Verify fixture sizes and SHA-256 values recorded in an inputs README."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys


ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{64})`\s*\|")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    rows = [ROW.match(line) for line in args.manifest.read_text(encoding="utf-8").splitlines()]
    entries = [row for row in rows if row]
    if not entries:
        errors.append("manifest contains no fixture rows")
    for row in entries:
        assert row is not None
        relative, expected_size, expected_sha = row.groups()
        path = (args.manifest.parent / relative).resolve()
        if not path.is_file():
            errors.append(f"missing fixture: {relative}")
            continue
        data = path.read_bytes()
        actual_size = len(data)
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_size != int(expected_size):
            errors.append(f"size mismatch {relative}: expected {expected_size}, got {actual_size}")
        if actual_sha != expected_sha:
            errors.append(f"sha mismatch {relative}: expected {expected_sha}, got {actual_sha}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: verified {len(entries)} fixtures from {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

