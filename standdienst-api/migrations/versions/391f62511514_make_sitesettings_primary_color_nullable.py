"""make SiteSettings.primary_color nullable

Revision ID: 391f62511514
Revises: 88cbe51d47ff
Create Date: 2026-05-26 09:13:33.438355

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '391f62511514'
down_revision = '88cbe51d47ff'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.alter_column('primary_color',
               existing_type=sa.VARCHAR(length=7),
               nullable=True)


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.alter_column('primary_color',
               existing_type=sa.VARCHAR(length=7),
               nullable=False)
