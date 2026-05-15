"""Pydantic models for ARC workspace configuration (ADR-001)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkspaceConfig(BaseModel):
    """Workspace identity settings."""
    name: Optional[str] = None
    trust_level: str = "auto"


class RuntimeConfig(BaseModel):
    """Runtime selection settings."""
    default: str = "auto"
    auto_detect: bool = True
    fallback: str = "stub"


class ExecutionConfig(BaseModel):
    """Execution settings."""
    isolation: str = "none"
    default_profile: str = "local-safe"
    timeout_seconds: int = 300
    allow_paid_calls: bool = False
    background: bool = False


class ProviderConfig(BaseModel):
    """Provider routing overrides."""
    default_provider: str = "openai"
    default_model: str = "gpt-4.1-mini"
    routing_mode: str = "manual"
    dry_run: bool = True
    accounts: list[str] = Field(default_factory=list)


class SwarmGraphConfig(BaseModel):
    """SwarmGraph-specific settings."""
    provider: str = "openai"
    base_url: str = ""
    run_backend: str = "stub"
    cli_path: str = ""


class LangGraphConfig(BaseModel):
    """LangGraph-specific settings."""
    export: str = ""


class CrewAIConfig(BaseModel):
    """CrewAI-specific settings."""
    export: str = ""


class ContextConfig(BaseModel):
    """Context provider settings."""
    search_provider: str = "brave"
    context7_api_key_env: str = ""
    github_token_env: str = ""


class TelemetryConfig(BaseModel):
    """Telemetry settings."""
    otel_endpoint: str = ""
    otel_genai_experimental: bool = False


class UIConfig(BaseModel):
    """UI preference overrides."""
    show_mock_warnings: bool = True
    compact_sidebar: bool = False
    auto_open_sidebar: bool = True


class SecurityConfig(BaseModel):
    """Security settings."""
    redact_secrets: bool = True
    audit_enabled: bool = False
    audit_secret_env: str = ""
    allowed_paths: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)


class ArcConfig(BaseModel):
    """Top-level ARC workspace configuration (ADR-001)."""
    version: int = 1
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    swarmgraph: SwarmGraphConfig = Field(default_factory=SwarmGraphConfig)
    langgraph: LangGraphConfig = Field(default_factory=LangGraphConfig)
    crewai: CrewAIConfig = Field(default_factory=CrewAIConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    def flatten(self) -> dict[str, Any]:
        """Return config as a flat key: value dict for display."""
        result: dict[str, Any] = {}
        _flatten(self, "", result)
        return result


def _flatten(obj: Any, prefix: str, result: dict[str, Any]) -> None:
    if isinstance(obj, BaseModel):
        for field_name in type(obj).model_fields:
            value = getattr(obj, field_name)
            key = f"{prefix}.{field_name}" if prefix else field_name
            _flatten(value, key, result)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            _flatten(v, key, result)
    elif isinstance(obj, list):
        result[prefix] = obj
    else:
        result[prefix] = obj
