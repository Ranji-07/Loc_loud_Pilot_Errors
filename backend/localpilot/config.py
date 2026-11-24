from __future__ import annotations

import ipaddress
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All settings can be overridden with LOCALPILOT_<NAME> environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_prefix="LOCALPILOT_", env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = Field(8765, ge=1, le=65535)
    allow_non_loopback_bind: bool = False

    repo_root: Path = REPO_ROOT
    data_dir: Path = Path(r"E:\LocalPilot\data") if sys.platform == "win32" else Path.home() / ".localpilot"
    runbooks_dir: Path | None = None
    web_dist: Path | None = None
    pricing_file: Path | None = None

    ollama_url: str = "http://127.0.0.1:11434"
    remote_ollama_url: str = "http://127.0.0.1:11435"
    litellm_url: str | None = None
    agent_server_url: str | None = None
    small_model: str = "qwen2.5:0.5b"
    summary_cache_seconds: int = Field(600, ge=0)

    aws_region: str = "eu-north-1"
    step_timeout_seconds: int = Field(1800, ge=10)
    log_level: str = "INFO"

    @field_validator("host")
    @classmethod
    def _host_is_ip_or_localhost(cls, v: str) -> str:
        if v != "localhost":
            ipaddress.ip_address(v)
        return v

    @model_validator(mode="after")
    def _defaults_and_bind_guard(self) -> "Settings":
        if self.runbooks_dir is None:
            self.runbooks_dir = self.repo_root / "config" / "runbooks"
        if self.web_dist is None:
            self.web_dist = self.repo_root / "apps" / "web" / "dist"
        if self.pricing_file is None:
            self.pricing_file = self.repo_root / "config" / "pricing.yaml"
        loopback = self.host == "localhost" or ipaddress.ip_address(self.host).is_loopback
        if not loopback and not self.allow_non_loopback_bind:
            raise ValueError(
                "LocalPilot executes approved commands; binding to a non-loopback address "
                "requires LOCALPILOT_ALLOW_NON_LOOPBACK_BIND=true"
            )
        return self

    @property
    def db_path(self) -> Path:
        return self.data_dir / "localpilot.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def aws_state_file(self) -> Path:
        return self.data_dir / "aws" / "target.json"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.log_dir, self.aws_state_file.parent):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
