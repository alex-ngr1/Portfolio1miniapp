from io import BytesIO

from app.models import UserRole
from tests.conftest import add_member, auth_header, create_user

JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb00430001010101010101010101010101010101"
    "01010101010101010101010101010101010101010101010101010101010101010101010101010101"
    "01ffc00011080001000103011100021101031101ffc400140001000000000000000000000000000000"
    "08ffc40014100100000000000000000000000000000000ffda000c03010002110311003f00aa"
    "ffd9"
)


def _setup(client, db_session):
    create_user(db_session, 1001, UserRole.OWNER, "Марина")
    worker = create_user(db_session, 1002, UserRole.WORKER, "Олена")
    owner_h = auth_header(client, 1001)
    worker_h = auth_header(client, 1002)
    goal = client.post("/api/goals", json={"name": "Прогрес", "description": "x"}, headers=owner_h).json()
    add_member(db_session, goal["id"], worker.id)
    task = client.post(
        f"/api/goals/{goal['id']}/tasks",
        json={"title": "Крок 20", "weight_percent": 20},
        headers=worker_h,
    ).json()
    return goal["id"], task["id"], owner_h, worker_h


def _upload(client, task_id, worker_h):
    return client.post(
        f"/api/tasks/{task_id}/evidence",
        data={"proof_note": "Перевірка що працює: прогін пройшов, усе як треба."},
        files={"files": ("shot.jpg", BytesIO(JPEG), "image/jpeg")},
        headers=worker_h,
    )


def test_progress_only_increases_on_owner_close(client, db_session):
    goal_id, task_id, owner_h, worker_h = _setup(client, db_session)
    before = client.get(f"/api/goals/{goal_id}", headers=owner_h).json()
    assert before["progress_percent"] == 0

    uploaded = _upload(client, task_id, worker_h)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["status"] == "awaiting_review"

    after_upload = client.get(f"/api/goals/{goal_id}", headers=owner_h).json()
    assert after_upload["progress_percent"] == 0
    assert after_upload["pending_reviews"] == 1

    closed = client.post(f"/api/tasks/{task_id}/close", headers=owner_h)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"

    after_close = client.get(f"/api/goals/{goal_id}", headers=owner_h).json()
    assert after_close["progress_percent"] == 20
    assert after_close["pending_reviews"] == 0


def test_reject_does_not_credit_percent(client, db_session):
    goal_id, task_id, owner_h, worker_h = _setup(client, db_session)
    uploaded = _upload(client, task_id, worker_h)
    assert uploaded.status_code == 200

    rejected = client.post(
        f"/api/tasks/{task_id}/reject",
        json={"reason": "Не видно, що система тримає навантаження."},
        headers=owner_h,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "open"

    after_reject = client.get(f"/api/goals/{goal_id}", headers=owner_h).json()
    assert after_reject["progress_percent"] == 0
    assert after_reject["pending_reviews"] == 0

    again = _upload(client, task_id, worker_h)
    assert again.status_code == 200
    closed = client.post(f"/api/tasks/{task_id}/close", headers=owner_h)
    assert closed.status_code == 200
    assert client.get(f"/api/goals/{goal_id}", headers=owner_h).json()["progress_percent"] == 20
