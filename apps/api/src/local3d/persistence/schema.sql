PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    token_digest TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    progress_percent INTEGER CHECK (progress_percent IS NULL OR (progress_percent BETWEEN 0 AND 100)),
    progress_message TEXT,
    engine_job_id TEXT,
    workflow_revision TEXT NOT NULL,
    input_asset_id TEXT,
    output_asset_id TEXT,
    error_code TEXT,
    error_message TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (input_asset_id) REFERENCES job_assets (id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (output_asset_id) REFERENCES job_assets (id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS job_assets (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('input', 'intermediate', 'output')),
    relative_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES generation_jobs (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_job_assets_job_kind_output
    ON job_assets (job_id, kind)
    WHERE kind = 'output';

CREATE INDEX IF NOT EXISTS idx_job_assets_job_id ON job_assets (job_id);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    progress_percent INTEGER CHECK (progress_percent IS NULL OR (progress_percent BETWEEN 0 AND 100)),
    safe_message TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (job_id, sequence),
    FOREIGN KEY (job_id) REFERENCES generation_jobs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id_sequence
    ON job_events (job_id, sequence);
