WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def for_user(conn, user_id):
    return {
        (r["weekday"], r["block"])
        for r in conn.execute(
            "SELECT weekday, block FROM availability WHERE user_id = ? AND available = 1", (user_id,)
        )
    }


def save(conn, user_id, checked, blocks):
    """`checked` is a set of (weekday, block). Writes every cell so unchecking sticks."""
    conn.execute("DELETE FROM availability WHERE user_id = ?", (user_id,))
    conn.executemany(
        "INSERT INTO availability (user_id, weekday, block, available) VALUES (?, ?, ?, ?)",
        [(user_id, d, b, 1 if (d, b) in checked else 0) for d in range(7) for b in blocks],
    )


def summary(conn):
    """{(weekday, block): {total, tanks, healers}} counting each person's main's role."""
    out = {}
    for r in conn.execute(
        "SELECT a.weekday, a.block, COUNT(*) AS total, "
        "COALESCE(SUM(c.role = 'Tank'), 0) AS tanks, COALESCE(SUM(c.role = 'Healer'), 0) AS healers "
        "FROM availability a LEFT JOIN characters c ON c.user_id = a.user_id AND c.is_main = 1 "
        "WHERE a.available = 1 GROUP BY a.weekday, a.block"
    ):
        out[(r["weekday"], r["block"])] = {
            "total": r["total"], "tanks": r["tanks"], "healers": r["healers"]
        }
    return out
