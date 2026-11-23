"""initial schema: runbooks, audit, model calls, usage snapshots

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runbook_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("runbook_id", sa.String(100), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "step_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runbook_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("original_command", sa.Text, nullable=False),
        sa.Column("command", sa.Text),
        sa.Column("modified", sa.Boolean, nullable=False),
        sa.Column("risk", sa.String(10), nullable=False),
        sa.Column("exit_code", sa.Integer),
        sa.Column("output", sa.Text, nullable=False),
        sa.Column("started_at", sa.DateTime),
        sa.Column("finished_at", sa.DateTime),
        sa.UniqueConstraint("run_id", "step_id"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime, nullable=False, index=True),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("action", sa.String(60), nullable=False, index=True),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("detail", sa.JSON, nullable=False),
    )
    op.create_table(
        "model_calls",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime, nullable=False, index=True),
        sa.Column("task", sa.String(60), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False, index=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=False),
        sa.Column("completion_tokens", sa.Integer, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=False),
        sa.Column("cached", sa.Boolean, nullable=False),
        sa.Column("output", sa.Text, nullable=False),
    )
    op.create_table(
        "usage_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime, nullable=False, index=True),
        sa.Column("data", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    for t in ("usage_snapshots", "model_calls", "audit_events", "step_runs", "runbook_runs"):
        op.drop_table(t)
