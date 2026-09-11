from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_feature005_preserves_single_notebook_and_tunnel_boundaries() -> None:
    spec = (ROOT / "specs/005-nginx-mango74-deployment/spec.md").read_text(encoding="utf-8")
    constitution = (ROOT / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    assert "mango74-api.mangosgo.com" in spec
    assert "127.0.0.1:8080" in spec
    plan = (ROOT / "specs/005-nginx-mango74-deployment/plan.md").read_text(encoding="utf-8")
    assert "127.0.0.1:8000" in plan
    assert "127.0.0.1:8188" in plan
    assert "single" in constitution.lower() and "notebook" in constitution.lower()


def test_production_frontend_does_not_embed_private_or_temporary_endpoints() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [*(ROOT / "apps/web/app").rglob("*.ts"), *(ROOT / "apps/web/components").rglob("*.ts")]
    )
    assert "trycloudflare.com" not in source
    assert "161.200.90.4" not in source
