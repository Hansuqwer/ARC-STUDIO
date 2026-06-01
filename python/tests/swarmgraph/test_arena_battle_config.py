"""Tests for arena_battle_mode configuration."""

from __future__ import annotations

import pytest

from swarmgraph.config import SwarmGraphConfig, ExecutionMode


def test_arena_battle_mode_default_false():
    """arena_battle_mode defaults to False."""
    config = SwarmGraphConfig()
    assert config.arena_battle_mode is False


def test_arena_battle_mode_can_be_enabled():
    """arena_battle_mode can be set to True."""
    config = SwarmGraphConfig(arena_battle_mode=True)
    assert config.arena_battle_mode is True


def test_arena_battle_mode_with_provider_backed():
    """arena_battle_mode works with provider_backed execution mode."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        arena_battle_mode=True,
    )
    assert config.arena_battle_mode is True
    assert config.execution_mode == ExecutionMode.provider_backed


def test_arena_battle_mode_with_fake_offline():
    """arena_battle_mode can be set with fake_offline (for testing)."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.fake_offline,
        arena_battle_mode=True,
    )
    assert config.arena_battle_mode is True
    assert config.execution_mode == ExecutionMode.fake_offline


def test_arena_battle_mode_frozen():
    """SwarmGraphConfig is frozen (immutable)."""
    config = SwarmGraphConfig(arena_battle_mode=True)
    with pytest.raises(Exception):  # ValidationError or similar
        config.arena_battle_mode = False
