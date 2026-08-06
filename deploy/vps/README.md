# Spine — VPS production deploy

This folder runs **Postgres + API + dashboard + Caddy (TLS)** on **one server** with a **predictable monthly bill** (no pay-per-GB egress surprises). Users sign in with their **own email and password**; the browser only talks to the **dashboard BFF**; the BFF calls the API on the private Docker network.

Local development is unchanged: use the repo root [`docker-compose.yml`](../../docker-compose.yml) from your clone of this repository.

**HTTPS works on HTTP but 503 on HTTPS with Cloudflare?** See **[CLOUDFLARE.md](CLOUDFLARE.md)** (grey cloud DNS-only is the usual fix).

---

## What you pay (ballpark)

| Item | Typical cost (USD) |
|------|---------------------|
| **Small VPS** (e.g. DigitalOcean, Linode, Vultr, Hetzner) | **~$6-12 / month** for a 1-2 GB RAM plan |
| **Domain** (optional, recommended) | **~$10-15 / year** |
| **This stack** | **$0** extra software -- you only pay the provider above |

---

## What you must provide (checklist)

1. **A VPS** -- Ubuntu 22.04/24.04 LTS. Note its **public IPv4**.
2. **Secrets** (generate long random strings):
   - `POSTGRES_PASSWORD` (and matching `DATABASE_URL` password)
   - `ADMIN_API_KEY`
   - `SESSION_SECRET`
3. **DNS (recommended)** -- an **A record** pointing your hostname (e.g. `demo.yourcompany.com`) to VPS IP.

---

## Server setup (once per VPS)

SSH in as root or a sudo user, then:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in, then clone your repo and `cd` into `<repo>/deploy/vps`.

---

## Configure and start

```bash
cd <your-repo>/deploy/vps
cp env.production.example .env
nano .env   # fill every REQUIRED value
```

**TLS vs quick HTTP test**

| Goal | Set in `.env` |
|------|----------------|
| **HTTPS with a domain** | `SITE_ADDRESS=demo.yourdomain.com` (DNS must point to VPS first) |
| **HTTP by IP only** | `SITE_ADDRESS=:80` |
| **Agents (Claude Code, SDKs)** | `API_ADDRESS=api.demo.yourdomain.com` + DNS **A** record → same VPS IP |

`SITE_ADDRESS` serves the **dashboard** (browser + BFF). `API_ADDRESS` serves **`/v1/intercept`** for org API keys. Agents must use the API host, not the dashboard host.

Bring the stack up:

```bash
docker compose up -d --build
```

Check:

```bash
curl -sS http://127.0.0.1/health   # via BFF → {"status":"ok",...}
```

---

## Seed org + create first user

From `deploy/vps` on the server:

```bash
# 1. Seed the demo org (creates org + agent + policy + org key)
docker compose exec api sh -c 'export SPINE_BASE_URL=http://127.0.0.1:8000 && python tools/seed_demo.py'
```

Note the printed `org_id`. Then create a user:

```bash
# 2. Create a user and assign to the org
docker compose exec api python tools/create_user.py \
    --email you@company.com \
    --name "Your Name" \
    --org-id <ORG_ID_FROM_STEP_1> \
    --role admin
```

Open the site in a browser and sign in with the email and password you just set.

---

## Operations

| Task | Command |
|------|---------|
| Logs (all) | `docker compose logs -f` |
| Logs (API) | `docker compose logs -f api` |
| Restart after `.env` change | `docker compose up -d --force-recreate` |
| Upgrade after `git pull` | `docker compose up -d --build` |
| Create another user | `docker compose exec api python tools/create_user.py --email ... --name ... --org-id ... --role member` |

---

## Troubleshooting

### "The site won't load" / browser spins

```bash
docker compose ps                    # everything should be running
docker compose logs --tail 80 caddy  # check Caddy output
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/health  # want 200
```

### "Login then kicked back to login"

Session cookie / HTTP vs HTTPS mismatch. Ensure you have the latest code (`git pull && docker compose up -d --build`). Open the site using the scheme that matches your `SITE_ADDRESS` -- HTTPS for a domain, HTTP for `:80`.

### Caddy log: "listening only on the HTTP port"

Caddy was using `SITE_ADDRESS=:80` inside the container. Check:

```bash
docker compose exec caddy printenv SITE_ADDRESS
```

Should print your domain, not `:80`. If wrong, verify `.env` and run `docker compose up -d --force-recreate caddy`.

---

## Security notes

- Change **all** default passwords; restrict SSH to keys; keep the OS patched.
- Users authenticate with individual email/password (bcrypt-hashed, JWT tokens).
- API keys for programmatic/SDK access remain separate from user accounts.
