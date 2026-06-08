"""Property/fuzz tests (hypothesis) for the Batch 6 mobile hardening primitives.

Covers the safety-critical invariants of:
- SecureLocalStore  — encrypt/decrypt round-trip + ciphertext-at-rest + tamper fail-closed
- EgressGuard       — deterministic budget/critical-class decisions + budget never exceeded
- CapabilityEntryGate — route is ALWAYS fixtures and never reaches a real device (default-denied)
"""

from __future__ import annotations

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from agent_runtime_cockpit.mobile import (
    CapabilityEntryGate,
    EgressGuard,
    FeatureFlags,
    InMemoryKeyProvider,
    SecureLocalStore,
    SecureStoreError,
)
from agent_runtime_cockpit.mobile.capability_gate import FIXTURES_ROUTE

# JSON-serializable values the store must round-trip.
_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=64),
    lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(max_size=8), c, max_size=4),
    max_leaves=8,
)


# ───────────────────────── SecureLocalStore ─────────────────────────


@given(key=st.text(min_size=1, max_size=40), value=_VALUES)
@settings(max_examples=150, deadline=None)
def test_secure_store_roundtrip(key, value) -> None:
    store = SecureLocalStore(key_provider=InMemoryKeyProvider())
    store.put(key, value)
    assert store.get(key) == value
    assert store.delete(key) is True
    assert key not in store.keys()


@given(
    value=st.text(
        min_size=24, max_size=120, alphabet=st.characters(min_codepoint=65, max_codepoint=90)
    )
)
@settings(max_examples=80, deadline=None)
def test_secure_store_ciphertext_at_rest(tmp_path_factory, value) -> None:
    # distinct uppercase-only token => will not coincidentally appear in urlsafe-b64 ciphertext
    path = tmp_path_factory.mktemp("ss") / "store.json"
    store = SecureLocalStore(key_provider=InMemoryKeyProvider(), path=path)
    store.put("secret", value, "critical")
    raw = path.read_text(encoding="utf-8")
    assert value not in raw  # plaintext never persisted
    assert store.get("secret") == value  # but still decryptable


@given(value=st.text(min_size=1, max_size=64))
@settings(max_examples=60, deadline=None)
def test_secure_store_tamper_fails_closed(tmp_path_factory, value) -> None:
    key = InMemoryKeyProvider()
    path = tmp_path_factory.mktemp("ss") / "store.json"
    store = SecureLocalStore(key_provider=key, path=path)
    store.put("k", value)
    # corrupt the persisted ciphertext, reload with the same key
    blob = json.loads(path.read_text())
    entry = blob["entries"]["k"] if "entries" in blob else next(iter(blob.values()))
    ct = entry["ciphertext"]
    entry["ciphertext"] = ("A" if ct[:1] != "A" else "B") + ct[1:]
    path.write_text(json.dumps(blob), encoding="utf-8")
    reloaded = SecureLocalStore(key_provider=InMemoryKeyProvider(key.get_key()), path=path)
    try:
        reloaded.get("k")
        raise AssertionError("tampered ciphertext must fail closed")
    except SecureStoreError:
        pass


# ───────────────────────── EgressGuard ─────────────────────────


@given(
    budget=st.integers(min_value=0, max_value=10_000),
    cost=st.integers(min_value=-50, max_value=20_000),
    cls=st.sampled_from(["low", "internal", "sensitive", "critical"]),
)
@settings(max_examples=200, deadline=None)
def test_egress_check_is_deterministic_and_safe(budget, cost, cls) -> None:
    guard = EgressGuard(budget_bytes=budget)
    d1 = guard.check(cost, cls)
    d2 = guard.check(cost, cls)
    assert d1.as_dict() == d2.as_dict()  # pure / deterministic

    if cls == "critical":
        assert d1.allowed is False  # critical never egresses
    elif cost < 0:
        assert d1.allowed is False
    elif cost > budget:
        assert d1.allowed is False
    else:
        assert d1.allowed is True
        assert d1.remaining_bytes == budget - cost


@given(
    budget=st.integers(min_value=0, max_value=5_000),
    costs=st.lists(st.integers(min_value=0, max_value=2_000), max_size=20),
)
@settings(max_examples=120, deadline=None)
def test_egress_record_never_exceeds_budget(budget, costs) -> None:
    guard = EgressGuard(budget_bytes=budget)
    for c in costs:
        guard.record(c, "low")
        assert guard.usage()["used_total"] <= budget  # budget is never exceeded


# ───────────────────────── CapabilityEntryGate ─────────────────────────

_CAP = st.text(min_size=1, max_size=48)


@given(cap=_CAP, flag_on=st.booleans(), compliance=st.booleans())
@settings(max_examples=200, deadline=None)
def test_gate_never_routes_to_real_device(cap, flag_on, compliance) -> None:
    flags = FeatureFlags()
    if flag_on:
        flags.enable(f"native.{cap}")
    gate = CapabilityEntryGate(flags, b"k" * 32)

    decision = gate.evaluate(cap, compliance_present=compliance)
    # THE safety invariant: route is always fixtures regardless of any input.
    assert decision.route == FIXTURES_ROUTE
    assert decision.simulator_preview is True

    result = gate.execute(cap, compliance_present=compliance)
    assert result["route"] == FIXTURES_ROUTE
    assert result["executed_real_device"] is False


@given(cap=_CAP)
@settings(max_examples=60, deadline=None)
def test_gate_default_denied(cap) -> None:
    # default-off flags + no signed plan + no grant => not eligible
    gate = CapabilityEntryGate(FeatureFlags(), b"k" * 32)
    decision = gate.evaluate(cap)
    assert decision.eligible is False
    assert "feature_flag_off_or_kill_switch_engaged" in decision.missing
    assert "signed_plan_invalid" in decision.missing
