from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.services.job_service import JobService
from local3d.main import create_app


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"


@pytest.mark.asyncio
@pytest.mark.parametrize("setting", ["max_pending_jobs", "max_submissions_per_minute", "max_identical_per_minute"])
async def test_admission_limits_are_atomic_and_survive_restart(tmp_path, setting):
    settings = Settings(storage_root=tmp_path, database_path=tmp_path / "jobs.db", **{setting: 2})
    first = JobService(settings)
    await first.startup()
    # Two service instances exercise the shared durable admission transaction.
    second = JobService(settings)
    await second.startup()

    async def submit(service):
        return await service.create_job(io.BytesIO(FIXTURE.read_bytes()), filename="image.png", content_type="image/png")

    outcomes = await asyncio.gather(*(submit(first if i % 2 else second) for i in range(5)), return_exceptions=True)
    accepted = [o for o in outcomes if not isinstance(o, BaseException)]
    rejected = [o for o in outcomes if isinstance(o, BaseException)]
    assert len(accepted) == 2
    assert len(rejected) == 3
    assert all(type(o).__name__ == "SubmissionLimitError" for o in rejected)
    assert len(await first.repository.list_nonterminal()) == 2
    for job, token in accepted:
        assert token
        asset = await first.repository.get_asset(job.input_asset_id)
        assert first.storage.resolve_asset(job.job_id, asset.relative_path).is_file()
    # Rejected uploads leave no job directories; existing accepted work survives.
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 2
    restarted = JobService(settings)
    await restarted.startup()
    with pytest.raises(Exception, match="Submission capacity temporarily unavailable"):
        await submit(restarted)


def test_five_submissions_are_accepted_and_excess_returns_safe_retry(tmp_path):
    settings = Settings(storage_root=tmp_path, database_path=tmp_path / 'jobs.db')
    with TestClient(create_app(settings)) as client:
        accepted = [client.post('/api/v1/jobs', files={'file': ('image.png', FIXTURE.read_bytes(), 'image/png')}) for _ in range(5)]
        limited = client.post('/api/v1/jobs', files={'file': ('image.png', FIXTURE.read_bytes(), 'image/png')})
        assert all(r.status_code == 201 for r in accepted)
        assert len({r.json()['job_id'] for r in accepted}) == 5
        assert limited.status_code == 429
        assert limited.headers['retry-after'] == '60'
        assert limited.headers['cache-control'] == 'no-store'
        assert limited.json() == {'error': {'code': 'submission_limited', 'message': 'Submission capacity temporarily unavailable'}}
        for response in accepted:
            job = response.json()
            status = client.get('/api/v1/jobs/' + job['job_id'], headers={'X-Job-Token': job['job_token']})
            assert status.status_code == 200
