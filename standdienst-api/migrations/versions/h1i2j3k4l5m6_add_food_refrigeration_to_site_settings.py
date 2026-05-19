"""Add food_refrigeration_enabled to site_settings

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'h1i2j3k4l5m6'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings') as batch_op:
        batch_op.add_column(sa.Column(
            'food_refrigeration_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='true',
        ))


def downgrade():
    with op.batch_alter_table('site_settings') as batch_op:
        batch_op.drop_column('food_refrigeration_enabled')
