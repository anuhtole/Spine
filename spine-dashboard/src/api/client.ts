const PREFIX = "/api/spine";

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(message: string, status: number, body: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function parseMaybeJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function spineFetch<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers: extra, ...rest } = init;
  const headers = new Headers(extra);
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const url = path.startsWith("http") ? path : `${PREFIX}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...rest,
    credentials: "include",
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) {
    const body = await res.text();
    let detail = body;
    try {
      const j = JSON.parse(body) as { detail?: unknown; error?: unknown };
      if (j?.detail !== undefined) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      else if (j?.error !== undefined) detail = String(j.error);
    } catch {
      /* keep text */
    }
    throw new ApiError(detail || res.statusText, res.status, body);
  }
  return (await parseMaybeJson(res)) as T;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string;
  org_id: string;
  org_name: string;
  role: string;
}

export interface AuthMeResponse {
  authenticated: boolean;
  user?: UserInfo;
}

export async function authLogin(email: string, password: string): Promise<{ ok: boolean; user: UserInfo }> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const j = (await res.json().catch(() => ({}))) as { error?: unknown; detail?: unknown };
    // FastAPI 422 validation errors return `detail` as a list of objects, not a
    // string. Coerce anything non-string into a JSON snippet rather than letting
    // it render as "[object Object]".
    const toMsg = (v: unknown): string | null => {
      if (!v) return null;
      if (typeof v === "string") return v;
      try {
        return JSON.stringify(v);
      } catch {
        return null;
      }
    };
    const msg = toMsg(j.detail) || toMsg(j.error) || `Login failed (HTTP ${res.status})`;
    throw new Error(msg);
  }
  return (await res.json()) as { ok: boolean; user: UserInfo };
}

export async function authLogout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
}

export async function authMe(): Promise<AuthMeResponse> {
  const res = await fetch("/api/auth/me", { credentials: "include" });
  return (await res.json()) as AuthMeResponse;
}

export async function sessionConfig(): Promise<{
  orgId: string | null;
  orgName: string | null;
  role: string | null;
  spineConfigured: boolean;
  platformAdmin: boolean;
}> {
  const res = await fetch("/api/config", { credentials: "include" });
  if (!res.ok) throw new Error("Not authenticated");
  return (await res.json()) as {
    orgId: string | null;
    orgName: string | null;
    role: string | null;
    spineConfigured: boolean;
    platformAdmin: boolean;
  };
}
