# Feature 005 local real Nginx flow

Date: 2026-09-09

The controlled job was submitted from the repository root using the loopback
Nginx listener and the approved API Host header:

```text
POST http://127.0.0.1:8080/api/v1/jobs
Host: mango74-api.mangosgo.com
```

The request then traversed Nginx → FastAPI → ComfyUI → RTX 5070. No public
IP, inbound port, Cloudflare hostname, or Quick Tunnel was used.

Sanitized result:

```json
{
  "states": ["queued", "running", "completed"],
  "terminal_status": "completed",
  "elapsed_seconds": 182.67,
  "preview_http": 200,
  "download_http": 200,
  "result_bytes": 3736992,
  "preview_download_equal": true,
  "sha256": "71d1bb573648c8023aa7c4e796bd534bd8e1595ca65cef0c03fd3d1d620aa919",
  "glb_magic": "glTF"
}
```

The job identifier and access token are intentionally omitted. The output was
retrieved through both protected preview and download operations; the byte
streams matched and the GLB magic was valid. This evidence proves the local
Nginx path only; it does not prove named-Tunnel, NT Server, or off-campus
production acceptance.
