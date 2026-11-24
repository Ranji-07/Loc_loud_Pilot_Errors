"""Project context, prompts, profiles and durable tasks."""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("root", sa.Text, nullable=False, unique=True),
        sa.Column("instructions", sa.Text, nullable=False),
        sa.Column("architecture", sa.Text, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_table("context_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("path", sa.Text),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_commit", sa.String(40)),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_table("agent_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(120), nullable=False),
        sa.Column("adapter", sa.String(30), nullable=False),
        sa.Column("instructions", sa.Text, nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False))
    op.create_table("saved_prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_table("prompt_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("saved_prompts.id"), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("prompt_id", "version"))
    op.create_table("tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agent_profiles.id"), nullable=False, index=True),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("requirements", sa.Text, nullable=False),
        sa.Column("acceptance", sa.Text, nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("continue_run_id", sa.String(36), sa.ForeignKey("agent_runs.id")),
        sa.Column("context_ids", sa.JSON, nullable=False),
        sa.Column("include_instructions", sa.Boolean, nullable=False),
        sa.Column("include_architecture", sa.Boolean, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id")),
        sa.Column("error", sa.Text),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, index=True),
        sa.Column("queued_at", sa.DateTime),
        sa.Column("allow_cloud", sa.Boolean, nullable=False),
        sa.Column("snapshot", sa.JSON, nullable=False))
    op.create_table("task_attempts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False, index=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False, unique=True),
        sa.Column("snapshot", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False))


def downgrade():
    for name in ("task_attempts", "tasks", "prompt_versions", "saved_prompts", "agent_profiles", "context_items", "projects"):
        op.drop_table(name)
