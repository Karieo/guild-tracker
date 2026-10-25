from flask import Blueprint, render_template, request

from guild.db import get_db
from guild.models import characters, gamedata

bp = Blueprint("professions", __name__)

OVERLAP_AT = 3


@bp.get("/professions")
def index():
    conn = get_db()
    mains_only = request.args.get("mains") == "1"
    chars = characters.all_characters(conn, mains_only=mains_only)
    by_prof = {}
    for c in chars:
        for p in c["profs"]:
            by_prof.setdefault(p["profession"], []).append(
                {"name": c["name"], "class_name": c["class_name"], "skill": p["skill"],
                 "owner": c["owner_name"]}
            )
    rows = []
    for prof in gamedata.professions(conn):
        people = sorted(by_prof.get(prof["name"], []), key=lambda p: (-p["skill"], p["name"].lower()))
        state = "gap" if not people else "overlap" if len(people) >= OVERLAP_AT else "ok"
        rows.append({"name": prof["name"], "kind": prof["kind"], "people": people, "state": state})
    return render_template(
        "professions.html",
        rows=rows,
        gaps=[r["name"] for r in rows if r["state"] == "gap" and r["kind"] == "primary"],
        mains_only=mains_only,
        overlap_at=OVERLAP_AT,
    )
