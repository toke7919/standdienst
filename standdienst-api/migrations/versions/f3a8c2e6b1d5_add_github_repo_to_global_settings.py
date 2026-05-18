"""add github_repo to global_settings

Revision ID: f3a8c2e6b1d5
Revises: d9e1f4b2c7a8
Create Date: 2026-05-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a8c2e6b1d5'
down_revision = 'd9e1f4b2c7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('global_settings',
        sa.Column('github_repo', sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column('global_settings', 'github_repo')
