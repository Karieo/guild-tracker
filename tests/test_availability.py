from guild.models import availability, characters
from tests.conftest import CHAR, post


def test_save_and_reload(login, member, db):
    c = login(member)
    post(c, "/availability", cell=["0|6–8pm", "4|8–10pm"])
    db.commit()
    assert availability.for_user(db, member["id"]) == {(0, "6–8pm"), (4, "8–10pm")}
    post(c, "/availability", cell=["4|8–10pm"])  # unchecking sticks
    db.commit()
    assert availability.for_user(db, member["id"]) == {(4, "8–10pm")}


def test_ignores_bogus_cells(login, member, db):
    post(login(member), "/availability", cell=["9|6–8pm", "0|not a block", "junk"])
    db.commit()
    assert availability.for_user(db, member["id"]) == set()


def test_heatmap_counts_tanks_and_healers(login, member, officer, db):
    post(login(member), "/characters/new", **{**CHAR, "role": "Tank"})
    post(login(officer), "/characters/new", **{**CHAR, "name": "Heals", "role": "Healer"})
    post(login(member), "/availability", cell=["2|8–10pm"])
    post(login(officer), "/availability", cell=["2|8–10pm"])
    db.commit()
    s = availability.summary(db)[(2, "8–10pm")]
    assert s == {"total": 2, "tanks": 1, "healers": 1}
    assert login(member).get("/availability").status_code == 200
