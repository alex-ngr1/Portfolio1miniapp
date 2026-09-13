"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("role", sa.Enum("OWNER", "WORKER", name="userrole", native_enum=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)

    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goals_owner_id"), "goals", ["owner_id"], unique=False)

    op.create_table(
        "goal_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "user_id", name="uq_goal_member"),
    )
    op.create_index(op.f("ix_goal_members_goal_id"), "goal_members", ["goal_id"], unique=False)
    op.create_index(op.f("ix_goal_members_user_id"), "goal_members", ["user_id"], unique=False)

    op.create_table(
        "invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("used_by_id", sa.Uuid(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.ForeignKeyConstraint(["used_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invites_code"), "invites", ["code"], unique=True)
    op.create_index(op.f("ix_invites_goal_id"), "invites", ["goal_id"], unique=False)
    op.create_index(op.f("ix_invites_telegram_id"), "invites", ["telegram_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight_percent", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "AWAITING_REVIEW", "CLOSED", name="taskstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_assignee_id"), "tasks", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_tasks_goal_id"), "tasks", ["goal_id"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("proof_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_task_id"), "evidence", ["task_id"], unique=False)

    op.create_table(
        "evidence_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.Enum("PHOTO", "VIDEO", name="filekind", native_enum=False), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_files_evidence_id"), "evidence_files", ["evidence_id"], unique=False)


def downgrade() -> None:
    op.drop_table("evidence_files")
    op.drop_table("evidence")
    op.drop_table("tasks")
    op.drop_table("invites")
    op.drop_table("goal_members")
    op.drop_table("goals")
    op.drop_table("users")
