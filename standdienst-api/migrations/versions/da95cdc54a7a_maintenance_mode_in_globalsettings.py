"""maintenance_mode in GlobalSettings

Revision ID: da95cdc54a7a
Revises: a722bd2fed8a
Create Date: 2026-05-27 14:34:14.581907

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da95cdc54a7a'
down_revision = 'a722bd2fed8a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('maintenance_mode', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_column('maintenance_mode')
