"use client";

import { useEffect, useState } from "react";

import { downloadJob, Job, modelResponse } from "../lib/api/jobs";
import { useJobStatus } from "../lib/jobs/use-job-status";
import { JobStatusView } from "./job-status";
import { ModelViewer } from "./model-viewer";

interface GenerationResultProps {
  job: Job;
  jobToken: string;
}

export function GenerationResult({ job: initialJob, jobToken }: GenerationResultProps) {
  const { job, error: statusError } = useJobStatus(initialJob.job_id, jobToken, { initialJob });
  const [modelSrc, setModelSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    if (job?.status === "completed") {
      void modelResponse(job.job_id, jobToken)
        .then((response) => response.blob())
        .then((blob) => {
          if (!active) return;
          objectUrl = URL.createObjectURL(blob);
          setModelSrc(objectUrl);
        })
        .catch((caught) => {
          if (active) setError(caught instanceof Error ? caught.message : "Model unavailable");
        });
    }
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job?.status, job?.job_id, jobToken]);

  async function handleDownload() {
    try {
      if (!job) return;
      const response = await downloadJob(job.job_id, jobToken);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `${job.job_id}.glb`;
      anchor.click();
      URL.revokeObjectURL(objectUrl);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download unavailable");
    }
  }

  return (
    <section aria-label="Generation result">
      <JobStatusView job={job} error={statusError} />
      {error ? <p role="alert">{error}</p> : null}
      {modelSrc ? <ModelViewer src={modelSrc} /> : null}
      {job?.status === "completed" ? (
        <button type="button" onClick={() => void handleDownload()}>
          Download GLB
        </button>
      ) : null}
    </section>
  );
}
