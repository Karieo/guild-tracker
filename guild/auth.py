"""Discord OAuth2 login, session user loading, CSRF, role gates.

Everything except PUBLIC_ENDPOINTS requires a logged-in user. The role is read
from the DB on every request, so a demotion applies immediately."""
import functools
import hmac
import secrets
from urllib.parse import urlencode

import requests
from flask import (Blueprint, Response, abort, current_app, flash, g, redirect,
                   render_template, request, session, url_for)

from guild.db import get_db
from guild.models import users

DISCORD_API = "https://discord.com/api/v10"
PUBLIC_ENDPOINTS = {"auth.login_page", "auth.start", "auth.callback", "healthz", "static"}
ROLE_RANK = {"member": 0, "officer": 1, "owner": 2}

bp = Blueprint("auth", __name__)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def _unauthenticated():
    target = url_for("auth.login_page")
    if request.headers.get("HX-Request"):
        return Response(status=401, headers={"HX-Redirect": target})
    return redirect(target)


def init_app(app):
    app.register_blueprint(bp)

    @app.before_request
    def gate():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
            return None
        user = None
        uid = session.get("user_id")
        if uid:
            conn = get_db()
            user = users.get(conn, uid)
            if user:
                synced = users.sync_owner(conn, user, current_app.config["OWNER_DISCORD_ID"])
                if synced["role"] != user["role"]:
                    conn.commit()  # persist even if this request ends in a 4xx rollback
                user = synced
        if user is None:
            session.pop("user_id", None)
            return _unauthenticated()
        g.user = user
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
            if not hmac.compare_digest(sent, session.get("csrf", "")) or not session.get("csrf"):
                abort(400, "Bad CSRF token. Reload the page and try again.")
        return None


def role_required(role):
    def deco(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if ROLE_RANK[g.user["role"]] < ROLE_RANK[role]:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return deco


def is_officer(user):
    return ROLE_RANK[user["role"]] >= ROLE_RANK["officer"]


def fetch_discord_profile(code):
    """Exchange an OAuth code. Returns (profile dict, list of guild ids).
    Isolated so tests can replace it."""
    cfg = current_app.config
    token = requests.post(
        f"{DISCORD_API}/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["BASE_URL"] + url_for("auth.callback"),
            "client_id": cfg["DISCORD_CLIENT_ID"],
            "client_secret": cfg["DISCORD_CLIENT_SECRET"],
        },
        timeout=10,
    )
    token.raise_for_status()
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    me = requests.get(f"{DISCORD_API}/users/@me", headers=headers, timeout=10)
    me.raise_for_status()
    guilds = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=headers, timeout=10)
    guilds.raise_for_status()
    return me.json(), [g_["id"] for g_ in guilds.json()]


@bp.get("/login")
def login_page():
    return render_template("login.html")


@bp.get("/auth/discord")
def start():
    session["oauth_state"] = secrets.token_urlsafe(16)
    cfg = current_app.config
    query = urlencode({
        "client_id": cfg["DISCORD_CLIENT_ID"],
        "response_type": "code",
        "scope": "identify guilds",
        "redirect_uri": cfg["BASE_URL"] + url_for("auth.callback"),
        "state": session["oauth_state"],
    })
    return redirect(f"https://discord.com/oauth2/authorize?{query}")


@bp.get("/auth/callback")
def callback():
    expected = session.pop("oauth_state", None)
    code = request.args.get("code")
    if not code or not expected or not hmac.compare_digest(request.args.get("state", ""), expected):
        flash("Login failed. Please try again.")
        return redirect(url_for("auth.login_page"))
    try:
        profile, guild_ids = fetch_discord_profile(code)
    except (requests.RequestException, KeyError, ValueError):
        flash("Couldn't reach Discord. Please try again.")
        return redirect(url_for("auth.login_page"))

    if current_app.config["DISCORD_GUILD_ID"] not in guild_ids:
        session.clear()
        return render_template("not_in_guild.html"), 403

    conn = get_db()
    user = users.upsert_discord(
        conn, profile["id"], profile.get("global_name") or profile["username"], profile.get("avatar")
    )
    users.sync_owner(conn, user, current_app.config["OWNER_DISCORD_ID"])
    session.clear()  # new session on login
    session["user_id"] = user["id"]
    session.permanent = True
    return redirect(url_for("index"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
