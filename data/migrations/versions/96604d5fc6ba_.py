"""empty message

Revision ID: 96604d5fc6ba
Revises: cbd2831b73af
Create Date: 2024-05-18 18:39:55.876279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '96604d5fc6ba'
down_revision = 'cbd2831b73af'
branch_labels = None
depends_on = None


def upgrade():
    from quad.models import Map
    op.bulk_insert(
        Map.__table__,
        [
            {"code": "koth", "name": "Tower of Koth"},
        ]
    )


def downgrade():
    pass

