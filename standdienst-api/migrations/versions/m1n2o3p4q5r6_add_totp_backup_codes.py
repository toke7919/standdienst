"""add totp_backup_codes to admins and organizers

Revision ID: m1n2o3p4q5r6
Revises: l1m2n3o4p5q6
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'm1n2o3p4q5r6'
down_revision = 'l1m2n3o4p5q6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admins') as batch_op:
        batch_op.add_column(sa.Column('totp_backup_codes', sa.JSON, nullable=True))
    with op.batch_alter_table('organizers') as batch_op:
        batch_op.add_column(sa.Column('totp_backup_codes', sa.JSON, nullable=True))


def downgrade():
    with op.batch_alter_table('organizers') as batch_op:
        batch_op.drop_column('totp_backup_codes')
    with op.batch_alter_table('admins') as batch_op:
        batch_op.drop_column('totp_backup_codes')
