"""daily contributions

Revision ID: c3d4e5f6a7b8
Revises: b7c1e2d3f4a5
Create Date: 2026-07-14 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b7c1e2d3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_contributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_daily_contributions_day", "daily_contributions", ["day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_daily_contributions_day", table_name="daily_contributions")
    op.drop_table("daily_contributions")
