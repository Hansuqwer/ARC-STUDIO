"""Isolation providers — execution boundary abstraction (ADR-006)."""

from .base import IsolationProvider, IsolationResult
from .none import NoneIsolationProvider
from .selector import (
    BACKENDS,
    build_execution_provider,
    build_isolation_provider,
    resolve_isolation_backend,
)
from .subprocess import SubprocessIsolationProvider
from .vz_provider import VZNoNetworkProof, VZProofResult, generate_vz_proof_artifacts

__all__ = [
    "BACKENDS",
    "IsolationProvider",
    "IsolationResult",
    "NoneIsolationProvider",
    "SubprocessIsolationProvider",
    "VZNoNetworkProof",
    "VZProofResult",
    "build_execution_provider",
    "build_isolation_provider",
    "generate_vz_proof_artifacts",
    "resolve_isolation_backend",
]
