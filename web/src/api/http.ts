/** Same-origin API (works on Pi + Cloudflare tunnel). */

const WEB_VERSION = "0.1.0";

export function getWebVersion(): string {
  return WEB_VERSION;
}

function authHeader(): HeadersInit {
  const t = localStorage.getItem("bb_access_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  const ah = authHeader() as Record<string, string>;
  if (ah.Authorization) {
    headers.set("Authorization", ah.Authorization);
  }
  if (!headers.has("Accept") && !init.body) {
    headers.set("Accept", "application/json");
  }
  return fetch(path, { ...init, headers });
}

export async function readErrorMessage(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (j && typeof j.detail === "string") {
      return j.detail;
    }
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function loginPassword(email: string, password: string) {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  const data = (await res.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };
  localStorage.setItem("bb_access_token", data.access_token);
  localStorage.setItem("bb_refresh_token", data.refresh_token);
}

export async function oauthComplete(exchange: string) {
  const res = await apiFetch("/api/auth/oauth/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exchange }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  const data = (await res.json()) as {
    access_token: string;
    refresh_token: string;
  };
  localStorage.setItem("bb_access_token", data.access_token);
  localStorage.setItem("bb_refresh_token", data.refresh_token);
}

export async function refreshTokens(): Promise<boolean> {
  const rt = localStorage.getItem("bb_refresh_token");
  if (!rt) {
    return false;
  }
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!res.ok) {
    return false;
  }
  const data = (await res.json()) as { access_token: string; refresh_token: string };
  localStorage.setItem("bb_access_token", data.access_token);
  localStorage.setItem("bb_refresh_token", data.refresh_token);
  return true;
}

/**
 * Same as apiFetch but retries once after refreshing tokens on 401 (matches fetchMe).
 * Use for all Bearer-authenticated API calls except login/oauth/refresh.
 */
export async function apiFetchAuth(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let res = await apiFetch(path, init);
  if (res.status === 401) {
    if (await refreshTokens()) {
      res = await apiFetch(path, init);
    }
  }
  return res;
}

export function logout() {
  localStorage.removeItem("bb_access_token");
  localStorage.removeItem("bb_refresh_token");
}

export type MeUser = {
  email: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  storage_used_bytes?: number | null;
  storage_limit_bytes?: number | null;
};

export async function fetchMe(): Promise<MeUser> {
  const res = await apiFetchAuth("/api/users/me");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<MeUser>;
}

export type Preferences = {
  theme: string;
  content_background_image: string | null;
  content_background_opacity: number;
  favorite_paths: string[];
};

export async function fetchPreferences(): Promise<Preferences> {
  const res = await apiFetchAuth("/api/users/me/preferences");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<Preferences>;
}

export async function patchPreferences(p: Partial<Preferences>): Promise<Preferences> {
  const res = await apiFetchAuth("/api/users/me/preferences", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<Preferences>;
}

export type FileRow = { path: string; mtime: number; hash?: string | null };

export async function listFiles(): Promise<FileRow[]> {
  const res = await apiFetchAuth("/api/files/list");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<FileRow[]>;
}

export type StorageInfo = {
  used_bytes: number;
  limit_bytes: number | null;
  server_disk_total_bytes?: number | null;
  server_disk_used_bytes?: number | null;
};

export async function fetchStorage(): Promise<StorageInfo> {
  const res = await apiFetchAuth("/api/files/storage");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<StorageInfo>;
}

export async function deleteFile(path: string): Promise<void> {
  const res = await apiFetchAuth(`/api/files/delete?path=${encodeURIComponent(path)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
}

export async function uploadFile(path: string, file: File): Promise<void> {
  const res = await apiFetchAuth(`/api/files/upload?path=${encodeURIComponent(path)}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: file,
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
}

export async function downloadBlob(path: string): Promise<Blob> {
  const res = await apiFetchAuth(`/api/files/download?path=${encodeURIComponent(path)}`);
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.blob();
}

export async function clientPing(opts: {
  last_sync_ok?: boolean | null;
  last_sync_at?: string | null;
}): Promise<void> {
  await apiFetchAuth("/api/clients/ping", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_type: "web",
      client_version: WEB_VERSION,
      last_sync_ok: opts.last_sync_ok ?? null,
      last_sync_at: opts.last_sync_at ?? null,
    }),
  });
}

export type ServerEvent = {
  id: number;
  created_at: string;
  level: string;
  category: string;
  message: string;
  detail_json?: string | null;
  user_email?: string | null;
};

export type ClientConn = {
  user_email: string;
  client_type: string;
  client_version: string;
  last_seen_at: string;
  last_sync_at?: string | null;
  last_sync_ok?: boolean | null;
  backend_version_at_ping?: string | null;
};

export async function adminEvents(limit = 100): Promise<ServerEvent[]> {
  const res = await apiFetchAuth(`/api/admin/events?limit=${limit}`);
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<ServerEvent[]>;
}

export async function adminClients(): Promise<ClientConn[]> {
  const res = await apiFetchAuth("/api/admin/clients");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<ClientConn[]>;
}

export async function adminListUsers(): Promise<MeUser[]> {
  const res = await apiFetchAuth("/api/users");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<MeUser[]>;
}

export async function adminCreateUser(body: {
  email: string;
  first_name: string;
  last_name: string;
}): Promise<unknown> {
  const res = await apiFetchAuth("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json();
}

export async function adminDeleteUser(email: string): Promise<void> {
  const res = await apiFetchAuth(`/api/users/${encodeURIComponent(email)}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
}

export async function fetchMetaVersion(): Promise<{
  api_version: string;
  min_supported_client_version: string;
  google_signin_available: boolean;
}> {
  const res = await fetch("/api/meta/version");
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<{
    api_version: string;
    min_supported_client_version: string;
    google_signin_available: boolean;
  }>;
}
