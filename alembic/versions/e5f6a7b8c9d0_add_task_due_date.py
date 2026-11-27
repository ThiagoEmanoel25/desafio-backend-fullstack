"""Add optional calendar deadline."""
import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("tasks", "due_date")
