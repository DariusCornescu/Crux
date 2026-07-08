"""listening spotify_track_id

Revision ID: 2e51f8fb6006
Revises: 22f82bca0e98
Create Date: 2026-07-08 13:03:32.422328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e51f8fb6006'
down_revision: Union[str, None] = '22f82bca0e98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listening_sessions",
                  sa.Column("spotify_track_id", sa.String(length=64), nullable=True))
    op.create_index("ix_listening_sessions_spotify_track_id",
                    "listening_sessions", ["spotify_track_id"])


def downgrade() -> None:
    op.drop_index("ix_listening_sessions_spotify_track_id",
                  table_name="listening_sessions")
    op.drop_column("listening_sessions", "spotify_track_id")
