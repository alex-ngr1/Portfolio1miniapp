from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User, UserRole

bearer = HTTPBearer(auto_error=False)


class TelegramAuthError(ValueError):
    pass


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    if not init_data:
        raise TelegramAuthError("Порожній initData")
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("Немає hash у initData")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise TelegramAuthError("Підпис Telegram невалідний")
    user_raw = parsed.get("user")
    if not user_raw:
        raise TelegramAuthError("У initData немає user")
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("Некоректний user у initData") from exc


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tg": user.telegram_id,
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def upsert_user(db: Session, tg_user: dict) -> User:
    telegram_id = int(tg_user["id"])
    user = db.query(User).filter(User.telegram_id == telegram_id).one_or_none()
    role = UserRole.OWNER if telegram_id == settings.owner_telegram_id else UserRole.WORKER
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name") or "Користувач",
            last_name=tg_user.get("last_name"),
            role=role,
        )
        db.add(user)
    else:
        user.username = tg_user.get("username") or user.username
        user.first_name = tg_user.get("first_name") or user.first_name
        user.last_name = tg_user.get("last_name") if tg_user.get("last_name") is not None else user.last_name
        if telegram_id == settings.owner_telegram_id:
            user.role = UserRole.OWNER
    db.commit()
    db.refresh(user)
    return user


def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Потрібен токен")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалідний токен") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Користувача не знайдено")
    return user
