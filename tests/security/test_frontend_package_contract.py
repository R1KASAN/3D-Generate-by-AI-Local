import json
import zipfile
from pathlib import Path

from scripts.verify.verify_frontend_package import _archive_files, create_archive, validate


def test_frontend_package_accepts_static_files() -> None:
    result = validate(
        [
            ("index.html", b"<html><script src=/_next/app.js></script></html>"),
            ("_next/app.js", b"console.log('ok')"),
            ("_next/app.css", b"body{}"),
        ]
    )
    assert result["valid"] is True


def test_frontend_package_rejects_runtime_and_internal_content() -> None:
    result = validate(
        [
            ("index.html", b"<html></html>"),
            ("storage/jobs.sqlite3", b"data"),
            ("private.env", b"TOKEN=secret"),
            ("_next/internal.js", b"http://127.0.0.1:8000"),
        ]
    )
    assert result["valid"] is False
    assert result["failures"]


def test_firebase_preview_mount_preserves_mango74_asset_boundary() -> None:
    config = json.loads(Path("firebase.json").read_text(encoding="utf-8"))
    redirects = config["hosting"]["redirects"]
    assert {item["source"]: item["destination"] for item in redirects}["/"] == "/mango74/"

    build_script = Path("scripts/windows/build_frontend_package.ps1").read_text(encoding="utf-8")
    assert "$DeploymentEnv -eq 'firebase-preview'" in build_script
    assert "Join-Path $outRoot 'mango74'" in build_script


def test_archive_creator_uses_posix_paths_and_linux_safe_permissions(tmp_path: Path) -> None:
    root = tmp_path / "out"
    (root / "_next" / "static").mkdir(parents=True)
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "_next" / "static" / "app.js").write_text("ok", encoding="utf-8")
    archive = tmp_path / "front-end.zip"

    create_archive(root, archive)

    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        assert {info.orig_filename for info in infos} == {
            "_next/static/app.js",
            "index.html",
        }
        assert all("\\" not in info.orig_filename for info in infos)
        assert all((info.external_attr >> 16) == 0o100644 for info in infos)
    assert validate(_archive_files(archive))["valid"] is True


def test_archive_validator_rejects_raw_windows_separators(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    member = "assets/app.js"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(member, b"ok")
        handle.writestr("index.html", b"<html></html>")
    data = archive.read_bytes().replace(member.encode(), b"assets\\app.js")
    archive.write_bytes(data)

    result = validate(_archive_files(archive))

    assert result["valid"] is False
    assert any("non-POSIX archive path" in failure for failure in result["failures"])


def test_build_script_uses_portable_archive_creator() -> None:
    build_script = Path("scripts/windows/build_frontend_package.ps1").read_text(encoding="utf-8")
    assert "--create-archive $OutputPath" in build_script
    assert "Compress-Archive" not in build_script
