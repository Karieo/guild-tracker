import pytest

from guild import create_app
from guild.db import connect
from guild.models import users

OWNER = "1000"
GUILD = "42"


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE_PATH": str(tmp_path / "test.db"),
        "OWNER_DISCORD_ID": OWNER,
        "DISCORD_GUILD_ID": GUILD,
        "DISCORD_CLIENT_ID": "cid",
        "DISCORD_CLIENT_SECRET": "secret",
        "BASE_URL": "http://localhost",
    })


@pytest.fixture
def db(app):
    conn = connect(app.config["DATABASE_PATH"])
    yield conn
    conn.close()


@pytest.fixture
def make_user(db):
    def make(discord_id, name=None, role="member"):
        user = users.upsert_discord(db, discord_id, name or f"user{discord_id}", None)
        if role != "member":
            db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user["id"]))
        db.commit()
        return users.get(db, user["id"])
    return make


@pytest.fixture
def login(app):
    """Return a test client logged in as the given user row."""
    def do(user):
        client = app.test_client()
        with client.session_transaction() as s:
            s["user_id"] = user["id"]
            s["csrf"] = "tok"
        return client
    return do


def post(client, url, **data):
    data["csrf_token"] = "tok"
    return client.post(url, data=data)


@pytest.fixture
def owner(make_user):
    return make_user(OWNER, "Clay", "owner")


@pytest.fixture
def officer(make_user):
    return make_user("2000", "Off", "officer")


@pytest.fixture
def member(make_user):
    return make_user("3000", "Mem")


CHAR = {"name": "Thrall", "class_name": "Shaman", "race": "Orc", "role": "Healer",
        "status": "leveling", "level": "10"}
