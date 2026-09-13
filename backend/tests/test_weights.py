from app.models import UserRole
from tests.conftest import add_member, auth_header, create_user


def _setup(client, db_session):
    owner = create_user(db_session, 1001, UserRole.OWNER, "Марина", "Гнатюк")
    worker = create_user(db_session, 1002, UserRole.WORKER, "Олена", "Коваль")
    headers = auth_header(client, 1001)
    goal = client.post("/api/goals", json={"name": "Тестова ціль", "description": "x"}, headers=headers)
    assert goal.status_code == 201, goal.text
    goal_id = goal.json()["id"]
    add_member(db_session, goal_id, worker.id)
    return owner, worker, goal_id, headers, auth_header(client, 1002)


def test_weights_cannot_exceed_100(client, db_session):
    _, _, goal_id, _, worker_headers = _setup(client, db_session)
    first = client.post(
        f"/api/goals/{goal_id}/tasks",
        json={"title": "Етап 1", "weight_percent": 60},
        headers=worker_headers,
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/goals/{goal_id}/tasks",
        json={"title": "Етап 2", "weight_percent": 40},
        headers=worker_headers,
    )
    assert second.status_code == 201
    overflow = client.post(
        f"/api/goals/{goal_id}/tasks",
        json={"title": "Зайве", "weight_percent": 1},
        headers=worker_headers,
    )
    assert overflow.status_code == 400
    assert "100" in overflow.json()["detail"]

    detail = client.get(f"/api/goals/{goal_id}", headers=worker_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["allocated_weight"] == 100
    assert body["remaining_weight"] == 0


def test_weight_sum_exactly_100_ok(client, db_session):
    _, _, goal_id, _, worker_headers = _setup(client, db_session)
    res = client.post(
        f"/api/goals/{goal_id}/tasks",
        json={"title": "Усе одразу", "weight_percent": 100},
        headers=worker_headers,
    )
    assert res.status_code == 201
    detail = client.get(f"/api/goals/{goal_id}", headers=worker_headers).json()
    assert detail["allocated_weight"] == 100


def test_weight_zero_rejected(client, db_session):
    _, _, goal_id, _, worker_headers = _setup(client, db_session)
    res = client.post(
        f"/api/goals/{goal_id}/tasks",
        json={"title": "Нуль", "weight_percent": 0},
        headers=worker_headers,
    )
    assert res.status_code == 422
