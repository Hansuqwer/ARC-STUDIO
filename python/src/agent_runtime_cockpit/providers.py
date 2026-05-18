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


ProviderId = str


class ProviderAuthKind(str, Enum):
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH_DEVICE = "oauth_device"
    OAUTH_WEB = "oauth_web"
    WEB_SESSION = "web_session"
    LOCAL = "local"
    RESEARCH_ONLY = "research_only"


class AuthHeaderStyle(str, Enum):
    BEARER = "bearer"
    X_API_KEY = "x-api-key"


class ProviderDefinition(BaseModel):
    id: ProviderId
    display_name: str
    category: str = "model_api"
    auth_kind: ProviderAuthKind = ProviderAuthKind.API_KEY
    credential_label: str = "API key"
    default_base_url: str
    env_key_names: list[str] = Field(default_factory=list)
    auth_header: AuthHeaderStyle = AuthHeaderStyle.BEARER
    default_models: list[str] = Field(default_factory=list)
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_chat: bool = True
    supports_embeddings: bool = False
    supports_images: bool = False
    supports_web_auth: bool = False
    status: Literal["supported", "env_ref_only", "oauth_planned", "research_only", "not_recommended"] = "env_ref_only"
    docs_url: str = ""
    warnings: list[str] = Field(default_factory=list)


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


class ProviderCostGateResult(BaseModel):
    provider: str
    model: str
    dry_run: bool
    live_enabled: bool
    paid_allowed: bool
    allowed: bool
    reason: str | None = None


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
        validate_env_var_name(api_key_env)
        account = ProviderAccount(
            provider=provider,
            label=label,
            key_env_var=api_key_env,
            key_fingerprint=None,
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


WEB_AUTH_WARNING = "Web session auth is research-only. ARC does not capture browser cookies or passwords. Use official API/OAuth where available."


def _p(
    id: str,
    display_name: str,
    env: list[str] | None = None,
    base_url: str = "",
    *,
    category: str = "model_api",
    auth_kind: ProviderAuthKind = ProviderAuthKind.API_KEY,
    auth_header: AuthHeaderStyle = AuthHeaderStyle.BEARER,
    credential_label: str = "API key",
    docs_url: str = "",
    default_models: list[str] | None = None,
    supports_tools: bool = False,
    supports_chat: bool = True,
    supports_embeddings: bool = False,
    supports_images: bool = False,
    supports_web_auth: bool = False,
    status: Literal["supported", "env_ref_only", "oauth_planned", "research_only", "not_recommended"] = "env_ref_only",
    warnings: list[str] | None = None,
) -> ProviderDefinition:
    return ProviderDefinition(
        id=id,
        display_name=display_name,
        category=category,
        auth_kind=auth_kind,
        credential_label=credential_label,
        default_base_url=base_url,
        env_key_names=env or [],
        auth_header=auth_header,
        default_models=default_models or [],
        supports_tools=supports_tools,
        supports_chat=supports_chat,
        supports_embeddings=supports_embeddings,
        supports_images=supports_images,
        supports_web_auth=supports_web_auth,
        status=status,
        docs_url=docs_url,
        warnings=warnings or [],
    )


PROVIDERS: list[ProviderDefinition] = [
    _p("openai", "OpenAI / ChatGPT API", ["OPENAI_API_KEY"], "https://api.openai.com/v1", docs_url="https://platform.openai.com/docs", default_models=["gpt-4.1", "gpt-4.1-mini", "o4-mini"], supports_tools=True, supports_embeddings=True, supports_images=True),
    _p("anthropic", "Anthropic / Claude API", ["ANTHROPIC_API_KEY"], "https://api.anthropic.com", docs_url="https://docs.anthropic.com/", default_models=["claude-opus-4", "claude-sonnet-4", "claude-haiku-4"], supports_tools=True),
    _p("google-ai", "Google AI / Gemini Developer API", ["GOOGLE_API_KEY", "GEMINI_API_KEY"], "https://generativelanguage.googleapis.com", docs_url="https://ai.google.dev/gemini-api/docs", default_models=["gemini-2.5-pro", "gemini-2.5-flash"], supports_tools=True, supports_embeddings=True, supports_images=True),
    _p("google-vertex", "Google Vertex AI", ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"], "https://aiplatform.googleapis.com", auth_kind=ProviderAuthKind.OAUTH_WEB, credential_label="Google credentials", status="oauth_planned", docs_url="https://cloud.google.com/vertex-ai/generative-ai/docs"),
    _p("xai-grok", "xAI / Grok API", ["XAI_API_KEY"], "https://api.x.ai/v1", docs_url="https://docs.x.ai/", default_models=["grok-4", "grok-3"], supports_tools=True),
    _p("perplexity", "Perplexity API", ["PERPLEXITY_API_KEY", "PPLX_API_KEY"], "https://api.perplexity.ai", docs_url="https://docs.perplexity.ai/", default_models=["sonar", "sonar-pro"]),
    _p("openrouter", "OpenRouter", ["OPENROUTER_API_KEY"], "https://openrouter.ai/api/v1", docs_url="https://openrouter.ai/docs", default_models=["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4"], supports_tools=True),
    _p("azure-openai", "Azure OpenAI", ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"], "", docs_url="https://learn.microsoft.com/azure/ai-services/openai/", default_models=["deployment-name"], supports_tools=True, supports_embeddings=True, supports_images=True),
    _p("aws-bedrock", "AWS Bedrock", ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_REGION"], "", credential_label="AWS credentials", docs_url="https://docs.aws.amazon.com/bedrock/", default_models=["anthropic.claude", "amazon.nova"], supports_tools=True),
    _p("mistral", "Mistral AI", ["MISTRAL_API_KEY"], "https://api.mistral.ai/v1", docs_url="https://docs.mistral.ai/", supports_tools=True, supports_embeddings=True),
    _p("cohere", "Cohere", ["COHERE_API_KEY"], "https://api.cohere.com/v2", docs_url="https://docs.cohere.com/", supports_tools=True, supports_embeddings=True),
    _p("together", "Together AI", ["TOGETHER_API_KEY"], "https://api.together.xyz/v1", docs_url="https://docs.together.ai/", supports_tools=True, supports_embeddings=True),
    _p("fireworks", "Fireworks AI", ["FIREWORKS_API_KEY"], "https://api.fireworks.ai/inference/v1", docs_url="https://docs.fireworks.ai/", supports_tools=True),
    _p("groq", "Groq", ["GROQ_API_KEY"], "https://api.groq.com/openai/v1", docs_url="https://console.groq.com/docs", supports_tools=True),
    _p("replicate", "Replicate", ["REPLICATE_API_TOKEN"], "https://api.replicate.com/v1", auth_kind=ProviderAuthKind.BEARER_TOKEN, credential_label="API token", docs_url="https://replicate.com/docs"),
    _p("huggingface", "Hugging Face", ["HF_TOKEN", "HUGGINGFACE_API_TOKEN"], "https://api-inference.huggingface.co", auth_kind=ProviderAuthKind.BEARER_TOKEN, credential_label="Access token", docs_url="https://huggingface.co/docs/api-inference/index"),
    _p("deepseek", "DeepSeek", ["DEEPSEEK_API_KEY"], "https://api.deepseek.com/v1", docs_url="https://api-docs.deepseek.com/", supports_tools=True),
    _p("qwen", "Alibaba DashScope / Qwen", ["QWEN_API_KEY", "DASHSCOPE_API_KEY"], "https://dashscope.aliyuncs.com/compatible-mode/v1", docs_url="https://help.aliyun.com/zh/model-studio/", default_models=["qwen-max", "qwen-plus", "qwen-turbo"], supports_tools=True),
    _p("kimi", "Kimi / Moonshot", ["MOONSHOT_API_KEY", "KIMI_API_KEY"], "https://api.moonshot.ai/v1", docs_url="https://platform.moonshot.ai/docs", default_models=["kimi-k2", "moonshot-v1-128k", "moonshot-v1-32k"], supports_tools=True),
    _p("baidu-qianfan", "Baidu Qianfan / ERNIE", ["QIANFAN_AK", "QIANFAN_SK", "BAIDU_API_KEY"], "", docs_url="https://cloud.baidu.com/doc/WENXINWORKSHOP/"),
    _p("zhipu", "Zhipu AI / GLM", ["ZHIPUAI_API_KEY"], "https://open.bigmodel.cn/api/paas/v4", docs_url="https://docs.bigmodel.cn/", supports_tools=True),
    _p("tencent-hunyuan", "Tencent Hunyuan", ["TENCENTCLOUD_SECRET_ID", "TENCENTCLOUD_SECRET_KEY"], "", credential_label="Tencent Cloud credentials", docs_url="https://cloud.tencent.com/document/product/1729"),
    _p("ai21", "AI21", ["AI21_API_KEY"], "https://api.ai21.com/studio/v1", docs_url="https://docs.ai21.com/"),
    _p("cerebras", "Cerebras Inference", ["CEREBRAS_API_KEY"], "https://api.cerebras.ai/v1", docs_url="https://inference-docs.cerebras.ai/"),
    _p("sambanova", "SambaNova Cloud", ["SAMBANOVA_API_KEY"], "https://api.sambanova.ai/v1", docs_url="https://docs.sambanova.ai/"),
    _p("nvidia-nim", "NVIDIA NIM", ["NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"], "https://integrate.api.nvidia.com/v1", docs_url="https://docs.nvidia.com/nim/"),
    _p("ibm-watsonx", "IBM watsonx", ["WATSONX_APIKEY", "WATSONX_PROJECT_ID"], "https://us-south.ml.cloud.ibm.com", docs_url="https://dataplatform.cloud.ibm.com/docs/"),
    _p("cloudflare-workers-ai", "Cloudflare Workers AI", ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"], "https://api.cloudflare.com/client/v4", auth_kind=ProviderAuthKind.BEARER_TOKEN, docs_url="https://developers.cloudflare.com/workers-ai/"),
    _p("voyage", "Voyage AI", ["VOYAGE_API_KEY"], "https://api.voyageai.com/v1", category="embedding", docs_url="https://docs.voyageai.com/", supports_chat=False, supports_embeddings=True),
    _p("jina", "Jina AI", ["JINA_API_KEY"], "https://api.jina.ai/v1", category="embedding", docs_url="https://jina.ai/embeddings/", supports_chat=False, supports_embeddings=True),
    _p("pinecone", "Pinecone", ["PINECONE_API_KEY"], "https://api.pinecone.io", category="vector_db", docs_url="https://docs.pinecone.io/", supports_chat=False),
    _p("weaviate", "Weaviate", ["WEAVIATE_API_KEY", "WEAVIATE_URL"], "", category="vector_db", docs_url="https://weaviate.io/developers/weaviate", supports_chat=False),
    _p("zilliz", "Zilliz / Milvus", ["ZILLIZ_API_KEY", "ZILLIZ_CLOUD_URI"], "", category="vector_db", docs_url="https://docs.zilliz.com/", supports_chat=False),
    _p("supabase", "Supabase AI / Vector", ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"], "", category="vector_db", credential_label="Supabase key", docs_url="https://supabase.com/docs", supports_chat=False),
    _p("langsmith", "LangSmith", ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"], "https://api.smith.langchain.com", category="observability", docs_url="https://docs.smith.langchain.com/", supports_chat=False),
    _p("langfuse", "Langfuse", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"], "", category="observability", credential_label="Langfuse keys", docs_url="https://langfuse.com/docs", supports_chat=False),
    _p("helicone", "Helicone", ["HELICONE_API_KEY"], "https://oai.helicone.ai/v1", category="gateway", docs_url="https://docs.helicone.ai/"),
    _p("portkey", "Portkey", ["PORTKEY_API_KEY"], "https://api.portkey.ai/v1", category="gateway", docs_url="https://portkey.ai/docs"),
    _p("litellm", "LiteLLM Proxy", ["LITELLM_API_KEY", "LITELLM_BASE_URL"], "", category="gateway", docs_url="https://docs.litellm.ai/"),
    _p("ollama", "Ollama", [], "http://localhost:11434", category="local", auth_kind=ProviderAuthKind.LOCAL, credential_label="No key required", status="supported", docs_url="https://github.com/ollama/ollama", default_models=["llama3.1"], warnings=["Local provider; no API key required."]),
    _p("lm-studio", "LM Studio", [], "http://localhost:1234/v1", category="local", auth_kind=ProviderAuthKind.LOCAL, credential_label="No key required", status="supported", docs_url="https://lmstudio.ai/docs", warnings=["Local provider; no API key required."]),
    _p("vllm", "vLLM OpenAI-compatible", [], "http://localhost:8000/v1", category="local", auth_kind=ProviderAuthKind.LOCAL, credential_label="No key required", status="supported", docs_url="https://docs.vllm.ai/", warnings=["Local provider; no API key required unless your server requires one."]),
    _p("llama-cpp", "llama.cpp server", [], "http://localhost:8080/v1", category="local", auth_kind=ProviderAuthKind.LOCAL, credential_label="No key required", status="supported", docs_url="https://github.com/ggml-org/llama.cpp", warnings=["Local provider; no API key required unless your server requires one."]),
    _p("localai", "LocalAI", [], "http://localhost:8080/v1", category="local", auth_kind=ProviderAuthKind.LOCAL, credential_label="No key required", status="supported", docs_url="https://localai.io/", warnings=["Local provider; no API key required unless your server requires one."]),
    _p("github-models", "GitHub Models", ["GITHUB_TOKEN", "GH_TOKEN"], "https://models.inference.ai.azure.com", auth_kind=ProviderAuthKind.BEARER_TOKEN, credential_label="GitHub token", docs_url="https://docs.github.com/en/github-models"),
    _p("github", "GitHub API", ["GITHUB_TOKEN", "GH_TOKEN"], "https://api.github.com", category="developer_tool", auth_kind=ProviderAuthKind.BEARER_TOKEN, credential_label="GitHub token", docs_url="https://docs.github.com/en/rest", supports_chat=False),
    _p("hf-endpoints", "Hugging Face Inference Endpoints", ["HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"], "", auth_kind=ProviderAuthKind.BEARER_TOKEN, credential_label="Access token", docs_url="https://huggingface.co/docs/inference-endpoints"),
    _p("elevenlabs", "ElevenLabs", ["ELEVENLABS_API_KEY"], "https://api.elevenlabs.io", category="audio", docs_url="https://elevenlabs.io/docs", supports_chat=False),
    _p("tavily", "Tavily", ["TAVILY_API_KEY"], "https://api.tavily.com", category="search", docs_url="https://docs.tavily.com/", supports_chat=False),
    _p("brave-search", "Brave Search API", ["BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY"], "https://api.search.brave.com", category="search", auth_header=AuthHeaderStyle.X_API_KEY, docs_url="https://api.search.brave.com/app/documentation", supports_chat=False),
    _p("serper", "Serper", ["SERPER_API_KEY"], "https://google.serper.dev", category="search", auth_header=AuthHeaderStyle.X_API_KEY, docs_url="https://serper.dev/", supports_chat=False),
    _p("exa", "Exa", ["EXA_API_KEY"], "https://api.exa.ai", category="search", docs_url="https://docs.exa.ai/", supports_chat=False),
    _p("browserbase", "Browserbase", ["BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID"], "https://api.browserbase.com", category="browser", docs_url="https://docs.browserbase.com/", supports_chat=False),
    _p("composio", "Composio", ["COMPOSIO_API_KEY"], "https://backend.composio.dev", category="tools", docs_url="https://docs.composio.dev/", supports_chat=False),
    _p("e2b", "E2B", ["E2B_API_KEY"], "https://api.e2b.dev", category="sandbox", docs_url="https://e2b.dev/docs", supports_chat=False),
    _p("chatgpt-web", "ChatGPT Web", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING]),
    _p("claude-web", "Claude Web", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING]),
    _p("grok-web", "Grok Web", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING]),
    _p("perplexity-web", "Perplexity Web", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING]),
    _p("antigravity", "Antigravity", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING, "No official auth automation researched in this environment."]),
    _p("omniroute", "Omniroute", [], category="web_auth", auth_kind=ProviderAuthKind.RESEARCH_ONLY, credential_label="Research only", supports_web_auth=True, status="research_only", warnings=[WEB_AUTH_WARNING, "Web search was unavailable; Omniroute auth config requires follow-up research before implementation."]),
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


ENV_VAR_RE = re.compile(r"^[A-Z_][A-Z0-9_]{1,127}$")
RAW_KEY_HINT_RE = re.compile(r"(?:^sk-|^xox[baprs]-|bearer\s+|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,})", re.I)


def validate_env_var_name(value: str) -> str:
    if RAW_KEY_HINT_RE.search(value):
        raise ValueError("Expected an environment variable name, not a raw key or token.")
    if not ENV_VAR_RE.match(value):
        raise ValueError("Environment variable names must look like OPENAI_API_KEY.")
    return value


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


def check_provider_cost_gate(request: ProviderRequest, env: dict[str, str] | None = None) -> ProviderCostGateResult:
    routing = ProviderRoutingStore().get()
    provider = request.provider or routing.default_provider
    model = request.model or routing.default_model
    dry_run = request.dry_run
    live_enabled = (env or os.environ).get("ARC_ALLOW_LIVE_PROVIDER_TESTS") == "true"
    paid_allowed = request.allow_paid_calls or routing.allow_paid_calls
    if not dry_run and not live_enabled:
        return ProviderCostGateResult(
            provider=provider,
            model=model,
            dry_run=dry_run,
            live_enabled=live_enabled,
            paid_allowed=paid_allowed,
            allowed=False,
            reason="live_provider_calls_disabled",
        )
    if not dry_run and not paid_allowed:
        return ProviderCostGateResult(
            provider=provider,
            model=model,
            dry_run=dry_run,
            live_enabled=live_enabled,
            paid_allowed=paid_allowed,
            allowed=False,
            reason="paid_provider_calls_disabled",
        )
    return ProviderCostGateResult(
        provider=provider,
        model=model,
        dry_run=dry_run,
        live_enabled=live_enabled,
        paid_allowed=paid_allowed,
        allowed=True,
    )


def dry_run_proxy(request: ProviderRequest) -> ProviderResponse:
    gate = check_provider_cost_gate(request)
    if not gate.allowed and gate.reason == "live_provider_calls_disabled":
        raise RuntimeError("Live provider calls disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true.")
    if not gate.allowed and gate.reason == "paid_provider_calls_disabled":
        raise RuntimeError("Paid provider calls disabled. Set allow_paid_calls=true.")
    quota = ProviderQuotaStore().reserve(gate.provider, dry_run=gate.dry_run)
    if not quota["allowed"]:
        raise RuntimeError(str(quota["reason"]))
    return ProviderResponse(provider=gate.provider, model=gate.model, dry_run=True, message="Dry-run provider proxy response. No network call was made.")
