"""drop github_repo und github_pat aus global_settings

Revision ID: b7c1e9d4a2f8
Revises: s1t2u3v4w5x6
Create Date: 2026-09-03 00:00:00.000000

Bewusste Ausnahme von der Additive-only-Regel (siehe CLAUDE.md): Das
Upstream-Repository ist öffentlich und fest in version.py hinterlegt
(GITHUB_REPO). Es gibt keine Konfiguration von Repo oder PAT mehr über
Setup, Admin-Einstellungen oder .env – die Spalten werden entfernt.

SQLite (Tests) braucht batch_alter_table für DROP COLUMN.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c1e9d4a2f8'
down_revision = 's1t2u3v4w5x6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_column('github_pat')
        batch_op.drop_column('github_repo')


def downgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('github_repo', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('github_pat', sa.String(length=500), nullable=True))
