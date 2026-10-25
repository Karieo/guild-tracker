from flask import Blueprint, render_template

from guild.db import get_db
from guild.models import characters

bp = Blueprint("leveling", __name__)


@bp.get("/leveling")
def index():
    chars = characters.all_characters(get_db(), mains_only=True)  # already level-desc
    at_cap = sum(1 for c in chars if c["level"] >= characters.MAX_LEVEL)
    return render_template(
        "leveling.html", chars=chars, at_cap=at_cap, stale_days=characters.STALE_DAYS,
        cap=characters.MAX_LEVEL,
    )
