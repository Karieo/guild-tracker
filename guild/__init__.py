from flask import Flask, g, redirect, url_for
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

from guild import auth, db, timeutil
from guild.config import load_config
from guild.models import gamedata, settings


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(load_config())
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set (see .env.example)")

    # Behind Cloudflare Tunnel: trust one hop of forwarded headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    auth.init_app(app)

    from guild.routes import (admin, announcements, availability, characters,
                              leveling, polls, professions, roster)
    for module in (characters, roster, leveling, professions, polls, availability,
                   announcements, admin):
        app.register_blueprint(module.bp)

    @app.get("/")
    def index():
        return redirect(url_for("characters.mine"))

    @app.get("/healthz")
    def healthz():
        return "ok"

    @app.context_processor
    def inject():
        conn = db.get_db()
        return {
            "guild_name": settings.get(conn, "guild_name", "Guild"),
            "class_colors": gamedata.class_colors(conn),
            "user": g.get("user"),
            "csrf_token": auth.csrf_token,
            "csrf_field": lambda: Markup(
                f'<input type="hidden" name="csrf_token" value="{auth.csrf_token()}">'
            ),
        }

    app.add_template_filter(timeutil.to_central, "central")
    app.add_template_filter(
        lambda h, uid: f"https://cdn.discordapp.com/avatars/{uid}/{h}.png?size=64" if h else "",
        "avatar_url",
    )
    return app
