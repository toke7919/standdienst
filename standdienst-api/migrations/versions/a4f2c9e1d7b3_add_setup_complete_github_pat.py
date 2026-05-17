"""add setup_complete and github_pat to global_settings

Revision ID: a4f2c9e1d7b3
Revises: c1efeb76ffc8
Create Date: 2026-05-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4f2c9e1d7b3'
down_revision = 'c1efeb76ffc8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('global_settings',
        sa.Column('setup_complete', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')))
    op.add_column('global_settings',
        sa.Column('github_pat', sa.String(length=500), nullable=True))

    # Bestehende Installationen mit vorhandenem Admin automatisch als abgeschlossen markieren
    conn = op.get_bind()
    try:
        admin_count = conn.execute(sa.text('SELECT COUNT(*) FROM admins')).scalar()
        if admin_count > 0:
            gs_count = conn.execute(sa.text('SELECT COUNT(*) FROM global_settings')).scalar()
            if gs_count > 0:
                conn.execute(sa.text('UPDATE global_settings SET setup_complete = true'))
            else:
                conn.execute(sa.text(
                    'INSERT INTO global_settings (setup_complete) VALUES (true)'
                ))
    except Exception:
        pass


def downgrade():
    op.drop_column('global_settings', 'github_pat')
    op.drop_column('global_settings', 'setup_complete')
