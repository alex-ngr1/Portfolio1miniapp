from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    WORKER = "worker"


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    AWAITING_REVIEW = "awaiting_review"
    CLOSED = "closed"


class FileKind(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), default=UserRole.WORKER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owned_goals: Mapped[list[Goal]] = relationship(back_populates="owner")
    memberships: Mapped[list[GoalMember]] = relationship(back_populates="user")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="owned_goals")
    members: Mapped[list[GoalMember]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    tasks: Mapped[list[Task]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    invites: Mapped[list[Invite]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class GoalMember(Base):
    __tablename__ = "goal_members"
    __table_args__ = (UniqueConstraint("goal_id", "user_id", name="uq_goal_member"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goal: Mapped[Goal] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    used_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goal: Mapped[Goal] = relationship(back_populates="invites")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    weight_percent: Mapped[int] = mapped_column(Integer)
    assignee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), default=TaskStatus.OPEN, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    goal: Mapped[Goal] = relationship(back_populates="tasks")
    assignee: Mapped[User] = relationship(foreign_keys=[assignee_id])
    evidence: Mapped[list[Evidence]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), index=True)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    proof_note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[Task] = relationship(back_populates="evidence")
    files: Mapped[list[EvidenceFile]] = relationship(back_populates="evidence", cascade="all, delete-orphan")
    uploaded_by: Mapped[User] = relationship(foreign_keys=[uploaded_by_id])


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id"), index=True)
    stored_name: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    kind: Mapped[FileKind] = mapped_column(Enum(FileKind, native_enum=False))
    size_bytes: Mapped[int] = mapped_column(Integer)

    evidence: Mapped[Evidence] = relationship(back_populates="files")
