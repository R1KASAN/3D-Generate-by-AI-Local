"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getJob, Job, JobStatus, userFacingJobError } from "../api/jobs";

type FetchStatus = (jobId: string, jobToken: string, signal?: AbortSignal) => Promise<Job>;

interface UseJobStatusOptions {
  initialJob?: Job;
  fetchStatus?: FetchStatus;
}

interface UseJobStatusResult {
  job: Job | undefined;
  error: string | null;
  replaceJob: (job: Job) => void;
}

const defaultFetchStatus: FetchStatus = (id, token, signal) => getJob(id, token, fetch, signal);

const TERMINAL: ReadonlySet<JobStatus> = new Set(["completed", "failed", "cancelled"]);

export function useJobStatus(
  jobId: string | null,
  jobToken: string | null,
  options: UseJobStatusOptions = {},
): UseJobStatusResult {
  const { initialJob, fetchStatus = defaultFetchStatus } = options;
  const [job, setJob] = useState<Job | undefined>(initialJob);
  const [error, setError] = useState<string | null>(null);
  const lastConfirmedJob = useRef<Job | undefined>(initialJob);
  const replaceJob = useCallback((latest: Job) => {
    lastConfirmedJob.current = latest;
    setJob(latest);
    setError(null);
  }, []);

  useEffect(() => {
    if (!jobId || !jobToken) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    const poll = async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 1_500);
      try {
        const latest = await fetchStatus(jobId, jobToken, controller.signal);
        if (!active) return;
        lastConfirmedJob.current = latest;
        setJob(latest);
        setError(null);
        if (TERMINAL.has(latest.status)) return;
        const delay = attempts === 0 ? 2_000 : attempts === 1 ? 5_000 : 10_000;
        attempts += 1;
        timer = setTimeout(() => void poll(), delay);
      } catch (caught) {
        if (!active) return;
        if (lastConfirmedJob.current) setJob(lastConfirmedJob.current);
        setError(userFacingJobError(caught, "Status unavailable; retrying."));
        const delay = attempts === 0 ? 2_000 : attempts === 1 ? 5_000 : 10_000;
        attempts += 1;
        timer = setTimeout(() => void poll(), delay);
      } finally {
        window.clearTimeout(timeout);
      }
    };

    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [fetchStatus, jobId, jobToken]);

  return { job, error, replaceJob };
}
