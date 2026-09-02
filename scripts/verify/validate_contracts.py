#!/usr/bin/env python3
"""Validate the static API and ComfyUI workflow contract artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml


REQUIRED_PATHS = {
    "/jobs",
    "/jobs/{job_id}",
    "/jobs/{job_id}/model",
    "/jobs/{job_id}/download",
    "/health/live",
    "/health/ready",
}
REQUIRED_MANIFEST_MARKERS = (
    "workflow_id",
    "workflow_revision",
    "api_workflow_sha256",
    "required_node_classes",
    "output_binding",
    "licenses",
)


def validate_openapi(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"OpenAPI cannot be parsed: {exc}"]
    if not isinstance(document, dict):
        return ["OpenAPI document must be a mapping"]
    if document.get("openapi") != "3.1.0":
        errors.append("OpenAPI version must be 3.1.0")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        errors.append("OpenAPI paths must be a mapping")
    else:
        missing = sorted(REQUIRED_PATHS - set(paths))
        if missing:
            errors.append(f"OpenAPI missing paths: {', '.join(missing)}")
    schemes = document.get("components", {}).get("securitySchemes", {})
    job_token = schemes.get("JobToken", {}) if isinstance(schemes, dict) else {}
    if job_token.get("in") != "header" or job_token.get("name") != "X-Job-Token":
        errors.append("JobToken must be the X-Job-Token header scheme")
    return errors


def validate_manifest(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Workflow manifest cannot be read: {exc}"]
    errors = [f"Workflow manifest missing marker: {marker}" for marker in REQUIRED_MANIFEST_MARKERS if marker not in text]
    if "NEEDS CLARIFICATION" in text:
        errors.append("Workflow manifest contains an unresolved clarification")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("openapi", type=Path)
    parser.add_argument("workflow_manifest", type=Path)
    args = parser.parse_args()
    errors = validate_openapi(args.openapi) + validate_manifest(args.workflow_manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.openapi}")
    print(f"PASS: {args.workflow_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

