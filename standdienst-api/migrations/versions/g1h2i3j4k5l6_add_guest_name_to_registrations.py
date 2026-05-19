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
    with op.batch_alter_table('registrations') as batch_op:
        batch_op.add_column(sa.Column('guest_name', sa.String(100), nullable=True))
        batch_op.alter_column('volunteer_id', nullable=True)


def downgrade():
    with op.batch_alter_table('registrations') as batch_op:
        batch_op.alter_column('volunteer_id', nullable=False)
        batch_op.drop_column('guest_name')
