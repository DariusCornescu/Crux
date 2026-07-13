"""daily reflections

Revision ID: b7c1e2d3f4a5
Revises: c2a265f9dbc4
Create Date: 2026-07-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1e2d3f4a5'
down_revision: Union[str, None] = 'c2a265f9dbc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_reflections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
    )
    op.create_index("ix_daily_reflections_day", "daily_reflections", ["day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_daily_reflections_day", table_name="daily_reflections")
    op.drop_table("daily_reflections")
