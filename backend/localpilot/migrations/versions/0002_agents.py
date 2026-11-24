"""agent runs, agent events, approvals; credits on model calls

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent", sa.String(30), nullable=False),
        sa.Column("session_id", sa.String(64), index=True),
        sa.Column("parent_run_id", sa.String(36)),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("model_location", sa.String(10), nullable=False),
        sa.Column("autonomy", sa.String(10), nullable=False),
        sa.Column("cwd", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("result_text", sa.Text, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("usage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, index=True),
        sa.Column("finished_at", sa.DateTime),
    )
    op.create_table(
        "agent_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("at", sa.DateTime, nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.UniqueConstraint("run_id", "seq"),
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("run_id", sa.String(36), index=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("risk", sa.String(10), nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("options", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("decided_by", sa.String(30)),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False, index=True),
        sa.Column("decided_at", sa.DateTime),
    )
    with op.batch_alter_table("model_calls") as b:
        b.add_column(sa.Column("credits", sa.Float, nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("model_calls") as b:
        b.drop_column("credits")
    for t in ("approvals", "agent_events", "agent_runs"):
        op.drop_table(t)
