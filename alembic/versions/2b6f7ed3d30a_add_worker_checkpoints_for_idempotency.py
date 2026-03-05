"""add worker checkpoints for idempotency

Revision ID: 2b6f7ed3d30a
Revises: 63ce5d994671
Create Date: 2026-03-05 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b6f7ed3d30a"
down_revision: Union[str, Sequence[str], None] = "63ce5d994671"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "worker_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("worker_name", sa.String(length=50), nullable=False),
        sa.Column("event_key", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_name", "event_key", name="uq_worker_event"),
    )
    op.create_index(op.f("ix_worker_checkpoints_id"), "worker_checkpoints", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_worker_checkpoints_id"), table_name="worker_checkpoints")
    op.drop_table("worker_checkpoints")
