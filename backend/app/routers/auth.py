from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import TelegramAuthError, create_token, upsert_user, verify_telegram_init_data
from app.config import settings
from app.db import get_db
from app.invites import apply_pending_invites
from app.models import User, UserRole
from app.schemas import AuthResponse, DemoAuthIn, TelegramAuthIn
from app.serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
def auth_telegram(body: TelegramAuthIn, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    try:
        tg_user = verify_telegram_init_data(body.init_data, settings.bot_token)
    except TelegramAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user = upsert_user(db, tg_user)
    apply_pending_invites(db, user)
    return AuthResponse(token=create_token(user), user=user_out(user), demo=False)


@router.post("/demo", response_model=AuthResponse)
def auth_demo(body: DemoAuthIn, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Демо-вхід вимкнено")
    user: User | None = None
    if body.telegram_id is not None:
        user = db.query(User).filter(User.telegram_id == body.telegram_id).one_or_none()
    elif body.as_role == "owner":
        user = db.query(User).filter(User.role == UserRole.OWNER).order_by(User.created_at).first()
    elif body.as_role == "worker":
        user = db.query(User).filter(User.telegram_id == 1004).one_or_none()
        if user is None:
            user = (
                db.query(User)
                .filter(User.role == UserRole.WORKER)
                .order_by(User.created_at.desc())
                .first()
            )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Демо-користувача не знайдено. Запустіть seed.")
    apply_pending_invites(db, user)
    return AuthResponse(token=create_token(user), user=user_out(user), demo=True)
