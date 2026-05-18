"""add name to admins

Revision ID: a1b2c3d4e5f6
Revises: f3a8c2e6b1d5
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f3a8c2e6b1d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('admins', sa.Column('name', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('admins', 'name')
