"""daily moods

Revision ID: c2a265f9dbc4
Revises: 1593b46425e2
Create Date: 2026-07-09 16:02:10.108722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2a265f9dbc4'
down_revision: Union[str, None] = '1593b46425e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_moods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("phrase", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
    )
    op.create_index("ix_daily_moods_day", "daily_moods", ["day"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_daily_moods_day", table_name="daily_moods")
    op.drop_table("daily_moods")
