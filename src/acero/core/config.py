"""Configuration loading and validation.

Layered resolution (lowest to highest precedence):
  1. configs/default.yaml
  2. configs/<env>.yaml
  3. environment variables (ACERO_*)

Validated with Pydantic so a bad config fails loudly at startup.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import ConfigError


def repo_root() -> Path:
    """Locate the repository root by walking up until pyproject.toml is found."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


class StorageConfig(BaseModel):
    db_url: str = "sqlite:///acero_data/acero.sqlite"
    workspace_dir: str = "research"
    artifacts_dir: str = "research/artifacts"


class LLMConfig(BaseModel):
    provider: str = "mock"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"
    temperature: float = 0.0
    max_tokens: int = 1024


class SandboxConfig(BaseModel):
    backend: str = "subprocess"
    timeout_sec: int = 30
    memory_mb: int = 1024
    network: str = "disabled"


class RetrievalConfig(BaseModel):
    method: str = "bm25"
    top_k: int = 5


class AppConfig(BaseModel):
    name: str = "ACERO"
    version: str = "0.4.0"
    env: str = "development"


class LoggingConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    level: str = "INFO"
    json_logs: bool = Field(default=True, alias="json")


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    policies_dir: str = "policies"

    def abs_db_url(self, root: Path | None = None) -> str:
        """Resolve a relative sqlite path against the repo root."""
        root = root or repo_root()
        prefix = "sqlite:///"
        if self.storage.db_url.startswith(prefix):
            rel = self.storage.db_url[len(prefix):]
            if not os.path.isabs(rel):
                return prefix + str((root / rel).resolve())
        return self.storage.db_url


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _env_overrides() -> dict[str, Any]:
    """Map a curated set of ACERO_* env vars onto the config tree."""
    m: dict[str, Any] = {}

    def setp(path: list[str], value: Any) -> None:
        node = m
        for key in path[:-1]:
            node = node.setdefault(key, {})
        node[path[-1]] = value

    env = os.environ
    if "ACERO_ENV" in env:
        setp(["app", "env"], env["ACERO_ENV"])
    if "ACERO_DB_URL" in env:
        setp(["storage", "db_url"], env["ACERO_DB_URL"])
    if "ACERO_WORKSPACE" in env:
        setp(["storage", "workspace_dir"], env["ACERO_WORKSPACE"])
    if "ACERO_LLM_PROVIDER" in env:
        setp(["llm", "provider"], env["ACERO_LLM_PROVIDER"])
    if "ACERO_OLLAMA_HOST" in env:
        setp(["llm", "ollama_host"], env["ACERO_OLLAMA_HOST"])
    if "ACERO_OLLAMA_MODEL" in env:
        setp(["llm", "ollama_model"], env["ACERO_OLLAMA_MODEL"])
    if "ACERO_SANDBOX_BACKEND" in env:
        setp(["sandbox", "backend"], env["ACERO_SANDBOX_BACKEND"])
    if "ACERO_SANDBOX_TIMEOUT_SEC" in env:
        setp(["sandbox", "timeout_sec"], int(env["ACERO_SANDBOX_TIMEOUT_SEC"]))
    if "ACERO_SANDBOX_MEM_MB" in env:
        setp(["sandbox", "memory_mb"], int(env["ACERO_SANDBOX_MEM_MB"]))
    return m


def load_config(env: str | None = None, root: Path | None = None) -> Config:
    """Load and validate the layered configuration."""
    root = root or repo_root()
    env = env or os.environ.get("ACERO_ENV", "development")
    cfg_dir = root / "configs"
    merged = _load_yaml(cfg_dir / "default.yaml")
    merged = _deep_merge(merged, _load_yaml(cfg_dir / f"{env}.yaml"))
    merged = _deep_merge(merged, _env_overrides())
    try:
        return Config(**merged)
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"Invalid configuration: {exc}") from exc


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()
