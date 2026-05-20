"""Add impressum/datenschutz templates and contact fields

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = 'j1k2l3m4n5o6'
branch_labels = None
depends_on = None


def upgrade():
    # Neue Felder in global_settings
    with op.batch_alter_table('global_settings') as batch_op:
        batch_op.add_column(sa.Column('impressum_template_html', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('datenschutz_template_html', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('contact_organisation', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_person', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_street', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_zip_city', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('contact_email', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_phone', sa.String(50), nullable=True))

    # Neue Felder in instances
    with op.batch_alter_table('instances') as batch_op:
        batch_op.add_column(sa.Column('contact_organisation', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_person', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_street', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_zip_city', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('contact_email', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('contact_phone', sa.String(50), nullable=True))


def downgrade():
    with op.batch_alter_table('instances') as batch_op:
        for col in ('contact_organisation', 'contact_person', 'contact_street',
                    'contact_zip_city', 'contact_email', 'contact_phone'):
            batch_op.drop_column(col)

    with op.batch_alter_table('global_settings') as batch_op:
        for col in ('impressum_template_html', 'datenschutz_template_html',
                    'contact_organisation', 'contact_person', 'contact_street',
                    'contact_zip_city', 'contact_email', 'contact_phone'):
            batch_op.drop_column(col)
