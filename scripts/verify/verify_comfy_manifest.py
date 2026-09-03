#!/usr/bin/env python3
"""Verify a ComfyUI workflow manifest against a running ComfyUI instance.

Checks that pinned commits still match the installed repositories, that every
node class the manifest depends on is registered in the live `/object_info`,
and that any recorded workflow-JSON hashes still match on disk. Fails closed:
any mismatch, unreachable instance, or malformed manifest exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request


def git_head(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip()


def fetch_object_info(base_url: str, timeout: float) -> dict | None:
    try:
        with urllib.request.urlopen(f"{base_url}/object_info", timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--comfy-root",
        type=Path,
        required=True,
        help="Path to the ComfyUI installation whose commits are pinned.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    errors: list[str] = []

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest {args.manifest}: {exc}", file=sys.stderr)
        return 1

    # 1. ComfyUI commit pin
    expected_comfy = manifest.get("comfyui_commit")
    if not expected_comfy:
        errors.append("manifest is missing comfyui_commit")
    else:
        actual_comfy = git_head(args.comfy_root)
        if actual_comfy is None:
            errors.append(f"cannot read git HEAD at {args.comfy_root}")
        elif actual_comfy != expected_comfy:
            errors.append(
                f"ComfyUI commit mismatch: manifest {expected_comfy}, installed {actual_comfy}"
            )

    # 2. Custom node commit pins (entries with a null commit are project-owned
    #    additions that are intentionally not tracked against an upstream repo)
    for name, entry in (manifest.get("custom_nodes") or {}).items():
        expected = entry.get("commit") if isinstance(entry, dict) else entry
        if expected is None:
            continue
        node_path = args.comfy_root / "custom_nodes" / name
        actual = git_head(node_path)
        if actual is None:
            errors.append(f"cannot read git HEAD for custom node {name} at {node_path}")
        elif actual != expected:
            errors.append(
                f"custom node {name} commit mismatch: manifest {expected}, installed {actual}"
            )

    # 3. Live /object_info node-class registration
    object_info = fetch_object_info(args.base_url, args.timeout)
    if object_info is None:
        errors.append(f"cannot reach {args.base_url}/object_info")
    else:
        required = list(manifest.get("required_node_classes") or [])
        required += list((manifest.get("smoke_workflow") or {}).get("required_node_classes") or [])
        output_binding = manifest.get("output_binding") or {}
        output_class = output_binding.get("node_class")
        if output_class:
            required.append(output_class)
        if not required:
            errors.append("manifest declares no required node classes to verify")
        for node_class in sorted(set(required)):
            if node_class not in object_info:
                errors.append(f"node class not registered in running instance: {node_class}")

    # 4. Workflow JSON hashes, wherever the manifest has pinned them
    hash_sources = [("", manifest)]
    if isinstance(manifest.get("smoke_workflow"), dict):
        hash_sources.append(("smoke_workflow.", manifest["smoke_workflow"]))

    for prefix, section in hash_sources:
        for hash_field, path_field in (
            ("api_workflow_sha256", "api_workflow_path"),
            ("editable_workflow_sha256", "editable_workflow_path"),
        ):
            expected = section.get(hash_field)
            if not expected:
                continue
            relative = section.get(path_field)
            if not relative:
                errors.append(f"{prefix}{hash_field} is pinned but {prefix}{path_field} is missing")
                continue
            path = (args.manifest.parent / relative).resolve()
            if not path.is_file():
                errors.append(f"workflow file missing for {prefix}{hash_field}: {path}")
                continue
            actual = sha256_file(path)
            if actual != expected:
                errors.append(
                    f"{prefix}{hash_field} mismatch: manifest {expected}, file {actual}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: manifest {args.manifest} matches the running instance at {args.base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
