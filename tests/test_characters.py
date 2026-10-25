from guild.models import characters
from tests.conftest import CHAR, post


def _add(client, **over):
    return post(client, "/characters/new", **{**CHAR, **over})


def test_create_edit_delete(login, member, db):
    c = login(member)
    assert _add(c).status_code == 302
    char = characters.for_user(db, member["id"])[0]
    assert char["name"] == "Thrall" and char["is_main"] == 1  # first char becomes main

    r = post(c, f"/characters/{char['id']}/edit", **{**CHAR, "level": "20", "profs": ["Mining"], "skill-Mining": "150"})
    assert r.status_code == 302
    db.commit()
    char = characters.for_user(db, member["id"])[0]
    assert char["level"] == 20 and char["profs"][0]["profession"] == "Mining" and char["profs"][0]["skill"] == 150

    assert post(c, f"/characters/{char['id']}/delete").status_code == 302
    assert characters.for_user(db, member["id"]) == []


def test_validation_errors(login, member, db):
    c = login(member)
    assert _add(c, name="").status_code == 400
    assert _add(c, level="61").status_code == 400
    assert _add(c, race="Human").status_code == 400  # Alliance race hidden while Horde
    assert _add(c, class_name="Necromancer").status_code == 400
    assert characters.for_user(db, member["id"]) == []


def test_only_one_main_per_user(login, member, db):
    c = login(member)
    _add(c, name="One")
    _add(c, name="Two", is_main="1")
    mains = [x["name"] for x in characters.for_user(db, member["id"]) if x["is_main"]]
    assert mains == ["Two"]


def test_delete_main_promotes_another(login, member, db):
    c = login(member)
    _add(c, name="One")
    _add(c, name="Two")
    post(c, f"/characters/{characters.for_user(db, member['id'])[0]['id']}/delete")
    assert [x["is_main"] for x in characters.for_user(db, member["id"])] == [1]


def test_quick_level_and_status(login, member, db):
    c = login(member)
    _add(c, level="59")
    cid = characters.for_user(db, member["id"])[0]["id"]
    r = c.post(f"/characters/{cid}/level", data={"delta": "1", "csrf_token": "tok"}, headers={"HX-Request": "true"})
    assert r.status_code == 200 and b"char-" in r.data
    char = characters.get(db, cid)
    assert char["level"] == 60 and char["status"] == "60"
    post(c, f"/characters/{cid}/level", delta="5")  # clamps at 60
    assert characters.get(db, cid)["level"] == 60
    post(c, f"/characters/{cid}/level", delta="-1")
    char = characters.get(db, cid)
    assert char["level"] == 59 and char["status"] == "leveling"


def test_members_cannot_touch_others_characters(login, member, make_user, db):
    other = make_user("4000", "Other")
    _add(login(other))
    cid = characters.for_user(db, other["id"])[0]["id"]
    c = login(member)
    assert c.get(f"/characters/{cid}/edit").status_code == 403
    assert post(c, f"/characters/{cid}/delete").status_code == 403
    assert post(c, f"/characters/{cid}/level", delta="1").status_code == 403
    assert characters.get(db, cid) is not None


def test_officer_can_edit_anyones_character(login, officer, member, db):
    _add(login(member))
    cid = characters.for_user(db, member["id"])[0]["id"]
    r = post(login(officer), f"/characters/{cid}/edit?from=admin", **{**CHAR, "name": "Renamed"})
    assert r.status_code == 302 and "/admin" in r.headers["Location"]
    db.commit()
    assert characters.get(db, cid)["name"] == "Renamed"
