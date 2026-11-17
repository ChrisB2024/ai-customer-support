"""initial schema: events, tickets, messages, knowledge_base

Revision ID: 0001
Revises:
Create Date: 2026-11-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        create table events (
          id bigint generated always as identity primary key,
          gmail_message_id text not null unique,
          status text not null default 'processing'
            check (status in ('processing', 'processed', 'skipped', 'failed')),
          attempts int not null default 1,
          error text,
          result jsonb,
          created_at timestamptz not null default now(),
          processed_at timestamptz
        )
    """)

    op.execute("""
        create table tickets (
          id bigint generated always as identity primary key,
          gmail_thread_id text not null unique,
          customer_email text not null,
          subject text not null default '',
          category text,
          status text not null default 'open'
            check (status in ('open', 'answered', 'escalated')),
          proposed_action text,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
    """)

    op.execute("""
        create table messages (
          id bigint generated always as identity primary key,
          ticket_id bigint not null references tickets (id) on delete cascade,
          gmail_message_id text not null unique,
          direction text not null check (direction in ('in', 'out')),
          from_address text not null,
          body text not null,
          created_at timestamptz not null default now()
        )
    """)
    op.execute("create index messages_ticket_id_idx on messages (ticket_id)")

    op.execute("""
        create table knowledge_base (
          id bigint generated always as identity primary key,
          section text not null,
          title text not null,
          content text not null,
          updated_at timestamptz not null default now(),
          unique (section, title)
        )
    """)

    for table in ("events", "tickets", "messages", "knowledge_base"):
        op.execute(f"alter table {table} enable row level security")


def downgrade() -> None:
    # Reverse order: messages references tickets.
    for table in ("knowledge_base", "messages", "tickets", "events"):
        op.execute(f"drop table if exists {table}")
