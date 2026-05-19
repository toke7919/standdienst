"""add guest_name to registrations, volunteer_id nullable

Revision ID: g1h2i3j4k5l6
Revises: e5f6a7b8c9d0
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'g1h2i3j4k5l6'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('registrations', sa.Column('guest_name', sa.String(100), nullable=True))
    op.alter_column('registrations', 'volunteer_id', nullable=True)


def downgrade():
    op.alter_column('registrations', 'volunteer_id', nullable=False)
    op.drop_column('registrations', 'guest_name')
