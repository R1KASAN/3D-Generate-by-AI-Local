"""Fail-closed repository/evidence secret and temporary-host scanner.

The scanner reports file paths and rule names only; it never prints a matched
secret or user content. Binary files, model/output trees, caches, and virtual
environments are intentionally excluded from this source/evidence check.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".ps1", ".cmd", ".ts", ".tsx", ".css", ".html", ".xml"}
SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__", "output", "storage", "logs", "tmp"}
RULES = {
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "provider-token": re.compile(r"\b(?:sk|ghp|github_pat|xoxb|xoxp)-[A-Za-z0-9_-]{12,}\b"),
    "real-quick-host": re.compile(r"https://(?!(?:secret|sample|replace-with-current-random-host|random)\.)[a-z0-9-]+\.trycloudflare\.com\b", re.I),
}


def scan(root: Path, sentinels: list[str]) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name, pattern in RULES.items():
            if pattern.search(content):
                findings.append((str(path.relative_to(root)), name))
        for sentinel in sentinels:
            if sentinel and sentinel in content:
                findings.append((str(path.relative_to(root)), "supplied-sentinel"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--sentinel", action="append", default=[])
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.require_evidence and not (root / "evidence/feature-004/final-validation.md").exists():
        print("FAIL: required feature-004 evidence file is missing", file=sys.stderr)
        return 1
    findings = scan(root, args.sentinel)
    if findings:
        for path, rule in findings:
            print(f"FAIL: {rule} in {path}", file=sys.stderr)
        return 1
    print("PASS: no configured secret, supplied sentinel, or real Quick Tunnel host found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
