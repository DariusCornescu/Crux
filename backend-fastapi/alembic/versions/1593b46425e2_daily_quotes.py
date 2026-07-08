"""daily quotes

Revision ID: 1593b46425e2
Revises: e4e98d2a95f1
Create Date: 2026-07-08 17:28:19.767660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1593b46425e2'
down_revision: Union[str, None] = 'e4e98d2a95f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
    )
    op.create_index("ix_daily_quotes_day", "daily_quotes", ["day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_daily_quotes_day", table_name="daily_quotes")
    op.drop_table("daily_quotes")
