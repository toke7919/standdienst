"""add volunteer.updated_at, global_settings.volunteer_retention_months + timezone

Revision ID: c3d7e8f2a5b6
Revises: a4f2c9e1d7b3
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d7e8f2a5b6'
down_revision = 'a4f2c9e1d7b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('volunteers') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ))

    # Bestehende Zeilen mit created_at befüllen
    op.execute("UPDATE volunteers SET updated_at = created_at WHERE updated_at IS NULL")

    with op.batch_alter_table('global_settings') as batch_op:
        batch_op.add_column(sa.Column(
            'timezone',
            sa.String(100),
            nullable=False,
            server_default='Europe/Berlin',
        ))
        batch_op.add_column(sa.Column(
            'volunteer_retention_months',
            sa.Integer,
            nullable=True,
        ))


def downgrade():
    with op.batch_alter_table('global_settings') as batch_op:
        batch_op.drop_column('volunteer_retention_months')
        batch_op.drop_column('timezone')

    with op.batch_alter_table('volunteers') as batch_op:
        batch_op.drop_column('updated_at')
