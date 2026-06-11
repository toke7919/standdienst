"""add updated_at to admins and organizers

Revision ID: s1t2u3v4w5x6
Revises: r1s2t3u4v5w6
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = 's1t2u3v4w5x6'
down_revision = 'r1s2t3u4v5w6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admins') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))
    with op.batch_alter_table('organizers') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))


def downgrade():
    with op.batch_alter_table('organizers') as batch_op:
        batch_op.drop_column('updated_at')
    with op.batch_alter_table('admins') as batch_op:
        batch_op.drop_column('updated_at')
