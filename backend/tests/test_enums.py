from sqlalchemy import text

from app.models import UserRole
from tests.conftest import add_member, auth_header, create_user


def test_list_goals_worker_when_owner_role_written_lowercase(client, db_session):
    owner = create_user(db_session, 1001, UserRole.OWNER, "Марина", "Гнатюк")
    worker = create_user(db_session, 1002, UserRole.WORKER, "Олена", "Коваль")
    owner_h = auth_header(client, 1001)
    created = client.post("/api/goals", json={"name": "Будинок №8", "description": "x"}, headers=owner_h)
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    add_member(db_session, goal_id, worker.id)

    db_session.execute(text("UPDATE users SET role = 'owner' WHERE telegram_id = 1001"))
    db_session.commit()
    db_session.expire_all()

    stored = db_session.execute(text("SELECT role FROM users WHERE telegram_id = 1001")).scalar()
    assert stored == "owner"
    assert stored != UserRole.OWNER.name

    worker_h = auth_header(client, 1002)
    res = client.get("/api/goals", headers=worker_h)
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["name"] == "Будинок №8"
    assert owner.role == UserRole.OWNER
