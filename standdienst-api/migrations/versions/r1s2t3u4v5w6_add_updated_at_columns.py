"""add updated_at to stands, event_dates, shifts, food_donation_types

Revision ID: r1s2t3u4v5w6
Revises: q1r2s3t4u5v6
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'r1s2t3u4v5w6'
down_revision = 'q1r2s3t4u5v6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('stands') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))
    with op.batch_alter_table('event_dates') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))
    with op.batch_alter_table('shifts') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))
    with op.batch_alter_table('food_donation_types') as batch_op:
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True), nullable=True,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ))


def downgrade():
    with op.batch_alter_table('food_donation_types') as batch_op:
        batch_op.drop_column('updated_at')
    with op.batch_alter_table('shifts') as batch_op:
        batch_op.drop_column('updated_at')
    with op.batch_alter_table('event_dates') as batch_op:
        batch_op.drop_column('updated_at')
    with op.batch_alter_table('stands') as batch_op:
        batch_op.drop_column('updated_at')
