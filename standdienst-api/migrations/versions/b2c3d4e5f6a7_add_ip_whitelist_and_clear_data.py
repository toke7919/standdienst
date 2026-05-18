"""add ip_whitelist to global_settings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('global_settings', sa.Column('ip_whitelist', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('global_settings', 'ip_whitelist')
