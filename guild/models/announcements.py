def all_announcements(conn):
    return conn.execute(
        "SELECT a.*, u.name AS poster_name FROM announcements a JOIN users u ON u.id = a.posted_by "
        "ORDER BY a.id DESC"
    ).fetchall()


def create(conn, title, body, posted_by):
    return conn.execute(
        "INSERT INTO announcements (title, body, posted_by) VALUES (?, ?, ?)", (title, body, posted_by)
    ).lastrowid
