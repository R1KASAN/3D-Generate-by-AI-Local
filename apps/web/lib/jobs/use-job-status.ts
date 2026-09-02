"use client";

import { useEffect, useState } from "react";

import { getJob, Job, JobStatus } from "../api/jobs";

type FetchStatus = (jobId: string, jobToken: string) => Promise<Job>;

interface UseJobStatusOptions {
  initialJob?: Job;
  fetchStatus?: FetchStatus;
}

interface UseJobStatusResult {
  job: Job | undefined;
  error: string | null;
}

const TERMINAL: ReadonlySet<JobStatus> = new Set(["completed", "failed", "cancelled"]);

export function useJobStatus(
  jobId: string | null,
  jobToken: string | null,
  options: UseJobStatusOptions = {},
): UseJobStatusResult {
  const { initialJob, fetchStatus = getJob } = options;
  const [job, setJob] = useState<Job | undefined>(initialJob);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId || !jobToken) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    const poll = async () => {
      try {
        const latest = await fetchStatus(jobId, jobToken);
        if (!active) return;
        setJob(latest);
        setError(null);
        if (TERMINAL.has(latest.status)) return;
        const delay = attempts === 0 ? 2_000 : attempts === 1 ? 5_000 : 10_000;
        attempts += 1;
        timer = setTimeout(() => void poll(), delay);
      } catch {
        if (!active) return;
        setError("Status unavailable");
        const delay = attempts === 0 ? 2_000 : attempts === 1 ? 5_000 : 10_000;
        attempts += 1;
        timer = setTimeout(() => void poll(), delay);
      }
    };

    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [fetchStatus, jobId, jobToken]);

  return { job, error };
}
