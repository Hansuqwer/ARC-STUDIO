# AgentRouter opencode Proxy

Status: local OpenAI-compatible proxy scaffold. Tests use mocked upstream only; no live AgentRouter key was used.

## Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| opencode config schema | https://opencode.ai/config.json | `provider` entries support `options.apiKey`, `options.baseURL`, `models`, `enabled_providers`, and `model` uses `provider/model-id`. | Document opencode config pointing at `http://127.0.0.1:8787/v1` with a dummy local key. | High | Exact `api` value for custom OpenAI-compatible providers remains schema-permitted but not proven live. |
| opencode local config | `opencode.json` | Project config already exists and only configures `amazon-bedrock`. | Do not overwrite existing provider config; provide copy/paste snippet instead. | High | User may prefer global config under `~/.config/opencode/opencode.json`. |
| ARC provider code | `python/src/agent_runtime_cockpit/provider_action.py` | ARC provider config stores env refs only and avoids direct key storage. | Proxy reads `AGENTROUTER_API_KEY` from env and never writes secrets. | High | No existing AgentRouter provider definition exists. |
| Web search | N/A | Google Search tool returned account verification `403`. | AgentRouter API was not externally verified; proxy assumes OpenAI-compatible `/v1/models` and `/v1/chat/completions` pass-through. | Low | Confirm official AgentRouter base URL, auth scheme, models, streaming behavior. |

## Setup

```bash
export AGENTROUTER_API_KEY="..."
export AGENTROUTER_BASE_URL="https://api.agentrouter.org/v1"
export ARC_AGENTROUTER_PROXY_PORT=8787
export ARC_AGENTROUTER_DEFAULT_MODEL="agentrouter/default"
cd python
uv run arc providers agentrouter-proxy
```

Dry config check:

```bash
cd python
uv run arc providers agentrouter-proxy --json
```

The proxy binds to `127.0.0.1` only.

## opencode Config Snippet

Add this to project `opencode.json` or global `~/.config/opencode/opencode.json`, then restart opencode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "agentrouter-local": {
      "name": "AgentRouter Local Proxy",
      "options": {
        "baseURL": "http://127.0.0.1:8787/v1",
        "apiKey": "opencode-local-proxy"
      },
      "models": {
        "agentrouter/default": {
          "id": "agentrouter/default",
          "name": "AgentRouter Default",
          "family": "openai-compatible",
          "tool_call": true,
          "reasoning": true,
          "temperature": true,
          "limit": { "context": 128000, "output": 8192 }
        }
      }
    }
  },
  "model": "agentrouter-local/agentrouter/default"
}
```

If opencode requires an explicit provider API adapter for your installed version, use the same `options.baseURL` / `options.apiKey` against the built-in OpenAI-compatible provider override instead.

## Endpoints

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

The proxy forwards upstream authorization as `Authorization: Bearer $AGENTROUTER_API_KEY`.

## Security Notes

- `AGENTROUTER_API_KEY` stays in the proxy environment.
- opencode receives only a dummy local proxy key.
- Error payloads redact the configured upstream key.
- Request body cap defaults to 1 MiB.
- Upstream timeout defaults to 60 seconds.

## Limitations

- Live AgentRouter API compatibility is not proven.
- Streaming pass-through is implemented for `stream: true`, but only mocked tests were run.
- No auth is enforced on the local loopback proxy; do not expose it beyond `127.0.0.1`.
