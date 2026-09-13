from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.access import require_owner, require_task
from app.auth import current_user
from app.config import settings
from app.db import get_db
from app.models import Evidence, EvidenceFile, FileKind, Task, TaskStatus, User
from app.schemas import RejectIn, TaskOut
from app.serializers import task_out

router = APIRouter(prefix="/api", tags=["tasks"])

PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED = PHOTO_TYPES | VIDEO_TYPES


def _load_task(db: Session, task_id) -> Task:
    task = (
        db.query(Task)
        .options(
            joinedload(Task.assignee),
            joinedload(Task.goal),
            joinedload(Task.evidence).joinedload(Evidence.files),
            joinedload(Task.evidence).joinedload(Evidence.uploaded_by),
        )
        .filter(Task.id == task_id)
        .one_or_none()
    )
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Етап не знайдено")
    return task


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = _load_task(db, task_id)
    if task.goal.owner_id != user.id and task.assignee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Це не ваш етап")
    return task_out(task)


@router.post("/tasks/{task_id}/evidence", response_model=TaskOut)
async def upload_evidence(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
    proof_note: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
):
    task = _load_task(db, task_id)
    if task.assignee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Докази завантажує виконавець етапу")
    if task.status == TaskStatus.CLOSED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Етап уже закрито")
    note = (proof_note or "").strip()
    if len(note) < 8:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Потрібна коротка примітка про перевірку, що все працює як треба.",
        )
    incoming = [f for f in files if f.filename]
    if not incoming:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Додайте фото або відео як доказ")

    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)

    evidence = Evidence(task_id=task.id, uploaded_by_id=user.id, proof_note=note)
    db.add(evidence)
    db.flush()

    for upload in incoming:
        content_type = upload.content_type or "application/octet-stream"
        if content_type not in ALLOWED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Тип файлу не підтримується: {content_type}")
        data = await upload.read()
        if not data:
            continue
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл завеликий (ліміт 25 МБ)")
        kind = FileKind.PHOTO if content_type in PHOTO_TYPES else FileKind.VIDEO
        stored = f"{evidence.id}-{uuid.uuid4().hex}{Path(upload.filename or '').suffix.lower()}"
        (folder / stored).write_bytes(data)
        db.add(
            EvidenceFile(
                evidence_id=evidence.id,
                stored_name=stored,
                original_name=upload.filename or stored,
                mime_type=content_type,
                kind=kind,
                size_bytes=len(data),
            )
        )

    task.status = TaskStatus.AWAITING_REVIEW
    task.reject_reason = None
    db.commit()
    return task_out(_load_task(db, task.id))


@router.post("/tasks/{task_id}/close", response_model=TaskOut)
def close_task(
    task_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = _load_task(db, task_id)
    require_owner(user, task.goal)
    if task.status != TaskStatus.AWAITING_REVIEW:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Закрити можна лише етап на перевірці")
    if not task.evidence:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Немає доказів для закриття")
    task.status = TaskStatus.CLOSED
    task.closed_at = datetime.now(timezone.utc)
    task.closed_by_id = user.id
    task.reject_reason = None
    db.commit()
    return task_out(_load_task(db, task.id))


@router.post("/tasks/{task_id}/reject", response_model=TaskOut)
def reject_task(
    task_id: uuid.UUID,
    body: RejectIn,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = _load_task(db, task_id)
    require_owner(user, task.goal)
    if task.status != TaskStatus.AWAITING_REVIEW:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Відхилити можна лише етап на перевірці")
    task.status = TaskStatus.OPEN
    task.reject_reason = body.reason.strip()
    task.closed_at = None
    task.closed_by_id = None
    db.commit()
    return task_out(_load_task(db, task.id))
