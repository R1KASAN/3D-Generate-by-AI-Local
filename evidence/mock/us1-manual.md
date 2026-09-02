# US1 Mock Flow Evidence

**Feature**: `001-local-3d-generation`
**Environment**: macOS, CPython 3.12.12, FastAPI TestClient, deterministic mock adapter
**Scope**: Local mock flow only; no Windows/NVIDIA/ComfyUI or public-network claim.

## Command

```text
uv run --project apps/api python - <<'PY'
... create_app(Settings(...)), upload valid-reference.png,
... poll status, fetch model and download, compare SHA-256 ...
PY
```

The exact command executed was:

```bash
uv run --project apps/api python - <<'PY'
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.main import create_app

fixture = Path('fixtures/inputs/valid-reference.png').read_bytes()
with TemporaryDirectory() as directory:
    root = Path(directory)
    settings = Settings(storage_root=root / 'storage', database_path=root / 'storage' / 'jobs.sqlite3')
    with TestClient(create_app(settings)) as client:
        created = client.post('/api/v1/jobs', files={'file': ('reference.png', fixture, 'image/png')})
        assert created.status_code == 201, created.text
        payload = created.json()
        job_id, token = payload['job_id'], payload['job_token']
        states = []
        for _ in range(3):
            response = client.get(f'/api/v1/jobs/{job_id}', headers={'X-Job-Token': token})
            assert response.status_code == 200, response.text
            states.append(response.json()['status'])
        model = client.get(f'/api/v1/jobs/{job_id}/model', headers={'X-Job-Token': token})
        download = client.get(f'/api/v1/jobs/{job_id}/download', headers={'X-Job-Token': token})
        assert model.status_code == 200, model.text
        assert download.status_code == 200, download.text
        model_sha = sha256(model.content).hexdigest()
        download_sha = sha256(download.content).hexdigest()
        assert model_sha == download_sha
        assert model.headers['cache-control'] == 'private, no-store'
        assert 'attachment' in download.headers['content-disposition'].lower()
        print({'status_after_submit': payload['status'], 'states': states, 'model_sha256': model_sha, 'download_sha256': download_sha, 'bytes': len(model.content)})
PY
```

## Observed result

```text
{'status_after_submit': 'queued', 'states': ['queued', 'processing', 'completed'], 'model_sha256': '5039d930f833b34e65ded1117e0d94a897eef954e87c2b2a3ea21426e53bb916', 'download_sha256': '5039d930f833b34e65ded1117e0d94a897eef954e87c2b2a3ea21426e53bb916', 'bytes': 1236}
```

The model and download responses were both HTTP 200. Preview response cache
policy was `private, no-store`; the download response included attachment
disposition. The two SHA-256 values match exactly.

## Verdict

`PASS` — one valid image reached queued → processing → completed in mock mode,
the published textured GLB was served, and preview/download bytes matched.
