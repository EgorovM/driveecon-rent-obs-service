const API = import.meta.env.VITE_API_URL ?? "";

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
      ...(init?.headers as Record<string, string>),
    },
  });
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
  const res = await fetch(`${API}${path}`, { method: "POST", body: fd });
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
