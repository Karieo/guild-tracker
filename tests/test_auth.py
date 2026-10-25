import pytest

from guild import auth
from tests.conftest import GUILD, post


@pytest.mark.parametrize("url", [
    "/", "/characters", "/roster", "/leveling", "/professions", "/polls",
    "/availability", "/announcements", "/admin", "/polls/new",
])
def test_pages_require_login(app, url):
    r = app.test_client().get(url)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_login_page_and_healthz_are_public(app):
    c = app.test_client()
    assert c.get("/login").status_code == 200
    assert c.get("/healthz").status_code == 200


def test_htmx_request_gets_401_with_redirect(app):
    r = app.test_client().post("/characters/1/level", headers={"HX-Request": "true"})
    assert r.status_code == 401 and "/login" in r.headers["HX-Redirect"]


def test_logged_in_user_can_see_pages(login, member):
    assert login(member).get("/roster").status_code == 200


def test_post_without_csrf_rejected(login, member):
    r = login(member).post("/availability", data={})
    assert r.status_code == 400


def _callback(app, monkeypatch, guilds, discord_id="555"):
    monkeypatch.setattr(
        auth, "fetch_discord_profile",
        lambda code: ({"id": discord_id, "username": "newbie", "avatar": None}, guilds),
    )
    c = app.test_client()
    with c.session_transaction() as s:
        s["oauth_state"] = "abc"
    return c, c.get("/auth/callback?code=x&state=abc")


def test_callback_lets_guild_member_in(app, monkeypatch):
    c, r = _callback(app, monkeypatch, [GUILD, "other"])
    assert r.status_code == 302
    assert c.get("/roster").status_code == 200


def test_callback_rejects_non_member(app, monkeypatch):
    c, r = _callback(app, monkeypatch, ["other"])
    assert r.status_code == 403 and b"guild members" in r.data
    assert c.get("/roster").status_code == 302  # still not logged in


def test_callback_rejects_bad_state(app):
    c = app.test_client()
    with c.session_transaction() as s:
        s["oauth_state"] = "abc"
    r = c.get("/auth/callback?code=x&state=WRONG")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_owner_discord_id_becomes_owner_on_login(app, monkeypatch, db):
    _callback(app, monkeypatch, [GUILD], discord_id="1000")
    assert db.execute("SELECT role FROM users WHERE discord_id = '1000'").fetchone()["role"] == "owner"
