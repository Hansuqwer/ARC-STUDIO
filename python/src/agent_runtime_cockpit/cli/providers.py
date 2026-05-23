"""Provider, accounts, key, quota, routing commands (Phase 25)."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok

from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    _out,
    _setup_logging,
)
from ._subapps import accounts_app, key_app, providers_app, quota_app, routing_app


@providers_app.command("list")
def providers_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List built-in provider definitions. No network calls are made."""
    _setup_logging(debug)
    from ..provider_action import PROVIDERS

    _out(ok([provider.model_dump() for provider in PROVIDERS]), json_output)


@providers_app.command("catalog")
def providers_catalog(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status (supported, env_ref_only, oauth_planned, research_only)",
    ),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List provider catalog with setup guidance.

    Shows available providers with setup instructions, required environment variables,
    and documentation links. Use --status or --category to filter results.
    """
    _setup_logging(debug)
    from ..provider_action import PROVIDERS

    # Filter providers
    providers = PROVIDERS
    if status:
        providers = [p for p in providers if p.status == status]
    if category:
        providers = [p for p in providers if p.category == category]

    if json_output:
        # JSON output: raw provider definitions
        _out(ok([provider.model_dump() for provider in providers]), json_output)
        return

    # Human-readable output with setup guidance
    output_lines = []
    output_lines.append(f"\n{'=' * 80}")
    output_lines.append(f"ARC Studio Provider Catalog ({len(providers)} providers)")
    output_lines.append(f"{'=' * 80}\n")

    for provider in providers:
        output_lines.append(f"Provider: {provider.display_name}")
        output_lines.append(f"  ID: {provider.id}")
        output_lines.append(f"  Status: {provider.status}")
        output_lines.append(f"  Auth: {provider.credential_label}")

        if provider.env_key_names:
            env_vars = " or ".join(provider.env_key_names)
            output_lines.append(f"  Required: {env_vars}")

        if provider.default_models:
            models = ", ".join(provider.default_models[:3])
            if len(provider.default_models) > 3:
                models += f" (+{len(provider.default_models) - 3} more)"
            output_lines.append(f"  Models: {models}")

        # Features
        features = []
        if provider.supports_tools:
            features.append("tools")
        if provider.supports_chat:
            features.append("chat")
        if provider.supports_embeddings:
            features.append("embeddings")
        if provider.supports_images:
            features.append("images")
        if provider.supports_streaming:
            features.append("streaming")
        if features:
            output_lines.append(f"  Features: {', '.join(features)}")

        if provider.docs_url:
            output_lines.append(f"  Docs: {provider.docs_url}")

        # Setup instructions
        if provider.env_key_names and provider.auth_kind.value != "local":
            output_lines.append("\n  Setup:")
            if provider.docs_url:
                output_lines.append(
                    f"    1. Get {provider.credential_label} from {provider.docs_url}"
                )
            output_lines.append(
                f'    2. Set environment variable: export {provider.env_key_names[0]}="..."'
            )
            output_lines.append(f"    3. Test connection: arc providers test {provider.id}")
        elif provider.auth_kind.value == "local":
            output_lines.append("\n  Setup:")
            output_lines.append("    Local provider - no API key required")
            if provider.docs_url:
                output_lines.append(f"    See {provider.docs_url} for installation")

        # Warnings
        if provider.warnings:
            for warning in provider.warnings:
                output_lines.append(f"  ⚠️  {warning}")

        output_lines.append("")  # Blank line between providers

    output_lines.append(f"{'=' * 80}")
    output_lines.append("Commands:")
    output_lines.append("  arc providers test <provider-id>  - Test provider connection")
    output_lines.append("  arc providers models              - List available models")
    output_lines.append("  arc providers status              - Show configured providers")
    output_lines.append(f"{'=' * 80}\n")

    print("\n".join(output_lines))
    _out(ok({"count": len(providers)}), True)  # Still output JSON for programmatic use


@providers_app.command("status")
def providers_status(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return dry-run provider status from environment presence only."""
    import os

    _setup_logging(debug)
    from ..provider_action import provider_statuses

    _out(ok([status.model_dump() for status in provider_statuses(os.environ)]), json_output)


@providers_app.command("diagnostics")
def providers_diagnostics(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return redacted provider diagnostics (statuses, routing, accounts, quota).

    No network calls are made. All secrets are redacted.
    """
    import os

    _setup_logging(debug)
    from ..provider_action import redacted_diagnostics

    _out(ok(redacted_diagnostics(os.environ)), json_output)


@providers_app.command("test")
def providers_test(
    provider_id: str = typer.Argument(..., help="Provider id to test"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Test provider connection using environment variables.

    Validates that required environment variables are set and have valid format.
    No network calls are made. Use 'arc providers action --live' for live testing.
    """
    _setup_logging(debug)
    import os
    from ..provider_action import PROVIDERS, provider_statuses

    # Find provider definition
    provider = next((p for p in PROVIDERS if p.id == provider_id), None)
    if provider is None:
        available = ", ".join(sorted(p.id for p in PROVIDERS[:10]))
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown provider: {provider_id}. Try: {available}... (use 'arc providers list' for all)",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Check environment variables
    statuses = provider_statuses(os.environ)
    status = next((s for s in statuses if s.provider == provider_id), None)

    if not status or not status.api_key_configured:
        missing_vars = (
            " or ".join(provider.env_key_names) if provider.env_key_names else "credentials"
        )
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Provider '{provider_id}' not configured. Set environment variable: {missing_vars}",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Build success result
    result = {
        "provider": provider_id,
        "display_name": provider.display_name,
        "configured": True,
        "env_source": status.api_key_source,
        "base_url": provider.default_base_url,
        "status": provider.status,
        "test_result": "credentials_present",
        "message": f"✓ Provider '{provider.display_name}' is configured via {status.api_key_source}",
        "docs_url": provider.docs_url if provider.docs_url else None,
    }

    _out(ok(result), json_output)


@providers_app.command("models")
def providers_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider id"),
    configured_only: bool = typer.Option(
        True,
        "--configured-only/--all",
        help="Show only configured providers (default: configured only)",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available models from providers.

    By default, shows models from configured providers only (those with env vars set).
    Use --all to show models from all providers regardless of configuration.
    """
    _setup_logging(debug)
    import os
    from ..provider_action import PROVIDERS, provider_statuses

    # Get provider statuses to see which are configured
    statuses = provider_statuses(os.environ)
    configured_providers = {s.provider for s in statuses if s.api_key_configured}

    # Build model list
    models = []
    for p in PROVIDERS:
        if provider and p.id != provider:
            continue

        # Check if provider is configured (has env vars or is local)
        is_configured = p.id in configured_providers or p.auth_kind.value == "local"

        if configured_only and not is_configured:
            continue

        # Add each model from this provider
        for model in p.default_models:
            models.append(
                {
                    "provider": p.id,
                    "provider_name": p.display_name,
                    "model": model,
                    "configured": is_configured,
                    "supports_tools": p.supports_tools,
                    "supports_chat": p.supports_chat,
                    "supports_streaming": p.supports_streaming,
                    "base_url": p.default_base_url,
                }
            )

    if not models:
        if configured_only:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "No configured providers found. Set provider environment variables or use --all to see all models.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        else:
            _out(ok([]), json_output)
            return

    _out(ok(models), json_output)


@providers_app.command("proxy")
def providers_proxy(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Provider id (default: routing default)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Model name (default: routing default)"
    ),
    prompt: str = typer.Option("Hello", "--prompt", help="Prompt text for dry-run proxy"),
    live: bool = typer.Option(
        False,
        "--live",
        help="Request live provider mode; still requires env gate and --allow-paid-calls",
    ),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow paid provider calls when --live is set"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Dry-run provider proxy. No network call is made.

    Validates routing, quota reservation, and gating without
    invoking any LLM API. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true
    and --allow-paid-calls for a live proxy call.
    """
    _setup_logging(debug)
    import os
    from ..provider_action import (
        ProviderRequest,
        ProviderRoutingStore,
        check_provider_cost_gate,
        dry_run_proxy,
    )

    routing = ProviderRoutingStore().get()
    req = ProviderRequest(
        provider=provider or routing.default_provider,
        model=model or routing.default_model,
        prompt=prompt,
        dry_run=not live,
        allow_paid_calls=allow_paid_calls,
    )
    try:
        gate = check_provider_cost_gate(req, os.environ)
        if not gate.allowed:
            messages = {
                "live_provider_calls_disabled": "Live provider calls disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true and pass --live --allow-paid-calls.",
                "paid_provider_calls_disabled": "Paid provider calls disabled. Pass --allow-paid-calls with --live.",
            }
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    messages.get(
                        gate.reason or "", gate.reason or "Provider cost gate blocked request"
                    ),
                ),
                json_output,
            )
            raise typer.Exit(1)
        if live:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Live provider proxy is gated but not implemented in this CLI path; no network call was made.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        resp = dry_run_proxy(req)
        _out(ok(resp.model_dump()), json_output)
    except RuntimeError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)


@providers_app.command("action")
def providers_action(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Provider id (default: routing default)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Model name (default: routing default)"
    ),
    prompt: str = typer.Option(
        "ARC provider action smoke", "--prompt", help="Prompt text for smoke contract"
    ),
    live: bool = typer.Option(False, "--live", help="Request gated live smoke scaffold"),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow paid provider calls when --live is set"
    ),
    confirm: Optional[str] = typer.Option(
        None, "--confirm", help="Required value: RUN_PROVIDER_ACTION:<provider>:<model>"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run narrow provider action contract; live path is gated closed smoke scaffold."""
    _setup_logging(debug)
    import os
    from ..provider_action import ProviderActionRequest, ProviderRoutingStore, run_provider_action

    routing = ProviderRoutingStore().get()
    req = ProviderActionRequest(
        provider=provider or routing.default_provider,
        model=model or routing.default_model,
        prompt=prompt,
        dry_run=not live,
        allow_paid_calls=allow_paid_calls,
        confirmation=confirm,
    )
    try:
        result = run_provider_action(req, os.environ)
    except RuntimeError as exc:
        messages = {
            "live_provider_calls_disabled": "Live provider action disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true and pass --live --allow-paid-calls plus --confirm.",
            "paid_provider_calls_disabled": "Paid provider calls disabled. Pass --allow-paid-calls with --live.",
            "provider_key_env_missing": "Provider key env var missing. Configure an env ref; raw keys are not accepted.",
        }
        raw_message = str(exc)
        message = messages.get(raw_message, raw_message)
        _out(err(ArcErrorCode.INVALID_INPUT, message), json_output)
        raise typer.Exit(1)
    _out(ok(result.model_dump()), json_output)


providers_app.add_typer(accounts_app)
providers_app.add_typer(key_app)


@key_app.command("status")
def providers_key_status(
    provider: Optional[str] = typer.Argument(None, help="Provider id filter"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show provider key status from env vars and saved env-ref accounts."""
    import os

    _setup_logging(debug)
    from ..provider_action import PROVIDERS, ProviderAccountStore, provider_statuses

    env_status = {status.provider: status.model_dump() for status in provider_statuses(os.environ)}
    accounts = ProviderAccountStore().list_accounts()
    entries = []
    for definition in PROVIDERS:
        if provider and definition.id != provider:
            continue
        matching_accounts = [a for a in accounts if a.provider == definition.id]
        status = env_status.get(definition.id, {})
        entries.append(
            {
                "provider": definition.id,
                "display_name": definition.display_name,
                "auth_kind": definition.auth_kind.value,
                "credential_label": definition.credential_label,
                "status": definition.status,
                "configured": bool(status.get("api_key_configured"))
                or any(a.enabled for a in matching_accounts)
                or definition.auth_kind.value == "local",
                "source": status.get("api_key_source")
                and "env"
                or (
                    "account_ref"
                    if matching_accounts
                    else ("local" if definition.auth_kind.value == "local" else "unset")
                ),
                "env_key_names": definition.env_key_names,
                "accounts": [a.model_dump() for a in matching_accounts],
                "warnings": definition.warnings,
            }
        )
    _out(ok(entries), json_output)


@key_app.command("set")
def providers_key_set(
    provider: str = typer.Argument(..., help="Provider id"),
    env_var: str = typer.Option(..., "--env", help="Environment variable containing the key"),
    label: Optional[str] = typer.Option(None, "--label", help="Account label"),
    model: Optional[str] = typer.Option(None, "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Save an env-var-backed provider key reference. Never stores raw keys."""
    _setup_logging(debug)
    from ..provider_action import PROVIDERS, ProviderAccountStore, validate_env_var_name

    provider_ids = {p.id for p in PROVIDERS}
    if provider not in provider_ids:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown provider: {provider}"), json_output)
        raise typer.Exit(2)
    try:
        validate_env_var_name(env_var)
        account = ProviderAccountStore().add_env_account(
            provider, label or "default", env_var, model
        )
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(account.model_dump()), json_output)


@key_app.command("unset")
def providers_key_unset(
    provider_or_account_id: str = typer.Argument(..., help="Provider id or account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete saved provider key references. Does not modify environment variables."""
    _setup_logging(debug)
    from ..provider_action import ProviderAccountStore

    store = ProviderAccountStore()
    accounts = store.list_accounts()
    deleted: list[str] = []
    for account in accounts:
        if account.id == provider_or_account_id or account.provider == provider_or_account_id:
            if store.delete(account.id):
                deleted.append(account.id)
    _out(ok({"deleted": deleted, "count": len(deleted)}), json_output)


@accounts_app.command("list")
def providers_accounts_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List provider accounts without exposing secrets."""
    _setup_logging(debug)
    from ..provider_action import ProviderAccountStore

    accounts = ProviderAccountStore().list_accounts()
    _out(ok([account.model_dump() for account in accounts]), json_output)


@accounts_app.command("add")
def providers_accounts_add(
    provider: str = typer.Option(..., "--provider", help="Provider id"),
    label: str = typer.Option(..., "--label", help="Account label"),
    api_key_env: str = typer.Option(
        ..., "--api-key-env", help="Environment variable containing the key"
    ),
    default_model: Optional[str] = typer.Option(None, "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Add an env-var-backed provider account. The key is never printed."""
    _setup_logging(debug)
    from ..provider_action import ProviderAccountStore

    account = ProviderAccountStore().add_env_account(provider, label, api_key_env, default_model)
    _out(ok(account.model_dump()), json_output)


@accounts_app.command("disable")
def providers_accounts_disable(
    account_id: str = typer.Argument(..., help="Account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Disable a provider account."""
    _setup_logging(debug)
    from ..provider_action import ProviderAccountStore

    account = ProviderAccountStore().set_enabled(account_id, False)
    if account is None:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Provider account not found: {account_id}"),
            json_output,
        )
        raise typer.Exit(1)
    _out(ok(account.model_dump()), json_output)


@accounts_app.command("delete")
def providers_accounts_delete(
    account_id: str = typer.Argument(..., help="Account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a provider account metadata record."""
    _setup_logging(debug)
    from ..provider_action import ProviderAccountStore

    deleted = ProviderAccountStore().delete(account_id)
    _out(ok({"deleted": deleted, "account_id": account_id}), json_output)


providers_app.add_typer(quota_app)


@quota_app.command("show")
def providers_quota_show(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show today's provider quota usage."""
    _setup_logging(debug)
    from ..provider_action import ProviderQuotaStore

    store = ProviderQuotaStore()
    usage = store.usage()
    if provider:
        filtered = {k: v for k, v in usage.get("counters", {}).items() if f":{provider}" in k}
        payload = {"date": usage["date"], "provider": provider, "counters": filtered}
    else:
        payload = usage
    _out(ok(payload), json_output)


@quota_app.command("reset")
def providers_quota_reset(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Reset today's local provider quota counters only."""
    _setup_logging(debug)
    from ..provider_action import ProviderQuotaStore

    store = ProviderQuotaStore()
    store.reset()
    _out(ok({"reset": True, "scope": "local_quota_counters_only"}), json_output)


providers_app.add_typer(routing_app)


@routing_app.command("get")
def providers_routing_get(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return persisted dry-run routing policy."""
    _setup_logging(debug)
    from ..provider_action import ProviderRoutingStore

    _out(ok(ProviderRoutingStore().get().model_dump()), json_output)


@routing_app.command("set")
def providers_routing_set(
    mode: str = typer.Option("manual", "--mode", help="manual | priority | fallback"),
    provider: str = typer.Option("openai", "--provider", help="Default provider"),
    model: str = typer.Option("gpt-4.1-mini", "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Persist provider routing policy. Live calls remain gated."""
    _setup_logging(debug)
    from ..provider_action import ProviderRoutingPolicy, ProviderRoutingStore

    policy = ProviderRoutingPolicy(mode=mode, default_provider=provider, default_model=model)
    _out(ok(ProviderRoutingStore().set(policy).model_dump()), json_output)
