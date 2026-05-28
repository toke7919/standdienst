"""add is_draft to event_dates

Revision ID: q1r2s3t4u5v6
Revises: p1q2r3s4t5u6
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'q1r2s3t4u5v6'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('event_dates') as batch_op:
        batch_op.add_column(sa.Column(
            'is_draft', sa.Boolean(), nullable=False,
            server_default=sa.text('false'),
        ))


def downgrade():
    with op.batch_alter_table('event_dates') as batch_op:
        batch_op.drop_column('is_draft')
