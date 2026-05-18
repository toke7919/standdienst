"""add first_last_name to volunteers

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d5e6f7a8b9'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('volunteers', sa.Column('first_name', sa.String(length=100), nullable=True))
    op.add_column('volunteers', sa.Column('last_name', sa.String(length=100), nullable=True))
    # Bestehende Datensätze: name → first_name migrieren
    op.execute("UPDATE volunteers SET first_name = name WHERE first_name IS NULL")


def downgrade():
    op.drop_column('volunteers', 'last_name')
    op.drop_column('volunteers', 'first_name')
