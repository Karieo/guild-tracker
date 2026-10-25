from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from guild import discord_webhook, timeutil
from guild.auth import role_required
from guild.db import get_db
from guild.models import polls, settings

bp = Blueprint("polls", __name__)


def _poll_or_404(conn, poll_id):
    poll = polls.get(conn, poll_id)
    if poll is None:
        abort(404)
    return poll


@bp.get("/polls")
def index():
    return render_template("polls/index.html", polls=polls.all_polls(get_db()))


@bp.route("/polls/new", methods=["GET", "POST"])
@role_required("officer")
def new():
    if request.method == "GET":
        return render_template("polls/new.html", v={}, errors=[])
    conn = get_db()
    question = request.form.get("question", "").strip()
    labels = [l.strip()[:80] for l in request.form.get("options", "").splitlines() if l.strip()]
    errors = []
    if not question or len(question) > 200:
        errors.append("Add a question (200 characters max).")
    if len(labels) < 2 or len(labels) > 12:
        errors.append("Give 2 to 12 options, one per line.")
    closes_at = None
    if request.form.get("closes_at"):
        try:
            closes_at = timeutil.central_input_to_utc(request.form["closes_at"])
            if closes_at <= timeutil.now_str():
                errors.append("Close time must be in the future.")
        except ValueError:
            errors.append("Close time isn't valid.")
    if errors:
        return render_template("polls/new.html", v=request.form, errors=errors), 400

    poll_id = polls.create(conn, question, labels, g.user["id"], closes_at,
                           request.form.get("multi_select") == "1")
    flash("Poll created.")
    if request.form.get("post_discord"):
        link = current_app.config["BASE_URL"] + url_for("polls.show", poll_id=poll_id)
        body = "\n".join(f"• {l}" for l in labels) + "\n\nVote on the site."
        url = settings.get(conn, "webhook_url") or current_app.config["DISCORD_WEBHOOK_URL"]
        if discord_webhook.send_embed(url, f"Poll: {question}", body, link):
            flash("Posted to Discord.")
        else:
            flash("Poll saved, but the Discord post failed. Check the webhook URL in Admin.")
    return redirect(url_for("polls.show", poll_id=poll_id))


@bp.get("/polls/<int:poll_id>")
def show(poll_id):
    conn = get_db()
    poll = _poll_or_404(conn, poll_id)
    options = polls.results(conn, poll_id)
    return render_template(
        "polls/show.html", poll=poll, options=options, open=polls.is_open(poll),
        mine=polls.user_choices(conn, poll_id, g.user["id"]),
        total=max(1, sum(o["count"] for o in options)),
    )


@bp.post("/polls/<int:poll_id>/vote")
def vote(poll_id):
    conn = get_db()
    poll = _poll_or_404(conn, poll_id)
    try:
        polls.cast(conn, poll, g.user["id"], [int(o) for o in request.form.getlist("option")])
        flash("Vote saved.")
    except ValueError as e:
        flash(str(e))
    return redirect(url_for("polls.show", poll_id=poll_id))


@bp.post("/polls/<int:poll_id>/close")
@role_required("officer")
def close(poll_id):
    conn = get_db()
    _poll_or_404(conn, poll_id)
    polls.close(conn, poll_id)
    flash("Poll closed.")
    return redirect(url_for("polls.show", poll_id=poll_id))
