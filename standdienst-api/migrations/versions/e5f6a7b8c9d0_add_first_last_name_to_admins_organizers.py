"""add first_name and last_name to admins and organizers

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('admins', sa.Column('first_name', sa.String(50), nullable=True))
    op.add_column('admins', sa.Column('last_name', sa.String(50), nullable=True))
    op.add_column('organizers', sa.Column('first_name', sa.String(50), nullable=True))
    op.add_column('organizers', sa.Column('last_name', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('organizers', 'last_name')
    op.drop_column('organizers', 'first_name')
    op.drop_column('admins', 'last_name')
    op.drop_column('admins', 'first_name')
