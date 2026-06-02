"""Providers view — interactive widget to browse all providers, configure API keys,
and select a model. Mirrors OpenCode's /connect → /models flow.

Loads all providers from the live models.dev catalog (ARC_MODELS_DEV_LIVE=1) or
the bundled snapshot. Every provider is shown; free-tier providers are marked ★.
"""

from __future__ import annotations

import os
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from ..data import DataStore


def _load_all_providers() -> list[Any]:
    """Return all providers — live catalog first, bundled snapshot as fallback."""
    import asyncio

    from agent_runtime_cockpit.providers.models_dev import (
        bundled_openai_compatible_providers,
        fetch_models_dev_catalog,
    )

    if os.environ.get("ARC_MODELS_DEV_LIVE"):
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(fetch_models_dev_catalog())
            loop.close()
            return list(result.values())
        except Exception:
            pass
    return list(bundled_openai_compatible_providers().values())


def _is_configured(provider: Any) -> bool:
    """True if any env var or stored credential is set for this provider."""
    for env_var in provider.env:
        if os.environ.get(env_var):
            return True
    try:
        from agent_runtime_cockpit.auth.manager import get_decrypted_api_key

        if get_decrypted_api_key(provider.id, trust_check=False):
            return True
    except Exception:
        pass
    return False


def _has_free_model(provider: Any) -> bool:
    return any(
        not (m.cost.get("input", 1) or m.cost.get("output", 1)) for m in provider.models.values()
    )


def _provider_row(provider: Any) -> str:
    star = "★ " if _has_free_model(provider) else "  "
    check = "✓" if _is_configured(provider) else " "
    env = provider.env[0] if provider.env else ""
    return f"[{check}] {star}{provider.name}  ({env})"


# ─────────────────────────── MODEL LIST ──────────────────────────────────────


class ModelListScreen(ModalScreen[str | None]):
    """Show all models for a provider; select one to set as current model."""

    BINDINGS = [Binding("escape", "dismiss_none", "Back")]

    def __init__(self, provider: Any, data: DataStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._provider = provider
        self._data = data

    def compose(self) -> ComposeResult:
        yield Label(f"Models — {self._provider.name}", id="model-title")
        yield Input(placeholder="Filter models…", id="model-filter")
        yield ListView(id="model-list")

    def on_mount(self) -> None:
        self._models = list(self._provider.models.values())
        self._populate(self._models)
        self.query_one("#model-filter", Input).focus()

    def _populate(self, models: list[Any]) -> None:
        lv = self.query_one("#model-list", ListView)
        lv.clear()
        for m in models[:100]:
            ctx = m.limit.get("context", 0)
            ctx_str = f"{ctx // 1000}K" if ctx else "?"
            free = "★ free  " if not (m.cost.get("input", 1) or m.cost.get("output", 1)) else ""
            tc = "tools" if m.tool_call else "no-tools"
            lv.append(ListItem(Label(f"{m.name or m.id}  ({ctx_str} ctx, {free}{tc})")))

    @on(Input.Changed, "#model-filter")
    def filter(self, event: Input.Changed) -> None:
        q = event.value.lower()
        filtered = [m for m in self._models if q in (m.name or m.id).lower()] if q else self._models
        self._populate(filtered)

    @on(ListView.Selected)
    def select_model(self, event: ListView.Selected) -> None:
        # Determine selected model by index
        lv = self.query_one("#model-list", ListView)
        q = self.query_one("#model-filter", Input).value.lower()
        filtered = [m for m in self._models if q in (m.name or m.id).lower()] if q else self._models
        idx = lv.index
        if idx is not None and 0 <= idx < len(filtered):
            model = filtered[idx]
            self._data.current_model = model.id
            self._data.current_provider = self._provider.id
            self.dismiss(model.id)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)


# ─────────────────────────── API KEY ENTRY ───────────────────────────────────


class ApiKeyScreen(ModalScreen[bool]):
    """Enter / clear the API key for a provider, then show models."""

    BINDINGS = [Binding("escape", "dismiss_false", "Back")]

    def __init__(self, provider: Any, data: DataStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._provider = provider
        self._data = data

    def compose(self) -> ComposeResult:
        env = self._provider.env[0] if self._provider.env else "API_KEY"
        configured = _is_configured(self._provider)
        status = (
            "✓ Already configured — enter new key to replace, or leave blank to keep"
            if configured
            else f"Set {env}"
        )
        yield Label(f"{self._provider.name}", id="prov-title")
        yield Label(status, id="prov-status")
        yield Label(f"Base URL: {self._provider.api}", id="prov-url")
        if self._provider.doc:
            yield Label(f"Docs: {self._provider.doc}", id="prov-doc")
        yield Input(placeholder=f"Enter {env}…", password=True, id="key-input")
        yield Label("Enter: save  |  Esc: back  |  Tab: skip to models", id="key-hint")

    def on_mount(self) -> None:
        self.query_one("#key-input", Input).focus()

    @on(Input.Submitted, "#key-input")
    def save_key(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if key:
            try:
                from agent_runtime_cockpit.auth.manager import (
                    encrypt_credential,
                    save_credential,
                )

                cred = encrypt_credential(self._provider.id, key)
                save_credential(cred)
                # Set env var immediately so it's picked up without restart
                for env_var in self._provider.env:
                    os.environ[env_var] = key
            except Exception as exc:
                self.query_one("#prov-status", Label).update(f"⚠ Save failed: {exc}")
                return

        # Show model list
        def _after_models(model_id: str | None) -> None:
            self.dismiss(True)

        self.app.push_screen(ModelListScreen(self._provider, self._data), _after_models)

    def on_key(self, event) -> None:
        if event.key == "tab":
            event.stop()

            # Skip key entry — go straight to models
            def _after(model_id: str | None) -> None:
                self.dismiss(True)

            self.app.push_screen(ModelListScreen(self._provider, self._data), _after)

    def action_dismiss_false(self) -> None:
        self.dismiss(False)


# ─────────────────────────── PROVIDER LIST ───────────────────────────────────


class ProvidersView(ModalScreen[None]):
    """Full-catalog interactive provider list.

    Typing filters the list. Enter on a row opens API key entry + model list.
    """

    BINDINGS = [Binding("escape", "dismiss_screen", "Close")]

    def __init__(self, data: DataStore, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data = data
        self._providers: list[Any] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="providers-container"):
            yield Label("Providers  (type to filter, Enter to configure)", id="prov-header")
            yield Input(placeholder="Search providers…", id="prov-filter")
            yield ListView(id="prov-list")
            yield Label(
                "★=free  ✓=configured  |  Enter:configure  Tab:models  Esc:close", id="prov-footer"
            )

    def on_mount(self) -> None:
        self._providers = _load_all_providers()
        self._populate(self._providers)
        self.query_one("#prov-filter", Input).focus()

    def _populate(self, providers: list[Any]) -> None:
        lv = self.query_one("#prov-list", ListView)
        lv.clear()
        for p in providers:
            lv.append(ListItem(Label(_provider_row(p))))

    @on(Input.Changed, "#prov-filter")
    def filter(self, event: Input.Changed) -> None:
        q = event.value.lower()
        filtered = (
            [p for p in self._providers if q in p.name.lower() or q in p.id.lower()]
            if q
            else self._providers
        )
        self._populate(filtered)

    def _selected_provider(self) -> Any | None:
        lv = self.query_one("#prov-list", ListView)
        q = self.query_one("#prov-filter", Input).value.lower()
        filtered = (
            [p for p in self._providers if q in p.name.lower() or q in p.id.lower()]
            if q
            else self._providers
        )
        idx = lv.index
        if idx is not None and 0 <= idx < len(filtered):
            return filtered[idx]
        return None

    @on(ListView.Selected)
    def open_provider(self, event: ListView.Selected) -> None:
        provider = self._selected_provider()
        if provider:
            self.app.push_screen(ApiKeyScreen(provider, self._data))

    def on_key(self, event) -> None:
        if event.key == "tab":
            event.stop()
            provider = self._selected_provider()
            if provider:
                self.app.push_screen(ModelListScreen(provider, self._data))

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)
