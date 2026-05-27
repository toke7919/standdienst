"""digest-prefs-per-instanz

Revision ID: ebbcf4e58c0b
Revises: cce01a1943ca
Create Date: 2026-05-27 09:32:19.520713

"""
from alembic import op
import sqlalchemy as sa


revision = 'ebbcf4e58c0b'
down_revision = 'cce01a1943ca'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'admin_digest_subscriptions',
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('admin_id', 'instance_id'),
    )

    with op.batch_alter_table('organizer_instances', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('digest_enabled', sa.Boolean(), server_default='true', nullable=False)
        )

    # Bestehende Opt-outs übernehmen: Organizer mit notifications_enabled=False
    # erhalten digest_enabled=False für alle ihre Instanzen.
    op.execute("""
        UPDATE organizer_instances
        SET digest_enabled = false
        WHERE organizer_id IN (
            SELECT id FROM organizers WHERE notifications_enabled = false
        )
    """)


def downgrade():
    with op.batch_alter_table('organizer_instances', schema=None) as batch_op:
        batch_op.drop_column('digest_enabled')

    op.drop_table('admin_digest_subscriptions')
