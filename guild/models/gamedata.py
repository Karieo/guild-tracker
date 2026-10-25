def classes(conn):
    return conn.execute("SELECT * FROM game_classes ORDER BY sort, name").fetchall()


def class_colors(conn):
    return {r["name"]: r["color"] for r in classes(conn)}


def races(conn, faction):
    return conn.execute(
        "SELECT * FROM races WHERE faction = ? ORDER BY sort, name", (faction,)
    ).fetchall()


def professions(conn):
    return conn.execute("SELECT * FROM professions ORDER BY kind = 'secondary', sort, name").fetchall()
