from guild import timeutil


def get(conn, poll_id):
    return conn.execute(
        "SELECT p.*, u.name AS creator_name FROM polls p JOIN users u ON u.id = p.created_by "
        "WHERE p.id = ?",
        (poll_id,),
    ).fetchone()


def is_open(poll):
    if poll["is_closed"]:
        return False
    return poll["closes_at"] is None or poll["closes_at"] > timeutil.now_str()


def all_polls(conn):
    rows = conn.execute(
        "SELECT p.*, u.name AS creator_name, "
        "(SELECT COUNT(DISTINCT user_id) FROM poll_votes WHERE poll_id = p.id) AS voters "
        "FROM polls p JOIN users u ON u.id = p.created_by ORDER BY p.id DESC"
    ).fetchall()
    return [dict(r, open=is_open(r)) for r in rows]


def create(conn, question, labels, created_by, closes_at, multi_select):
    cur = conn.execute(
        "INSERT INTO polls (question, created_by, closes_at, multi_select) VALUES (?, ?, ?, ?)",
        (question, created_by, closes_at, 1 if multi_select else 0),
    )
    poll_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO poll_options (poll_id, label) VALUES (?, ?)", [(poll_id, l) for l in labels]
    )
    return poll_id


def results(conn, poll_id):
    options = [dict(r, voters=[]) for r in conn.execute(
        "SELECT id, label FROM poll_options WHERE poll_id = ? ORDER BY id", (poll_id,))]
    by_id = {o["id"]: o for o in options}
    for v in conn.execute(
        "SELECT v.option_id, u.name FROM poll_votes v JOIN users u ON u.id = v.user_id "
        "WHERE v.poll_id = ? ORDER BY u.name COLLATE NOCASE",
        (poll_id,),
    ):
        by_id[v["option_id"]]["voters"].append(v["name"])
    for o in options:
        o["count"] = len(o["voters"])
    return options


def user_choices(conn, poll_id, user_id):
    return {
        r["option_id"]
        for r in conn.execute(
            "SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id)
        )
    }


def cast(conn, poll, user_id, option_ids):
    """Replace the user's votes on a poll. Raises ValueError on a bad vote."""
    if not is_open(poll):
        raise ValueError("This poll is closed.")
    valid = {r["id"] for r in conn.execute("SELECT id FROM poll_options WHERE poll_id = ?", (poll["id"],))}
    chosen = set(option_ids)
    if not chosen or not chosen <= valid:
        raise ValueError("Pick at least one option.")
    if not poll["multi_select"] and len(chosen) > 1:
        raise ValueError("Pick only one option.")
    conn.execute("DELETE FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll["id"], user_id))
    conn.executemany(
        "INSERT INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)",
        [(poll["id"], o, user_id) for o in sorted(chosen)],
    )


def close(conn, poll_id):
    conn.execute("UPDATE polls SET is_closed = 1 WHERE id = ?", (poll_id,))
