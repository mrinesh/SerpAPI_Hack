/**
 * The only place the frontend makes HTTP calls. Backend errors share one shape
 * (`{"error": {code, message, details}}`, see docs/ARCHITECTURE.md#error-contract) and are
 * rethrown as `ApiError`.
 */

const BASE_URL = "/api"; // proxied to FastAPI by the Vite dev server

const UNREACHABLE = "Can't reach the backend. Is it running? (make dev)";

interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** The endpoint is scaffolded but not built; `featureId` names its CHECKLIST.md row. */
  get isNotImplemented(): boolean {
    return this.code === "not_implemented";
  }

  get featureId(): string | undefined {
    const id = this.details.feature_id;
    return typeof id === "string" ? id : undefined;
  }

  /** For `validation_error`: {field: message}, keyed by the request-body field name. */
  get fieldErrors(): Record<string, string> {
    const fields = this.details.fields;
    if (!Array.isArray(fields)) return {};
    const errors: Record<string, string> = {};
    for (const { loc, msg } of fields as { loc: string[]; msg: string }[]) {
      const field = loc[0] === "body" ? loc[1] : loc.at(-1);
      if (field && !(field in errors)) errors[field] = msg;
    }
    return errors;
  }
}

/** A message for any error from `apiFetch`, including the backend being unreachable. */
export function describeError(error: unknown): string {
  return error instanceof ApiError ? error.message : UNREACHABLE; // fetch itself failed
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const csrf = typeof document === "undefined" ? "" : document.cookie.split("; ")
    .find(value => value.startsWith("realty_csrf="))?.slice("realty_csrf=".length) ?? "";
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {}), ...init.headers },
  });
  if (response.status === 204) return undefined as T;

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event("realty-auth-expired"));
    const error = (body as ApiErrorBody | null)?.error;
    // The dev proxy answers 502/504 with no body when FastAPI is down.
    if (!error && (response.status === 502 || response.status === 504)) {
      throw new ApiError(response.status, "backend_unreachable", UNREACHABLE);
    }
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? response.statusText,
      error?.details,
    );
  }
  return body as T;
}
