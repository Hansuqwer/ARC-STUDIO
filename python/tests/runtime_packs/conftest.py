"""Shared pytest configuration and fixtures for Runtime Pack SDK tests.

Filters the cosmetic Pydantic v2 UserWarning about field names that shadow
deprecated BaseModel methods (``validate``, ``schema``) — these field names are
required by the Runtime Pack manifest spec.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

# Suppress pydantic UserWarning: field name 'validate'/'schema' shadows parent
warnings.filterwarnings(
    "ignore",
    message=r"Field name .* shadows an attribute in parent",
    category=UserWarning,
)

from agent_runtime_cockpit.runtime_packs import (  # noqa: E402
    MANIFEST_FILENAME,
    RUNTIME_PACK_SCHEMA_VERSION,
    OpaqueNodePolicy,
    RuntimeCapability,
    RuntimeIdentity,
    RuntimeIrDeclaration,
    RuntimeKind,
    RuntimePackManifest,
    manifest_hash,
)

# ── Re-usable manifest builders ───────────────────────────────────────────────


def _pin(m: RuntimePackManifest) -> RuntimePackManifest:
    """Recompute and pin manifest_hash in place."""
    m.manifest_hash = manifest_hash(m)
    return m


def make_minimal_manifest() -> RuntimePackManifest:
    """A valid, hash-pinned, zero-risk manifest for acme.minimal-runtime."""
    m = RuntimePackManifest(
        schema_version=RUNTIME_PACK_SCHEMA_VERSION,
        id="acme.minimal-runtime",
        name="Acme Minimal Runtime",
        version="0.1.0",
        description="Minimal runtime for testing.",
        runtime=RuntimeIdentity(
            runtime_name="AcmeRuntime",
            runtime_kind=RuntimeKind.AGENT,
            language="python",
        ),
    )
    return _pin(m)


def make_ir_manifest() -> RuntimePackManifest:
    """A valid, hash-pinned manifest that declares IR export at version 1."""
    m = RuntimePackManifest(
        schema_version=RUNTIME_PACK_SCHEMA_VERSION,
        id="acme.ir-runtime",
        name="Acme IR Runtime",
        version="1.0.0",
        description="A runtime that can export SwarmGraph IR.",
        runtime=RuntimeIdentity(
            runtime_name="AcmeIRRuntime",
            runtime_kind=RuntimeKind.GRAPH,
            language="python",
        ),
        ir=RuntimeIrDeclaration(
            can_export_ir=True,
            supported_ir_version=1,
            opaque_node_policy=OpaqueNodePolicy.REJECT,
        ),
        capabilities=[
            RuntimeCapability(
                name="export_graph",
                reads=True,
                replayable=True,
                auditable=True,
            )
        ],
    )
    return _pin(m)


# ── Pytest fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def minimal_manifest() -> RuntimePackManifest:
    return make_minimal_manifest()


@pytest.fixture()
def ir_manifest() -> RuntimePackManifest:
    return make_ir_manifest()


@pytest.fixture()
def tmp_pack_dir(tmp_path: Path) -> Path:
    """A fresh temporary directory for scaffold / registry tests."""
    return tmp_path / "pack"


@pytest.fixture()
def manifest_file(tmp_path: Path) -> Path:
    """Write the minimal manifest to a temp file and return the path."""
    m = make_minimal_manifest()
    p = tmp_path / MANIFEST_FILENAME
    p.write_text(json.dumps(m.model_dump(mode="json"), indent=2), encoding="utf-8")
    return p


@pytest.fixture()
def workspace_dir(tmp_path: Path) -> Path:
    """A temporary workspace root (simulates a project dir)."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws
