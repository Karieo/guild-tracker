# Guild Tracker

Roster tracker for a ~10–15 person **World of Warcraft: Forever** guild (Classic Plus, launches Nov 4, 2026, level cap 60). We're **Horde**. Phase 1 must be live before launch. Keep it small, simple, easy to maintain. Most users are on phones.

## Stack (decided, don't swap)
- Python 3.12 + Flask, server-rendered Jinja + HTMX (vendored, no React, no build step)
- SQLite file in a mounted Docker volume (`./data`)
- Docker + docker-compose on `bastion` (Jetson TX2, **arm64**), exposed through the existing Cloudflare Tunnel
- No Supabase, Vercel or paid services. Config in `.env` (see `.env.example`)

## Rules of the app
- Every page except `/login` needs Discord login (OAuth2, scopes `identify guilds`), and the user must be in our Discord server (`DISCORD_GUILD_ID`).
- Roles: **member** (own characters, votes, availability), **officer** (edit anyone's characters, polls, announcements, settings), **owner** (everything, plus promote/demote officers).
- Owner = `OWNER_DISCORD_ID` in `.env`, nobody else, can't be demoted. Role is read from the DB on every request, so changes apply immediately. All role changes are logged in `role_changes`.
- Classes, races, professions are seed data in the DB (`migrations/002_seed_game_data.sql`), not hardcoded in templates. Class/race combos are not enforced. Alliance races stay in the table but are hidden while faction = Horde.
- Times are stored UTC, shown in Central with a note. No full timezone handling.

## Layout
- `guild/db.py`, `guild/models/` — plain SQLite functions that take a connection, no request/Flask logic. **The phase 2 bot shares these** (it will install the same requirements). Use `guild.db.connect()` + `migrate()`.
- `guild/routes/` — one blueprint per page. `guild/auth.py` — OAuth, CSRF, role gates.
- `migrations/NNN_*.sql` — numbered, run at startup, never edit an applied one (add a new file).
- `backup/` — sidecar that runs nightly `sqlite3 .backup`.

## Not in phase 1 (plan for it, don't build it)
Discord bot (slash-command polls, raid signups, reminders) as a separate container in this repo; raid calendar/attendance; "who can craft X" recipe lookup; Blizzard API.

## Working rules
- Plan first. Never push, deploy or delete without asking Clay. Small, logical commits.
- Tests: `python -m pytest` (use `requirements-dev.txt`). Cover auth gating, character CRUD, one vote per user, availability, role rules.
