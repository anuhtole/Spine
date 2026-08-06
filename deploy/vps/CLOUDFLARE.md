# Cloudflare + Spine demo (fix HTTPS 503 / “site breaks”)

If **`http://demo…` works** but **`https://demo…` shows 503** (or “service unavailable”), the problem is almost always **Cloudflare talking to your Droplet on port 443**, not your React app.

Do **one** of these paths (A is best).

---

## Path A — Recommended: DNS only (grey cloud)

1. Cloudflare → **DNS** → your **`demo`** **A** record.
2. Turn the proxy **OFF** (cloud icon **grey**, label **DNS only**).
3. Wait **2–10 minutes**.
4. Open **`https://demo.spinelayer.com`** again.

Traffic goes **browser → your Droplet (Caddy) → Let’s Encrypt**. No Cloudflare TLS in the middle.

---

## Path B — Keep orange cloud (Proxied)

1. Cloudflare → **SSL/TLS** → set mode to **Full** (not Off).
2. If you still get 503, try **Full (strict)** **only after** Caddy has successfully obtained a cert (check `docker compose logs caddy` on the Droplet).
3. Confirm DigitalOcean **firewall** allows **TCP 443** to the Droplet.

Cloudflare will connect to your origin on **443**. Caddy must answer HTTPS there (Let’s Encrypt).

---

## Path C — Emergency “make HTTPS load” (weaker security)

Only if you insist on orange cloud and origin HTTPS keeps failing:

- Cloudflare **SSL/TLS** → **Flexible** (HTTPS browser → Cloudflare, **HTTP** Cloudflare → origin :80).

This is **not** ideal (plaintext Cloudflare → your server), but it stops the “HTTPS is dead” symptom while you fix certs.

---

## Checklist on the Droplet

```bash
cd ~/YOUR_REPO/deploy/vps
docker compose ps
curl -sS -o /dev/null -w "local http health: %{http_code}\n" http://127.0.0.1/health
```

`local http health` should be **200**. If Caddy logs show ACME / TLS errors, fix DNS + port **443** first, then `docker compose up -d --force-recreate caddy`.

---

## Your `.env` must match the hostname

```env
SITE_ADDRESS=demo.spinelayer.com
```

(no `https://` prefix). After any Caddyfile change:

```bash
docker compose up -d --force-recreate caddy
```
