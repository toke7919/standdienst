"""add notifications_enabled to volunteers

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'l1m2n3o4p5q6'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('volunteers',
        sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('volunteers', 'notifications_enabled')
