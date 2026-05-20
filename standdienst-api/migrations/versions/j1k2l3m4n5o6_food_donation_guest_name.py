"""Add guest_name to food_donations, make volunteer_id nullable

Revision ID: j1k2l3m4n5o6
Revises: i1j2k3l4m5n6
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'j1k2l3m4n5o6'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('food_donations') as batch_op:
        batch_op.add_column(sa.Column('guest_name', sa.String(100), nullable=True))
        batch_op.alter_column('volunteer_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('food_donations') as batch_op:
        batch_op.drop_column('guest_name')
        batch_op.alter_column('volunteer_id', existing_type=sa.Integer(), nullable=False)
