"use client";

import { FormEvent, useState } from "react";

import { createJob, JobCreated } from "../lib/api/jobs";

interface GenerationFormProps {
  onCreated: (job: JobCreated) => void;
}

export function GenerationForm({ onCreated }: GenerationFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a JPEG or PNG image first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createJob(file);
      onCreated(created);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Generation could not be started.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="3D generation form">
      <label htmlFor="reference-image">Reference image</label>
      <input
        id="reference-image"
        type="file"
        accept=".jpg,.jpeg,.png"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <button type="submit" disabled={!file || submitting}>
        {submitting ? "Submitting…" : "Generate 3D"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
    </form>
  );
}
