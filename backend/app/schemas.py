from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    role: str
    display_name: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut
    demo: bool = False


class TelegramAuthIn(BaseModel):
    init_data: str = Field(alias="initData")

    model_config = {"populate_by_name": True}


class DemoAuthIn(BaseModel):
    as_role: str | None = Field(default=None, alias="as")
    telegram_id: int | None = None

    model_config = {"populate_by_name": True}


class GoalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    weight_percent: int = Field(ge=1, le=100)
    assignee_id: uuid.UUID | None = None


class InviteCreate(BaseModel):
    telegram_id: int | None = None


class InviteRedeem(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class FileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    kind: str
    url: str


class EvidenceOut(BaseModel):
    id: uuid.UUID
    proof_note: str
    created_at: datetime
    uploaded_by: UserOut
    files: list[FileOut]


class TaskOut(BaseModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    goal_name: str
    title: str
    description: str | None
    weight_percent: int
    status: str
    assignee: UserOut
    reject_reason: str | None
    created_at: datetime
    closed_at: datetime | None
    latest_evidence: EvidenceOut | None = None


class GoalListOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    progress_percent: int
    allocated_weight: int
    remaining_weight: int
    pending_reviews: int
    members_count: int
    created_at: datetime


class GoalDetailOut(GoalListOut):
    owner: UserOut
    members: list[UserOut]
    tasks: list[TaskOut]


class InviteOut(BaseModel):
    id: uuid.UUID
    code: str
    telegram_id: int | None
    used: bool
    added_immediately: bool = False
    deep_link: str
