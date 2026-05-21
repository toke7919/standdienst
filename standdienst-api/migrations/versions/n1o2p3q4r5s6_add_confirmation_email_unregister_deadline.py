"""add email_confirmation_enabled and unregister_deadline_hours

Revision ID: n1o2p3q4r5s6
Revises: m1n2o3p4q5r6
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'n1o2p3q4r5s6'
down_revision = 'm1n2o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('volunteers',
        sa.Column('email_confirmation_enabled', sa.Boolean(), nullable=False,
                  server_default='true'))
    op.add_column('site_settings',
        sa.Column('unregister_deadline_hours', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('site_settings', 'unregister_deadline_hours')
    op.drop_column('volunteers', 'email_confirmation_enabled')
