"""trusted_proxies zu global_settings hinzufügen

Revision ID: c3d8f1a7e2b9
Revises: b7c1e9d4a2f8
Create Date: 2026-11-10 00:00:00.000000

IP/CIDR externer Reverse-Proxys (z. B. NPMPlus), deren X-Forwarded-For
übernommen wird – ersetzt die .env-Variable TRUSTED_PROXIES aus v3.122.2.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d8f1a7e2b9'
down_revision = 'b7c1e9d4a2f8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trusted_proxies', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_column('trusted_proxies')
