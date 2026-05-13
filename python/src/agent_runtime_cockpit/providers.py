"""Provider registry, routing, and dry-run proxy foundation."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ProviderId = Literal["openai", "anthropic", "openrouter", "qwen", "kimi", "g4f-groq", "g4f-gemini", "g4f-nvidia", "g4f-pollinations", "g4f-ollama"]


class AuthHeaderStyle(str, Enum):
    BEARER = "bearer"
    X_API_KEY = "x-api-key"


class ProviderDefinition(BaseModel):
    id: ProviderId
    display_name: str
    default_base_url: str
    env_key_names: list[str] = Field(default_factory=list)
    auth_header: AuthHeaderStyle = AuthHeaderStyle.BEARER
    default_models: list[str] = Field(default_factory=list)
    supports_streaming: bool = True
    supports_tools: bool = False


class ProviderStatus(BaseModel):
    provider: str
    display_name: str
    enabled: bool = True
    dry_run: bool = True
    base_url_configured: bool = True
    api_key_configured: bool = False
    api_key_source: str | None = None
    message: str


class ProviderRoutingPolicy(BaseModel):
    mode: Literal["manual", "priority", "fallback"] = "manual"
    default_provider: ProviderId = "openai"
    default_model: str = "gpt-4.1-mini"
    dry_run: bool = True
    allow_paid_calls: bool = False
    max_retries: int = 1
    timeout_ms: int = 30000


class ProviderAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    provider: ProviderId
    label: str
    enabled: bool = True
    key_env_var: str | None = None
    key_fingerprint: str | None = None
    masked_key: str | None = None
    base_url: str | None = None
    default_model: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProviderRequest(BaseModel):
    provider: ProviderId | None = None
    model: str | None = None
    prompt: str | None = None
    dry_run: bool = True
    allow_paid_calls: bool = False


class ProviderResponse(BaseModel):
    provider: str
    model: str
    dry_run: bool
    message: str


class ProviderAccountStore:
    """JSON account metadata store. Secrets are env refs only in this beta foundation."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.environ.get("ARC_PROVIDER_CONFIG", Path.home() / ".arc" / "providers.json"))

    def list_accounts(self) -> list[ProviderAccount]:
        data = self._load()
        return [ProviderAccount.model_validate(item) for item in data.get("accounts", [])]

    def add_env_account(
        self,
        provider: ProviderId,
        label: str,
        api_key_env: str,
        default_model: str | None = None,
        base_url: str | None = None,
    ) -> ProviderAccount:
        account = ProviderAccount(
            provider=provider,
            label=label,
            key_env_var=api_key_env,
            key_fingerprint=fingerprint(os.environ.get(api_key_env, api_key_env)),
            masked_key=mask_secret(os.environ.get(api_key_env)) or f"env:{api_key_env}",
            default_model=default_model,
            base_url=base_url,
        )
        accounts = self.list_accounts()
        accounts.append(account)
        self._save(accounts)
        return account

    def add_direct_key_account(self, *_args: Any, **_kwargs: Any) -> ProviderAccount:
        raise RuntimeError("Direct key storage requires a secure OS keychain backend; use --api-key-env.")

    def set_enabled(self, account_id: str, enabled: bool) -> ProviderAccount | None:
        accounts = self.list_accounts()
        updated: ProviderAccount | None = None
        for i, account in enumerate(accounts):
            if account.id == account_id:
                updated = account.model_copy(update={"enabled": enabled})
                accounts[i] = updated
                break
        if updated:
            self._save(accounts)
        return updated

    def delete(self, account_id: str) -> bool:
        accounts = self.list_accounts()
        kept = [account for account in accounts if account.id != account_id]
        self._save(kept)
        return len(kept) != len(accounts)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "accounts": []}
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "accounts": []}

    def _save(self, accounts: list[ProviderAccount]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"version": 1, "accounts": [a.model_dump() for a in accounts]}, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".providers_")
        try:
            os.write(fd, payload.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.path)


class ProviderRoutingStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.environ.get("ARC_PROVIDER_ROUTING", Path.home() / ".arc" / "provider-routing.json"))

    def get(self) -> ProviderRoutingPolicy:
        if not self.path.exists():
            return DEFAULT_ROUTING
        try:
            return ProviderRoutingPolicy.model_validate(json.loads(self.path.read_text()))
        except (OSError, json.JSONDecodeError, ValueError):
            return DEFAULT_ROUTING

    def set(self, policy: ProviderRoutingPolicy) -> ProviderRoutingPolicy:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(policy.model_dump_json(indent=2))
        return policy


class ProviderQuotaStore:
    """UTC daily request counters for beta-safe provider throttling."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.environ.get("ARC_PROVIDER_QUOTA", Path.home() / ".arc" / "provider-quota.json"))

    def reserve(
        self,
        provider: str,
        account_id: str | None = None,
        provider_cap: int | None = None,
        account_cap: int | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        data = self._load_today()
        bucket = "dry_run" if dry_run else "live"
        provider_key = f"{bucket}:provider:{provider}"
        account_key = f"{bucket}:account:{account_id}" if account_id else None
        provider_count = int(data["counters"].get(provider_key, 0))
        account_count = int(data["counters"].get(account_key, 0)) if account_key else 0
        if provider_cap is not None and provider_count >= provider_cap:
            return {"allowed": False, "reason": "provider_request_cap_exceeded", "provider": provider}
        if account_key and account_cap is not None and account_count >= account_cap:
            return {"allowed": False, "reason": "account_request_cap_exceeded", "account_id": account_id}
        data["counters"][provider_key] = provider_count + 1
        if account_key:
            data["counters"][account_key] = account_count + 1
        self._save(data)
        return {"allowed": True, "provider_count": data["counters"][provider_key], "account_count": data["counters"].get(account_key) if account_key else None}

    def usage(self) -> dict[str, Any]:
        return self._load_today()

    def reset(self) -> None:
        self._save({"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "counters": {}})

    def remaining(
        self,
        provider: str,
        account_id: str | None = None,
        provider_cap: int | None = None,
        account_cap: int | None = None,
        dry_run: bool = True,
    ) -> dict[str, int | None]:
        data = self._load_today()
        bucket = "dry_run" if dry_run else "live"
        provider_key = f"{bucket}:provider:{provider}"
        account_key = f"{bucket}:account:{account_id}" if account_id else None
        provider_count = int(data["counters"].get(provider_key, 0))
        account_count = int(data["counters"].get(account_key, 0)) if account_key else 0
        return {
            "provider": None if provider_cap is None else max(provider_cap - provider_count, 0),
            "account": None if account_key is None or account_cap is None else max(account_cap - account_count, 0),
        }

    def _load_today(self) -> dict[str, Any]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                if data.get("date") == today:
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {"date": today, "counters": {}}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".provider_quota_")
        try:
            os.write(fd, payload.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.path)


PROVIDERS: list[ProviderDefinition] = [
    ProviderDefinition(id="openai", display_name="OpenAI / ChatGPT", default_base_url="https://api.openai.com/v1", env_key_names=["OPENAI_API_KEY"], default_models=["gpt-4.1", "gpt-4.1-mini", "o4-mini"], supports_tools=True),
    ProviderDefinition(id="anthropic", display_name="Anthropic / Claude", default_base_url="https://api.anthropic.com", env_key_names=["ANTHROPIC_API_KEY"], auth_header=AuthHeaderStyle.X_API_KEY, default_models=["claude-opus-4", "claude-sonnet-4", "claude-haiku-4"], supports_tools=True),
    ProviderDefinition(id="openrouter", display_name="OpenRouter", default_base_url="https://openrouter.ai/api/v1", env_key_names=["OPENROUTER_API_KEY"], default_models=["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4"], supports_tools=True),
    ProviderDefinition(id="qwen", display_name="Qwen", default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", env_key_names=["QWEN_API_KEY", "DASHSCOPE_API_KEY"], default_models=["qwen-max", "qwen-plus", "qwen-turbo"], supports_tools=True),
    ProviderDefinition(id="kimi", display_name="Kimi / Moonshot", default_base_url="https://api.moonshot.ai/v1", env_key_names=["MOONSHOT_API_KEY", "KIMI_API_KEY"], default_models=["kimi-k2", "moonshot-v1-128k", "moonshot-v1-32k"], supports_tools=True),
    ProviderDefinition(id="g4f-groq", display_name="G4F: Groq (Free)", default_base_url="https://g4f.space/api/groq", env_key_names=[], default_models=["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen/qwen3-32b"], supports_tools=True),
    ProviderDefinition(id="g4f-gemini", display_name="G4F: Gemini (Free)", default_base_url="https://g4f.space/api/gemini", env_key_names=[], default_models=["models/gemini-2.5-flash", "models/gemini-3-flash-preview", "models/gemini-flash-latest"], supports_tools=True),
    ProviderDefinition(id="g4f-nvidia", display_name="G4F: Nvidia (Free)", default_base_url="https://g4f.space/api/nvidia", env_key_names=[], default_models=["deepseek-ai/deepseek-v4-pro", "nvidia/nemotron-3-super-120b-a12b", "meta/llama-3.3-70b-instruct"], supports_tools=True),
    ProviderDefinition(id="g4f-pollinations", display_name="G4F: Pollinations (Free)", default_base_url="https://g4f.space/api/pollinations", env_key_names=[], default_models=["openai-fast", "claude-fast", "gemini-fast", "mistral"], supports_tools=True),
    ProviderDefinition(id="g4f-ollama", display_name="G4F: Ollama (Free)", default_base_url="https://g4f.space/api/ollama", env_key_names=[], default_models=["deepseek-v4-pro", "glm-5.1", "qwen3.5:397b", "nemotron-3-super"], supports_tools=True),
]

DEFAULT_ROUTING = ProviderRoutingPolicy()


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "[REDACTED]"
    return f"{value[:3]}...{value[-4:]}"


def fingerprint(value: str | None) -> str | None:
    return value[-4:] if value else None


SECRET_PATTERNS = [
    re.compile(r"sk-ant-api03-[A-Za-z0-9_-]+"),
    re.compile(r"sk-(?:ant|or|proj)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"bearer\s+[A-Za-z0-9.~+/=-]{16,}", re.I),
]


def redact(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub("<redacted>", redacted)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: "<redacted>" if _sensitive_key(key) else redact(item) for key, item in value.items()}
    return value


def _sensitive_key(key: str) -> bool:
    return key.lower().replace("-", "_") in {"api_key", "authorization", "x_api_key", "x_dashscope_api_key", "x_moonshot_api_key"}


def provider_statuses(env: dict[str, str]) -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    for provider in PROVIDERS:
        source = next((name for name in provider.env_key_names if env.get(name)), None)
        statuses.append(ProviderStatus(provider=provider.id, display_name=provider.display_name, api_key_configured=source is not None, api_key_source=source, message="Dry-run provider definition loaded. Live calls require ARC_ALLOW_LIVE_PROVIDER_TESTS=true."))
    return statuses


def redacted_diagnostics(env: dict[str, str]) -> dict[str, object]:
    return redact({"live_tests_enabled": env.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") == "true", "providers": [status.model_dump() for status in provider_statuses(env)], "routing": ProviderRoutingStore().get().model_dump(), "accounts": [account.model_dump() for account in ProviderAccountStore().list_accounts()], "quota": ProviderQuotaStore().usage()})


def dry_run_proxy(request: ProviderRequest) -> ProviderResponse:
    routing = ProviderRoutingStore().get()
    provider = request.provider or routing.default_provider
    model = request.model or routing.default_model
    if not request.dry_run and os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        raise RuntimeError("Live provider calls disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true.")
    if not request.dry_run and not request.allow_paid_calls:
        raise RuntimeError("Paid provider calls disabled. Set allow_paid_calls=true.")
    quota = ProviderQuotaStore().reserve(provider, dry_run=request.dry_run)
    if not quota["allowed"]:
        raise RuntimeError(str(quota["reason"]))
    return ProviderResponse(provider=provider, model=model, dry_run=True, message="Dry-run provider proxy response. No network call was made.")
