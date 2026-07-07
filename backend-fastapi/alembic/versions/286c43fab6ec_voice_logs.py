"""voice logs

Revision ID: 286c43fab6ec
Revises: c2257a2f00bd
Create Date: 2026-07-05 01:50:31.071590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '286c43fab6ec'
down_revision: Union[str, None] = 'c2257a2f00bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The 'activitytype' enum already exists in Postgres (created by the
    # baseline migration for activities.type) -- re-creating it here would
    # fail with DuplicateObject. On SQLite enums are plain VARCHAR, so the
    # generic sa.Enum is fine there.
    if op.get_bind().dialect.name == "postgresql":
        session_type = postgresql.ENUM('sprint', 'tempo', 'easy_run', 'hike', 'ruck',
                                       'strength', name='activitytype', create_type=False)
    else:
        session_type = sa.Enum('sprint', 'tempo', 'easy_run', 'hike', 'ruck',
                               'strength', name='activitytype')

    op.create_table('voice_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('activity_id', sa.Integer(), nullable=True),
    sa.Column('lang', sa.String(length=8), nullable=True),
    sa.Column('transcript', sa.Text(), nullable=False),
    sa.Column('perceived_effort', sa.Integer(), nullable=True),
    sa.Column('session_type', session_type, nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('extraction_method', sa.String(length=16), nullable=False),
    sa.Column('extracted', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], name=op.f('fk_voice_logs_activity_id_activities')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_voice_logs'))
    )
    with op.batch_alter_table('voice_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_voice_logs_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    # The enum type is owned by the baseline migration -- only the table goes.
    with op.batch_alter_table('voice_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_voice_logs_created_at'))

    op.drop_table('voice_logs')
