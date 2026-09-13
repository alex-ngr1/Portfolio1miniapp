from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("OWNER_TELEGRAM_ID", "1001")
os.environ.setdefault("UPLOAD_DIR", "/tmp/tsilnyk-test-uploads")
os.environ.setdefault("SKIP_SEED", "true")

from app.config import settings  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import GoalMember, User, UserRole  # noqa: E402

settings.demo_mode = True
settings.skip_seed = True
settings.jwt_secret = "test-secret"
settings.upload_dir = Path("/tmp/tsilnyk-test-uploads")
settings.upload_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db, telegram_id: int, role: UserRole, first: str, last: str = "") -> User:
    user = User(
        telegram_id=telegram_id,
        username=first.lower(),
        first_name=first,
        last_name=last or None,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(client: TestClient, telegram_id: int) -> dict[str, str]:
    res = client.post("/api/auth/demo", json={"telegram_id": telegram_id})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


def add_member(db, goal_id, user_id) -> None:
    db.add(GoalMember(goal_id=uuid.UUID(str(goal_id)), user_id=user_id))
    db.commit()
