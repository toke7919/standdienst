"""feat: asp-felder, organizer-notifications, per-instance-admin

Revision ID: 88cbe51d47ff
Revises: n1o2p3q4r5s6
Create Date: 2026-05-25 16:56:57.929850

"""
from alembic import op
import sqlalchemy as sa


revision = '88cbe51d47ff'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_asp', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('contact_asp_email', sa.String(length=200), nullable=True))

    with op.batch_alter_table('instances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_asp', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('contact_asp_email', sa.String(length=200), nullable=True))

    with op.batch_alter_table('organizer_instances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_instance_admin', sa.Boolean(), nullable=False,
                                      server_default=sa.false()))

    # Datenmigration: is_instance_admin aus Organizer-Tabelle in die Join-Tabelle übernehmen
    conn = op.get_bind()
    admins = conn.execute(
        sa.text("SELECT id FROM organizers WHERE is_instance_admin = true")
    ).fetchall()
    if admins:
        admin_ids = [row[0] for row in admins]
        for oid in admin_ids:
            conn.execute(
                sa.text(
                    "UPDATE organizer_instances SET is_instance_admin = true WHERE organizer_id = :oid"
                ),
                {"oid": oid},
            )

    with op.batch_alter_table('organizers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notifications_enabled', sa.Boolean(), nullable=False,
                                      server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('organizers', schema=None) as batch_op:
        batch_op.drop_column('notifications_enabled')

    with op.batch_alter_table('organizer_instances', schema=None) as batch_op:
        batch_op.drop_column('is_instance_admin')

    with op.batch_alter_table('instances', schema=None) as batch_op:
        batch_op.drop_column('contact_asp_email')
        batch_op.drop_column('contact_asp')

    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_column('contact_asp_email')
        batch_op.drop_column('contact_asp')
