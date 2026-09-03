from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from uuid import UUID


def main() -> int:
    parser = argparse.ArgumentParser(description="Read one Phase 10 reboot-probe job without exposing its token.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()

    job_id = str(UUID(args.job_id))
    database = args.database.resolve(strict=True)
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT status, error_code, attempt_count, updated_at FROM generation_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise SystemExit("reboot probe job was not found")
    print(
        json.dumps(
            {
                "job_id": job_id,
                "status": row[0],
                "error_code": row[1],
                "attempt_count": row[2],
                "updated_at": row[3],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
