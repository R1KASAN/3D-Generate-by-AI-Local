"use client";

import { useEffect, useState } from "react";

import { GenerationForm } from "../components/generation-form";
import { GenerationResult } from "../components/generation-result";
import { JobCreated } from "../lib/api/jobs";

const JOB_STORAGE_KEY = "local3d:last-job";

export default function HomePage() {
  const [job, setJob] = useState<JobCreated | null>(null);

  useEffect(() => {
    try {
      const stored = window.sessionStorage.getItem(JOB_STORAGE_KEY);
      if (stored) {
        const restored = JSON.parse(stored) as JobCreated;
        window.setTimeout(() => setJob(restored), 0);
      }
    } catch {
      // Ignore malformed browser state and allow a fresh submission.
    }
  }, []);

  useEffect(() => {
    if (job) window.sessionStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(job));
  }, [job]);

  function handleCreated(created: JobCreated) {
    setJob(created);
    window.sessionStorage.setItem(JOB_STORAGE_KEY, JSON.stringify(created));
  }

  return (
    <main>
      <h1>Local 3D Generator</h1>
      <p>Upload one reference image to generate a textured GLB.</p>
      <GenerationForm onCreated={handleCreated} />
      {job ? <GenerationResult job={job} jobToken={job.job_token} /> : null}
    </main>
  );
}
