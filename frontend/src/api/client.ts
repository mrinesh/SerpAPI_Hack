/**
 * The only place the frontend makes HTTP calls. Backend errors share one shape
 * (`{"error": {code, message, details}}`, see docs/ARCHITECTURE.md#error-contract) and are
 * rethrown as `ApiError`.
 */

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
}

const BASE_URL = "/api"; // proxied to FastAPI by the Vite dev server

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (response.status === 204) return undefined as T;

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body as ApiErrorBody | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? response.statusText,
      error?.details,
    );
  }
  return body as T;
}
