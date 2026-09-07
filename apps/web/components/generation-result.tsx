"use client";

import { useEffect, useState } from "react";

import { cancelJob, downloadJob, Job, modelResponse, userFacingJobError } from "../lib/api/jobs";
import { useJobStatus } from "../lib/jobs/use-job-status";
import { JobStatusView } from "./job-status";
import { ModelViewer } from "./model-viewer";

interface GenerationResultProps {
  job: Job;
  jobToken: string;
}

export function GenerationResult({ job: initialJob, jobToken }: GenerationResultProps) {
  const { job, error: statusError, replaceJob } = useJobStatus(initialJob.job_id, jobToken, { initialJob });
  const [modelSrc, setModelSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    if (job?.status === "completed" && job.model_url) {
      void modelResponse(job.job_id, jobToken)
        .then((response) => response.blob())
        .then((blob) => {
          if (!active) return;
          objectUrl = URL.createObjectURL(blob);
          setModelSrc(objectUrl);
        })
        .catch((caught) => {
          if (active) setError(userFacingJobError(caught, "Model unavailable"));
        });
    }
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job?.status, job?.job_id, job?.model_url, jobToken]);

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
      setError(userFacingJobError(caught, "Download unavailable"));
    }
  }

  async function handleCancel() {
    if (!job || job.status !== "queued" || cancelling) return;
    setCancelling(true);
    setError(null);
    try {
      replaceJob(await cancelJob(job.job_id, jobToken));
    } catch (caught) {
      setError(userFacingJobError(caught, "Unable to cancel this queued job."));
    } finally {
      setCancelling(false);
    }
  }

  return (
    <section aria-label="Generation result">
      <JobStatusView job={job} error={statusError} />
      {error ? <p role="alert">{error}</p> : null}
      {job?.status === "queued" ? (
        <button type="button" onClick={() => void handleCancel()} disabled={cancelling}>
          {cancelling ? "Cancelling…" : "Cancel queued job"}
        </button>
      ) : null}
      {job?.status === "completed" && !job.model_url && !job.download_url ? (
        <p role="alert">Generation completed, but the result is unavailable.</p>
      ) : null}
      {modelSrc ? <ModelViewer src={modelSrc} /> : null}
      {job?.status === "completed" && job.download_url ? (
        <button type="button" onClick={() => void handleDownload()}>
          Download GLB
        </button>
      ) : null}
    </section>
  );
}
