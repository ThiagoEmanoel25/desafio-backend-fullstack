"""Add explicit administrator privilege."""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False,
                                    server_default=sa.false()))


def downgrade():
    op.drop_column("users", "is_admin")
