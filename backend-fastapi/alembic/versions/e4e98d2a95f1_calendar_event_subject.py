"""calendar event subject

Revision ID: e4e98d2a95f1
Revises: 2e51f8fb6006
Create Date: 2026-07-08 17:08:17.886027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4e98d2a95f1'
down_revision: Union[str, None] = '2e51f8fb6006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("calendar_events", sa.Column("subject", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("calendar_events", "subject")
