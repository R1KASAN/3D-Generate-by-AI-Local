"""Compare sanitized route baselines while ignoring documented dynamic fields."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(before: dict, after: dict) -> list[str]:
    differences: list[str] = []
    old = {item["path"]: item for item in before.get("routes", [])}
    new = {item["path"]: item for item in after.get("routes", [])}
    for path in sorted(set(old) | set(new)):
        if path not in old or path not in new:
            differences.append(f"route set changed: {path}")
            continue
        for field in ("status", "sha256", "headers"):
            if old[path].get(field) != new[path].get(field):
                differences.append(f"{path}: {field} changed")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    differences = compare(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    print(json.dumps({"differences": differences, "pass": not differences}, indent=2))
    return 0 if not differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
