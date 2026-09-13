from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Goal, GoalMember, Invite, User


def telegram_invite_link(code: str) -> str:
    username = (settings.bot_username or "").lstrip("@").strip()
    payload = code.strip().upper()
    if username:
        return f"https://t.me/{username}?start={payload}"
    return f"https://t.me/?start={payload}"


def generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def add_member(db: Session, goal: Goal, user: User) -> bool:
    exists = (
        db.query(GoalMember)
        .filter(GoalMember.goal_id == goal.id, GoalMember.user_id == user.id)
        .one_or_none()
    )
    if exists or goal.owner_id == user.id:
        return False
    db.add(GoalMember(goal_id=goal.id, user_id=user.id))
    return True


def apply_pending_invites(db: Session, user: User) -> None:
    pending = (
        db.query(Invite)
        .filter(Invite.telegram_id == user.telegram_id, Invite.used_at.is_(None))
        .all()
    )
    now = datetime.now(timezone.utc)
    for invite in pending:
        add_member(db, invite.goal, user)
        invite.used_by_id = user.id
        invite.used_at = now
    if pending:
        db.commit()


def redeem_code(db: Session, user: User, code: str) -> Goal:
    invite = db.query(Invite).filter(Invite.code == code.strip().upper()).one_or_none()
    if invite is None:
        raise ValueError("Код запрошення недійсний")
    if invite.used_at is not None:
        if invite.used_by_id == user.id:
            return invite.goal
        raise ValueError("Цей код уже використано")
    if invite.telegram_id and invite.telegram_id != user.telegram_id:
        raise ValueError("Цей код призначено іншому Telegram-акаунту")
    add_member(db, invite.goal, user)
    invite.used_by_id = user.id
    invite.used_at = datetime.now(timezone.utc)
    db.commit()
    return invite.goal
