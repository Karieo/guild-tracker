import os


def load_config():
    env = os.environ
    base_url = env.get("BASE_URL", "http://localhost:8000").rstrip("/")
    return {
        "SECRET_KEY": env.get("SECRET_KEY", ""),
        "DATABASE_PATH": env.get("DATABASE_PATH", "data/guild.db"),
        "DISCORD_CLIENT_ID": env.get("DISCORD_CLIENT_ID", ""),
        "DISCORD_CLIENT_SECRET": env.get("DISCORD_CLIENT_SECRET", ""),
        "DISCORD_GUILD_ID": env.get("DISCORD_GUILD_ID", ""),
        "DISCORD_WEBHOOK_URL": env.get("DISCORD_WEBHOOK_URL", ""),
        "OWNER_DISCORD_ID": env.get("OWNER_DISCORD_ID", ""),
        "BASE_URL": base_url,
        "SESSION_COOKIE_SECURE": base_url.startswith("https://"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": 60 * 60 * 24 * 30,
    }
