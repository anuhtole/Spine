import express from "express";
import session from "express-session";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");

const SPINE_BASE = (
  process.env.SPINE_BASE_URL ||
  process.env.GUTS_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");
const ADMIN_KEY =
  process.env.SPINE_ADMIN_API_KEY ||
  process.env.GUTS_ADMIN_API_KEY ||
  process.env.ADMIN_API_KEY ||
  "";
const SESSION_SECRET = process.env.SESSION_SECRET || "dev-change-me-in-production";
const NODE_ENV = process.env.NODE_ENV || "development";
const IS_PRODUCTION = NODE_ENV === "production";
const SERVE_STATIC =
  process.env.SERVE_STATIC === "true" || NODE_ENV === "production";
const PORT = Number(process.env.BFF_PORT || process.env.PORT || (SERVE_STATIC ? 4173 : 3001));

const WEAK_SECRETS = new Set([
  "",
  "dev-change-me-in-production",
  "change-me-long-random-string",
]);

if (IS_PRODUCTION && WEAK_SECRETS.has(SESSION_SECRET)) {
  throw new Error("SESSION_SECRET must be set to a strong random value in production");
}

const PLATFORM_ADMIN_EMAILS = (process.env.BFF_PLATFORM_ADMIN_EMAILS || "")
  .split(",")
  .map((e) => e.trim().toLowerCase())
  .filter(Boolean);

function platformAdminPath(pathname) {
  return pathname.startsWith("/v1/orgs");
}

function isPlatformAdmin(req) {
  const email = req.session?.user?.email?.toLowerCase();
  return Boolean(email && PLATFORM_ADMIN_EMAILS.includes(email));
}

function orgAdminPath(pathname) {
  return pathname.startsWith("/v1/approvals");
}

function requireAuth(req, res, next) {
  if (req.session?.user?.token) return next();
  return res.status(401).json({ error: "Unauthorized" });
}

function requireOrgAdmin(req, res, next) {
  if (req.session?.user?.role === "admin") return next();
  return res.status(403).json({ error: "Organization admin role required" });
}

function upstreamError(res, status, message) {
  const body = { error: message };
  if (!IS_PRODUCTION) body.upstream = SPINE_BASE;
  return res.status(status).json(body);
}

const PROXY_HEADER_ALLOWLIST = new Set([
  "accept",
  "accept-language",
  "content-type",
  "x-request-id",
  "idempotency-key",
]);

const app = express();

app.disable("x-powered-by");

app.use((_req, res, next) => {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("X-Frame-Options", "DENY");
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (IS_PRODUCTION) {
    res.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  }
  next();
});

app.get("/health", (_req, res) => {
  res.status(200).json({ status: "ok", service: "spine-dashboard-bff" });
});

app.set("trust proxy", 1);

const sessionCookieSecure =
  process.env.COOKIE_SECURE === "false" ? false : "auto";

app.use(
  session({
    name: "spine_sid",
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: sessionCookieSecure,
      maxAge: 24 * 60 * 60 * 1000,
    },
  }),
);

app.post("/api/auth/login", express.json({ limit: "64kb" }), async (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) {
    return res.status(400).json({ error: "Email and password are required" });
  }

  let upstream;
  try {
    upstream = await fetch(`${SPINE_BASE}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "API unreachable";
    return upstreamError(res, 502, msg);
  }

  const data = await upstream.json();
  if (!upstream.ok) {
    return res.status(upstream.status).json({ error: data.detail || "Login failed" });
  }

  const user = data.user;
  req.session.regenerate((regenErr) => {
    if (regenErr) {
      return res.status(500).json({ error: "Could not establish session" });
    }
    req.session.user = {
      token: data.token,
      id: user.id,
      email: user.email,
      name: user.name,
      org_id: user.org_id,
      org_name: user.org_name,
      role: user.role,
    };
    return res.json({ ok: true, user });
  });
});

app.post("/api/auth/logout", (req, res) => {
  req.session.destroy(() => res.json({ ok: true }));
});

app.get("/api/auth/me", (req, res) => {
  if (!req.session?.user?.token) {
    return res.json({ authenticated: false });
  }
  return res.json({
    authenticated: true,
    user: {
      id: req.session.user.id,
      email: req.session.user.email,
      name: req.session.user.name,
      org_id: req.session.user.org_id,
      org_name: req.session.user.org_name,
      role: req.session.user.role,
    },
  });
});

app.get("/api/config", requireAuth, (req, res) => {
  return res.json({
    orgId: req.session.user.org_id,
    orgName: req.session.user.org_name,
    role: req.session.user.role,
    spineConfigured: true,
    platformAdmin: isPlatformAdmin(req),
  });
});

app.get("/api/spine/v1/audit/stream", requireAuth, async (req, res) => {
  const upstreamUrl = `${SPINE_BASE}/v1/audit/stream`;

  let upstream;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${req.session.user.token}`,
        Accept: "text/event-stream",
      },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Upstream fetch failed";
    return upstreamError(res, 502, msg);
  }

  if (!upstream.ok) {
    const text = await upstream.text();
    res.status(upstream.status);
    res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/json");
    return res.send(text);
  }

  res.status(200);
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");

  if (!upstream.body) {
    return res.end();
  }

  const reader = upstream.body.getReader();
  let closed = false;
  req.on("close", () => {
    closed = true;
    void reader.cancel();
  });

  try {
    while (!closed) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value?.length) res.write(Buffer.from(value));
    }
  } catch {
    /* client disconnected */
  } finally {
    if (!res.writableEnded) res.end();
  }
});

app.use(
  "/api/spine",
  requireAuth,
  express.raw({ type: () => true, limit: "2mb" }),
  async (req, res) => {
    const rawUrl = req.originalUrl;
    const prefix = "/api/spine";
    let rest = rawUrl.startsWith(prefix) ? rawUrl.slice(prefix.length) : rawUrl;
    const pathname = rest.split("?")[0] || "";

    const usePlatformAdminKey = platformAdminPath(pathname);

    if (usePlatformAdminKey && !isPlatformAdmin(req)) {
      return res.status(403).json({
        error: "Platform organization management is not enabled for this account",
      });
    }

    if (usePlatformAdminKey && !ADMIN_KEY) {
      return upstreamError(res, 503, "Platform admin API key is not configured on the BFF");
    }

    if (orgAdminPath(pathname)) {
      if (req.session.user.role !== "admin") {
        return res.status(403).json({ error: "Organization admin role required" });
      }
      const q = new URLSearchParams(rest.includes("?") ? rest.split("?")[1] : "");
      q.set("org_id", req.session.user.org_id);
      rest = `${pathname}?${q.toString()}`;
    }

    const upstreamUrl = `${SPINE_BASE}${rest}`;
    const headers = new Headers();
    if (usePlatformAdminKey) {
      headers.set("X-API-Key", ADMIN_KEY);
    } else {
      headers.set("Authorization", `Bearer ${req.session.user.token}`);
    }

    for (const [k, v] of Object.entries(req.headers)) {
      const lk = k.toLowerCase();
      if (!PROXY_HEADER_ALLOWLIST.has(lk) || v == null) continue;
      headers.set(k, Array.isArray(v) ? v.join(", ") : String(v));
    }

    const body =
      req.method === "GET" || req.method === "HEAD"
        ? undefined
        : Buffer.isBuffer(req.body) && req.body.length
          ? req.body
          : undefined;

    let upstream;
    try {
      upstream = await fetch(upstreamUrl, {
        method: req.method,
        headers,
        body,
        redirect: "manual",
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Upstream fetch failed";
      return upstreamError(res, 502, msg);
    }

    res.status(upstream.status);
    upstream.headers.forEach((val, key) => {
      const lk = key.toLowerCase();
      if (lk === "transfer-encoding" || lk === "content-encoding") return;
      res.setHeader(key, val);
    });
    const buf = Buffer.from(await upstream.arrayBuffer());
    return res.send(buf);
  },
);

if (SERVE_STATIC) {
  const dist = path.join(rootDir, "dist");
  app.use(express.static(dist));
  app.get(/^(?!\/api).*/, (_req, res) => {
    res.sendFile(path.join(dist, "index.html"));
  });
}

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(
    `[spine-dashboard BFF] listening on ${PORT} (static=${SERVE_STATIC}) → API ${SPINE_BASE}`,
  );
});
