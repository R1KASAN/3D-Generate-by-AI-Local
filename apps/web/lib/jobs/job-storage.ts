import { getPublicRuntimeConfig } from "../config/public-runtime";
import type { JobCreated } from "../api/jobs";

const STORAGE_PREFIX = "local3d:last-job:";

function key(apiBaseUrl = getPublicRuntimeConfig().apiBaseUrl): string {
  return `${STORAGE_PREFIX}${apiBaseUrl}`;
}

function isJobRecord(value: unknown): value is JobCreated {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<JobCreated>;
  return typeof candidate.job_id === "string" && typeof candidate.job_token === "string" &&
    typeof candidate.status === "string";
}

export function readStoredJob(
  storage: Storage = window.sessionStorage,
  apiBaseUrl?: string,
): JobCreated | null {
  try {
    const raw = storage.getItem(key(apiBaseUrl));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isJobRecord(parsed)) return null;
    if (parsed.expires_at && Date.parse(parsed.expires_at) <= Date.now()) {
      storage.removeItem(key(apiBaseUrl));
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function writeStoredJob(
  job: JobCreated,
  storage: Storage = window.sessionStorage,
  apiBaseUrl?: string,
): void {
  storage.setItem(key(apiBaseUrl), JSON.stringify(job));
}

export function clearStoredJob(
  storage: Storage = window.sessionStorage,
  apiBaseUrl?: string,
): void {
  storage.removeItem(key(apiBaseUrl));
}

export function jobStorageKey(apiBaseUrl?: string): string {
  return key(apiBaseUrl);
}
