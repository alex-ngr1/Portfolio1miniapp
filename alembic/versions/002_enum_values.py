"""store enum values, not names

Revision ID: 002_enum_values
Revises: 001_initial
Create Date: 2026-09-13

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_enum_values"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'owner' WHERE role IN ('OWNER', 'Owner')")
    op.execute("UPDATE users SET role = 'worker' WHERE role IN ('WORKER', 'Worker')")
    op.execute("UPDATE tasks SET status = 'open' WHERE status IN ('OPEN', 'Open')")
    op.execute("UPDATE tasks SET status = 'awaiting_review' WHERE status IN ('AWAITING_REVIEW', 'Awaiting_review')")
    op.execute("UPDATE tasks SET status = 'closed' WHERE status IN ('CLOSED', 'Closed')")
    op.execute("UPDATE evidence_files SET kind = 'photo' WHERE kind IN ('PHOTO', 'Photo')")
    op.execute("UPDATE evidence_files SET kind = 'video' WHERE kind IN ('VIDEO', 'Video')")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'OWNER' WHERE role = 'owner'")
    op.execute("UPDATE users SET role = 'WORKER' WHERE role = 'worker'")
    op.execute("UPDATE tasks SET status = 'OPEN' WHERE status = 'open'")
    op.execute("UPDATE tasks SET status = 'AWAITING_REVIEW' WHERE status = 'awaiting_review'")
    op.execute("UPDATE tasks SET status = 'CLOSED' WHERE status = 'closed'")
    op.execute("UPDATE evidence_files SET kind = 'PHOTO' WHERE kind = 'photo'")
    op.execute("UPDATE evidence_files SET kind = 'VIDEO' WHERE kind = 'video'")
