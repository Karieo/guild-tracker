from guild import timeutil

ROLES = ("Tank", "Healer", "DPS")
STATUSES = ("planned", "leveling", "60")
MAX_LEVEL = 60
STALE_DAYS = 7


def get(conn, char_id):
    return conn.execute(
        "SELECT c.*, u.name AS owner_name FROM characters c JOIN users u ON u.id = c.user_id "
        "WHERE c.id = ?",
        (char_id,),
    ).fetchone()


def _with_professions(conn, rows):
    out = [dict(r) for r in rows]
    if not out:
        return out
    ids = [c["id"] for c in out]
    marks = ",".join("?" * len(ids))
    by_char = {}
    for p in conn.execute(
        f"SELECT * FROM character_professions WHERE character_id IN ({marks}) "
        "ORDER BY is_primary DESC, profession",
        ids,
    ):
        by_char.setdefault(p["character_id"], []).append(dict(p))
    for c in out:
        c["profs"] = by_char.get(c["id"], [])
        c["days_stale"] = timeutil.days_since(c["level_updated_at"])
    return out


def for_user(conn, user_id):
    rows = conn.execute(
        "SELECT c.*, u.name AS owner_name FROM characters c JOIN users u ON u.id = c.user_id "
        "WHERE c.user_id = ? ORDER BY c.is_main DESC, c.name COLLATE NOCASE",
        (user_id,),
    ).fetchall()
    return _with_professions(conn, rows)


def all_characters(conn, mains_only=False):
    sql = (
        "SELECT c.*, u.name AS owner_name FROM characters c JOIN users u ON u.id = c.user_id "
        + ("WHERE c.is_main = 1 " if mains_only else "")
        + "ORDER BY c.level DESC, c.name COLLATE NOCASE"
    )
    return _with_professions(conn, conn.execute(sql).fetchall())


def profession_skills(conn, char_id):
    return {
        r["profession"]: r["skill"]
        for r in conn.execute(
            "SELECT profession, skill FROM character_professions WHERE character_id = ?", (char_id,)
        )
    }


def parse_form(conn, form, faction):
    """Validate a character form. Returns (data, professions {name: skill}, errors)."""
    from guild.models import gamedata

    errors = []
    name = form.get("name", "").strip()
    if not name or len(name) > 24:
        errors.append("Name is required (24 characters max).")
    class_name = form.get("class_name", "")
    if class_name not in {c["name"] for c in gamedata.classes(conn)}:
        errors.append("Pick a class.")
    race = form.get("race", "")
    if race not in {r["name"] for r in gamedata.races(conn, faction)}:
        errors.append("Pick a race.")
    role = form.get("role", "")
    if role not in ROLES:
        errors.append("Pick a role.")
    status = form.get("status", "planned")
    if status not in STATUSES:
        errors.append("Pick a status.")
    try:
        level = int(form.get("level", 1))
        if not 1 <= level <= MAX_LEVEL:
            raise ValueError
    except ValueError:
        level = 1
        errors.append("Level must be 1 to 60.")

    known = {p["name"]: p for p in gamedata.professions(conn)}
    profs = {}
    for prof in form.getlist("profs"):
        if prof not in known:
            continue
        try:
            skill = int(form.get(f"skill-{prof}") or 0)
            if not 0 <= skill <= 300:
                raise ValueError
        except ValueError:
            errors.append(f"{prof} skill must be 0 to 300.")
            skill = 0
        profs[prof] = skill

    data = {
        "name": name,
        "class_name": class_name,
        "race": race,
        "role": role,
        "status": status,
        "level": level,
        "spec_note": form.get("spec_note", "").strip()[:80],
        "notes": form.get("notes", "").strip()[:500],
        "is_main": 1 if form.get("is_main") else 0,
    }
    return data, profs, errors


def _normalize_status(level, status):
    if level >= MAX_LEVEL:
        return "60"
    if status == "60":
        return "leveling"
    if status == "planned" and level > 1:
        return "leveling"
    return status


def _set_main(conn, user_id, char_id):
    conn.execute("UPDATE characters SET is_main = 0 WHERE user_id = ? AND id != ?", (user_id, char_id))
    conn.execute("UPDATE characters SET is_main = 1 WHERE id = ?", (char_id,))


def _ensure_main(conn, user_id):
    if conn.execute(
        "SELECT 1 FROM characters WHERE user_id = ? AND is_main = 1", (user_id,)
    ).fetchone():
        return
    first = conn.execute(
        "SELECT id FROM characters WHERE user_id = ? ORDER BY id LIMIT 1", (user_id,)
    ).fetchone()
    if first:
        conn.execute("UPDATE characters SET is_main = 1 WHERE id = ?", (first["id"],))


def _save_professions(conn, char_id, profs):
    kinds = {r["name"]: r["kind"] for r in conn.execute("SELECT name, kind FROM professions")}
    conn.execute("DELETE FROM character_professions WHERE character_id = ?", (char_id,))
    conn.executemany(
        "INSERT INTO character_professions (character_id, profession, skill, is_primary) "
        "VALUES (?, ?, ?, ?)",
        [(char_id, p, s, 1 if kinds[p] == "primary" else 0) for p, s in profs.items()],
    )


def create(conn, user_id, data, profs):
    status = _normalize_status(data["level"], data["status"])
    cur = conn.execute(
        "INSERT INTO characters (user_id, name, class_name, race, role, spec_note, level, "
        "status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, data["name"], data["class_name"], data["race"], data["role"],
         data["spec_note"], data["level"], status, data["notes"]),
    )
    char_id = cur.lastrowid
    _save_professions(conn, char_id, profs)
    if data["is_main"]:
        _set_main(conn, user_id, char_id)
    _ensure_main(conn, user_id)
    return char_id


def update(conn, char_id, data, profs):
    char = get(conn, char_id)
    status = _normalize_status(data["level"], data["status"])
    level_updated = (
        timeutil.now_str() if data["level"] != char["level"] else char["level_updated_at"]
    )
    conn.execute(
        "UPDATE characters SET name = ?, class_name = ?, race = ?, role = ?, spec_note = ?, "
        "level = ?, level_updated_at = ?, status = ?, notes = ? WHERE id = ?",
        (data["name"], data["class_name"], data["race"], data["role"], data["spec_note"],
         data["level"], level_updated, status, data["notes"], char_id),
    )
    _save_professions(conn, char_id, profs)
    if data["is_main"]:
        _set_main(conn, char["user_id"], char_id)
    _ensure_main(conn, char["user_id"])


def set_level(conn, char_id, level):
    char = get(conn, char_id)
    level = max(1, min(MAX_LEVEL, level))
    conn.execute(
        "UPDATE characters SET level = ?, level_updated_at = ?, status = ? WHERE id = ?",
        (level, timeutil.now_str(), _normalize_status(level, char["status"]), char_id),
    )


def delete(conn, char_id):
    char = get(conn, char_id)
    conn.execute("DELETE FROM characters WHERE id = ?", (char_id,))
    _ensure_main(conn, char["user_id"])
