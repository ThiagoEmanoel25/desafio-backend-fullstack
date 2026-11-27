"""Persist daily AI quotas independently of cache."""

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_daily_usage",
        sa.Column("scope", sa.String(80), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("used", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("ai_daily_usage")
