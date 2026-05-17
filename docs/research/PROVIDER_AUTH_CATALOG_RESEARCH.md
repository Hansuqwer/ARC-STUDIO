# Provider Auth Catalog Research

Generated: 2026-05-16

Status: implementation support note for ARC provider catalog. No live provider calls were made.

## Research Inputs

Context7 sources:

- `/openai/openai-python`: OpenAI SDK reads `OPENAI_API_KEY` by default.
- `/anthropics/anthropic-sdk-python`: Anthropic SDK reads `ANTHROPIC_API_KEY` by default.
- `/googleapis/python-genai`: Gemini Developer API supports `GEMINI_API_KEY` and `GOOGLE_API_KEY`; Vertex uses project/location credentials.
- `/websites/github_en_rest`: GitHub REST auth uses bearer-style tokens; Actions commonly exposes `GITHUB_TOKEN` and `GH_TOKEN`.
- `/eclipse-theia/theia`: Theia supports frontend/backend modules, preferences, and widgets; preferences are not secure storage.
- `/fastapi/typer`: nested CLI command groups and option validation fit `arc providers key ...` UX.

Web search status: unavailable in this environment because Google Search returned `Not authenticated with Antigravity`. Omniroute and web-auth findings are therefore conservative and marked research-only.

## Implementation Choices

- API providers are env-ref only in v0.1.
- Local providers use `local` auth and require no key by default.
- Web-session providers are `research_only`; ARC does not capture browser cookies, passwords, or session tokens.
- GitHub is token-env-ref only (`GITHUB_TOKEN`, `GH_TOKEN`).
- Provider keys are separate from audit HMAC keys.
- Direct provider-key keychain storage remains future work.

## Provider Coverage

The catalog currently contains 61 entries. Required entries are present:

| Provider | ID | Auth | Env refs / status |
|---|---|---|---|
| OpenAI | `openai` | API key | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | API key | `ANTHROPIC_API_KEY` |
| Google AI / Gemini | `google-ai` | API key | `GOOGLE_API_KEY`, `GEMINI_API_KEY` |
| Google Vertex AI | `google-vertex` | OAuth planned | Google credentials |
| xAI / Grok API | `xai-grok` | API key | `XAI_API_KEY` |
| Perplexity API | `perplexity` | API key | `PERPLEXITY_API_KEY`, `PPLX_API_KEY` |
| OpenRouter | `openrouter` | API key | `OPENROUTER_API_KEY` |
| Azure OpenAI | `azure-openai` | API key | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| AWS Bedrock | `aws-bedrock` | cloud credentials | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_REGION` |
| Alibaba DashScope / Qwen | `qwen` | API key | `QWEN_API_KEY`, `DASHSCOPE_API_KEY` |
| Moonshot / Kimi | `kimi` | API key | `MOONSHOT_API_KEY`, `KIMI_API_KEY` |
| GitHub API | `github` | bearer token | `GITHUB_TOKEN`, `GH_TOKEN` |
| ChatGPT Web | `chatgpt-web` | research-only | no cookie capture |
| Claude Web | `claude-web` | research-only | no cookie capture |
| Grok Web | `grok-web` | research-only | no cookie capture |
| Perplexity Web | `perplexity-web` | research-only | no cookie capture |
| Antigravity | `antigravity` | research-only | no official auth automation verified |
| Omniroute | `omniroute` | research-only | web search blocked; follow-up required |

Other catalog entries include Mistral, Cohere, Together, Fireworks, Groq, Replicate, Hugging Face, DeepSeek, Baidu Qianfan, Zhipu, Tencent Hunyuan, AI21, Cerebras, SambaNova, NVIDIA NIM, IBM watsonx, Cloudflare Workers AI, Voyage, Jina, Pinecone, Weaviate, Zilliz, Supabase, LangSmith, Langfuse, Helicone, Portkey, LiteLLM, Ollama, LM Studio, vLLM, llama.cpp, LocalAI, GitHub Models, Hugging Face Inference Endpoints, ElevenLabs, Tavily, Brave Search, Serper, Exa, Browserbase, Composio, and E2B.

## Web Auth Warning

Web-auth entries are intentionally not implemented beyond metadata. ARC must not automate web sessions by scraping browser cookies or credentials. Use official APIs or OAuth/device-code flows where available.

## Omniroute Findings

No reliable Omniroute auth-config documentation could be fetched because web search was unavailable. The provider is included as `research_only` with no env refs. Before implementation, verify whether Omniroute has an official API, OAuth, CLI token store, or web-session-only mechanism.

## Verification Expectations

- `arc providers catalog --json` returns all catalog entries and no raw keys.
- `arc providers key set <provider> --env ENV_VAR` stores only env var names.
- Raw key-looking values passed to `--env` are rejected.
- IDE Config tab shows provider dropdown, env-var input, and web-auth warning.
