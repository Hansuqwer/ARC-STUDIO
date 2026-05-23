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
def providers_catalog(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List provider auth catalog entries. No secrets or network calls."""
    _setup_logging(debug)
    from ..provider_action import PROVIDERS

    _out(ok([provider.model_dump() for provider in PROVIDERS]), json_output)


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
