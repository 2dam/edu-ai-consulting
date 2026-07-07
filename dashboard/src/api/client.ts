const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const USER_ID_KEY = "edu_community_user_id";

export function getStoredUserId(): number | null {
  const raw = localStorage.getItem(USER_ID_KEY);
  return raw ? Number(raw) : null;
}

export function setStoredUserId(id: number | null) {
  if (id === null) {
    localStorage.removeItem(USER_ID_KEY);
  } else {
    localStorage.setItem(USER_ID_KEY, String(id));
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const userId = getStoredUserId();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(userId ? { "X-User-Id": String(userId) } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // 응답 본문이 JSON이 아닐 수 있음 - statusText로 폴백
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
};
