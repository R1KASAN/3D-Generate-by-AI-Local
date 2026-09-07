from pathlib import Path

import pytest

from local3d.persistence.database import Database


@pytest.mark.parametrize(
    ("version", "expected"),
    [((3, 51, 3), "WAL"), ((3, 49, 1), "DELETE")],
)
def test_journal_mode_policy_is_version_gated(tmp_path: Path, version: tuple[int, int, int], expected: str) -> None:
    database = Database(tmp_path / "jobs.sqlite3", sqlite_version=version)
    assert database.journal_mode == expected


def test_negative_busy_timeout_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        Database(tmp_path / "jobs.sqlite3", busy_timeout_ms=-1)
