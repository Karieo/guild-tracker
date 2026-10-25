import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from guild.auth import role_required
from guild.db import get_db
from guild.models import characters, settings, users

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("")
@role_required("officer")
def index():
    conn = get_db()
    is_owner = g.user["role"] == "owner"
    return render_template(
        "admin.html",
        s=settings.all(conn),
        blocks="\n".join(settings.blocks(conn)),
        chars=characters.all_characters(conn),
        members=users.all(conn) if is_owner else [],
        log=users.role_log(conn) if is_owner else [],
        is_owner=is_owner,
    )


@bp.post("/settings")
@role_required("officer")
def save_settings():
    conn = get_db()
    guild_name = request.form.get("guild_name", "").strip()[:60]
    faction = request.form.get("faction", "")
    blocks = [b.strip()[:20] for b in request.form.get("blocks", "").splitlines() if b.strip()]
    if not guild_name or faction not in ("Horde", "Alliance") or not 1 <= len(blocks) <= 8:
        flash("Guild name, faction, and 1 to 8 time blocks are required.")
        return redirect(url_for("admin.index"))
    settings.set_many(conn, {
        "guild_name": guild_name,
        "faction": faction,
        "webhook_url": request.form.get("webhook_url", "").strip(),
        "availability_blocks": json.dumps(blocks, ensure_ascii=False),
    })
    flash("Settings saved.")
    return redirect(url_for("admin.index"))


@bp.post("/members/<int:user_id>/role")
@role_required("owner")
def set_role(user_id):
    conn = get_db()
    try:
        target = users.change_role(conn, g.user, user_id, request.form.get("role", ""))
        flash(f"{target['name']} is now {target['role']}.")
    except PermissionError as e:
        abort(403, str(e))
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("admin.index"))
