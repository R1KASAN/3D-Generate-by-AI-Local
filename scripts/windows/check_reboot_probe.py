from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from uuid import UUID


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read sanitized reboot-probe state without exposing tokens or engine handles."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--job-id", action="append", required=True)
    args = parser.parse_args()

    job_ids = [str(UUID(value)) for value in args.job_id]
    database = args.database.resolve(strict=True)
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        rows = []
        for job_id in job_ids:
            row = connection.execute(
                "SELECT status, error_code, attempt_count, updated_at "
                "FROM generation_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise SystemExit(f"reboot probe job was not found: {job_id}")
            event_count = connection.execute(
                "SELECT COUNT(*) FROM job_events WHERE job_id = ?", (job_id,)
            ).fetchone()[0]
            rows.append(
                {
                    "job_id": job_id,
                    "status": row[0],
                    "error_code": row[1],
                    "attempt_count": row[2],
                    "updated_at": row[3],
                    "event_count": event_count,
                }
            )
    finally:
        connection.close()

    print(json.dumps({"jobs": rows}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
