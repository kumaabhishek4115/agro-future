/**
 * Thin browser-side client for the FastAPI backend.
 * Requests go to /api/v1/* and are proxied by the Next.js rewrite in next.config.mjs.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** FastAPI errors are `{ detail: string }` or `{ detail: [{ msg, loc }] }` for 422. */
function extractDetail(body: unknown, fallback: string): string {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        typeof item === 'object' && item !== null && 'msg' in item
          ? String((item as { msg: unknown }).msg)
          : null,
      )
      .filter(Boolean);
    if (messages.length > 0) return messages.join(', ');
  }
  return fallback;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' });
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const token = typeof window === 'undefined' ? null : localStorage.getItem('token');

  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const json = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(extractDetail(json, `Request failed (${res.status})`), res.status);
  }
  return json as T;
}
