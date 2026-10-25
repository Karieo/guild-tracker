from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from guild.db import get_db
from guild.models import availability, settings

bp = Blueprint("availability", __name__)


@bp.get("/availability")
def index():
    conn = get_db()
    summary = availability.summary(conn)
    return render_template(
        "availability.html",
        blocks=settings.blocks(conn),
        weekdays=availability.WEEKDAYS,
        mine=availability.for_user(conn, g.user["id"]),
        summary=summary,
        peak=max((s["total"] for s in summary.values()), default=1),
    )


@bp.post("/availability")
def save():
    conn = get_db()
    blocks = settings.blocks(conn)
    checked = set()
    for cell in request.form.getlist("cell"):
        day, _, block = cell.partition("|")
        if day.isdigit() and 0 <= int(day) <= 6 and block in blocks:
            checked.add((int(day), block))
    availability.save(conn, g.user["id"], checked, blocks)
    flash("Availability saved.")
    return redirect(url_for("availability.index"))
