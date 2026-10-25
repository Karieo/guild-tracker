from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from guild.auth import is_officer
from guild.db import get_db
from guild.models import characters, gamedata, settings

bp = Blueprint("characters", __name__)


def _own_or_officer(char):
    if char is None:
        abort(404)
    if char["user_id"] != g.user["id"] and not is_officer(g.user):
        abort(403)
    return char


def _back():
    if request.args.get("from") == "admin" and is_officer(g.user):
        return redirect(url_for("admin.index"))
    return redirect(url_for("characters.mine"))


def _form_page(conn, char, form_vals, profs, errors):
    faction = settings.get(conn, "faction", "Horde")
    return render_template(
        "characters/form.html",
        char=char,
        v=form_vals,
        profs=profs,
        errors=errors,
        classes=gamedata.classes(conn),
        races=gamedata.races(conn, faction),
        all_professions=gamedata.professions(conn),
        roles=characters.ROLES,
        statuses=characters.STATUSES,
    ), (400 if errors else 200)


@bp.get("/characters")
def mine():
    conn = get_db()
    return render_template("characters/mine.html", chars=characters.for_user(conn, g.user["id"]))


@bp.route("/characters/new", methods=["GET", "POST"])
def new():
    conn = get_db()
    if request.method == "POST":
        data, profs, errors = characters.parse_form(conn, request.form, settings.get(conn, "faction"))
        if errors:
            return _form_page(conn, None, request.form, profs, errors)
        characters.create(conn, g.user["id"], data, profs)
        flash(f"{data['name']} added.")
        return redirect(url_for("characters.mine"))
    first = not characters.for_user(conn, g.user["id"])
    return _form_page(conn, None, {"level": 1, "status": "planned", "is_main": "1" if first else ""}, {}, [])


@bp.route("/characters/<int:cid>/edit", methods=["GET", "POST"])
def edit(cid):
    conn = get_db()
    char = _own_or_officer(characters.get(conn, cid))
    if request.method == "POST":
        data, profs, errors = characters.parse_form(conn, request.form, settings.get(conn, "faction"))
        if errors:
            return _form_page(conn, char, request.form, profs, errors)
        characters.update(conn, cid, data, profs)
        flash(f"{data['name']} saved.")
        return _back()
    vals = dict(char, is_main="1" if char["is_main"] else "")
    return _form_page(conn, char, vals, characters.profession_skills(conn, cid), [])


@bp.post("/characters/<int:cid>/delete")
def delete(cid):
    conn = get_db()
    char = _own_or_officer(characters.get(conn, cid))
    characters.delete(conn, cid)
    flash(f"{char['name']} deleted.")
    return _back()


@bp.post("/characters/<int:cid>/level")
def level(cid):
    """One-tap level update. Returns the card for HTMX, or redirects."""
    conn = get_db()
    char = _own_or_officer(characters.get(conn, cid))
    try:
        if "delta" in request.form:
            new_level = char["level"] + int(request.form["delta"])
        else:
            new_level = int(request.form["level"])
    except (KeyError, ValueError):
        abort(400)
    characters.set_level(conn, cid, new_level)
    if request.headers.get("HX-Request"):
        card = next(c for c in characters.for_user(conn, char["user_id"]) if c["id"] == cid)
        return render_template("partials/char_card.html", c=card)
    return _back()
