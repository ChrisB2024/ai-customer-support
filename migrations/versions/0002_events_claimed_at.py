"""events.claimed_at: when the current processing attempt started

Lets start_event reclaim events stuck in 'processing' after a crash.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("alter table events add column claimed_at timestamptz not null default now()")


def downgrade() -> None:
    op.execute("alter table events drop column claimed_at")
