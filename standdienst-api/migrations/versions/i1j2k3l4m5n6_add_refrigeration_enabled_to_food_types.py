"""Add refrigeration_enabled to food_donation_types

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'i1j2k3l4m5n6'
down_revision = 'h1i2j3k4l5m6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('food_donation_types') as batch_op:
        batch_op.add_column(sa.Column(
            'refrigeration_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ))


def downgrade():
    with op.batch_alter_table('food_donation_types') as batch_op:
        batch_op.drop_column('refrigeration_enabled')
