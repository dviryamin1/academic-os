"""Add curriculum item code and pages.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("curriculum_items") as batch_operation:
        batch_operation.add_column(
            sa.Column("code", sa.String(), nullable=True)
        )
        batch_operation.add_column(
            sa.Column("pages", sa.String(), nullable=True)
        )

    curriculum_items = sa.table(
        "curriculum_items",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    op.execute(
        curriculum_items.update()
        .where(curriculum_items.c.code.is_(None))
        .values(code=sa.cast(curriculum_items.c.id, sa.String()))
    )

    with op.batch_alter_table("curriculum_items") as batch_operation:
        batch_operation.alter_column(
            "code",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("curriculum_items") as batch_operation:
        batch_operation.drop_column("pages")
        batch_operation.drop_column("code")

