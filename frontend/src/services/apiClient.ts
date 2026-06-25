import { environment } from "@/config/environment";
import { useAuthStore } from "@/store/authStore";
import { useTenantStore } from "@/store/tenantStore";

export class ApiClientError extends Error {
  status?: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status?: number, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export const API_BASE_URL = environment.apiBaseUrl;
const normalizedBaseUrl = API_BASE_URL.replace(/\/+$/, "");

let basePathname = "";
try {
  basePathname = new URL(normalizedBaseUrl || "/", "http://placeholder.local").pathname;
} catch {
  basePathname = normalizedBaseUrl || "/";
}

const cleanedBasePath = basePathname.replace(/\/+$/, "");
const baseHasFrontendSegment = /(^|\/)frontend(\/|$)/i.test(cleanedBasePath);

function ensureLeadingSlash(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

function withFrontendPrefix(path: string) {
  const normalizedPath = ensureLeadingSlash(path);
  if (baseHasFrontendSegment) return normalizedPath;
  if (normalizedPath === "/frontend" || normalizedPath.startsWith("/frontend/")) return normalizedPath;
  return `/frontend${normalizedPath}`;
}

function buildUrl(path: string) {
  const finalPath = withFrontendPrefix(path);
  if (!normalizedBaseUrl) return finalPath;
  return `${normalizedBaseUrl}${finalPath}`;
}

let refreshPromise: Promise<boolean> | null = null;

function buildHeaders(init?: RequestInit, tokenOverride?: string) {
  const { accessToken, user } = useAuthStore.getState();
  const tenant = useTenantStore.getState();
  const tenantId = tenant.activeTenantId ?? user?.tenantId;
  const companyId = tenant.activeCompanyId ?? user?.companyId;
  const headers = new Headers(init?.headers);

  if (!headers.has("Content-Type") && init?.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = tokenOverride ?? accessToken;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (tenantId) headers.set("X-Tenant-ID", tenantId);
  if (companyId) headers.set("X-Company-ID", companyId);
  headers.set("Accept", "application/json");
  return headers;
}

async function readError(response: Response) {
  try {
    const payload = await response.json() as { message?: string; detail?: string | { message?: string }; code?: string; details?: unknown };
    const detailMessage = typeof payload.detail === "string" ? payload.detail : payload.detail?.message;
    return { message: payload.message ?? detailMessage ?? (response.statusText || "Request failed"), code: payload.code ?? "API_ERROR", details: payload.details ?? payload.detail };
  } catch {
    return { message: response.statusText || "Request failed", code: "API_ERROR", details: undefined };
  }
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) return false;
    try {
      const response = await fetch(buildUrl("/auth/refresh"), { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ refreshToken }) });
      if (!response.ok) return false;
      const payload = await response.json() as { accessToken: string; refreshToken?: string };
      if (!payload.accessToken) return false;
      useAuthStore.getState().updateTokens(payload.accessToken, payload.refreshToken);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function request(path: string, init?: RequestInit) {
  return fetch(buildUrl(path), { credentials: "include", ...init, headers: buildHeaders(init) });
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response = await request(path, init);
  if (response.status === 401 && !path.includes("/auth/refresh") && await refreshAccessToken()) response = await request(path, init);

  if (!response.ok) {
    const error = await readError(response);
    if (response.status === 401) useAuthStore.getState().clearSession();
    const apiError = new ApiClientError(error.message, response.status, error.code, error.details);
    window.dispatchEvent(new CustomEvent("translatrix:api-error", { detail: apiError }));
    throw apiError;
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
  const contentLengthHeader = response.headers.get("Content-Length");

  if (contentLengthHeader === "0") return undefined as T;

  const rawBody = await response.text();
  if (!rawBody.trim()) return undefined as T;

  if (!contentType || contentType.includes("application/json")) {
    try {
      return JSON.parse(rawBody) as T;
    } catch (error) {
      const parseError = error instanceof Error ? error : new Error("Failed to parse JSON response");
      const apiError = new ApiClientError(parseError.message, response.status, "INVALID_JSON_RESPONSE", { body: rawBody });
      window.dispatchEvent(new CustomEvent("translatrix:api-error", { detail: apiError }));
      throw apiError;
    }
  }

  // Fallback: return raw text for non-JSON payloads.
  return rawBody as unknown as T;
}

export async function resolveApi<T>(path: string, _mockResolver: () => Promise<T>, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, init);
}

function resolveDownloadPath(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  if (normalizedBaseUrl && path.startsWith(normalizedBaseUrl)) return path;
  return buildUrl(path);
}

export async function apiDownload(path: string, fileName?: string): Promise<void> {
  const doFetch = () => fetch(resolveDownloadPath(path), { credentials: "include", headers: buildHeaders() });
  let response = await doFetch();
  if (response.status === 401 && await refreshAccessToken()) response = await doFetch();
  if (!response.ok) {
    const error = await readError(response);
    const apiError = new ApiClientError(error.message, response.status, error.code, error.details);
    window.dispatchEvent(new CustomEvent("translatrix:api-error", { detail: apiError }));
    throw apiError;
  }
  const blob = await response.blob();
  const contentDisposition = response.headers.get("Content-Disposition") ?? "";
  const match = contentDisposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
  const resolvedName = fileName ?? (match ? decodeURIComponent(match[1].replace(/"/g, "")) : "download");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = resolvedName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
