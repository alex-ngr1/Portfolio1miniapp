from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.invites import add_member
from app.models import (
    Evidence,
    EvidenceFile,
    FileKind,
    Goal,
    Task,
    TaskStatus,
    User,
    UserRole,
)

DEMO_GOAL_NAME = "Будинок №24"

# Мінімальний валідний JPEG 1×1, достатній для демо-прев’ю в галереї.
_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c191213"
    "0f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc000110800010001"
    "03012200021101031101ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b510"
    "0002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f0"
    "2433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a63646566676869"
    "6a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5"
    "c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda000c03010002110311003f00"
    "f7fa28a2803fffd9"
)


def _write_demo_file(name: str) -> tuple[str, int]:
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"seed-{name}"
    path = folder / stored
    if not path.exists():
        path.write_bytes(_JPEG)
    return stored, path.stat().st_size


def seed_demo(db: Session) -> None:
    existing = db.query(Goal).filter(Goal.name == DEMO_GOAL_NAME).one_or_none()
    if existing:
        return

    owner = db.query(User).filter(User.telegram_id == settings.owner_telegram_id).one_or_none()
    if owner is None:
        owner = User(
            telegram_id=settings.owner_telegram_id,
            username="golovnyy",
            first_name="Марина",
            last_name="Гнатюк",
            role=UserRole.OWNER,
        )
        db.add(owner)
        db.flush()
    else:
        owner.role = UserRole.OWNER

    workers_spec = [
        (1002, "olena_koval", "Олена", "Коваль"),
        (1003, "andriy_melnyk", "Андрій", "Мельник"),
        (1004, "ihor_bondar", "Ігор", "Бондар"),
    ]
    workers: list[User] = []
    for tg_id, username, first, last in workers_spec:
        user = db.query(User).filter(User.telegram_id == tg_id).one_or_none()
        if user is None:
            user = User(
                telegram_id=tg_id,
                username=username,
                first_name=first,
                last_name=last,
                role=UserRole.WORKER,
            )
            db.add(user)
            db.flush()
        workers.append(user)

    olena, andriy, ihor = workers
    now = datetime.now(timezone.utc)

    goal = Goal(
        name=DEMO_GOAL_NAME,
        description="Реконструкція житлового будинку, вул. Садова 24. Команда закриває етапи лише після фото/відео та короткої перевірки, що все працює.",
        owner_id=owner.id,
        created_at=now - timedelta(days=18),
    )
    db.add(goal)
    db.flush()

    for worker in workers:
        add_member(db, goal, worker)

    tasks_spec = [
        {
            "title": "Демонтаж старих комунікацій",
            "description": "Зняти зношені стояки, вивезти сміття, підготувати шахти.",
            "weight": 15,
            "assignee": andriy,
            "status": TaskStatus.CLOSED,
            "days_ago": 14,
            "note": "Перевірка: шахти чисті, старі труби зрізано, прохід вільний для нових стояків.",
            "closed_days_ago": 13,
        },
        {
            "title": "Електропроводка 1–2 поверх",
            "description": "Кабель, щиток, розеточні групи, заземлення.",
            "weight": 25,
            "assignee": olena,
            "status": TaskStatus.CLOSED,
            "days_ago": 10,
            "note": "Перевірка: автомати тримають навантаження, УЗО спрацьовує, усі групи підписані в щитку.",
            "closed_days_ago": 8,
        },
        {
            "title": "Водопостачання та каналізація",
            "description": "Нові стояки, розводка кухні й санвузлів, опресовування.",
            "weight": 20,
            "assignee": andriy,
            "status": TaskStatus.AWAITING_REVIEW,
            "days_ago": 6,
            "note": "Перевірка: стояки тримають тиск 6 бар, протікань немає. Лічильники опломбовані, злив іде вільно.",
            "closed_days_ago": None,
        },
        {
            "title": "Штукатурка та стяжка",
            "description": "Стіни під маяки, стяжка підлоги на двох поверхах.",
            "weight": 25,
            "assignee": ihor,
            "status": TaskStatus.OPEN,
            "days_ago": 3,
            "note": None,
            "closed_days_ago": None,
        },
        {
            "title": "Фінішне оздоблення",
            "description": "Фарбування, плінтуси, встановлення сантехніки й розеток.",
            "weight": 15,
            "assignee": ihor,
            "status": TaskStatus.OPEN,
            "days_ago": 1,
            "note": None,
            "closed_days_ago": None,
        },
    ]

    for spec in tasks_spec:
        task = Task(
            id=uuid.uuid4(),
            goal_id=goal.id,
            title=spec["title"],
            description=spec["description"],
            weight_percent=spec["weight"],
            assignee_id=spec["assignee"].id,
            status=spec["status"],
            created_by_id=spec["assignee"].id,
            created_at=now - timedelta(days=spec["days_ago"]),
            closed_at=(now - timedelta(days=spec["closed_days_ago"])) if spec["closed_days_ago"] else None,
            closed_by_id=owner.id if spec["status"] == TaskStatus.CLOSED else None,
        )
        db.add(task)
        db.flush()
        if spec["note"]:
            stored, size = _write_demo_file(f"{task.id}.jpg")
            ev = Evidence(
                task_id=task.id,
                uploaded_by_id=spec["assignee"].id,
                proof_note=spec["note"],
                created_at=now - timedelta(days=max(spec["days_ago"] - 1, 0)),
            )
            db.add(ev)
            db.flush()
            db.add(
                EvidenceFile(
                    evidence_id=ev.id,
                    stored_name=stored,
                    original_name="perevirka.jpg",
                    mime_type="image/jpeg",
                    kind=FileKind.PHOTO,
                    size_bytes=size,
                )
            )

    db.commit()
