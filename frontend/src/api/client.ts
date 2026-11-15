// Typed access to the backend. The base URL comes from VITE_API_BASE_URL (default "/api",
// which the Vite dev server proxies to the backend).

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; data: T | null; error: string };

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<ApiResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { headers: { Accept: "application/json" }, signal: signal ?? null });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    return { ok: false, status: 0, data: null, error: "Could not reach the Greenlight server." };
  }
  let data: T | null = null;
  try {
    data = (await response.json()) as T;
  } catch {
    data = null;
  }
  if (response.ok && data !== null) return { ok: true, status: response.status, data };
  return { ok: false, status: response.status, data, error: `The server answered ${response.status}.` };
}
