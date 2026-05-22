# How to Configure a Provider

**Goal:** Set up an LLM provider (OpenAI, Anthropic, etc.) for use with ARC Studio.

**Time:** 5-10 minutes  
**Prerequisites:** 
- ARC Studio installed
- API key from your chosen provider

---

## Choose Your Provider

ARC Studio supports multiple LLM providers. Choose one:

- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude 3.5 Sonnet, Claude 3 Opus)
- **Google** (Gemini Pro)
- **Alibaba** (Qwen)
- **Others** (see `arc providers list` for full list)

---

## Step 1: Get an API Key

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)

### Anthropic
1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key (starts with `sk-ant-`)

### Google
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API key"
3. Copy the key

---

## Step 2: Set the API Key

### Option A: Environment Variable (Recommended)

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

Then reload your shell:

```bash
source ~/.zshrc  # or ~/.bashrc
```

### Option B: .env File

Create `.env` in your workspace:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Important:** Add `.env` to `.gitignore` to avoid committing secrets.

---

## Step 3: Add Provider Account

Register the provider with ARC Studio:

```bash
cd python
uv run arc providers accounts add \
  --provider openai \
  --label "OpenAI Production" \
  --env-var OPENAI_API_KEY \
  --model gpt-4
```

**Parameters:**
- `--provider`: Provider name (openai, anthropic, google, etc.)
- `--label`: Friendly name for this account
- `--env-var`: Environment variable containing the API key
- `--model`: Default model to use (optional)

**Example for Anthropic:**

```bash
uv run arc providers accounts add \
  --provider anthropic \
  --label "Anthropic Claude" \
  --env-var ANTHROPIC_API_KEY \
  --model claude-3-5-sonnet-20241022
```

---

## Step 4: Verify Configuration

Check that the provider is configured:

```bash
uv run arc providers list
```

You should see your provider in the list with status "configured".

Check provider diagnostics:

```bash
uv run arc providers diagnostics
```

This shows:
- Which providers are configured
- Which API keys are present (redacted)
- Default models
- Routing policy

---

## Step 5: Test the Provider (Optional)

Test that the provider works:

```bash
uv run arc providers action \
  --provider openai \
  --action chat \
  --prompt "Hello, world!"
```

**Note:** This is a dry-run by default (no actual API call). To make a real call, set `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`.

---

## Troubleshooting

### "Provider not found"

**Problem:** `arc providers accounts add` fails with "Unknown provider: xyz"

**Solution:** Check available providers:

```bash
uv run arc providers catalog
```

Use the exact provider name from the catalog.

---

### "API key not found"

**Problem:** Provider shows "not configured" or "key missing"

**Solution:** 
1. Check the environment variable is set:
   ```bash
   echo $OPENAI_API_KEY
   ```
2. If empty, set it and reload your shell
3. Verify the variable name matches what you passed to `--env-var`

---

### "Invalid API key"

**Problem:** Provider test fails with "Invalid API key" or "Unauthorized"

**Solution:**
1. Verify the API key is correct (copy it again from the provider's website)
2. Check for extra spaces or newlines in the key
3. Ensure the key hasn't expired or been revoked
4. For OpenAI, check you have credits available

---

### "Model not found"

**Problem:** Provider test fails with "Model not found" or "Model not available"

**Solution:**
1. Check available models for your provider:
   ```bash
   uv run arc providers list --provider openai
   ```
2. Use a model from the list
3. For OpenAI, ensure you have access to the model (GPT-4 requires separate access)

---

## Next Steps

Now that your provider is configured:

- **[Run a workflow](./run-workflow.md)** using the provider
- **[Configure a profile](./configure-profile.md)** to control provider access
- **[Inspect traces](./inspect-trace.md)** to see provider calls

---

## Related Documentation

- **[Provider Reference](../reference/providers.md)** — Full list of supported providers
- **[Security Model](../explanation/security.md)** — How API keys are stored and used
- **[Error Codes](../reference/error-codes.md)** — Provider-related error codes
