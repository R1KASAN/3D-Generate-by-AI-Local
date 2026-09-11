from pathlib import Path

import yaml


def test_feature005_openapi_contract_parses_and_contains_job_operations() -> None:
    path = Path(__file__).resolve().parents[4] / "specs/005-nginx-mango74-deployment/contracts/openapi.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    paths = document["paths"]
    assert "/jobs" in paths
    assert "/jobs/{job_id}" in paths
    assert "/jobs/{job_id}/cancel" in paths
    assert "/jobs/{job_id}/model" in paths
    assert "/jobs/{job_id}/download" in paths

    refs = []
    for value in document["paths"].values():
        refs.extend(_refs(value))
    for ref in refs:
        assert ref.startswith("#/"), ref
        target = document
        for component in ref[2:].split("/"):
            target = target[component]
        assert target is not None


def _refs(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for child in value.values():
            yield from _refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _refs(child)
