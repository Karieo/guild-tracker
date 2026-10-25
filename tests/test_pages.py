import pytest

from tests.conftest import CHAR, post


@pytest.fixture
def populated(login, member, officer, owner):
    post(login(member), "/characters/new", **{**CHAR, "profs": ["Mining", "Herbalism"],
         "skill-Mining": "100", "skill-Herbalism": "50"})
    post(login(officer), "/characters/new", **{**CHAR, "name": "Tanky", "class_name": "Warrior",
         "role": "Tank", "level": "60", "profs": ["Mining"], "skill-Mining": "300"})
    post(login(officer), "/characters/new", **{**CHAR, "name": "Alt", "is_main": ""})
    post(login(officer), "/polls/new", question="When?", options="Tue\nWed")
    return login(owner)


@pytest.mark.parametrize("url", [
    "/characters", "/characters/new", "/roster", "/roster?alts=1", "/leveling", "/professions",
    "/professions?mains=1", "/polls", "/polls/1", "/polls/new", "/availability",
    "/announcements", "/admin",
])
def test_every_page_renders(populated, url):
    assert populated.get(url).status_code == 200


def test_roster_and_leveling_content(populated):
    roster = populated.get("/roster").data
    assert b"Thrall" in roster and b"Tanky" in roster and b"1</b> tanks" in roster
    assert b"<b>1</b> of 2 mains at 60" in populated.get("/leveling").data


def test_professions_flags_gaps(populated):
    page = populated.get("/professions").data
    assert b"Nobody has:" in page and b"Alchemy" in page and b"Mining" in page


def test_missing_poll_is_404(populated):
    assert populated.get("/polls/999").status_code == 404
