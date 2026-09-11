"use client";

import { useEffect, useState } from "react";

import { GenerationForm } from "../components/generation-form";
import { GenerationResult } from "../components/generation-result";
import { JobCreated } from "../lib/api/jobs";
import { getPublicRuntimeConfig } from "../lib/config/public-runtime";
import { readStoredJob, writeStoredJob } from "../lib/jobs/job-storage";

export default function HomePage() {
  const [job, setJob] = useState<JobCreated | null>(null);
  const runtime = getPublicRuntimeConfig();

  useEffect(() => {
    try {
      const restored = readStoredJob();
      if (restored) {
        window.setTimeout(() => setJob(restored), 0);
      }
    } catch {
      // Ignore malformed browser state and allow a fresh submission.
    }
  }, []);

  useEffect(() => {
    if (job) writeStoredJob(job);
  }, [job]);

  function handleCreated(created: JobCreated) {
    setJob(created);
    writeStoredJob(created);
  }

  return (
    <main>
      <h1>Local 3D Generator</h1>
      <aside role="note" aria-label={runtime.production ? "Production service notice" : "Test service notice"}>
        {runtime.production
          ? "Production AI service. Keep your job link private; the job token is capability-based access."
          : runtime.deploymentEnv === "preview" || runtime.deploymentEnv === "firebase-preview"
            ? "Firebase preview. AI access is enabled only when the API administrator explicitly allows this origin."
            : "Temporary non-production test service. The test URL is public and is not authentication."}
      </aside>
      <p>Upload one reference image to generate a textured GLB.</p>
      <GenerationForm onCreated={handleCreated} />
      {job ? <GenerationResult job={job} jobToken={job.job_token} /> : null}
    </main>
  );
}
