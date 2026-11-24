from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # SQLite has no timezone type; everything is stored as naive UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class RunbookRun(Base):
    __tablename__ = "runbook_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    runbook_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class StepRun(Base):
    __tablename__ = "step_runs"
    __table_args__ = (UniqueConstraint("run_id", "step_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runbook_runs.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    original_command: Mapped[str] = mapped_column(Text, default="")
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified: Mapped[bool] = mapped_column(Boolean, default=False)
    risk: Mapped[str] = mapped_column(String(10), default="low")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(60), index=True)
    target: Mapped[str] = mapped_column(String(200))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ModelCall(Base):
    __tablename__ = "model_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    task: Mapped[str] = mapped_column(String(60))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    output: Mapped[str] = mapped_column(Text, default="")
    credits: Mapped[float] = mapped_column(Float, default=0.0)


class UsageSnapshot(Base):
    __tablename__ = "usage_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent: Mapped[str] = mapped_column(String(30), default="droid")
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    parent_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    prompt: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(120))
    model_location: Mapped[str] = mapped_column(String(10), default="cloud")
    autonomy: Mapped[str] = mapped_column(String(10), default="off")
    cwd: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="starting", index=True)
    result_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentEvent(Base):
    __tablename__ = "agent_events"
    __table_args__ = (UniqueConstraint("run_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    type: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Approval(Base):
    """One record per approval request, shared by every client (dashboard, VS Code)."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(30), default="agent")
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    risk: Mapped[str] = mapped_column(String(10), default="medium")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    root: Mapped[str] = mapped_column(Text, unique=True)
    instructions: Mapped[str] = mapped_column(Text, default="")
    architecture: Mapped[str] = mapped_column(Text, default="")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContextItem(Base):
    __tablename__ = "context_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    source_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120), default="Coding")
    adapter: Mapped[str] = mapped_column(String(30), default="droid")
    instructions: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class SavedPrompt(Base):
    __tablename__ = "saved_prompts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("prompt_id", "version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("saved_prompts.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agent_profiles.id"), index=True)
    objective: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str] = mapped_column(Text, default="")
    acceptance: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    continue_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    context_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    include_instructions: Mapped[bool] = mapped_column(Boolean, default=False)
    include_architecture: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    allow_cloud: Mapped[bool] = mapped_column(Boolean, default=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TaskAttempt(Base):
    __tablename__ = "task_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), unique=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FileCheckpoint(Base):
    __tablename__ = "file_checkpoints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    approval_id: Mapped[str] = mapped_column(String(36), unique=True)
    root: Mapped[str] = mapped_column(Text)
    files: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="prepared")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
