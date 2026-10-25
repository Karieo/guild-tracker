ASSIGNABLE_ROLES = ("member", "officer")


def get(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def all(conn):
    return conn.execute(
        "SELECT * FROM users ORDER BY role = 'owner' DESC, role = 'officer' DESC, name COLLATE NOCASE"
    ).fetchall()


def upsert_discord(conn, discord_id, name, avatar):
    row = conn.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,)).fetchone()
    if row:
        conn.execute("UPDATE users SET name = ?, avatar = ? WHERE id = ?", (name, avatar, row["id"]))
        return get(conn, row["id"])
    cur = conn.execute(
        "INSERT INTO users (discord_id, name, avatar) VALUES (?, ?, ?)", (discord_id, name, avatar)
    )
    return get(conn, cur.lastrowid)


def sync_owner(conn, user, owner_discord_id):
    """The owner is whoever OWNER_DISCORD_ID names, and nobody else."""
    is_owner = bool(owner_discord_id) and user["discord_id"] == owner_discord_id
    if is_owner and user["role"] != "owner":
        want = "owner"
    elif not is_owner and user["role"] == "owner":
        want = "member"
    else:
        return user
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (want, user["id"]))
    return get(conn, user["id"])


def change_role(conn, actor, target_id, new_role):
    """Owner-only promote/demote between member and officer, logged."""
    if actor["role"] != "owner":
        raise PermissionError("Only the owner can change roles.")
    if new_role not in ASSIGNABLE_ROLES:
        raise ValueError("Role must be member or officer.")
    target = get(conn, target_id)
    if target is None:
        raise ValueError("No such member.")
    if target["role"] == "owner":
        raise PermissionError("The owner's role can't be changed.")
    if target["role"] == new_role:
        raise ValueError(f"{target['name']} is already {new_role}.")
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_id))
    conn.execute(
        "INSERT INTO role_changes (user_id, old_role, new_role, changed_by) VALUES (?, ?, ?, ?)",
        (target_id, target["role"], new_role, actor["id"]),
    )
    return get(conn, target_id)


def role_log(conn, limit=100):
    return conn.execute(
        "SELECT rc.*, t.name AS target_name, a.name AS actor_name FROM role_changes rc "
        "JOIN users t ON t.id = rc.user_id JOIN users a ON a.id = rc.changed_by "
        "ORDER BY rc.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
