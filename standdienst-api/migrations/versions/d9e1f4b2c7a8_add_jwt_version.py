"""add jwt_version to admins, organizers, volunteers

Revision ID: d9e1f4b2c7a8
Revises: c3d7e8f2a5b6
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'd9e1f4b2c7a8'
down_revision = 'c3d7e8f2a5b6'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('admins', 'organizers', 'volunteers'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column(
                'jwt_version',
                sa.Integer,
                nullable=False,
                server_default='1',
            ))


def downgrade():
    for table in ('admins', 'organizers', 'volunteers'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column('jwt_version')
