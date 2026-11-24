from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from ..config import Settings

Risk = Literal["low", "medium", "high"]
_PLACEHOLDER = re.compile(r"\{(repo_root|data_dir|python|aws_region|small_model|ollama_url|remote_ollama_url|port)\}")


class Step(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    explain: str
    command: str
    risk: Risk = "low"
    expected: str = ""
    check: str | None = None
    long_running: bool = False
    timeout: int | None = Field(None, ge=5)
    rollback: str | None = None
    optional: bool = False
    cwd: str | None = Field(None, description="Working directory relative to the repository root")


class Runbook(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    summary: str
    category: str = "setup"
    order: int = 100
    steps: list[Step]

    @model_validator(mode="after")
    def _unique_steps(self) -> "Runbook":
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate step ids in runbook {self.id}")
        return self

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)


def placeholders(settings: Settings) -> dict[str, str]:
    return {
        "repo_root": str(settings.repo_root),
        "data_dir": str(settings.data_dir),
        "python": sys.executable,
        "aws_region": settings.aws_region,
        "small_model": settings.small_model,
        "ollama_url": settings.ollama_url,
        "remote_ollama_url": settings.remote_ollama_url,
        "port": str(settings.port),
    }


def resolve(text: str | None, values: dict[str, str]) -> str | None:
    if text is None:
        return None
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def load_runbooks(directory: Path, settings: Settings) -> dict[str, Runbook]:
    values = placeholders(settings)
    books: dict[str, Runbook] = {}
    for f in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(f.read_text(encoding="utf-8"))
        for step in raw.get("steps", []):
            for key in ("command", "check", "explain", "expected", "rollback"):
                if key in step:
                    step[key] = resolve(step[key], values)
        rb = Runbook.model_validate(raw)
        root = settings.repo_root.resolve()
        for step in rb.steps:
            if step.cwd is not None:
                target = (root / step.cwd).resolve()
                if not target.is_relative_to(root):
                    raise ValueError(f"{rb.id}/{step.id}: cwd must stay inside the repository")
        if rb.id in books:
            raise ValueError(f"Duplicate runbook id {rb.id} in {f.name}")
        books[rb.id] = rb
    return dict(sorted(books.items(), key=lambda kv: (kv[1].order, kv[0])))
