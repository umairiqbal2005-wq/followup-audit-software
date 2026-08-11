const TOKEN_KEY = "aop_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

import type {
  AccessCatalog,
  AuditReport,
  DashboardStats,
  Observation,
  ObservationDetail,
  User,
} from "../types";

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; expires_in: number }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  accessCatalog: () => request<AccessCatalog>("/api/auth/access-catalog"),
  users: (params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return request<User[]>(`/api/users${qs}`);
  },
  updateUser: (id: number, body: object) =>
    request<User>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  createUser: (body: object) =>
    request<User>("/api/users", { method: "POST", body: JSON.stringify(body) }),
  dashboard: () => request<DashboardStats>("/api/observations/dashboard"),
  observations: (params?: Record<string, string>) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    return request<Observation[]>(`/api/observations${qs}`);
  },
  observation: (id: number) => request<ObservationDetail>(`/api/observations/${id}`),
  createObservation: (body: object) =>
    request<Observation>("/api/observations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  submitObservation: (id: number) =>
    request<Observation>(`/api/observations/${id}/submit`, { method: "POST" }),
  assignObservation: (id: number, body: object) =>
    request<Observation>(`/api/observations/${id}/assign`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  respondObservation: (id: number, body: object) =>
    request<Observation>(`/api/observations/${id}/respond`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  verifyObservation: (id: number, body: object) =>
    request<Observation>(`/api/observations/${id}/verify`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reports: () => request<AuditReport[]>("/api/reports"),
  createReport: (form: FormData) =>
    request<AuditReport>("/api/reports", { method: "POST", body: form }),
};
