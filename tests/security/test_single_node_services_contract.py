from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = ROOT / "deploy/windows/services"


def test_service_templates_keep_all_application_ports_on_loopback() -> None:
    content = "\n".join(path.read_text(encoding="utf-8") for path in SERVICE_ROOT.glob("*.xml"))
    assert "127.0.0.1" in content
    assert "0.0.0.0" not in content
    assert "161.200.90.4" not in content


def test_caddy_service_is_declared_after_api_and_web_dependencies() -> None:
    caddy = SERVICE_ROOT / "caddy.xml"
    assert caddy.is_file()
    root = ET.parse(caddy).getroot()
    assert root.findtext("id") == "Local3D-Caddy"
    env = next(node for node in root.findall("env") if node.attrib.get("name") == "CADDY_LISTEN_ADDRESS")
    assert env.attrib.get("value") == "127.0.0.1:8080"
    assert root.findtext("depend") == "Local3D-Web"


def test_comfyui_service_whitelists_only_approved_generation_nodes() -> None:
    for name in ("comfyui.xml", "Local3D-ComfyUI.xml"):
        arguments = ET.parse(SERVICE_ROOT / name).getroot().findtext("arguments") or ""
        assert "--disable-all-custom-nodes" in arguments
        assert "ComfyUI-Hunyuan3DWrapper" in arguments
        assert "ComfyUI_essentials" in arguments
        assert "local3d_smoke_nodes.py" in arguments
