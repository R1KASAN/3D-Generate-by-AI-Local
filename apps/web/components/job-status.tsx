"use client";

import { Job } from "../lib/api/jobs";

interface JobStatusProps {
  job: Job | undefined;
  error?: string | null;
}

export function JobStatusView({ job, error }: JobStatusProps) {
  if (!job) return <p role="status">Waiting for job status…</p>;

  const progress = job.progress_percent === null ? "Progress unavailable" : `Progress: ${job.progress_percent}%`;
  const queue = job.queue_position === null
    ? "Queue position unavailable"
    : `Queue position: ${job.queue_position}${job.queue_position_is_approximate ? " (approximate)" : ""}`;

  return (
    <section aria-label="Job status">
      <p role="status">Status: {job.status}</p>
      <p>{progress}</p>
      <p>{queue}</p>
      {job.progress_message ? <p>{job.progress_message}</p> : null}
      {job.error ? <p role="alert">{job.error.message}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
