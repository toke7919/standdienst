"""Entferne nie genutzte Spalten (SMB-Backup, privacy_policy, food_refrigeration)

Revision ID: p1q2r3s4t5u6
Revises: da95cdc54a7a
Create Date: 2026-05-27

Einmaliges Brechen der additive-only-Regel: alle 9 Spalten wurden in
derselben Session aus den SQLAlchemy-Models entfernt; keine Produktionsdaten
wurden je exklusiv in diesen Feldern gespeichert.
"""
from alembic import op
import sqlalchemy as sa

revision = 'p1q2r3s4t5u6'
down_revision = 'da95cdc54a7a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings') as batch_op:
        batch_op.drop_column('smb_enabled')
        batch_op.drop_column('smb_server')
        batch_op.drop_column('smb_share')
        batch_op.drop_column('smb_path')
        batch_op.drop_column('smb_username')
        batch_op.drop_column('smb_password')

    with op.batch_alter_table('site_settings') as batch_op:
        batch_op.drop_column('privacy_policy_html')
        batch_op.drop_column('log_retention_months')
        batch_op.drop_column('food_refrigeration_enabled')


def downgrade():
    with op.batch_alter_table('site_settings') as batch_op:
        batch_op.add_column(sa.Column('food_refrigeration_enabled',
                                      sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('log_retention_months',
                                      sa.Integer(), nullable=False, server_default='3'))
        batch_op.add_column(sa.Column('privacy_policy_html', sa.Text(), nullable=True))

    with op.batch_alter_table('global_settings') as batch_op:
        batch_op.add_column(sa.Column('smb_password', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('smb_username', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('smb_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('smb_share', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('smb_server', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('smb_enabled', sa.Boolean(), nullable=False,
                                      server_default='false'))
