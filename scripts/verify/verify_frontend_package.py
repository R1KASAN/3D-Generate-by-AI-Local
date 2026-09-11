"""Validate a Mango74 static frontend tree or archive without executing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


ALLOWED_SUFFIXES = {
    ".css", ".gif", ".html", ".ico", ".jpeg", ".jpg", ".js", ".json", ".map",
    ".png", ".svg", ".txt", ".webp", ".woff", ".woff2", ".xml",
}
FORBIDDEN_PATH_PARTS = {
    ".env", ".git", "__pycache__", "comfyui", "model", "models", "storage",
    "uploads", "generated", "workflow", "workflows", "credentials", "secret",
}
FORBIDDEN_CONTENT = re.compile(
    rb"(?:127\.0\.0\.1|161\.200\.90\.4|trycloudflare\.com|"
    rb"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)",
)


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path.relative_to(root).as_posix(), path.read_bytes()


def _archive_files(archive: Path):
    with zipfile.ZipFile(archive) as handle:
        for info in sorted(handle.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            # orig_filename preserves the raw ZIP member name. Do not silently
            # normalize Windows separators: they produce unsafe/unusable
            # directory permissions with some Linux unzip implementations.
            yield info.orig_filename, handle.read(info)


def create_archive(root: Path, archive: Path) -> None:
    """Create a deterministic ZIP with POSIX paths and Linux-safe modes."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as handle:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            name = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            handle.writestr(info, path.read_bytes(), compresslevel=9)


def validate(files) -> dict[str, object]:
    entries = []
    failures = []
    for name, content in files:
        if "\\" in name:
            failures.append(f"non-POSIX archive path: {name}")
        normalized = name.lstrip("./")
        posix_path = PurePosixPath(normalized)
        parts = set(posix_path.parts)
        if normalized.startswith("/") or ".." in posix_path.parts:
            failures.append(f"unsafe path: {name}")
        if parts & FORBIDDEN_PATH_PARTS:
            failures.append(f"forbidden path: {name}")
        suffix = posix_path.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            failures.append(f"non-static file: {name}")
        if FORBIDDEN_CONTENT.search(content):
            failures.append(f"forbidden content: {name}")
        entries.append({"path": normalized, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})

    if not entries:
        failures.append("package is empty")
    if not any(entry["path"].endswith(".html") for entry in entries):
        failures.append("package has no HTML entry point")
    return {"valid": not failures, "files": entries, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--root", type=Path)
    group.add_argument("--archive", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--create-archive", type=Path)
    args = parser.parse_args()
    if args.create_archive and not args.root:
        parser.error("--create-archive requires --root")
    if args.root:
        result = validate(_iter_files(args.root))
        if result["valid"] and args.create_archive:
            create_archive(args.root, args.create_archive)
    else:
        result = validate(_archive_files(args.archive))
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
