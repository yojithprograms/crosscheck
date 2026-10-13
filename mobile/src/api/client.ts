import { useAppStore } from "@/state/store";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "";

const DEFAULT_TIMEOUT_MS = 20_000;
const LONG_TIMEOUT_MS = 60_000; // /health, POST /reports, and the first request after launch (a sleeping host)

/** An error from the server, or from trying to reach it. `code` matches the server's error codes. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

type FetchOptions = {
  method?: "GET" | "POST" | "DELETE";
  json?: unknown;
  form?: FormData;
  timeoutMs?: number;
};

let firstRequestDone = false;

/**
 * Calls the CrossCheck API. Adds the base URL and the random X-Install-Id header, applies a timeout,
 * and turns the server's {detail: {code, message}} errors into ApiError.
 */
export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = "GET", json, form } = options;
  const timeoutMs =
    options.timeoutMs ?? (!firstRequestDone || path === "/health" ? LONG_TIMEOUT_MS : DEFAULT_TIMEOUT_MS);

  const headers: Record<string, string> = { "X-Install-Id": useAppStore.getState().installId };
  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form; // fetch sets the multipart boundary itself
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { method, headers, body, signal: controller.signal });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "AbortError";
    throw new ApiError(timedOut ? "TIMEOUT" : "NETWORK", timedOut ? "The server took too long to answer." : "Can't reach the server.", 0);
  } finally {
    clearTimeout(timer);
  }
  firstRequestDone = true;

  if (!response.ok) {
    let code = "SERVER_ERROR";
    let message = "Something went wrong.";
    try {
      const data = await response.json();
      if (data?.detail?.code) {
        code = data.detail.code;
        message = data.detail.message ?? message;
      } else if (Array.isArray(data?.detail)) {
        code = "BAD_REQUEST"; // the server rejected what we sent (validation)
      }
    } catch {
      // not JSON: keep the generic error
    }
    throw new ApiError(code, message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
