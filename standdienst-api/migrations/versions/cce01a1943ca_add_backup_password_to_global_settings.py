"""add backup_password to global_settings

Revision ID: cce01a1943ca
Revises: 391f62511514
Create Date: 2026-05-26 20:23:42.129536

"""
from alembic import op
import sqlalchemy as sa


revision = 'cce01a1943ca'
down_revision = '391f62511514'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('backup_password', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_column('backup_password')
