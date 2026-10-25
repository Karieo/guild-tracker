import sqlite3

import pytest

from guild.models import polls
from tests.conftest import post


@pytest.fixture
def poll(db, officer):
    pid = polls.create(db, "Raid night?", ["Tue", "Wed", "Thu"], officer["id"], None, False)
    db.commit()
    return pid


def _opts(db, pid):
    return [r["id"] for r in db.execute("SELECT id FROM poll_options WHERE poll_id = ?", (pid,))]


def test_members_cannot_create_polls(login, member):
    r = post(login(member), "/polls/new", question="Q?", options="a\nb")
    assert r.status_code == 403


def test_officer_creates_poll(login, officer, db):
    r = post(login(officer), "/polls/new", question="Q?", options="a\nb\n\nc", multi_select="1")
    assert r.status_code == 302
    db.commit()
    p = db.execute("SELECT * FROM polls").fetchone()
    assert p["multi_select"] == 1 and len(_opts(db, p["id"])) == 3


def test_poll_needs_two_options(login, officer):
    assert post(login(officer), "/polls/new", question="Q?", options="only one").status_code == 400


def test_one_vote_per_user_and_vote_can_change(login, member, poll, db):
    c = login(member)
    a, b, _ = _opts(db, poll)
    post(c, f"/polls/{poll}/vote", option=str(a))
    post(c, f"/polls/{poll}/vote", option=str(b))  # change, not add
    db.commit()
    rows = db.execute("SELECT option_id FROM poll_votes WHERE user_id = ?", (member["id"],)).fetchall()
    assert [r["option_id"] for r in rows] == [b]


def test_single_choice_rejects_two_options(login, member, poll, db):
    a, b, _ = _opts(db, poll)
    post(login(member), f"/polls/{poll}/vote", option=[str(a), str(b)])
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM poll_votes").fetchone()[0] == 0


def test_db_itself_enforces_single_choice(db, member, poll):
    a, b, _ = _opts(db, poll)
    db.execute("INSERT INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)", (poll, a, member["id"]))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)", (poll, b, member["id"]))
    with pytest.raises(sqlite3.IntegrityError):  # same option twice
        db.execute("INSERT INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)", (poll, a, member["id"]))


def test_multi_select_allows_several(login, member, officer, db):
    pid = polls.create(db, "Pick", ["x", "y", "z"], officer["id"], None, True)
    db.commit()
    a, b, _ = _opts(db, pid)
    post(login(member), f"/polls/{pid}/vote", option=[str(a), str(b)])
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM poll_votes WHERE user_id = ?", (member["id"],)).fetchone()[0] == 2


def test_no_votes_after_close(login, officer, member, poll, db):
    a = _opts(db, poll)[0]
    assert post(login(officer), f"/polls/{poll}/close").status_code == 302
    post(login(member), f"/polls/{poll}/vote", option=str(a))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM poll_votes").fetchone()[0] == 0


def test_expired_poll_is_closed(db, officer):
    pid = polls.create(db, "Old", ["a", "b"], officer["id"], "2000-01-01 00:00:00", False)
    assert not polls.is_open(polls.get(db, pid))


def test_results_show_who_voted(login, member, poll, db):
    a = _opts(db, poll)[0]
    c = login(member)
    post(c, f"/polls/{poll}/vote", option=str(a))
    page = c.get(f"/polls/{poll}")
    assert page.status_code == 200 and member["name"].encode() in page.data


def test_cannot_vote_for_option_of_another_poll(login, member, officer, poll, db):
    other = polls.create(db, "Other", ["p", "q"], officer["id"], None, False)
    db.commit()
    foreign = _opts(db, other)[0]
    post(login(member), f"/polls/{poll}/vote", option=str(foreign))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM poll_votes").fetchone()[0] == 0
