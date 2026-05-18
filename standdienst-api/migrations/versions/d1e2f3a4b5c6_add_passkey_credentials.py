"""add passkey_credentials table

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'passkey_credentials',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('admin_id', sa.Integer,
                  sa.ForeignKey('admins.id', ondelete='CASCADE'), nullable=True),
        sa.Column('organizer_id', sa.Integer,
                  sa.ForeignKey('organizers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('credential_id', sa.Text, unique=True, nullable=False),
        sa.Column('public_key', sa.Text, nullable=False),
        sa.Column('sign_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('name', sa.String(100), nullable=False, server_default='Passkey'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_passkey_credentials_admin_id', 'passkey_credentials', ['admin_id'])
    op.create_index('ix_passkey_credentials_organizer_id', 'passkey_credentials', ['organizer_id'])


def downgrade():
    op.drop_table('passkey_credentials')
