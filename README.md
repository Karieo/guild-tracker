# Guild Tracker

Roster, leveling, professions, polls, and raid availability for our WoW: Forever guild.
Flask + HTMX + SQLite, runs in Docker on bastion, behind Cloudflare Tunnel, Discord login only.

## 1. Create the Discord application

1. Go to <https://discord.com/developers/applications> → **New Application**.
2. **OAuth2** → copy the **Client ID** and **Client Secret** (reset it once to see it).
3. **OAuth2 → Redirects** → add exactly: `https://YOUR-SUBDOMAIN/auth/callback`
   (must match `BASE_URL` in `.env` plus `/auth/callback`).
4. In Discord, turn on **Developer Mode** (User Settings → Advanced). Right-click the server icon →
   **Copy Server ID** (that's `DISCORD_GUILD_ID`). Right-click yourself → **Copy User ID**
   (that's `OWNER_DISCORD_ID`).
5. **Webhook:** in the channel you want posts in: Edit Channel → Integrations → Webhooks → New Webhook →
   Copy URL. Put it in `.env` as `DISCORD_WEBHOOK_URL`, or paste it in the Admin page later.

The app asks for the `identify` and `guilds` scopes only. It never joins servers or reads messages.

## 2. Configure

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as SECRET_KEY
```

Fill in the rest of `.env`. Set `BASE_URL` to the public https URL.

## 3. Deploy on bastion

```bash
git clone git@github.com:Karieo/guild-tracker.git && cd guild-tracker
cp .env.example .env   # fill in, as above
docker compose up -d --build
docker compose logs -f web
```

The first build on the TX2 takes a few minutes. Images are `python:3.12-slim` and `alpine`, both multi-arch.
The web container listens on `127.0.0.1:8000`. The database is `./data/guild.db`.

Log in once with your Discord account. Because your ID is `OWNER_DISCORD_ID`, you become the owner.
Then open **Admin** to set the guild name, faction, and raid time blocks.

Update later with `git pull && docker compose up -d --build`. Migrations run on startup.

## 4. Add the subdomain to your Cloudflare Tunnel

Pick a subdomain (e.g. `guild.yourdomain.com`). Either way works:

**Dashboard (if the tunnel is remotely managed):** Zero Trust → Networks → Tunnels → your tunnel →
**Public Hostname** → Add: subdomain + domain, Service type `HTTP`, URL `localhost:8000`.
(If `cloudflared` runs inside Docker instead, use the host's address, e.g. `host.docker.internal:8000`
or the bastion LAN IP.)

**Config file (if you use `config.yml`):** add above the catch-all rule:

```yaml
ingress:
  - hostname: guild.yourdomain.com
    service: http://localhost:8000
  # ...your existing rules...
  - service: http_status:404
```

Then `cloudflared tunnel route dns <tunnel-name> guild.yourdomain.com` and restart cloudflared.

Use the same hostname in `BASE_URL` and the Discord redirect URL. Don't put Cloudflare Access in front of it;
the app handles login itself.

## Roles

- **member** — own characters, votes, availability
- **officer** — also edits anyone's characters, creates polls, posts announcements, edits settings
- **owner** — also promotes/demotes officers (Admin page, logged). Set only by `OWNER_DISCORD_ID`.

## Backups

The `backup` container makes a gzipped copy of the database every night at `BACKUP_HOUR` (UTC, set in
`docker-compose.yml`; 9 = 3–4am Central) into `./backups`, and removes copies older than `KEEP_DAYS` (14).
Run one now: `docker compose exec backup /backup.sh --once`.
Restore: stop `web`, `gunzip -c backups/guild-<stamp>.db.gz > data/guild.db`, start `web`.
Copy `./backups` somewhere off bastion now and then; a backup on the same disk won't survive the disk.

## Editing game data

Classes, races, and professions live in the database (`game_classes`, `races`, `professions`), seeded by
`migrations/002_seed_game_data.sql`. The Alliance races there are classic placeholders. To change
anything for Forever, add a new migration (e.g. `003_forever_tweaks.sql`) with `INSERT`/`UPDATE` statements.
Don't edit migrations that already ran.

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Phase 2 (not built)

Discord bot for slash-command polls, raid signups with buttons, and reminders. Separate container in this
repo, same SQLite file. It can `from guild.db import connect, migrate` and `from guild.models import ...`.
