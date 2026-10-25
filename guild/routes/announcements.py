from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from guild import discord_webhook
from guild.auth import role_required
from guild.db import get_db
from guild.models import announcements, settings

bp = Blueprint("announcements", __name__)


@bp.get("/announcements")
@role_required("officer")
def index():
    return render_template("announcements.html", items=announcements.all_announcements(get_db()), v={})


@bp.post("/announcements")
@role_required("officer")
def post():
    conn = get_db()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or len(title) > 200 or not body or len(body) > 3500:
        flash("Add a title (200 max) and a message (3500 max).")
        return render_template(
            "announcements.html", items=announcements.all_announcements(conn), v=request.form
        ), 400
    announcements.create(conn, title, body, g.user["id"])
    url = settings.get(conn, "webhook_url") or current_app.config["DISCORD_WEBHOOK_URL"]
    if discord_webhook.send_embed(url, title, body, current_app.config["BASE_URL"]):
        flash("Announcement posted to Discord.")
    else:
        flash("Saved, but the Discord post failed. Check the webhook URL in Admin.")
    return redirect(url_for("announcements.index"))
