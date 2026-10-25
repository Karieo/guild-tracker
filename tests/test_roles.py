import pytest

from guild.models import users
from tests.conftest import post


def _role(db, uid):
    return users.get(db, uid)["role"]


def test_owner_promotes_and_demotes_with_log(login, owner, member, db):
    c = login(owner)
    assert post(c, f"/admin/members/{member['id']}/role", role="officer").status_code == 302
    db.commit()
    assert _role(db, member["id"]) == "officer"
    post(c, f"/admin/members/{member['id']}/role", role="member")
    db.commit()
    assert _role(db, member["id"]) == "member"
    log = users.role_log(db)
    assert [(r["old_role"], r["new_role"], r["actor_name"]) for r in log] == [
        ("officer", "member", "Clay"), ("member", "officer", "Clay")]
    page = c.get("/admin").data
    assert b"Role change log" in page and b"officer" in page


def test_officer_cannot_promote_or_demote(login, officer, member, db):
    c = login(officer)
    assert post(c, f"/admin/members/{member['id']}/role", role="officer").status_code == 403
    assert post(c, f"/admin/members/{officer['id']}/role", role="member").status_code == 403
    assert _role(db, member["id"]) == "member" and _role(db, officer["id"]) == "officer"


def test_member_cannot_change_roles(login, member, officer, db):
    assert post(login(member), f"/admin/members/{officer['id']}/role", role="member").status_code == 403
    assert _role(db, officer["id"]) == "officer"


def test_owner_cannot_be_demoted(login, owner, db):
    assert post(login(owner), f"/admin/members/{owner['id']}/role", role="member").status_code == 403
    assert _role(db, owner["id"]) == "owner"


def test_officer_cannot_demote_owner(login, officer, owner, db):
    assert post(login(officer), f"/admin/members/{owner['id']}/role", role="member").status_code == 403
    assert _role(db, owner["id"]) == "owner"


def test_cannot_make_someone_owner(login, owner, member, db):
    post(login(owner), f"/admin/members/{member['id']}/role", role="owner")
    assert _role(db, member["id"]) == "member"


def test_model_enforces_rules_too(db, owner, officer, member):
    with pytest.raises(PermissionError):
        users.change_role(db, officer, member["id"], "officer")
    with pytest.raises(PermissionError):
        users.change_role(db, owner, owner["id"], "member")


def test_demoted_officer_loses_access_on_next_request(login, owner, officer, db):
    off = login(officer)  # session established while still an officer
    assert off.get("/admin").status_code == 200
    assert off.get("/announcements").status_code == 200
    post(login(owner), f"/admin/members/{officer['id']}/role", role="member")
    db.commit()
    assert off.get("/admin").status_code == 403
    assert off.get("/announcements").status_code == 403
    assert post(off, "/polls/new", question="Q", options="a\nb").status_code == 403
    assert off.get("/roster").status_code == 200  # still a normal member


def test_promoted_member_gains_access_immediately(login, owner, member, db):
    m = login(member)
    assert m.get("/admin").status_code == 403
    post(login(owner), f"/admin/members/{member['id']}/role", role="officer")
    db.commit()
    assert m.get("/admin").status_code == 200


def test_officer_sees_admin_but_not_role_controls(login, officer, member):
    page = login(officer).get("/admin").data
    assert b"Role change log" not in page and b"Promote" not in page


def test_owner_status_follows_config_not_db(login, owner, db):
    db.execute("UPDATE users SET role = 'member' WHERE id = ?", (owner["id"],))
    db.commit()
    assert login(owner).get("/admin").status_code == 200  # self-heals back to owner
    db.commit()
    assert _role(db, owner["id"]) == "owner"


def test_stale_owner_role_removed_when_config_changes(app, login, make_user, db):
    ex_owner = make_user("7777", "Ex", "owner")  # not the configured owner
    assert login(ex_owner).get("/admin").status_code == 403
    assert _role(db, ex_owner["id"]) == "member"


def test_announcements_officer_only(login, member, officer, monkeypatch):
    from guild import discord_webhook
    sent = []
    monkeypatch.setattr(discord_webhook.requests, "post", lambda *a, **k: sent.append(k) or type("R", (), {"ok": True})())
    app_url = "/announcements"
    assert post(login(member), app_url, title="T", body="B").status_code == 403
    assert not sent
