export type JobStatus = "queued" | "processing" | "completed" | "failed" | "cancelled";

export interface SafeError {
  code: string;
  message: string;
}

export interface Job {
  job_id: string;
  status: JobStatus;
  progress_percent: number | null;
  progress_message: string | null;
  queue_position: number | null;
  queue_position_is_approximate: boolean;
  error: SafeError | null;
  model_url: string | null;
  download_url: string | null;
  created_at: string;
  expires_at: string;
}

export interface JobCreated extends Job {
  job_token: string;
}

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export class JobsApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "JobsApiError";
  }
}

async function expectJson<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  let body: { error?: { code?: string; message?: string } } = {};
  try {
    body = (await response.json()) as typeof body;
  } catch {
    // Keep a safe fallback when a proxy returns a non-JSON error.
  }
  throw new JobsApiError(
    response.status,
    body.error?.code ?? "request_failed",
    body.error?.message ?? "Request failed",
  );
}

export async function createJob(file: File, fetcher: Fetcher = fetch): Promise<JobCreated> {
  const body = new FormData();
  body.append("file", file, file.name);
  const response = await fetcher("/api/v1/jobs", { method: "POST", body });
  return expectJson<JobCreated>(response);
}

export async function getJob(
  jobId: string,
  jobToken: string,
  fetcher: Fetcher = fetch,
): Promise<Job> {
  const response = await fetcher(`/api/v1/jobs/${encodeURIComponent(jobId)}`, {
    headers: { "X-Job-Token": jobToken, Accept: "application/json" },
    cache: "no-store",
  });
  return expectJson<Job>(response);
}

export async function downloadJob(
  jobId: string,
  jobToken: string,
  fetcher: Fetcher = fetch,
): Promise<Response> {
  const response = await fetcher(`/api/v1/jobs/${encodeURIComponent(jobId)}/download`, {
    headers: { "X-Job-Token": jobToken },
    cache: "no-store",
  });
  if (!response.ok) await expectJson<never>(response);
  return response;
}

export async function modelResponse(
  jobId: string,
  jobToken: string,
  fetcher: Fetcher = fetch,
): Promise<Response> {
  const response = await fetcher(`/api/v1/jobs/${encodeURIComponent(jobId)}/model`, {
    headers: { "X-Job-Token": jobToken },
    cache: "no-store",
  });
  if (!response.ok) await expectJson<never>(response);
  return response;
}

export function modelUrl(jobId: string): string {
  return `/api/v1/jobs/${encodeURIComponent(jobId)}/model`;
}

export function downloadUrl(jobId: string): string {
  return `/api/v1/jobs/${encodeURIComponent(jobId)}/download`;
}
