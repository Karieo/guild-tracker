import json

DEFAULT_BLOCKS = ["6–8pm", "8–10pm", "10pm–12am"]


def all(conn):
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}


def get(conn, key, default=""):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_many(conn, values):
    conn.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        list(values.items()),
    )


def blocks(conn):
    try:
        found = json.loads(get(conn, "availability_blocks", "[]"))
    except ValueError:
        found = []
    return found or DEFAULT_BLOCKS
