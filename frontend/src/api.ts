const API = import.meta.env.VITE_API_URL ?? "";

const TOKEN_KEY = "drivee_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function onUnauthorized(): void {
  clearToken();
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

function detailMessage(j: { detail?: unknown }): string {
  const d = j.detail;
  if (Array.isArray(d)) {
    return d.map((x: { msg?: string }) => x.msg ?? JSON.stringify(x)).join("; ");
  }
  if (typeof d === "string") {
    return d;
  }
  return JSON.stringify(j);
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers as Record<string, string>),
    },
  });
  if (res.status === 401) {
    onUnauthorized();
    throw new Error("Требуется вход");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = (await res.json()) as { detail?: unknown };
      msg = detailMessage(j);
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API}${path}`, { method: "POST", body: fd, headers: authHeaders() });
  if (res.status === 401) {
    onUnauthorized();
    throw new Error("Требуется вход");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = (await res.json()) as { detail?: unknown };
      msg = detailMessage(j);
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}
