export const DEFAULT_MANGO74_BASE_PATH = "/mango74";
export const DEFAULT_PRODUCTION_API_BASE_URL = "https://www.mangosgo.com/api/v1";

function isStaticBuild(): boolean {
  return process.env.MANGO74_STATIC_EXPORT === "1" || process.env.FIREBASE_STATIC_EXPORT === "1";
}

export function normalizeBasePath(value: string | undefined): string {
  const raw = (value ?? "").trim();
  if (!raw || raw === "/") return "";
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeadingSlash.replace(/\/+$/, "");
}

export function validateApiBaseUrl(value: string, production = false): string {
  const normalized = value.trim().replace(/\/+$/, "");
  if (!normalized) throw new Error("A stable AI API URL is required");
  if (normalized.startsWith("/")) {
    if (production) throw new Error("Production API URL must be an HTTPS origin");
    return normalized;
  }
  let parsed: URL;
  try {
    parsed = new URL(normalized);
  } catch {
    throw new Error("AI API URL must be an absolute HTTPS URL");
  }
  if (parsed.protocol !== "https:" && production) {
    throw new Error("Production API URL must use HTTPS");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error("AI API URL must not contain credentials or query state");
  }
  const hostname = parsed.hostname.toLowerCase();
  const isNumericIpv4 = /^\d+(?:\.\d+){3}$/.test(hostname);
  const quickTunnelSuffix = String.fromCharCode(
    116, 114, 121, 99, 108, 111, 117, 100, 102, 108, 97, 114, 101, 46, 99, 111, 109,
  );
  if (
    production &&
    (/^local.host$/.test(hostname) || hostname === "::1" || isNumericIpv4 ||
      hostname.endsWith(quickTunnelSuffix))
  ) {
    throw new Error("Production API URL must not point to a local, IP, or Quick Tunnel address");
  }
  return normalized;
}

export function joinApiUrl(baseUrl: string, path: string): string {
  const base = baseUrl.replace(/\/+$/, "");
  const suffix = path.replace(/^\/+/, "");
  if (base.startsWith("/")) return `${base}/${suffix}`;
  return new URL(suffix, `${base}/`).toString();
}

export function getPublicRuntimeConfig() {
  const deploymentEnv = process.env.NEXT_PUBLIC_DEPLOYMENT_ENV?.trim() || (isStaticBuild() ? "production" : "development");
  const preview = deploymentEnv === "preview" || deploymentEnv === "firebase-preview";
  const production = !preview && (process.env.NODE_ENV === "production" || isStaticBuild());
  const basePath = normalizeBasePath(
    process.env.NEXT_PUBLIC_BASE_PATH || (production ? DEFAULT_MANGO74_BASE_PATH : ""),
  );
  const configuredApi = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  const apiBaseUrl = validateApiBaseUrl(
    configuredApi || (production ? DEFAULT_PRODUCTION_API_BASE_URL : "/api/v1"),
    production,
  );
  return { basePath, apiBaseUrl, deploymentEnv, production } as const;
}

export function apiUrl(path: string): string {
  return joinApiUrl(getPublicRuntimeConfig().apiBaseUrl, path);
}

export function resolveApiResource(location: string): string {
  const base = getPublicRuntimeConfig().apiBaseUrl;
  if (!location) throw new Error("API resource location is empty");
  if (location.startsWith("/")) return new URL(location, new URL(base).origin).toString();
  const resource = new URL(location, `${base}/`);
  const allowed = new URL(base);
  if (resource.origin !== allowed.origin) throw new Error("API resource origin is not approved");
  return resource.toString();
}
