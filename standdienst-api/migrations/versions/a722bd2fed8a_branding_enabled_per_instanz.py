"""branding-enabled-per-instanz

Revision ID: a722bd2fed8a
Revises: ebbcf4e58c0b
Create Date: 2026-05-27 13:35:29.428132

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a722bd2fed8a'
down_revision = 'ebbcf4e58c0b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('branding_enabled', sa.Boolean(), server_default='true', nullable=False))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('branding_enabled')
