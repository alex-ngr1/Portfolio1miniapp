from app.config import settings
from app.invites import telegram_invite_link
from app.models import UserRole
from tests.conftest import add_member, auth_header, create_user


def test_invite_returns_telegram_deep_link(client, db_session):
    settings.bot_username = "tsilnyk_bot"
    create_user(db_session, 1001, UserRole.OWNER, "Марина")
    worker = create_user(db_session, 1002, UserRole.WORKER, "Олена")
    owner_h = auth_header(client, 1001)
    goal = client.post("/api/goals", json={"name": "Ціль", "description": "x"}, headers=owner_h).json()
    add_member(db_session, goal["id"], worker.id)

    res = client.post(f"/api/goals/{goal['id']}/invites", json={}, headers=owner_h)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["code"]
    assert body["deep_link"] == f"https://t.me/tsilnyk_bot?start={body['code']}"
    assert telegram_invite_link(body["code"]).startswith("https://t.me/tsilnyk_bot?start=")


def test_redeem_same_user_is_idempotent(client, db_session):
    create_user(db_session, 1001, UserRole.OWNER, "Марина")
    create_user(db_session, 1005, UserRole.WORKER, "Настя")
    owner_h = auth_header(client, 1001)
    worker_h = auth_header(client, 1005)
    goal = client.post("/api/goals", json={"name": "Ціль", "description": "x"}, headers=owner_h).json()
    invite = client.post(f"/api/goals/{goal['id']}/invites", json={}, headers=owner_h).json()
    first = client.post("/api/invites/redeem", json={"code": invite["code"]}, headers=worker_h)
    assert first.status_code == 200
    second = client.post("/api/invites/redeem", json={"code": invite["code"]}, headers=worker_h)
    assert second.status_code == 200
    assert second.json()["goal_id"] == goal["id"]
