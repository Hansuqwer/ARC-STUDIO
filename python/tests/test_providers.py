from agent_runtime_cockpit.providers import (
    DEFAULT_ROUTING,
    PROVIDERS,
    ProviderAccountStore,
    ProviderQuotaStore,
    ProviderRequest,
    ProviderRoutingPolicy,
    ProviderRoutingStore,
    check_provider_cost_gate,
    dry_run_proxy,
    mask_secret,
    provider_statuses,
    redact,
)


def test_provider_definitions_include_first_class_providers():
    ids = {provider.id for provider in PROVIDERS}
    assert {"openai", "anthropic", "openrouter", "qwen", "kimi"}.issubset(ids)


def test_provider_statuses_are_dry_run_and_do_not_expose_keys():
    statuses = provider_statuses({"QWEN_API_KEY": "sk-test-qwen-redacted"})
    qwen = next(status for status in statuses if status.provider == "qwen")
    assert qwen.dry_run is True
    assert qwen.api_key_configured is True
    assert qwen.api_key_source == "QWEN_API_KEY"
    assert "sk-test" not in qwen.model_dump_json()


def test_mask_secret_keeps_only_edges():
    assert mask_secret("sk-test-qwen-redacted") == "sk-...cted"
    assert mask_secret("short") == "[REDACTED]"


def test_default_routing_blocks_live_calls():
    assert DEFAULT_ROUTING.dry_run is True
    assert DEFAULT_ROUTING.allow_paid_calls is False


def test_redact_removes_keys_from_nested_payload():
    payload = {"headers": {"authorization": "Bearer abcdefghijklmnopqrstuvwxyz"}, "text": "sk-test-openai-redacted"}
    assert "abcdefghijklmnopqrstuvwxyz" not in str(redact(payload))
    assert "sk-test-openai-redacted" not in str(redact(payload))


def test_account_store_persists_env_ref_without_key(tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "sk-test-qwen-redacted")
    store = ProviderAccountStore(tmp_path / "providers.json")
    account = store.add_env_account("qwen", "personal", "QWEN_API_KEY")
    raw = (tmp_path / "providers.json").read_text()
    assert account.masked_key == "sk-...cted"
    assert "sk-test-qwen-redacted" not in raw
    assert store.list_accounts()[0].key_env_var == "QWEN_API_KEY"


def test_account_store_rejects_direct_key(tmp_path):
    store = ProviderAccountStore(tmp_path / "providers.json")
    try:
        store.add_direct_key_account("openai", "personal", "sk-test-openai-redacted")
    except RuntimeError as exc:
        assert "secure OS keychain" in str(exc)
    else:
        raise AssertionError("direct key storage should fail")


def test_routing_store_persists_policy(tmp_path):
    store = ProviderRoutingStore(tmp_path / "routing.json")
    policy = store.set(ProviderRoutingPolicy(mode="manual", default_provider="openai", default_model="gpt-4.1-mini"))
    assert policy.default_provider == "openai"
    assert store.get().default_model == "gpt-4.1-mini"


def test_proxy_dry_run_no_network(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    response = dry_run_proxy(ProviderRequest(provider="openai", model="gpt-4.1-mini", prompt="hello"))
    assert response.dry_run is True
    assert "No network call" in response.message


def test_cost_gate_allows_default_dry_run_without_live_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    monkeypatch.delenv("ARC_ALLOW_LIVE_PROVIDER_TESTS", raising=False)
    gate = check_provider_cost_gate(ProviderRequest(provider="openai", model="gpt-4.1-mini"), env={})
    assert gate.allowed is True
    assert gate.dry_run is True
    assert gate.live_enabled is False


def test_cost_gate_blocks_live_without_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    gate = check_provider_cost_gate(
        ProviderRequest(provider="openai", model="gpt-4.1-mini", dry_run=False, allow_paid_calls=True),
        env={},
    )
    assert gate.allowed is False
    assert gate.reason == "live_provider_calls_disabled"


def test_cost_gate_blocks_paid_without_request_or_policy_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    gate = check_provider_cost_gate(
        ProviderRequest(provider="openai", model="gpt-4.1-mini", dry_run=False),
        env={"ARC_ALLOW_LIVE_PROVIDER_TESTS": "true"},
    )
    assert gate.allowed is False
    assert gate.reason == "paid_provider_calls_disabled"


def test_proxy_blocked_live_does_not_reserve_quota(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    quota_path = tmp_path / "quota.json"
    monkeypatch.setenv("ARC_PROVIDER_QUOTA", str(quota_path))
    monkeypatch.delenv("ARC_ALLOW_LIVE_PROVIDER_TESTS", raising=False)
    try:
        dry_run_proxy(ProviderRequest(provider="openai", model="gpt-4.1-mini", dry_run=False, allow_paid_calls=True))
    except RuntimeError as exc:
        assert "Live provider calls disabled" in str(exc)
    else:
        raise AssertionError("live calls should fail before quota reservation")
    assert ProviderQuotaStore(quota_path).usage()["counters"] == {}


def test_proxy_live_requires_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_PROVIDER_ROUTING", str(tmp_path / "routing.json"))
    monkeypatch.delenv("ARC_ALLOW_LIVE_PROVIDER_TESTS", raising=False)
    try:
        dry_run_proxy(ProviderRequest(provider="openai", model="gpt-4.1-mini", dry_run=False))
    except RuntimeError as exc:
        assert "Live provider calls disabled" in str(exc)
    else:
        raise AssertionError("live calls should require explicit gate")


def test_quota_store_reserve_and_remaining(tmp_path):
    store = ProviderQuotaStore(tmp_path / "quota.json")
    assert store.remaining("openai", provider_cap=2)["provider"] == 2
    result = store.reserve("openai", provider_cap=2)
    assert result["allowed"] is True
    assert store.remaining("openai", provider_cap=2)["provider"] == 1


def test_quota_store_blocks_provider_cap(tmp_path):
    store = ProviderQuotaStore(tmp_path / "quota.json")
    assert store.reserve("openai", provider_cap=1)["allowed"] is True
    blocked = store.reserve("openai", provider_cap=1)
    assert blocked["allowed"] is False
    assert blocked["reason"] == "provider_request_cap_exceeded"


def test_quota_store_reset_clears_counters(tmp_path):
    store = ProviderQuotaStore(tmp_path / "quota.json")
    store.reserve("openai", account_id="acct", provider_cap=2, account_cap=2)
    store.reset()
    assert store.remaining("openai", "acct", provider_cap=2, account_cap=2) == {"provider": 2, "account": 2}
