from collections import Counter

from flask import Blueprint, render_template, request

from guild.db import get_db
from guild.models import characters, gamedata

bp = Blueprint("roster", __name__)


@bp.get("/roster")
def index():
    conn = get_db()
    include_alts = request.args.get("alts") == "1"
    chars = characters.all_characters(conn, mains_only=not include_alts)
    groups = []
    for cls in gamedata.classes(conn):
        members = sorted((c for c in chars if c["class_name"] == cls["name"]), key=lambda c: c["name"].lower())
        if members:
            groups.append((cls["name"], members))
    counts = Counter(c["role"] for c in chars)
    return render_template(
        "roster.html", groups=groups, counts=counts, total=len(chars), include_alts=include_alts
    )
