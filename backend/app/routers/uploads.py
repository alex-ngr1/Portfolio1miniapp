from pathlib import Path
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload

from app.access import is_member
from app.auth import bearer
from app.config import settings
from app.db import get_db
from app.models import Evidence, EvidenceFile, Task, User
import jwt

router = APIRouter(prefix="/api", tags=["uploads"])


def _user_from_token(db: Session, raw: str) -> User | None:
    try:
        payload = jwt.decode(raw, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return db.get(User, uuid.UUID(str(payload.get("sub"))))
    except jwt.PyJWTError:
        return None


@router.get("/uploads/{file_id}")
def get_upload(
    file_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    token: Annotated[str | None, Query()] = None,
):
    raw = creds.credentials if creds else token
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Потрібен токен")
    user = _user_from_token(db, raw)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалідний токен")
    row = (
        db.query(EvidenceFile)
        .options(joinedload(EvidenceFile.evidence).joinedload(Evidence.task).joinedload(Task.goal))
        .filter(EvidenceFile.id == file_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не знайдено")
    task = row.evidence.task
    if task.goal.owner_id != user.id and task.assignee_id != user.id and not is_member(db, user, task.goal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Немає доступу до файлу")
    path = Path(settings.upload_dir) / row.stored_name
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл відсутній на диску")
    return FileResponse(path, media_type=row.mime_type, filename=row.original_name)
