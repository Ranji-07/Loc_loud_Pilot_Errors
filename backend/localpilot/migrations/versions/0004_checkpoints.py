"""Scoped file checkpoints, without changing Git index or history."""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("file_checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False, index=True),
        sa.Column("approval_id", sa.String(36), nullable=False, unique=True),
        sa.Column("root", sa.Text, nullable=False),
        sa.Column("files", sa.JSON, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))


def downgrade():
    op.drop_table("file_checkpoints")
