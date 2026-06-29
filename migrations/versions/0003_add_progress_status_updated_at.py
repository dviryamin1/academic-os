"""Add the progress status update timestamp.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("study_progress") as batch_operation:
        batch_operation.add_column(
            sa.Column(
                "status_updated_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.func.current_timestamp(),
            )
        )

    with op.batch_alter_table("study_progress") as batch_operation:
        batch_operation.alter_column(
            "status_updated_at",
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("study_progress") as batch_operation:
        batch_operation.drop_column("status_updated_at")
